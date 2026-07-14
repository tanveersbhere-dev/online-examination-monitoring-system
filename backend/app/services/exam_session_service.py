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
