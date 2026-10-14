import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import EmailStr

from app.database.session import get_db
from app.security.permissions import RequireExaminer
from app.security.dependencies import get_current_user
from app.schemas.user_auth import UserResponse
from app.schemas.student import StudentCreate, StudentUpdate, StudentResponse
from app.schemas.exam import ExamResponse
from app.services.student_service import StudentService
from app.services.exceptions import StudentRegistrationError, DuplicateStudentError, InvalidExamError, EmailDeliveryError

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/register", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
async def register_student(
    full_name: str = Form(...),
    email: EmailStr = Form(...),
    exam_id: int = Form(...),
    father_name: Optional[str] = Form(None),
    credential_expiry_date: Optional[datetime] = Form(None),
    face_image: UploadFile = File(...),
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """Register a new student, bind them to an exam, process face image, generate credentials, and send email."""
    try:
        student_in = StudentCreate(
            full_name=full_name,
            email=email,
            exam_id=exam_id,
            father_name=father_name,
            credential_expiry_date=credential_expiry_date
        )
        service = StudentService(db)
        return await service.register_student_with_face(student_in, face_image)
    except DuplicateStudentError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except InvalidExamError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except EmailDeliveryError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    except StudentRegistrationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/me/exams", response_model=List[ExamResponse])
async def get_my_exams(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve exams assigned to the authenticated student."""
    service = StudentService(db)
    return await service.get_student_exams(current_user.id)

@router.get("", response_model=List[StudentResponse])
async def list_students(
    skip: int = 0,
    limit: int = 100,
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """List all registered students."""
    service = StudentService(db)
    return await service.list_students(skip=skip, limit=limit)

@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(
    student_id: int,
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve student details."""
    try:
        service = StudentService(db)
        return await service.get_student(student_id)
    except StudentRegistrationError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.put("/{student_id}", response_model=StudentResponse)
async def update_student(
    student_id: int,
    student_in: StudentUpdate,
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """Update student information."""
    try:
        service = StudentService(db)
        return await service.update_student(student_id, student_in)
    except StudentRegistrationError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_student(
    student_id: int,
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """Deactivate the student account (soft delete)."""
    try:
        service = StudentService(db)
        await service.deactivate_student(student_id)
    except StudentRegistrationError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
