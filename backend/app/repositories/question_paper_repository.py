import logging
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from app.models.question_paper import QuestionPaper
from app.repositories.base_repository import BaseRepository
from app.repositories.exceptions import DatabaseOperationError

logger = logging.getLogger(__name__)

class QuestionPaperRepository(BaseRepository[QuestionPaper]):
    def __init__(self, db: AsyncSession):
        super().__init__(QuestionPaper, db)

    def _base_query(self):
        """Helper to ensure we can easily eager load if needed."""
        # For now, we don't strictly need joinedload(QuestionPaper.uploader) 
        # since we only use uploaded_by, but adding it prevents any MissingGreenlet risks downstream.
        return select(QuestionPaper).options(joinedload(QuestionPaper.uploader))

    async def get_by_id(self, id: int) -> Optional[QuestionPaper]:
        try:
            result = await self.db.execute(self._base_query().filter(QuestionPaper.id == id))
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching QuestionPaper by id {id}: {e}")
            raise DatabaseOperationError("Failed to fetch question paper by id.") from e

    async def get_by_course(self, course_name: str, skip: int = 0, limit: int = 100, uploaded_by: Optional[int] = None) -> List[QuestionPaper]:
        try:
            query = self._base_query().filter(QuestionPaper.course_name.ilike(f"%{course_name}%"))
            if uploaded_by is not None:
                query = query.filter(QuestionPaper.uploaded_by == uploaded_by)
            result = await self.db.execute(query.offset(skip).limit(limit))
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching Question Papers by course {course_name}: {e}")
            raise DatabaseOperationError("Failed to fetch question papers by course.") from e

    async def get_all_papers(self, skip: int = 0, limit: int = 100, uploaded_by: Optional[int] = None) -> List[QuestionPaper]:
        try:
            query = self._base_query()
            if uploaded_by is not None:
                query = query.filter(QuestionPaper.uploaded_by == uploaded_by)
            result = await self.db.execute(query.offset(skip).limit(limit))
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching all Question Papers: {e}")
            raise DatabaseOperationError("Failed to fetch all question papers.") from e
