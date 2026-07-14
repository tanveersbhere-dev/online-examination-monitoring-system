import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import BaseEntity

if TYPE_CHECKING:
    from .exam_session import ExamSession

class AISession(BaseEntity):
    __tablename__ = "ai_sessions"
    
    session_uuid: Mapped[str] = mapped_column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True, nullable=False)
    state: Mapped[str] = mapped_column(String(50), default="CREATED", nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    stopped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    current_risk: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    
    # Relationship (One-to-One back to ExamSession, handled by uselist=False in ExamSession)
    exam_session: Mapped[Optional["ExamSession"]] = relationship("ExamSession", back_populates="ai_session")
