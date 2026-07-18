from typing import TYPE_CHECKING, Any
from sqlalchemy import Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import BaseEntity

if TYPE_CHECKING:
    from .exam_session import ExamSession

class RuntimeState(BaseEntity):
    __tablename__ = "runtime_states"
    
    exam_session_id: Mapped[int] = mapped_column(ForeignKey("exam_sessions.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # Position tracking
    current_section_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_question_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # State tracking using JSON for flexibility
    navigation_history: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    completed_sections: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    locked_sections: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    locked_questions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    execution_flags: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    # Relationships
    exam_session: Mapped["ExamSession"] = relationship("ExamSession", back_populates="runtime_state")
