import logging
from typing import List, Optional, Any
from sqlalchemy import select, desc
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.models.evidence import Evidence
from app.repositories.base_repository import BaseRepository
from app.repositories.exceptions import DatabaseOperationError, TransactionError

logger = logging.getLogger(__name__)

class EvidenceRepository(BaseRepository[Evidence]):
    def __init__(self, db: AsyncSession):
        super().__init__(Evidence, db)

    def _base_query(self):
        """Returns a base query with explicit eager loading to prevent MissingGreenlet exceptions."""
        return select(Evidence).options(
            joinedload(Evidence.violation)
        )

    async def get_by_id(self, id: int) -> Optional[Evidence]:
        try:
            result = await self.db.execute(self._base_query().filter(Evidence.id == id))
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching Evidence by id {id}: {e}")
            raise DatabaseOperationError(f"Failed to fetch Evidence by id.") from e

    async def get_by_violation(self, violation_id: int, skip: int = 0, limit: int = 100) -> List[Evidence]:
        try:
            result = await self.db.execute(
                self._base_query()
                .filter(Evidence.violation_id == violation_id)
                .order_by(desc(Evidence.timestamp))
                .offset(skip)
                .limit(limit)
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching Evidence by violation {violation_id}: {e}")
            raise DatabaseOperationError("Failed to fetch evidence by violation.") from e

    async def filter_evidence(
        self,
        violation_id: Optional[int] = None,
        evidence_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Evidence]:
        try:
            query = self._base_query()
            if violation_id:
                query = query.filter(Evidence.violation_id == violation_id)
            if evidence_type:
                query = query.filter(Evidence.evidence_type == evidence_type)
                
            query = query.order_by(desc(Evidence.timestamp)).offset(skip).limit(limit)
            result = await self.db.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error filtering Evidence: {e}")
            raise DatabaseOperationError("Failed to filter evidence.") from e

    async def create(self, **kwargs: Any) -> Evidence:
        try:
            db_obj = await super().create(**kwargs)
            fetched_obj = await self.get_by_id(db_obj.id)
            if not fetched_obj:
                raise TransactionError("Failed to retrieve created Evidence.")
            return fetched_obj
        except SQLAlchemyError as e:
            logger.error(f"Error creating Evidence: {e}")
            raise TransactionError(f"Failed to create Evidence.") from e

    async def update(self, db_obj: Evidence, **kwargs: Any) -> Evidence:
        try:
            updated_obj = await super().update(db_obj, **kwargs)
            fetched_obj = await self.get_by_id(updated_obj.id)
            if not fetched_obj:
                raise TransactionError("Failed to retrieve updated Evidence.")
            return fetched_obj
        except SQLAlchemyError as e:
            logger.error(f"Error updating Evidence id {db_obj.id}: {e}")
            raise TransactionError(f"Failed to update Evidence.") from e
