from datetime import datetime
from typing import List, TYPE_CHECKING, Optional
from sqlalchemy import String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import BaseEntity

if TYPE_CHECKING:
    from .user import User
    from .exam import Exam
    from .ai_session import AISession
    from .violation import Violation
    from .ai_event import AIEvent
    from .runtime_state import RuntimeState
    from .candidate_answer import CandidateAnswer

class ExamSession(BaseEntity):
    __tablename__ = "exam_sessions"
    
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    ai_session_id: Mapped[Optional[int]] = mapped_column(ForeignKey("ai_sessions.id"), unique=True, nullable=True)
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)
    
    # Evaluation Tracking Fields (Phase 10)
    evaluation_status: Mapped[Optional[str]] = mapped_column(String(50), default="PENDING", nullable=True)
    objective_score: Mapped[Optional[float]] = mapped_column(nullable=True, default=0.0)
    subjective_score: Mapped[Optional[float]] = mapped_column(nullable=True, default=0.0)
    total_score: Mapped[Optional[float]] = mapped_column(nullable=True, default=0.0)
    evaluated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    evaluated_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    
    # Relationships
    exam: Mapped["Exam"] = relationship("Exam", back_populates="sessions")
    student: Mapped["User"] = relationship("User", back_populates="exam_sessions", foreign_keys=[student_id])
    ai_session: Mapped[Optional["AISession"]] = relationship("AISession", back_populates="exam_session", single_parent=True, cascade="all, delete-orphan")
    violations: Mapped[List["Violation"]] = relationship("Violation", back_populates="exam_session", cascade="all, delete-orphan")
    ai_events: Mapped[List["AIEvent"]] = relationship("AIEvent", back_populates="exam_session", cascade="all, delete-orphan")
    runtime_state: Mapped[Optional["RuntimeState"]] = relationship("RuntimeState", back_populates="exam_session", uselist=False, cascade="all, delete-orphan")
    candidate_answers: Mapped[List["CandidateAnswer"]] = relationship("CandidateAnswer", back_populates="exam_session", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("exam_id", "student_id", name="uq_exam_session_student"),
    )
