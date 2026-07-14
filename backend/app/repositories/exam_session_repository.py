import logging
from typing import List, Optional, Any
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.models.exam_session import ExamSession
from app.repositories.base_repository import BaseRepository
from app.repositories.exceptions import DatabaseOperationError, TransactionError

logger = logging.getLogger(__name__)

from app.models.user import User
from app.models.exam import Exam

class ExamSessionRepository(BaseRepository[ExamSession]):
    def __init__(self, db: AsyncSession):
        super().__init__(ExamSession, db)

    def _base_query(self):
        """Returns a base query with explicit eager loading to prevent MissingGreenlet exceptions."""
        return select(ExamSession).options(
            joinedload(ExamSession.exam).joinedload(Exam.question_paper),
            joinedload(ExamSession.student).joinedload(User.role),
            joinedload(ExamSession.ai_session)
        )

    async def get_by_id(self, id: int) -> Optional[ExamSession]:
        try:
            result = await self.db.execute(self._base_query().filter(ExamSession.id == id))
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching ExamSession by id {id}: {e}")
            raise DatabaseOperationError(f"Failed to fetch ExamSession by id.") from e

    async def get_all(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        exam_id: Optional[int] = None, 
        student_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[ExamSession]:
        try:
            query = self._base_query()
            
            if exam_id:
                query = query.filter(ExamSession.exam_id == exam_id)
            if student_id:
                query = query.filter(ExamSession.student_id == student_id)
            if status:
                query = query.filter(ExamSession.status == status)
                
            query = query.offset(skip).limit(limit)
            result = await self.db.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching exam sessions: {e}")
            raise DatabaseOperationError("Failed to fetch exam sessions.") from e

    async def get_by_student_and_exam(self, student_id: int, exam_id: int) -> Optional[ExamSession]:
        try:
            result = await self.db.execute(
                self._base_query()
                .filter(ExamSession.student_id == student_id, ExamSession.exam_id == exam_id)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching ExamSession by student {student_id} and exam {exam_id}: {e}")
            raise DatabaseOperationError("Failed to fetch ExamSession.") from e

    async def get_running_sessions(self, skip: int = 0, limit: int = 100) -> List[ExamSession]:
        return await self.get_all(skip=skip, limit=limit, status="RUNNING")

    async def create(self, **kwargs: Any) -> ExamSession:
        try:
            db_obj = await super().create(**kwargs)
            fetched_obj = await self.get_by_id(db_obj.id)
            if not fetched_obj:
                raise TransactionError("Failed to retrieve created ExamSession.")
            return fetched_obj
        except SQLAlchemyError as e:
            logger.error(f"Error creating ExamSession: {e}")
            raise TransactionError(f"Failed to create ExamSession.") from e

    async def update(self, db_obj: ExamSession, **kwargs: Any) -> ExamSession:
        try:
            updated_obj = await super().update(db_obj, **kwargs)
            fetched_obj = await self.get_by_id(updated_obj.id)
            if not fetched_obj:
                raise TransactionError("Failed to retrieve updated ExamSession.")
            return fetched_obj
        except SQLAlchemyError as e:
            logger.error(f"Error updating ExamSession id {db_obj.id}: {e}")
            raise TransactionError(f"Failed to update ExamSession.") from e
