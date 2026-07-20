from typing import TYPE_CHECKING
from sqlalchemy import String, Integer, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import BaseEntity

if TYPE_CHECKING:
    from .exam import Exam
    from .exam_section_rule import ExamSectionRule
    from .question_paper import QuestionPaper
    from .question_option import QuestionOption

class ExamQuestionRule(BaseEntity):
    __tablename__ = "exam_question_rules"
    
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), nullable=True)
    question_paper_id: Mapped[int] = mapped_column(ForeignKey("question_papers.id", ondelete="CASCADE"), nullable=True)
    section_rule_id: Mapped[int] = mapped_column(ForeignKey("exam_section_rules.id", ondelete="CASCADE"), nullable=False)
    
    question_index: Mapped[int] = mapped_column(Integer, nullable=False)
    question_type: Mapped[str] = mapped_column(String(50), nullable=False, default="MCQ")
    marks: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    # New Content Fields for Structured Builder
    question_text: Mapped[str] = mapped_column(String, nullable=True)
    image_url: Mapped[str] = mapped_column(String(512), nullable=True)
    explanation: Mapped[str] = mapped_column(String, nullable=True)
    difficulty: Mapped[str] = mapped_column(String(50), nullable=True)
    
    character_limit: Mapped[int] = mapped_column(Integer, nullable=True)
    word_limit: Mapped[int] = mapped_column(Integer, nullable=True)
    attachment_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # DEPRECATED: Time belongs to the section/group. Kept for backwards compatibility but ignored.
    question_timer_seconds: Mapped[int] = mapped_column(Integer, nullable=True)
    
    autosave: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    individual_submission: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    editable_after_submission: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_multiple_submissions: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    max_submission_count: Mapped[int] = mapped_column(Integer, nullable=True)
    
    allow_editing_until_final: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    lock_immediately_after_submission: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    show_correctness_immediately: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    instructions: Mapped[str] = mapped_column(String, nullable=True)

    exam: Mapped["Exam"] = relationship("Exam", back_populates="question_rules")
    question_paper: Mapped["QuestionPaper"] = relationship("QuestionPaper", back_populates="question_rules")
    section_rule: Mapped["ExamSectionRule"] = relationship("ExamSectionRule", back_populates="question_rules")
    options: Mapped[List["QuestionOption"]] = relationship("QuestionOption", back_populates="question_rule", cascade="all, delete-orphan")
