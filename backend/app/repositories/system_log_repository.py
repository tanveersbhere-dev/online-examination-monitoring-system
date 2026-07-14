import logging
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.models.system_log import SystemLog
from app.repositories.base_repository import BaseRepository
from app.repositories.exceptions import DatabaseOperationError

logger = logging.getLogger(__name__)

class SystemLogRepository(BaseRepository[SystemLog]):
    def __init__(self, db: AsyncSession):
        super().__init__(SystemLog, db)

    async def get_recent_logs(self, limit: int = 100) -> List[SystemLog]:
        try:
            result = await self.db.execute(
                select(SystemLog).order_by(SystemLog.timestamp.desc()).limit(limit)
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching recent system logs: {e}")
            raise DatabaseOperationError("Failed to fetch recent system logs.") from e
