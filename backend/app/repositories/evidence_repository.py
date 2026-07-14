import logging
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.models.evidence import Evidence
from app.repositories.base_repository import BaseRepository
from app.repositories.exceptions import DatabaseOperationError

logger = logging.getLogger(__name__)

class EvidenceRepository(BaseRepository[Evidence]):
    def __init__(self, db: AsyncSession):
        super().__init__(Evidence, db)

    async def get_by_violation(self, violation_id: int, skip: int = 0, limit: int = 100) -> List[Evidence]:
        try:
            result = await self.db.execute(
                select(Evidence).filter(Evidence.violation_id == violation_id).offset(skip).limit(limit)
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching Evidence by violation {violation_id}: {e}")
            raise DatabaseOperationError("Failed to fetch evidence by violation.") from e
