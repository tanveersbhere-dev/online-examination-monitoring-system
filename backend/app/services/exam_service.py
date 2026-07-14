import os
import uuid
import logging
from typing import List, Optional
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.exam_session import ExamSession

from app.core.config import settings
from app.models.exam import Exam
from app.repositories.exam_repository import ExamRepository
from app.repositories.question_paper_repository import QuestionPaperRepository
from app.repositories.exceptions import EntityNotFoundError
from app.services.ai_session_manager import AISessionManager
from app.services.exceptions import (
    ExamNotFoundError, 
    InvalidExamStateError, 
    ScheduleConflictError, 
    QuestionPaperError,
    AISessionError
)
from app.schemas.exam import ExamCreate, ExamUpdate, ExamResponse, QuestionPaperResponse

logger = logging.getLogger(__name__)

class ExamService:
    ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}

    def __init__(self, db: AsyncSession):
        self.db = db
        self.exam_repo = ExamRepository(db)
        self.paper_repo = QuestionPaperRepository(db)
        
        if not os.path.exists(settings.UPLOAD_DIR):
            os.makedirs(settings.UPLOAD_DIR)

    # --- QUESTION PAPER MANAGEMENT ---

    async def upload_paper(self, title: str, course_name: str, uploader_id: int, file: UploadFile) -> QuestionPaperResponse:
        try:
            _, ext = os.path.splitext(file.filename)
            if ext.lower() not in self.ALLOWED_EXTENSIONS:
                raise QuestionPaperError(f"File type not allowed. Allowed types: {self.ALLOWED_EXTENSIONS}")

            unique_filename = f"{uuid.uuid4()}{ext}"
            file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)

            paper = await self.paper_repo.create(
                title=title,
                course_name=course_name,
                uploaded_by=uploader_id,
                file_path=file_path
            )
            
            logger.info(f"Question paper uploaded successfully: ID {paper.id}")
            return QuestionPaperResponse.model_validate(paper)
        except Exception as e:
            logger.error(f"Failed to upload question paper: {e}")
            raise QuestionPaperError("Failed to upload question paper.") from e

    async def get_all_papers(self, skip: int = 0, limit: int = 100) -> List[QuestionPaperResponse]:
        papers = await self.paper_repo.get_all(skip=skip, limit=limit)
        return [QuestionPaperResponse.model_validate(p) for p in papers]

    async def get_paper(self, paper_id: int) -> QuestionPaperResponse:
        paper = await self.paper_repo.get_by_id(paper_id)
        if not paper:
            raise EntityNotFoundError(f"QuestionPaper {paper_id} not found.")
        return QuestionPaperResponse.model_validate(paper)

    async def delete_paper(self, paper_id: int) -> None:
        paper = await self.paper_repo.get_by_id(paper_id)
        if not paper:
            raise EntityNotFoundError(f"QuestionPaper {paper_id} not found.")

        if os.path.exists(paper.file_path):
            os.remove(paper.file_path)

        await self.paper_repo.delete(paper_id)
        logger.info(f"Question paper deleted: ID {paper_id}")

    # --- EXAM LIFECYCLE MANAGEMENT ---

    async def create_exam(self, creator_id: int, exam_in: ExamCreate) -> ExamResponse:
        paper = await self.paper_repo.get_by_id(exam_in.question_paper_id)
        if not paper:
            raise QuestionPaperError(f"Question Paper {exam_in.question_paper_id} does not exist.")

        await self._check_schedule_conflict(
            course_name=exam_in.course_name,
            start=exam_in.scheduled_start,
            end=exam_in.scheduled_end
        )

        exam = await self.exam_repo.create(
            title=exam_in.title,
            course_name=exam_in.course_name,
            question_paper_id=exam_in.question_paper_id,
            scheduled_start=exam_in.scheduled_start,
            scheduled_end=exam_in.scheduled_end,
            duration_minutes=exam_in.duration_minutes,
            created_by=creator_id,
            status="DRAFT"
        )
        
        logger.info(f"Exam created successfully: ID {exam.id}")
        return ExamResponse.model_validate(exam)

    async def _check_schedule_conflict(self, course_name, start, end, exclude_exam_id=None):
        query = select(Exam).filter(
            Exam.course_name == course_name,
            Exam.status.notin_(["CANCELLED", "COMPLETED"]),
            Exam.scheduled_start < end,
            Exam.scheduled_end > start
        )
        if exclude_exam_id:
            query = query.filter(Exam.id != exclude_exam_id)
            
        result = await self.db.execute(query)
        conflicts = result.scalars().all()
        if conflicts:
            raise ScheduleConflictError(f"Exam scheduling conflicts with existing exam(s) for course {course_name}.")

    async def get_exam(self, exam_id: int) -> ExamResponse:
        try:
            exam = await self.exam_repo.get_by_id(exam_id)
            if not exam:
                raise ExamNotFoundError(f"Exam {exam_id} not found.")
            resp = ExamResponse.model_validate(exam)
            
            # Get assigned students count
            count_result = await self.db.execute(select(func.count(ExamSession.id)).where(ExamSession.exam_id == exam_id))
            resp.assigned_students_count = count_result.scalar() or 0
            
            resp.ai_session_status = "ACTIVE" if exam.status in ["RUNNING", "PAUSED"] else "INACTIVE"
            return resp
        except EntityNotFoundError:
            raise ExamNotFoundError(f"Exam {exam_id} not found.")

    async def get_all_exams(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        course_name: Optional[str] = None, 
        status: Optional[str] = None
    ) -> List[ExamResponse]:
        exams = await self.exam_repo.get_all(skip=skip, limit=limit, course_name=course_name, status=status)
        
        # Get assigned students counts
        counts = await self.db.execute(select(ExamSession.exam_id, func.count(ExamSession.id)).group_by(ExamSession.exam_id))
        count_map = {row[0]: row[1] for row in counts.all()}
        
        responses = []
        for e in exams:
            resp = ExamResponse.model_validate(e)
            resp.assigned_students_count = count_map.get(e.id, 0)
            resp.ai_session_status = "ACTIVE" if e.status in ["RUNNING", "PAUSED"] else "INACTIVE"
            responses.append(resp)
        return responses

    async def get_upcoming_exams(self, skip: int = 0, limit: int = 100) -> List[ExamResponse]:
        from datetime import datetime, timezone
        current_time = datetime.now(timezone.utc)
        exams = await self.exam_repo.get_upcoming_exams(current_time=current_time, skip=skip, limit=limit)
        
        # Get assigned students counts
        counts = await self.db.execute(select(ExamSession.exam_id, func.count(ExamSession.id)).group_by(ExamSession.exam_id))
        count_map = {row[0]: row[1] for row in counts.all()}
        
        responses = []
        for e in exams:
            resp = ExamResponse.model_validate(e)
            resp.assigned_students_count = count_map.get(e.id, 0)
            resp.ai_session_status = "ACTIVE" if e.status in ["RUNNING", "PAUSED"] else "INACTIVE"
            responses.append(resp)
        return responses

    async def update_exam(self, exam_id: int, exam_in: ExamUpdate) -> ExamResponse:
        exam = await self.exam_repo.get_by_id(exam_id)
        if not exam:
            raise ExamNotFoundError(f"Exam {exam_id} not found.")
            
        if exam.status not in ["DRAFT", "SCHEDULED"]:
            raise InvalidExamStateError("Cannot update exam configurations once it is ready or running.")

        update_data = exam_in.model_dump(exclude_unset=True)
        new_start = update_data.get('scheduled_start', exam.scheduled_start)
        new_end = update_data.get('scheduled_end', exam.scheduled_end)
        
        if 'scheduled_start' in update_data or 'scheduled_end' in update_data:
            if new_end <= new_start:
                raise ValueError("scheduled_end must be after scheduled_start")
            await self._check_schedule_conflict(
                course_name=exam.course_name,
                start=new_start,
                end=new_end,
                exclude_exam_id=exam.id
            )

        updated_exam = await self.exam_repo.update(exam, **update_data)
        logger.info(f"Exam updated: ID {exam_id}")
        return ExamResponse.model_validate(updated_exam)

    async def delete_exam(self, exam_id: int) -> None:
        exam = await self.exam_repo.get_by_id(exam_id)
        if not exam:
            raise ExamNotFoundError(f"Exam {exam_id} not found.")
            
        if exam.status in ["READY", "RUNNING", "PAUSED"]:
            raise InvalidExamStateError("Cannot delete an exam that is currently active or ready. Cancel it first.")
            
        await self.exam_repo.delete(exam_id)
        logger.info(f"Exam deleted: ID {exam_id}")

    async def assign_students(self, exam_id: int, student_ids: List[int]) -> int:
        exam = await self.exam_repo.get_by_id(exam_id)
        if not exam:
            raise ExamNotFoundError(f"Exam {exam_id} not found.")
            
        # Get existing sessions to avoid duplicates
        existing_sessions_result = await self.db.execute(select(ExamSession.student_id).where(ExamSession.exam_id == exam_id))
        existing_student_ids = set(existing_sessions_result.scalars().all())
        
        new_student_ids = [sid for sid in student_ids if sid not in existing_student_ids]
        
        for sid in new_student_ids:
            new_session = ExamSession(exam_id=exam_id, student_id=sid)
            self.db.add(new_session)
            
        await self.db.commit()
        return len(new_student_ids)

    # --- AI ORCHESTRATION & STATE MANAGEMENT ---

    async def _change_status(self, exam_id: int, new_status: str) -> ExamResponse:
        exam = await self.exam_repo.get_by_id(exam_id)
        if not exam:
            raise ExamNotFoundError(f"Exam {exam_id} not found.")
        updated_exam = await self.exam_repo.update(exam, status=new_status)
        
        resp = ExamResponse.model_validate(updated_exam)
        resp.ai_session_status = "ACTIVE" if updated_exam.status in ["RUNNING", "PAUSED"] else "INACTIVE"
        return resp

    async def start_exam(self, exam_id: int, student_id: int) -> ExamResponse:
        exam = await self.exam_repo.get_by_id(exam_id)
        if not exam:
            raise ExamNotFoundError(f"Exam {exam_id} not found.")
        if exam.status not in ["DRAFT", "SCHEDULED", "READY"]:
            raise InvalidExamStateError(f"Cannot start exam from state {exam.status}.")

        try:
            # AI Orchestration
            AISessionManager.initialize_session(exam.id, student_id)
            AISessionManager.start_session(exam.id)
            return await self._change_status(exam.id, "RUNNING")
        except Exception as e:
            logger.error(f"Failed to start AI Session for exam {exam_id}: {e}")
            raise AISessionError("Failed to start AI Session.") from e

    async def pause_exam(self, exam_id: int) -> ExamResponse:
        exam = await self.exam_repo.get_by_id(exam_id)
        if not exam or exam.status != "RUNNING":
            raise InvalidExamStateError("Only RUNNING exams can be paused.")
            
        try:
            AISessionManager.pause_session(exam.id)
            return await self._change_status(exam.id, "PAUSED")
        except Exception as e:
            logger.error(f"Failed to pause AI Session for exam {exam_id}: {e}")
            raise AISessionError("Failed to pause AI Session.") from e

    async def resume_exam(self, exam_id: int) -> ExamResponse:
        exam = await self.exam_repo.get_by_id(exam_id)
        if not exam or exam.status != "PAUSED":
            raise InvalidExamStateError("Only PAUSED exams can be resumed.")
            
        try:
            AISessionManager.resume_session(exam.id)
            return await self._change_status(exam.id, "RUNNING")
        except Exception as e:
            logger.error(f"Failed to resume AI Session for exam {exam_id}: {e}")
            raise AISessionError("Failed to resume AI Session.") from e

    async def complete_exam(self, exam_id: int) -> ExamResponse:
        exam = await self.exam_repo.get_by_id(exam_id)
        if not exam or exam.status not in ["RUNNING", "PAUSED"]:
            raise InvalidExamStateError("Only RUNNING or PAUSED exams can be completed.")
            
        try:
            AISessionManager.stop_session(exam.id)
            return await self._change_status(exam.id, "COMPLETED")
        except Exception as e:
            logger.error(f"Failed to stop AI Session for exam {exam_id}: {e}")
            raise AISessionError("Failed to cleanly stop AI Session.") from e
