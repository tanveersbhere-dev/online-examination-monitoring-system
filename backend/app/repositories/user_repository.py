import logging
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from app.models.user import User
from app.repositories.base_repository import BaseRepository
from app.repositories.exceptions import DatabaseOperationError

logger = logging.getLogger(__name__)

class UserRepository(BaseRepository[User]):
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    def _base_query_with_role(self):
        """Private helper to construct a base query eagerly loading the User.role relationship."""
        return select(User).options(joinedload(User.role))

    async def get_by_id(self, id: int) -> Optional[User]:
        try:
            result = await self.db.execute(self._base_query_with_role().filter(User.id == id))
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching User by id {id}: {e}")
            raise DatabaseOperationError("Failed to fetch user by id.") from e

    async def get_by_email(self, email: str) -> Optional[User]:
        try:
            result = await self.db.execute(self._base_query_with_role().filter(User.email == email))
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching User by email {email}: {e}")
            raise DatabaseOperationError("Failed to fetch user by email.") from e

    async def get_active_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        try:
            result = await self.db.execute(
                select(User).filter(User.is_active == True).offset(skip).limit(limit)
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching active users: {e}")
            raise DatabaseOperationError("Failed to fetch active users.") from e
