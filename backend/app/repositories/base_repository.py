import logging
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.database.base import BaseEntity
from app.repositories.exceptions import (
    DatabaseOperationError,
    EntityNotFoundError,
    TransactionError,
)

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType", bound=BaseEntity)

class BaseRepository(Generic[ModelType]):
    """
    Generic Base Repository encapsulating standard CRUD operations for a given SQLAlchemy model.
    """

    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def get_by_id(self, id: int) -> Optional[ModelType]:
        try:
            result = await self.db.execute(select(self.model).filter(self.model.id == id))
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching {self.model.__name__} by id {id}: {e}")
            raise DatabaseOperationError(f"Failed to fetch {self.model.__name__} by id.") from e

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        try:
            result = await self.db.execute(select(self.model).offset(skip).limit(limit))
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching all {self.model.__name__}: {e}")
            raise DatabaseOperationError(f"Failed to fetch all {self.model.__name__}.") from e

    async def create(self, **kwargs: Any) -> ModelType:
        try:
            db_obj = self.model(**kwargs)
            self.db.add(db_obj)
            await self.db.commit()
            await self.db.refresh(db_obj)
            logger.debug(f"Created {self.model.__name__} with id {db_obj.id}")
            return db_obj
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error creating {self.model.__name__}: {e}")
            raise TransactionError(f"Failed to create {self.model.__name__}.") from e

    async def update(self, db_obj: ModelType, **kwargs: Any) -> ModelType:
        try:
            for field, value in kwargs.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)
            self.db.add(db_obj)
            await self.db.commit()
            await self.db.refresh(db_obj)
            logger.debug(f"Updated {self.model.__name__} with id {db_obj.id}")
            return db_obj
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error updating {self.model.__name__} id {db_obj.id}: {e}")
            raise TransactionError(f"Failed to update {self.model.__name__}.") from e

    async def delete(self, id: int) -> bool:
        try:
            db_obj = await self.get_by_id(id)
            if not db_obj:
                raise EntityNotFoundError(f"{self.model.__name__} with id {id} not found.")
                
            await self.db.delete(db_obj)
            await self.db.commit()
            logger.debug(f"Deleted {self.model.__name__} with id {id}")
            return True
        except EntityNotFoundError:
            raise
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error deleting {self.model.__name__} id {id}: {e}")
            raise TransactionError(f"Failed to delete {self.model.__name__}.") from e

    async def exists(self, id: int) -> bool:
        try:
            result = await self.db.execute(
                select(func.count()).select_from(self.model).filter(self.model.id == id)
            )
            return result.scalar() > 0
        except SQLAlchemyError as e:
            logger.error(f"Error checking existence for {self.model.__name__} id {id}: {e}")
            raise DatabaseOperationError("Failed to check existence.") from e

    async def count(self) -> int:
        try:
            result = await self.db.execute(select(func.count()).select_from(self.model))
            return result.scalar() or 0
        except SQLAlchemyError as e:
            logger.error(f"Error counting {self.model.__name__}: {e}")
            raise DatabaseOperationError("Failed to count records.") from e

    async def paginate(self, page: int = 1, size: int = 50) -> List[ModelType]:
        skip = (page - 1) * size
        return await self.get_all(skip=skip, limit=size)
