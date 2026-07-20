import logging
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.exam_session import ExamSessionCreate, ExamSessionUpdate, ExamSessionResponse
from app.repositories.exam_session_repository import ExamSessionRepository
from app.repositories.exam_repository import ExamRepository
from app.repositories.user_repository import UserRepository
from app.repositories.exceptions import EntityNotFoundError
from app.services.exceptions import AuthorizationError

logger = logging.getLogger(__name__)

class ExamSessionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.session_repo = ExamSessionRepository(db)
        self.exam_repo = ExamRepository(db)
        self.user_repo = UserRepository(db)

    async def create_session(self, session_in: ExamSessionCreate) -> ExamSessionResponse:
        # Validate Exam
        exam = await self.exam_repo.get_by_id(session_in.exam_id)
        if not exam:
            raise EntityNotFoundError(f"Exam {session_in.exam_id} not found.")

        # Validate Student
        student = await self.user_repo.get_by_id(session_in.student_id)
        if not student:
            raise EntityNotFoundError(f"Student {session_in.student_id} not found.")

        if not student.role or student.role.name != "Student":
            raise ValueError(f"User {session_in.student_id} is not a Student.")

        # Validate Unique active session
        existing = await self.session_repo.get_by_student_and_exam(session_in.student_id, session_in.exam_id)
        if existing:
            raise ValueError(f"Student {session_in.student_id} already has a session for Exam {session_in.exam_id}.")

        # Create
        created_obj = await self.session_repo.create(
            exam_id=session_in.exam_id,
            student_id=session_in.student_id,
            status="PENDING"
        )
        return ExamSessionResponse.model_validate(created_obj)

    async def get_session(self, session_id: int) -> ExamSessionResponse:
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            raise EntityNotFoundError(f"ExamSession {session_id} not found.")
        return ExamSessionResponse.model_validate(session)

    async def get_all_sessions(
        self,
        skip: int = 0,
        limit: int = 100,
        exam_id: Optional[int] = None,
        student_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[ExamSessionResponse]:
        sessions = await self.session_repo.get_all(
            skip=skip,
            limit=limit,
            exam_id=exam_id,
            student_id=student_id,
            status=status
        )
        return [ExamSessionResponse.model_validate(s) for s in sessions]

    async def update_session(self, session_id: int, session_in: ExamSessionUpdate) -> ExamSessionResponse:
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            raise EntityNotFoundError(f"ExamSession {session_id} not found.")

        update_data = session_in.model_dump(exclude_unset=True)
        updated_obj = await self.session_repo.update(session, **update_data)
        return ExamSessionResponse.model_validate(updated_obj)

    async def update_status(self, session_id: int, new_status: str) -> ExamSessionResponse:
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            raise EntityNotFoundError(f"ExamSession {session_id} not found.")
            
        valid_transitions = {
            "PENDING": ["RUNNING", "CANCELLED"],
            "RUNNING": ["COMPLETED", "PAUSED"],
            "PAUSED": ["RUNNING", "COMPLETED"],
            "COMPLETED": [],
            "CANCELLED": []
        }
        
        if new_status not in valid_transitions.get(session.status, []):
            raise ValueError(f"Invalid status transition from {session.status} to {new_status}")
            
        update_data = {"status": new_status}
        if new_status == "RUNNING" and session.start_time is None:
            update_data["start_time"] = datetime.now(timezone.utc)
        elif new_status in ["COMPLETED", "CANCELLED"] and session.end_time is None:
            update_data["end_time"] = datetime.now(timezone.utc)
            
        updated_obj = await self.session_repo.update(session, **update_data)
        return ExamSessionResponse.model_validate(updated_obj)

    async def delete_session(self, session_id: int) -> None:
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            raise EntityNotFoundError(f"ExamSession {session_id} not found.")
            
        if session.status in ["RUNNING", "PAUSED"]:
            raise ValueError("Cannot delete an active exam session.")
            
        await self.session_repo.delete(session_id)

    # --- CANDIDATE RUNTIME METHODS ---
    
    async def enforce_active_runtime(self, exam_id: int, user_id: int) -> ExamSessionResponse:
        existing = await self.session_repo.get_by_student_and_exam(user_id, exam_id)
        if not existing:
            raise EntityNotFoundError("Session not found.")
            
        if existing.status != "RUNNING":
            raise ValueError(f"Exam session is not active. Status: {existing.status}")
            
        if existing.start_time and existing.exam:
            current_time = datetime.now(timezone.utc)
            start_time = existing.start_time
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)
                
            elapsed = (current_time - start_time).total_seconds()
            allowed = existing.exam.duration_minutes * 60
            
            # Allow a small grace period (e.g. 5 seconds) for network latency
            if elapsed > allowed + 5:
                await self.submit_runtime_session(exam_id, user_id)
                raise ValueError("Exam session has expired and was automatically submitted.")
                
        return existing


    async def start_runtime_session(self, exam_id: int, user_id: int) -> dict:
        from app.models.exam import Exam
        from sqlalchemy import select
        
        # Verify Exam
        exam = await self.exam_repo.get_by_id(exam_id)
        if not exam:
            raise EntityNotFoundError("Exam not found.")
            
        if exam.status not in ["READY", "RUNNING"]:
            raise ValueError(f"Exam is not ready to be taken. Status: {exam.status}")

        # Check existing session (Recovery)
        existing = await self.session_repo.get_by_student_and_exam(user_id, exam_id)
        
        current_time = datetime.now(timezone.utc)
        
        target_session = existing
        
        if existing:
            if existing.status == "COMPLETED":
                raise ValueError("You have already completed this exam.")
                
            # Session Recovery
            if existing.status == "PENDING":
                existing.status = "RUNNING"
                existing.start_time = current_time
                await self.db.commit()
                
            from app.services.runtime_state_service import RuntimeStateService
            runtime_service = RuntimeStateService(self.db)
            await runtime_service.initialize_state(existing.id)
            # Re-fetch to get eager loaded relations if necessary
            target_session = await self.session_repo.get_by_id(existing.id)
        else:
            raise ValueError("You are not assigned to this exam.")
            
        start_time = target_session.start_time
        if start_time and start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
            
        elapsed = (current_time - start_time).total_seconds() if start_time else 0
        time_left = max(0, int((exam.duration_minutes * 60) - elapsed))

        # AI Orchestration Integration
        try:
            from app.services.ai_session_manager import AISessionManager
            import json
            user = await self.user_repo.get_by_id(user_id)
            ref_embedding = json.loads(user.face_embedding) if user and user.face_embedding else None
            AISessionManager.initialize_session(target_session.id, user_id, reference_embedding=ref_embedding)
            AISessionManager.start_session(target_session.id)
        except Exception as e:
            logger.error(f"Failed to start AI session for ExamSession {target_session.id}: {e}")

        # Build Runtime Payload
        mode = "FILE"
        if exam.question_paper and exam.question_paper.mode:
            mode = exam.question_paper.mode

        payload = {
            "session": ExamSessionResponse.model_validate(target_session).model_dump(),
            "time_left_seconds": time_left,
            "mode": mode,
            "exam_config": {
                "duration_minutes": exam.duration_minutes,
                "title": exam.title
            }
        }

        if mode == "FILE":
            payload["file_url"] = f"/runtime/file?exam_id={exam.id}"
        else:
            sections_data = []
            sorted_sections = sorted(exam.section_rules, key=lambda s: s.section_index)
            for sec in sorted_sections:
                sec_dict = {
                    "id": str(sec.id),
                    "section_index": sec.section_index,
                    "section_name": sec.section_name,
                    "section_type": sec.section_type,
                    "questions": []
                }
                sorted_questions = sorted(sec.question_rules, key=lambda q: q.question_index)
                for q in sorted_questions:
                    q_dict = {
                        "id": str(q.id),
                        "question_index": q.question_index,
                        "question_type": q.question_type,
                        "text": q.question_text or "No text provided.",
                        "options": [opt.option_text for opt in q.options]
                    }
                    sec_dict["questions"].append(q_dict)
                sections_data.append(sec_dict)
            payload["sections"] = sections_data

        return payload

    async def submit_runtime_session(self, exam_id: int, user_id: int) -> ExamSessionResponse:
        existing = await self.session_repo.get_by_student_and_exam(user_id, exam_id)
        if not existing:
            raise EntityNotFoundError("Session not found.")
            
        if existing.status == "COMPLETED":
            return ExamSessionResponse.model_validate(existing)
            
        existing.status = "COMPLETED"
        existing.end_time = datetime.now(timezone.utc)
        await self.db.commit()
        existing = await self.session_repo.get_by_id(existing.id)
        
        # AI Orchestration Integration
        try:
            from app.services.ai_session_manager import AISessionManager
            AISessionManager.stop_session(existing.id)
        except Exception as e:
            logger.error(f"Failed to stop AI session for ExamSession {existing.id}: {e}")
        
        return ExamSessionResponse.model_validate(existing)
