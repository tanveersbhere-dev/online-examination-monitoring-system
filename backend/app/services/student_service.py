import os
import uuid
import json
import logging
from datetime import datetime
import cv2
import numpy as np
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.user import User
from app.models.role import Role
from app.models.exam import Exam
from app.models.exam_session import ExamSession
from app.schemas.exam import ExamResponse
from app.schemas.student import StudentCreate, StudentUpdate, StudentResponse
from app.services.credential_service import CredentialService
from app.services.email_service import EmailService
from app.services.password_service import PasswordService
from app.services.exceptions import DuplicateStudentError, InvalidExamError, StudentRegistrationError

# AI Engine Integration
from ai_engine.features.face_identity.embedding_processor import EmbeddingIdentityProcessor
from ai_engine.features.face_identity.models import FaceIdentityConfig
from ai_engine.features.face_identity.exceptions import EmbeddingGenerationError

logger = logging.getLogger(__name__)

class StudentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_student_role_id(self) -> int:
        role = await self.db.execute(select(Role).filter_by(name="STUDENT"))
        role_obj = role.scalar_one_or_none()
        if not role_obj:
            raise StudentRegistrationError("STUDENT role is not seeded in the database.")
        return role_obj.id

    async def register_student_with_face(self, data: StudentCreate, face_image: UploadFile) -> StudentResponse:
        # 1. Validate Exam exists
        exam = await self.db.execute(select(Exam).filter_by(id=data.exam_id))
        exam_obj = exam.scalar_one_or_none()
        if not exam_obj:
            raise InvalidExamError(f"Exam ID {data.exam_id} does not exist.")
            
        # 2. Validate Duplicate Email
        existing_user = await self.db.execute(select(User).filter_by(email=data.email))
        if existing_user.scalar_one_or_none():
            raise DuplicateStudentError(f"Email {data.email} is already registered.")

        # 3. Generate Face Embedding
        try:
            image_bytes = await face_image.read()
            np_img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
            if np_img is None:
                raise StudentRegistrationError("Invalid image format.")
            
            # Save Image to disk
            os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
            filename = f"face_{uuid.uuid4().hex}_{face_image.filename}"
            filepath = os.path.join(settings.UPLOAD_DIR, filename)
            cv2.imwrite(filepath, np_img)
            
            config = FaceIdentityConfig(embedding_model_name="buffalo_l")
            processor = EmbeddingIdentityProcessor(config)
            processor.initialize()
            
            embedding_list = processor._extract_embedding(np_img, bbox=None)
            if not embedding_list:
                raise StudentRegistrationError("No face detected in the provided image.")
                
            embedding_json = json.dumps(embedding_list)
        except EmbeddingGenerationError as e:
            raise StudentRegistrationError(f"Embedding failure: {e}") from e
        except Exception as e:
            raise StudentRegistrationError(f"Failed to process face image: {e}") from e

        # 4. Generate Credentials
        creds = CredentialService.provision_credentials()
        password_hash = PasswordService.hash(creds.password)
        student_role_id = await self._get_student_role_id()

        # Start nested transaction for atomicity
        async with self.db.begin_nested():
            # 5. Create User
            new_user = User(
                role_id=student_role_id,
                full_name=data.full_name,
                father_name=data.father_name,
                email=data.email,
                password_hash=password_hash,
                is_active=True,
                username=creds.username,
                credential_expiry_date=data.credential_expiry_date,
                account_status="ACTIVE",
                face_image_path=filepath,
                face_embedding=embedding_json,
                embedding_version="v1",
                registration_timestamp=datetime.utcnow()
            )
            self.db.add(new_user)
            await self.db.flush()
            
            # 6. Create ExamSession linking Student to Exam
            new_session = ExamSession(
                exam_id=exam_obj.id,
                student_id=new_user.id,
                status="PENDING"
            )
            self.db.add(new_session)
            await self.db.flush()

            # 7. Send Email
            await EmailService.send_registration_email(
                recipient_email=data.email,
                student_name=data.full_name,
                exam_name=exam_obj.title,
                username=creds.username,
                password_plain=creds.password,
                exam_date=exam_obj.scheduled_start,
                expiry_date=data.credential_expiry_date
            )
            
            logger.info(f"Student {data.email} successfully registered with face enrolled.")
            return StudentResponse.model_validate(new_user)

    async def list_students(self, skip: int = 0, limit: int = 100) -> list[StudentResponse]:
        student_role_id = await self._get_student_role_id()
        result = await self.db.execute(select(User).filter_by(role_id=student_role_id).offset(skip).limit(limit))
        return [StudentResponse.model_validate(u) for u in result.scalars().all()]

    async def get_student(self, student_id: int) -> StudentResponse:
        student_role_id = await self._get_student_role_id()
        result = await self.db.execute(select(User).filter_by(id=student_id, role_id=student_role_id))
        user = result.scalar_one_or_none()
        if not user:
            raise StudentRegistrationError(f"Student {student_id} not found.")
        return StudentResponse.model_validate(user)

    async def get_student_exams(self, student_id: int) -> list[ExamResponse]:
        student_role_id = await self._get_student_role_id()
        result = await self.db.execute(select(User).filter_by(id=student_id, role_id=student_role_id))
        student = result.scalar_one_or_none()
        if not student:
            raise StudentRegistrationError(f"Student {student_id} not found.")
            
        result = await self.db.execute(
            select(Exam)
            .join(ExamSession, Exam.id == ExamSession.exam_id)
            .where(ExamSession.student_id == student_id)
            .where(Exam.status != "DRAFT")
        )
        exams = result.scalars().all()
        responses = []
        for e in exams:
            resp = ExamResponse.model_validate(e)
            resp.ai_session_status = "ACTIVE" if e.status in ["RUNNING", "PAUSED"] else "INACTIVE"
            responses.append(resp)
        return responses

    async def update_student(self, student_id: int, data: StudentUpdate) -> StudentResponse:
        student_role_id = await self._get_student_role_id()
        result = await self.db.execute(select(User).filter_by(id=student_id, role_id=student_role_id))
        user = result.scalar_one_or_none()
        if not user:
            raise StudentRegistrationError(f"Student {student_id} not found.")
            
        if data.full_name is not None: user.full_name = data.full_name
        if data.father_name is not None: user.father_name = data.father_name
        if data.account_status is not None:
            user.account_status = data.account_status
            if data.account_status in ["DISABLED", "EXPIRED", "INACTIVE"]:
                user.is_active = False
            else:
                user.is_active = True
                
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(user)
        return StudentResponse.model_validate(user)

    async def deactivate_student(self, student_id: int):
        await self.update_student(student_id, StudentUpdate(account_status="DISABLED"))
        logger.info(f"Student {student_id} deactivated (soft delete).")
