import logging
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.models.question_paper import QuestionPaper
from app.repositories.base_repository import BaseRepository
from app.repositories.exceptions import DatabaseOperationError

logger = logging.getLogger(__name__)

class QuestionPaperRepository(BaseRepository[QuestionPaper]):
    def __init__(self, db: AsyncSession):
        super().__init__(QuestionPaper, db)

    async def get_by_course(self, course_name: str, skip: int = 0, limit: int = 100) -> List[QuestionPaper]:
        try:
            result = await self.db.execute(
                select(QuestionPaper).filter(QuestionPaper.course_name == course_name).offset(skip).limit(limit)
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching Question Papers by course {course_name}: {e}")
            raise DatabaseOperationError("Failed to fetch question papers by course.") from e
