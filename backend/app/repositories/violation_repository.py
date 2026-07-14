import logging
from typing import List, Optional, Any
from datetime import datetime
from sqlalchemy import select, and_, desc, asc
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.models.violation import Violation
from app.models.exam_session import ExamSession
from app.models.exam import Exam
from app.repositories.base_repository import BaseRepository
from app.repositories.exceptions import DatabaseOperationError, TransactionError

logger = logging.getLogger(__name__)

class ViolationRepository(BaseRepository[Violation]):
    def __init__(self, db: AsyncSession):
        super().__init__(Violation, db)

    def _base_query(self):
        """Returns a base query with explicit eager loading to prevent MissingGreenlet exceptions."""
        return select(Violation).options(
            joinedload(Violation.exam_session),
            joinedload(Violation.ai_session),
            selectinload(Violation.evidence)
        )

    async def get_by_id(self, id: int) -> Optional[Violation]:
        try:
            result = await self.db.execute(self._base_query().filter(Violation.id == id))
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching Violation by id {id}: {e}")
            raise DatabaseOperationError(f"Failed to fetch Violation by id.") from e

    async def get_by_exam_session(self, exam_session_id: int, skip: int = 0, limit: int = 100) -> List[Violation]:
        try:
            result = await self.db.execute(
                self._base_query()
                .filter(Violation.exam_session_id == exam_session_id)
                .order_by(desc(Violation.timestamp))
                .offset(skip)
                .limit(limit)
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching Violations by exam session {exam_session_id}: {e}")
            raise DatabaseOperationError("Failed to fetch violations by exam session.") from e

    async def filter_violations(
        self,
        exam_id: Optional[int] = None,
        student_id: Optional[int] = None,
        severity: Optional[str] = None,
        violation_type: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Violation]:
        try:
            query = self._base_query().join(Violation.exam_session)
            
            if exam_id:
                query = query.filter(ExamSession.exam_id == exam_id)
            if student_id:
                query = query.filter(ExamSession.student_id == student_id)
            if severity:
                query = query.filter(Violation.severity == severity)
            if violation_type:
                query = query.filter(Violation.violation_type == violation_type)
            if status:
                query = query.filter(Violation.status == status)
            if start_date:
                query = query.filter(Violation.timestamp >= start_date)
            if end_date:
                query = query.filter(Violation.timestamp <= end_date)
                
            query = query.order_by(desc(Violation.timestamp)).offset(skip).limit(limit)
            
            result = await self.db.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error filtering Violations: {e}")
            raise DatabaseOperationError("Failed to filter violations.") from e

    async def create(self, **kwargs: Any) -> Violation:
        try:
            db_obj = await super().create(**kwargs)
            fetched_obj = await self.get_by_id(db_obj.id)
            if not fetched_obj:
                raise TransactionError("Failed to retrieve created Violation.")
            return fetched_obj
        except SQLAlchemyError as e:
            logger.error(f"Error creating Violation: {e}")
            raise TransactionError(f"Failed to create Violation.") from e

    async def update(self, db_obj: Violation, **kwargs: Any) -> Violation:
        try:
            updated_obj = await super().update(db_obj, **kwargs)
            fetched_obj = await self.get_by_id(updated_obj.id)
            if not fetched_obj:
                raise TransactionError("Failed to retrieve updated Violation.")
            return fetched_obj
        except SQLAlchemyError as e:
            logger.error(f"Error updating Violation id {db_obj.id}: {e}")
            raise TransactionError(f"Failed to update Violation.") from e
