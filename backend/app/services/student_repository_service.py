import csv
import io
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, desc
from typing import List, Tuple

from app.models.student import Student
from app.models.activity import Activity
from app.schemas.student_repository import (
    StudentRepoCreate, StudentRepoUpdate, StudentImportRow,
    ImportConflict, ImportPreviewResponse
)

logger = logging.getLogger(__name__)

class StudentRepositoryService:
    def __init__(self, db: AsyncSession, examiner_id: int):
        self.db = db
        self.examiner_id = examiner_id

    async def _log_activity(self, action_type: str, description: str, resource_id: int = None):
        activity = Activity(
            user_id=self.examiner_id,
            action_type=action_type,
            description=description,
            resource_type="Student",
            resource_id=resource_id
        )
        self.db.add(activity)

    async def list_students(
        self, skip: int = 0, limit: int = 100, search: str = None, status: str = None, department: str = None
    ) -> Tuple[List[Student], int]:
        query = select(Student).where(Student.examiner_id == self.examiner_id)
        
        if status:
            query = query.where(Student.status == status)
        if department:
            query = query.where(Student.department == department)
        if search:
            search_filter = or_(
                Student.registration_number.ilike(f"%{search}%"),
                Student.full_name.ilike(f"%{search}%"),
                Student.email.ilike(f"%{search}%"),
                Student.phone.ilike(f"%{search}%"),
                Student.roll_number.ilike(f"%{search}%")
            )
            query = query.where(search_filter)

        # Count total matches
        from sqlalchemy import func
        count_query = select(func.count()).select_from(query.subquery())
        total_count = (await self.db.execute(count_query)).scalar() or 0

        query = query.order_by(desc(Student.created_at)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total_count

    async def get_student(self, student_id: int) -> Student:
        result = await self.db.execute(
            select(Student).where(Student.id == student_id, Student.examiner_id == self.examiner_id)
        )
        return result.scalar_one_or_none()

    async def create_student(self, data: StudentRepoCreate) -> Student:
        # Check duplicate registration number
        existing = await self.db.execute(
            select(Student).where(Student.examiner_id == self.examiner_id, Student.registration_number == data.registration_number)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Registration number '{data.registration_number}' already exists in your repository.")

        new_student = Student(
            examiner_id=self.examiner_id,
            **data.model_dump()
        )
        self.db.add(new_student)
        await self.db.flush()
        
        await self._log_activity("STUDENT_CREATED", f"Added student {new_student.full_name}", new_student.id)
        await self.db.commit()
        await self.db.refresh(new_student)
        return new_student

    async def _process_face_image_bytes(self, image_bytes: bytes, filename: str) -> Tuple[Optional[str], Optional[str]]:
        """Optional face image processing using existing EmbeddingIdentityProcessor.
        If image is missing/invalid, returns (None, None) without failing student creation."""
        try:
            import cv2
            import numpy as np
            import uuid
            import os
            import json
            from app.monitoring_integration.face_embedding_service import FaceEmbeddingService

            np_img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
            if np_img is None:
                logger.warning(f"Could not decode image bytes for {filename}")
                return None, None

            os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
            save_name = f"ref_{uuid.uuid4().hex}_{filename}"
            filepath = os.path.join(settings.UPLOAD_DIR, save_name)
            cv2.imwrite(filepath, np_img)

            emb_service = FaceEmbeddingService.get_instance()
            embedding_list = emb_service.extract_embedding(np_img)
            if not embedding_list:
                logger.warning(f"No face detected in reference image {filename}")
                return filepath, None

            embedding_json = json.dumps(embedding_list)
            return filepath, embedding_json
        except Exception as e:
            logger.warning(f"Failed to process optional reference image {filename}: {e}")
            return None, None

    async def create_student_with_image(self, data: StudentRepoCreate, image_bytes: Optional[bytes] = None, image_filename: Optional[str] = None) -> Student:
        student = await self.create_student(data)
        if image_bytes and image_filename:
            filepath, embedding_json = await self._process_face_image_bytes(image_bytes, image_filename)
            if filepath or embedding_json:
                student.face_image_path = filepath
                student.face_embedding = embedding_json
                student.embedding_version = "v1"
                await self.db.commit()
                await self.db.refresh(student)
        return student

    async def update_student(self, student_id: int, data: StudentRepoUpdate) -> Student:
        from app.models.user import User

        student = await self.get_student(student_id)
        if not student:
            raise ValueError("Student not found.")
            
        old_email = student.email
        update_data = data.model_dump(exclude_unset=True)

        new_email = update_data.get("email")
        new_name = update_data.get("full_name")

        # Synchronize with linked candidate User account if it exists
        user_result = await self.db.execute(select(User).where(User.email == old_email))
        user = user_result.scalar_one_or_none()

        if user:
            if new_email and new_email != old_email:
                dup_result = await self.db.execute(
                    select(User).where(User.email == new_email, User.id != user.id)
                )
                if dup_result.scalar_one_or_none():
                    raise ValueError("User with this email already exists.")
                user.email = new_email

            if new_name and new_name != user.full_name:
                user.full_name = new_name

        for key, value in update_data.items():
            setattr(student, key, value)
            
        await self._log_activity("STUDENT_UPDATED", f"Updated student {student.full_name}", student.id)
        await self.db.commit()
        await self.db.refresh(student)
        return student

    async def delete_student(self, student_id: int):
        student = await self.get_student(student_id)
        if not student:
            raise ValueError("Student not found.")
        if student.status == "ARCHIVED":
            raise ValueError("This student is already archived.")
        # Soft delete
        student.status = "ARCHIVED"
        await self._log_activity("STUDENT_ARCHIVED", f"Archived student {student.full_name}", student.id)
        await self.db.commit()

    async def reactivate_student(self, student_id: int) -> Student:
        student = await self.get_student(student_id)
        if not student:
            raise ValueError("Student not found.")
        if student.status != "ARCHIVED":
            raise ValueError("This student is not archived.")
        student.status = "ACTIVE"
        await self._log_activity("STUDENT_REACTIVATED", f"Reactivated student {student.full_name}", student.id)
        await self.db.commit()
        await self.db.refresh(student)
        return student

    async def bulk_action(self, student_ids: List[int], action: str):
        result = await self.db.execute(
            select(Student).where(Student.examiner_id == self.examiner_id, Student.id.in_(student_ids))
        )
        students = result.scalars().all()

        if action == "ARCHIVE":
            unarchived = [s for s in students if s.status != "ARCHIVED"]
            if not unarchived:
                raise ValueError("This student is already archived.")
            for student in unarchived:
                student.status = "ARCHIVED"
            await self._log_activity(f"BULK_{action}", f"Performed {action} on {len(unarchived)} students")
            await self.db.commit()
        elif action == "REACTIVATE":
            archived = [s for s in students if s.status == "ARCHIVED"]
            if not archived:
                raise ValueError("None of the selected students are archived.")
            for student in archived:
                student.status = "ACTIVE"
            await self._log_activity("BULK_REACTIVATE", f"Reactivated {len(archived)} students")
            await self.db.commit()
        else:
            for student in students:
                if action == "RESTORE":
                    student.status = "PENDING"
                elif action == "ACTIVATE":
                    student.status = "ACTIVE"
            await self._log_activity(f"BULK_{action}", f"Performed {action} on {len(students)} students")
            await self.db.commit()

    async def preview_import(self, file_content: str) -> ImportPreviewResponse:
        # Strip potential UTF-8 BOM
        if file_content.startswith('\ufeff'):
            file_content = file_content[1:]

        if not file_content.strip():
            raise ValueError("The uploaded CSV file is empty. Please provide a valid CSV file with student records.")

        f_io = io.StringIO(file_content)
        reader = csv.DictReader(f_io)
        
        if not reader.fieldnames:
            raise ValueError("Could not read column headers from CSV. Please ensure the first row contains valid column headers.")

        # Clean raw headers
        raw_headers = [h.strip() for h in reader.fieldnames if h]
        if not raw_headers:
            raise ValueError("The CSV file header row is empty.")

        normalized_headers = {h.lower().replace(" ", "_"): h for h in raw_headers}

        # Canonical allowed columns mapping
        canonical_map = {
            "registration_number": "registration_number",
            "reg_no": "registration_number",
            "reg_num": "registration_number",
            "registration_no": "registration_number",
            "regnumber": "registration_number",
            
            "full_name": "full_name",
            "name": "full_name",
            "student_name": "full_name",
            
            "email": "email",
            "email_address": "email",
            
            "phone": "phone",
            "phone_number": "phone",
            "contact": "phone",
            "contact_no": "phone",
            
            "roll_number": "roll_number",
            "roll_no": "roll_number",
            
            "department": "department",
            "dept": "department",
            
            "program": "program",
            "semester": "semester",
            "batch": "batch",
            "section": "section",
            "photo_filename": "photo_filename"
        }

        # Detect unrecognized or additional columns
        unrecognized_cols = []
        for norm_h, orig_h in normalized_headers.items():
            if norm_h not in canonical_map:
                unrecognized_cols.append(orig_h)

        if unrecognized_cols:
            raise ValueError(
                f"The CSV file contains unrecognized or unexpected columns: [{', '.join(unrecognized_cols)}]. "
                f"Please remove these extra columns. Allowed columns are: "
                f"Required: [registration_number, full_name, email], "
                f"Optional: [phone, roll_number, department, program, semester, batch, section]."
            )

        # Check required columns
        active_canonical = {canonical_map[norm_h] for norm_h in normalized_headers if norm_h in canonical_map}
        missing_required = []
        for req in ["registration_number", "full_name", "email"]:
            if req not in active_canonical:
                missing_required.append(req)

        if missing_required:
            raise ValueError(
                f"The CSV file is missing required column(s): [{', '.join(missing_required)}]. "
                f"Required format: [registration_number], [full_name], and [email]."
            )

        valid_data = []
        conflicts = []
        
        # Load all existing reg numbers for fast lookup
        result = await self.db.execute(select(Student.registration_number).where(Student.examiner_id == self.examiner_id))
        existing_regs = {r for r in result.scalars().all()}
        seen_in_batch = set()

        idx = 0
        for raw_row in reader:
            idx += 1
            # Normalize row keys
            row = {}
            for k, v in raw_row.items():
                if k:
                    norm_k = k.strip().lower().replace(" ", "_")
                    canonical_k = canonical_map.get(norm_k, norm_k)
                    row[canonical_k] = (v or "").strip()

            reg_num = row.get("registration_number", "")
            email = row.get("email", "")
            name = row.get("full_name", "")
            
            if not reg_num or not name or not email:
                conflicts.append(ImportConflict(
                    row_index=idx, 
                    registration_number=reg_num or "N/A", 
                    reason="Missing required fields (registration_number, full_name, or email)", 
                    suggested_resolution="Complete missing student information in CSV"
                ))
                continue
                
            if reg_num in existing_regs:
                conflicts.append(ImportConflict(
                    row_index=idx, 
                    registration_number=reg_num, 
                    reason="Registration number already exists in your repository", 
                    suggested_resolution="Duplicate entry skipped"
                ))
            elif reg_num in seen_in_batch:
                conflicts.append(ImportConflict(
                    row_index=idx, 
                    registration_number=reg_num, 
                    reason="Duplicate registration number within this CSV file", 
                    suggested_resolution="Remove duplicate row from CSV"
                ))
            else:
                seen_in_batch.add(reg_num)
                semester_str = row.get("semester", "")
                semester = int(semester_str) if semester_str.isdigit() else None
                valid_data.append(StudentImportRow(
                    registration_number=reg_num,
                    full_name=name,
                    email=email,
                    phone=row.get("phone", "") or None,
                    roll_number=row.get("roll_number", "") or None,
                    department=row.get("department", "") or None,
                    program=row.get("program", "") or None,
                    semester=semester,
                    batch=row.get("batch", "") or None,
                    section=row.get("section", "") or None,
                    photo_filename=None
                ))

        if idx == 0:
            raise ValueError("The CSV file contains column headers but no student data rows.")

        return ImportPreviewResponse(
            total_rows=idx,
            valid_rows=len(valid_data),
            duplicates=len([c for c in conflicts if "already exists" in c.reason or "within this CSV" in c.reason]),
            conflicts=conflicts,
            valid_data=valid_data
        )

    async def confirm_import(self, students: List[StudentImportRow], zip_bytes: Optional[bytes] = None):
        import zipfile

        zip_files_dict = {}
        if zip_bytes:
            try:
                with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                    for filename in zf.namelist():
                        basename = os.path.basename(filename)
                        if basename and not filename.endswith('/'):
                            zip_files_dict[basename.lower()] = zf.read(filename)
            except Exception as e:
                logger.warning(f"Failed to extract ZIP archive: {e}")

        added = 0
        for st in students:
            existing = await self.db.execute(
                select(Student).where(Student.examiner_id == self.examiner_id, Student.registration_number == st.registration_number)
            )
            if not existing.scalar_one_or_none():
                st_dict = st.model_dump(exclude={"photo_filename"})
                new_student = Student(examiner_id=self.examiner_id, **st_dict)
                self.db.add(new_student)
                await self.db.flush()

                if st.photo_filename and zip_files_dict:
                    fn_key = os.path.basename(st.photo_filename).lower()
                    if fn_key in zip_files_dict:
                        img_bytes = zip_files_dict[fn_key]
                        filepath, embedding_json = await self._process_face_image_bytes(img_bytes, fn_key)
                        if filepath or embedding_json:
                            new_student.face_image_path = filepath
                            new_student.face_embedding = embedding_json
                            new_student.embedding_version = "v1"

                added += 1
                
        await self._log_activity("STUDENT_IMPORTED", f"Imported {added} students")
        await self.db.commit()
