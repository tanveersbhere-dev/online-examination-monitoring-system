from datetime import datetime
from typing import List, TYPE_CHECKING, Optional
from sqlalchemy import String, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import BaseEntity

if TYPE_CHECKING:
    from .exam_session import ExamSession
    from .evidence import Evidence
    from .ai_session import AISession

class Violation(BaseEntity):
    __tablename__ = "violations"
    
    exam_session_id: Mapped[int] = mapped_column(ForeignKey("exam_sessions.id"), nullable=False)
    ai_session_id: Mapped[Optional[int]] = mapped_column(ForeignKey("ai_sessions.id"), nullable=True)
    violation_type: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    exam_session: Mapped["ExamSession"] = relationship("ExamSession", back_populates="violations")
    ai_session: Mapped[Optional["AISession"]] = relationship("AISession")
    evidence: Mapped[List["Evidence"]] = relationship("Evidence", back_populates="violation", cascade="all, delete-orphan")
