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

    async def update_student(self, student_id: int, data: StudentRepoUpdate) -> Student:
        student = await self.get_student(student_id)
        if not student:
            raise ValueError("Student not found.")
            
        update_data = data.model_dump(exclude_unset=True)
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
        # Soft delete
        student.status = "ARCHIVED"
        await self._log_activity("STUDENT_ARCHIVED", f"Archived student {student.full_name}", student.id)
        await self.db.commit()

    async def bulk_action(self, student_ids: List[int], action: str):
        result = await self.db.execute(
            select(Student).where(Student.examiner_id == self.examiner_id, Student.id.in_(student_ids))
        )
        students = result.scalars().all()
        
        for student in students:
            if action == "ARCHIVE":
                student.status = "ARCHIVED"
            elif action == "RESTORE":
                student.status = "PENDING" # or whatever is default
            elif action == "ACTIVATE":
                student.status = "ACTIVE"
        
        await self._log_activity(f"BULK_{action}", f"Performed {action} on {len(students)} students")
        await self.db.commit()

    async def preview_import(self, file_content: str) -> ImportPreviewResponse:
        reader = csv.DictReader(io.StringIO(file_content))
        valid_data = []
        conflicts = []
        
        # Load all existing reg numbers for fast lookup
        result = await self.db.execute(select(Student.registration_number).where(Student.examiner_id == self.examiner_id))
        existing_regs = {r for r in result.scalars().all()}

        for idx, row in enumerate(reader, start=1):
            reg_num = row.get("registration_number", "").strip()
            email = row.get("email", "").strip()
            name = row.get("full_name", "").strip()
            
            if not reg_num or not name or not email:
                conflicts.append(ImportConflict(
                    row_index=idx, registration_number=reg_num, reason="Missing required fields", suggested_resolution="Fix CSV"
                ))
                continue
                
            if reg_num in existing_regs:
                conflicts.append(ImportConflict(
                    row_index=idx, registration_number=reg_num, reason="Duplicate registration number", suggested_resolution="Skip or Update"
                ))
            else:
                semester_str = row.get("semester", "")
                semester = int(semester_str) if semester_str.isdigit() else None
                valid_data.append(StudentImportRow(
                    registration_number=reg_num,
                    full_name=name,
                    email=email,
                    phone=row.get("phone", "").strip() or None,
                    roll_number=row.get("roll_number", "").strip() or None,
                    department=row.get("department", "").strip() or None,
                    program=row.get("program", "").strip() or None,
                    semester=semester,
                    batch=row.get("batch", "").strip() or None,
                    section=row.get("section", "").strip() or None
                ))

        return ImportPreviewResponse(
            total_rows=idx,
            valid_rows=len(valid_data),
            duplicates=len([c for c in conflicts if "Duplicate" in c.reason]),
            conflicts=conflicts,
            valid_data=valid_data
        )

    async def confirm_import(self, students: List[StudentImportRow]):
        added = 0
        for st in students:
            # Check just in case
            existing = await self.db.execute(
                select(Student).where(Student.examiner_id == self.examiner_id, Student.registration_number == st.registration_number)
            )
            if not existing.scalar_one_or_none():
                new_student = Student(examiner_id=self.examiner_id, **st.model_dump())
                self.db.add(new_student)
                added += 1
                
        await self._log_activity("STUDENT_IMPORTED", f"Imported {added} students")
        await self.db.commit()
