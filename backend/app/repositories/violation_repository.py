import logging
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.models.violation import Violation
from app.repositories.base_repository import BaseRepository
from app.repositories.exceptions import DatabaseOperationError

logger = logging.getLogger(__name__)

class ViolationRepository(BaseRepository[Violation]):
    def __init__(self, db: AsyncSession):
        super().__init__(Violation, db)

    async def get_by_exam_session(self, exam_session_id: int, skip: int = 0, limit: int = 100) -> List[Violation]:
        try:
            result = await self.db.execute(
                select(Violation).filter(Violation.exam_session_id == exam_session_id).offset(skip).limit(limit)
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching Violations by exam session {exam_session_id}: {e}")
            raise DatabaseOperationError("Failed to fetch violations by exam session.") from e

    async def get_by_severity(self, severity: str, skip: int = 0, limit: int = 100) -> List[Violation]:
        try:
            result = await self.db.execute(
                select(Violation).filter(Violation.severity == severity).offset(skip).limit(limit)
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching Violations by severity {severity}: {e}")
            raise DatabaseOperationError("Failed to fetch violations by severity.") from e
