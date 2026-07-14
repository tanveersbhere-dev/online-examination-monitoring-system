import logging
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.models.ai_session import AISession
from app.repositories.base_repository import BaseRepository
from app.repositories.exceptions import DatabaseOperationError

logger = logging.getLogger(__name__)

class AISessionRepository(BaseRepository[AISession]):
    def __init__(self, db: AsyncSession):
        super().__init__(AISession, db)

    async def get_running_sessions(self, skip: int = 0, limit: int = 100) -> List[AISession]:
        try:
            result = await self.db.execute(
                select(AISession).filter(AISession.state == "RUNNING").offset(skip).limit(limit)
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching running AI sessions: {e}")
            raise DatabaseOperationError("Failed to fetch running AI sessions.") from e
