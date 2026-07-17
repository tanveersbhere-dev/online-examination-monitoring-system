from typing import List, TYPE_CHECKING
from sqlalchemy import String, Integer, ForeignKey, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import BaseEntity

if TYPE_CHECKING:
    from .exam import Exam
    from .exam_question_rule import ExamQuestionRule

class ExamSectionRule(BaseEntity):
    __tablename__ = "exam_section_rules"
    
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    section_index: Mapped[int] = mapped_column(Integer, nullable=False)
    section_name: Mapped[str] = mapped_column(String(255), nullable=False)
    section_type: Mapped[str] = mapped_column(String(50), nullable=False, default="MCQ")
    
    section_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=True)
    navigation_policy: Mapped[str] = mapped_column(String(50), nullable=False, default="FREE") # SEQUENTIAL, FREE
    allow_return_to_previous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    lock_after_timeout: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    randomize_questions: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    require_completion_before_next: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    section_weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    instructions: Mapped[str] = mapped_column(String, nullable=True)

    exam: Mapped["Exam"] = relationship("Exam", back_populates="section_rules")
    question_rules: Mapped[List["ExamQuestionRule"]] = relationship("ExamQuestionRule", back_populates="section_rule", cascade="all, delete-orphan")
