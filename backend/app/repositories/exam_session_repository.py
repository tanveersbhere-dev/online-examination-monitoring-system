import logging
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.models.exam_session import ExamSession
from app.repositories.base_repository import BaseRepository
from app.repositories.exceptions import DatabaseOperationError

logger = logging.getLogger(__name__)

class ExamSessionRepository(BaseRepository[ExamSession]):
    def __init__(self, db: AsyncSession):
        super().__init__(ExamSession, db)

    async def get_running_sessions(self, skip: int = 0, limit: int = 100) -> List[ExamSession]:
        try:
            # Assuming 'RUNNING' or similar status represents an active session
            result = await self.db.execute(
                select(ExamSession).filter(ExamSession.status == "RUNNING").offset(skip).limit(limit)
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching running exam sessions: {e}")
            raise DatabaseOperationError("Failed to fetch running exam sessions.") from e
