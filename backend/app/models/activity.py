from sqlalchemy import Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from typing import Optional

from app.database.base import Base

class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False) # e.g., "EXAM_CREATED", "STUDENT_IMPORTED"
    description: Mapped[str] = mapped_column(Text, nullable=False)
    resource_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True) # e.g., "Exam", "Student"
    resource_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship("User", back_populates="activities")
