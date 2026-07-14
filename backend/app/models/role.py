from typing import List, TYPE_CHECKING
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import BaseEntity

if TYPE_CHECKING:
    from .user import User

class Role(BaseEntity):
    __tablename__ = "roles"
    
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    
    # 1 -> Many Users
    users: Mapped[List["User"]] = relationship("User", back_populates="role", cascade="all, delete-orphan")
