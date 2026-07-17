from datetime import datetime
from typing import TYPE_CHECKING, Dict, Any
from sqlalchemy import String, Float, ForeignKey, DateTime, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import BaseEntity

if TYPE_CHECKING:
    from .exam_session import ExamSession

class AIEvent(BaseEntity):
    """
    Persists raw AI telemetry and tracking events, independent of whether they trigger a Violation.
    """
    __tablename__ = "ai_events"
    
    exam_session_id: Mapped[int] = mapped_column(ForeignKey("exam_sessions.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(50), default="INFO", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    source_module: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    
    # Relationships
    exam_session: Mapped["ExamSession"] = relationship("ExamSession", back_populates="ai_events")
