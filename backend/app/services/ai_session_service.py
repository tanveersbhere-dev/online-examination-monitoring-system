import logging
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.ai_session import AISessionCreate, AISessionUpdate, AISessionResponse
from app.repositories.ai_session_repository import AISessionRepository
from app.repositories.exam_session_repository import ExamSessionRepository
from app.services.ai_session_manager import AISessionManager
from app.repositories.exceptions import EntityNotFoundError
from app.services.exceptions import AuthorizationError

logger = logging.getLogger(__name__)

class AISessionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_repo = AISessionRepository(db)
        self.exam_session_repo = ExamSessionRepository(db)

    async def start_session(self, session_in: AISessionCreate) -> AISessionResponse:
        # Validate ExamSession
        exam_session = await self.exam_session_repo.get_by_id(session_in.exam_session_id)
        if not exam_session:
            raise EntityNotFoundError(f"ExamSession {session_in.exam_session_id} not found.")

        if exam_session.status != "RUNNING":
            raise ValueError("ExamSession must be RUNNING to start AI monitoring.")

        # Validate no active duplicate AI session
        if exam_session.ai_session_id is not None:
            raise ValueError(f"ExamSession {session_in.exam_session_id} already has an AI session.")

        # Create AI Session DB Entry
        ai_session = await self.ai_repo.create(
            state="RUNNING",
            started_at=datetime.now(timezone.utc)
        )

        # Link ExamSession to AI Session
        await self.exam_session_repo.update(exam_session, ai_session_id=ai_session.id)

        # Trigger background orchestrator
        # We pass exam_session_id to uniquely track the student attempt
        AISessionManager.initialize_session(exam_session_id=session_in.exam_session_id, student_id=exam_session.student_id)
        AISessionManager.start_session(exam_session_id=session_in.exam_session_id)

        # Fetch fully eager-loaded entity
        fetched = await self.ai_repo.get_by_id(ai_session.id)
        return AISessionResponse.model_validate(fetched)

    async def get_session(self, session_id: int) -> AISessionResponse:
        session = await self.ai_repo.get_by_id(session_id)
        if not session:
            raise EntityNotFoundError(f"AISession {session_id} not found.")
        return AISessionResponse.model_validate(session)

    async def get_all_sessions(self, skip: int = 0, limit: int = 100, state: Optional[str] = None) -> List[AISessionResponse]:
        sessions = await self.ai_repo.get_all(skip=skip, limit=limit, state=state)
        return [AISessionResponse.model_validate(s) for s in sessions]

    async def update_status(self, session_id: int, new_status: str) -> AISessionResponse:
        session = await self.ai_repo.get_by_id(session_id)
        if not session:
            raise EntityNotFoundError(f"AISession {session_id} not found.")

        valid_transitions = {
            "CREATED": ["RUNNING", "COMPLETED"],
            "RUNNING": ["PAUSED", "COMPLETED"],
            "PAUSED": ["RUNNING", "COMPLETED"],
            "COMPLETED": []
        }

        if new_status not in valid_transitions.get(session.state, []):
            raise ValueError(f"Invalid AI session status transition from {session.state} to {new_status}")

        update_data = {"state": new_status}
        if new_status == "RUNNING" and session.started_at is None:
            update_data["started_at"] = datetime.now(timezone.utc)
        elif new_status == "COMPLETED" and session.stopped_at is None:
            update_data["stopped_at"] = datetime.now(timezone.utc)

        updated_obj = await self.ai_repo.update(session, **update_data)

        # Notify backend manager
        exam_session_id = session.exam_session.id if session.exam_session else None
        if exam_session_id:
            if new_status == "PAUSED":
                AISessionManager.pause_session(exam_session_id)
            elif new_status == "RUNNING":
                AISessionManager.resume_session(exam_session_id)
            elif new_status == "COMPLETED":
                AISessionManager.stop_session(exam_session_id)

        return AISessionResponse.model_validate(updated_obj)

    async def delete_session(self, session_id: int) -> None:
        session = await self.ai_repo.get_by_id(session_id)
        if not session:
            raise EntityNotFoundError(f"AISession {session_id} not found.")
            
        if session.state in ["RUNNING", "PAUSED"]:
            raise ValueError("Cannot delete an active AI session.")
            
        await self.ai_repo.delete(session_id)
