from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
import logging

from app.models.runtime_state import RuntimeState
from app.repositories.base_repository import BaseRepository
from app.repositories.exceptions import DatabaseOperationError

logger = logging.getLogger(__name__)

class RuntimeStateRepository(BaseRepository[RuntimeState]):
    def __init__(self, db: AsyncSession):
        super().__init__(RuntimeState, db)

    async def get_by_session_id(self, exam_session_id: int) -> Optional[RuntimeState]:
        try:
            result = await self.db.execute(select(RuntimeState).filter(RuntimeState.exam_session_id == exam_session_id))
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching RuntimeState for session {exam_session_id}: {e}")
            raise DatabaseOperationError(f"Failed to fetch RuntimeState.") from e
