from typing import TYPE_CHECKING, Any
from sqlalchemy import Integer, Boolean, ForeignKey, JSON, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime

from app.database.base import BaseEntity

if TYPE_CHECKING:
    from .exam_session import ExamSession

class CandidateAnswer(BaseEntity):
    __tablename__ = "candidate_answers"
    
    exam_session_id: Mapped[int] = mapped_column(ForeignKey("exam_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    section_index: Mapped[int] = mapped_column(Integer, nullable=False)
    question_index: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Payload for the actual answer (e.g. {"selected_options": ["A", "B"]} or {"text": "My essay..."})
    answer_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    # State
    is_submitted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    submission_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint("exam_session_id", "section_index", "question_index", name="uq_candidate_answer_session_question"),
    )
    
    # Relationships
    exam_session: Mapped["ExamSession"] = relationship("ExamSession", back_populates="candidate_answers")
