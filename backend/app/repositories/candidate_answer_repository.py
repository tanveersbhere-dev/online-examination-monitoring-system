from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
import logging

from app.models.candidate_answer import CandidateAnswer
from app.repositories.base_repository import BaseRepository
from app.repositories.exceptions import DatabaseOperationError

logger = logging.getLogger(__name__)

class CandidateAnswerRepository(BaseRepository[CandidateAnswer]):
    def __init__(self, db: AsyncSession):
        super().__init__(CandidateAnswer, db)

    async def get_by_question(self, exam_session_id: int, section_index: int, question_index: int) -> Optional[CandidateAnswer]:
        try:
            result = await self.db.execute(
                select(CandidateAnswer)
                .filter(CandidateAnswer.exam_session_id == exam_session_id)
                .filter(CandidateAnswer.section_index == section_index)
                .filter(CandidateAnswer.question_index == question_index)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching answer for session {exam_session_id}, S:{section_index} Q:{question_index}: {e}")
            raise DatabaseOperationError("Failed to fetch CandidateAnswer.") from e

    async def get_all_for_session(self, exam_session_id: int) -> List[CandidateAnswer]:
        try:
            result = await self.db.execute(
                select(CandidateAnswer)
                .filter(CandidateAnswer.exam_session_id == exam_session_id)
                .order_by(CandidateAnswer.section_index, CandidateAnswer.question_index)
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching answers for session {exam_session_id}: {e}")
            raise DatabaseOperationError("Failed to fetch session answers.") from e
