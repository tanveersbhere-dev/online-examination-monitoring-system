from sqlalchemy import Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone

from app.database.base import Base

class WorkspacePreference(Base):
    __tablename__ = "workspace_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    theme: Mapped[str] = mapped_column(String(50), default="light", nullable=False)
    language: Mapped[str] = mapped_column(String(50), default="en", nullable=False)
    timezone: Mapped[str] = mapped_column(String(100), default="UTC", nullable=False)
    sidebar_collapsed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship("User", back_populates="workspace_preference")
