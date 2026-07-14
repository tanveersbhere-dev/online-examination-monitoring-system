import logging
from datetime import datetime
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.models.exam import Exam
from app.repositories.base_repository import BaseRepository
from app.repositories.exceptions import DatabaseOperationError

logger = logging.getLogger(__name__)

class ExamRepository(BaseRepository[Exam]):
    def __init__(self, db: AsyncSession):
        super().__init__(Exam, db)

    async def get_by_status(self, status: str, skip: int = 0, limit: int = 100) -> List[Exam]:
        try:
            result = await self.db.execute(
                select(Exam).filter(Exam.status == status).offset(skip).limit(limit)
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching Exam by status {status}: {e}")
            raise DatabaseOperationError("Failed to fetch exams by status.") from e

    async def get_upcoming_exams(self, current_time: datetime, skip: int = 0, limit: int = 100) -> List[Exam]:
        try:
            result = await self.db.execute(
                select(Exam)
                .filter(Exam.scheduled_start > current_time)
                .order_by(Exam.scheduled_start.asc())
                .offset(skip).limit(limit)
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching upcoming exams: {e}")
            raise DatabaseOperationError("Failed to fetch upcoming exams.") from e
