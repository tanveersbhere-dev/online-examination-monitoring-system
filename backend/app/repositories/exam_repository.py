import logging
from datetime import datetime
from typing import List, Optional, Any
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.models.exam import Exam
from app.repositories.base_repository import BaseRepository
from app.repositories.exceptions import DatabaseOperationError, TransactionError

logger = logging.getLogger(__name__)

class ExamRepository(BaseRepository[Exam]):
    def __init__(self, db: AsyncSession):
        super().__init__(Exam, db)

    def _base_query(self):
        """Returns a base query with explicit eager loading to prevent MissingGreenlet exceptions."""
        return select(Exam).options(joinedload(Exam.question_paper))

    async def get_by_id(self, id: int) -> Optional[Exam]:
        try:
            result = await self.db.execute(self._base_query().filter(Exam.id == id))
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching Exam by id {id}: {e}")
            raise DatabaseOperationError(f"Failed to fetch Exam by id.") from e

    async def get_all(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        course_name: Optional[str] = None, 
        status: Optional[str] = None
    ) -> List[Exam]:
        try:
            query = self._base_query()
            
            if course_name:
                query = query.filter(Exam.course_name.ilike(f"%{course_name}%"))
            if status:
                query = query.filter(Exam.status == status)
                
            query = query.offset(skip).limit(limit)
            result = await self.db.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching exams: {e}")
            raise DatabaseOperationError("Failed to fetch exams.") from e

    async def get_by_status(self, status: str, skip: int = 0, limit: int = 100) -> List[Exam]:
        # Utilizing the new get_all which supports filtering
        return await self.get_all(skip=skip, limit=limit, status=status)

    async def get_upcoming_exams(self, current_time: datetime, skip: int = 0, limit: int = 100) -> List[Exam]:
        try:
            result = await self.db.execute(
                self._base_query()
                .filter(Exam.scheduled_start > current_time)
                .order_by(Exam.scheduled_start.asc())
                .offset(skip).limit(limit)
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching upcoming exams: {e}")
            raise DatabaseOperationError("Failed to fetch upcoming exams.") from e

    async def create(self, **kwargs: Any) -> Exam:
        try:
            # We call the base create to handle DB insertion and commit
            db_obj = await super().create(**kwargs)
            # Re-fetch the object to properly load all relationships explicitly
            # Otherwise returning it directly might crash Pydantic models due to lazy loading
            fetched_obj = await self.get_by_id(db_obj.id)
            if not fetched_obj:
                raise TransactionError("Failed to retrieve created Exam.")
            return fetched_obj
        except SQLAlchemyError as e:
            logger.error(f"Error creating Exam: {e}")
            raise TransactionError(f"Failed to create Exam.") from e

    async def update(self, db_obj: Exam, **kwargs: Any) -> Exam:
        try:
            updated_obj = await super().update(db_obj, **kwargs)
            fetched_obj = await self.get_by_id(updated_obj.id)
            if not fetched_obj:
                raise TransactionError("Failed to retrieve updated Exam.")
            return fetched_obj
        except SQLAlchemyError as e:
            logger.error(f"Error updating Exam id {db_obj.id}: {e}")
            raise TransactionError(f"Failed to update Exam.") from e
