import logging
from typing import List, Optional, Any
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.models.ai_session import AISession
from app.models.exam_session import ExamSession
from app.models.user import User
from app.models.exam import Exam
from app.repositories.base_repository import BaseRepository
from app.repositories.exceptions import DatabaseOperationError, TransactionError

logger = logging.getLogger(__name__)

class AISessionRepository(BaseRepository[AISession]):
    def __init__(self, db: AsyncSession):
        super().__init__(AISession, db)

    def _base_query(self):
        """Returns a base query with explicit eager loading of the parent ExamSession and its dependencies."""
        return select(AISession).options(
            joinedload(AISession.exam_session).joinedload(ExamSession.exam).joinedload(Exam.question_paper),
            joinedload(AISession.exam_session).joinedload(ExamSession.student).joinedload(User.role)
        )

    async def get_by_id(self, id: int) -> Optional[AISession]:
        try:
            result = await self.db.execute(self._base_query().filter(AISession.id == id))
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching AISession by id {id}: {e}")
            raise DatabaseOperationError(f"Failed to fetch AISession by id.") from e

    async def get_by_uuid(self, session_uuid: str) -> Optional[AISession]:
        try:
            result = await self.db.execute(self._base_query().filter(AISession.session_uuid == session_uuid))
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching AISession by uuid {session_uuid}: {e}")
            raise DatabaseOperationError(f"Failed to fetch AISession by uuid.") from e

    async def get_by_exam_session_id(self, exam_session_id: int) -> Optional[AISession]:
        try:
            result = await self.db.execute(
                self._base_query().join(AISession.exam_session).filter(ExamSession.id == exam_session_id)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching AISession by exam_session_id {exam_session_id}: {e}")
            raise DatabaseOperationError("Failed to fetch AISession.") from e

    async def get_all(self, skip: int = 0, limit: int = 100, state: Optional[str] = None) -> List[AISession]:
        try:
            query = self._base_query()
            if state:
                query = query.filter(AISession.state == state)
            query = query.offset(skip).limit(limit)
            result = await self.db.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching AI sessions: {e}")
            raise DatabaseOperationError("Failed to fetch AI sessions.") from e

    async def get_running_sessions(self, skip: int = 0, limit: int = 100) -> List[AISession]:
        return await self.get_all(skip=skip, limit=limit, state="RUNNING")

    async def create(self, **kwargs: Any) -> AISession:
        try:
            db_obj = await super().create(**kwargs)
            fetched_obj = await self.get_by_id(db_obj.id)
            if not fetched_obj:
                raise TransactionError("Failed to retrieve created AISession.")
            return fetched_obj
        except SQLAlchemyError as e:
            logger.error(f"Error creating AISession: {e}")
            raise TransactionError(f"Failed to create AISession.") from e

    async def update(self, db_obj: AISession, **kwargs: Any) -> AISession:
        try:
            updated_obj = await super().update(db_obj, **kwargs)
            fetched_obj = await self.get_by_id(updated_obj.id)
            if not fetched_obj:
                raise TransactionError("Failed to retrieve updated AISession.")
            return fetched_obj
        except SQLAlchemyError as e:
            logger.error(f"Error updating AISession id {db_obj.id}: {e}")
            raise TransactionError(f"Failed to update AISession.") from e
