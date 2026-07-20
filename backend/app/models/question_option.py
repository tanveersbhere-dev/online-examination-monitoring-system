from typing import TYPE_CHECKING
from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import BaseEntity

if TYPE_CHECKING:
    from .exam_question_rule import ExamQuestionRule

class QuestionOption(BaseEntity):
    __tablename__ = "question_options"
    
    question_rule_id: Mapped[int] = mapped_column(ForeignKey("exam_question_rules.id", ondelete="CASCADE"), nullable=False)
    
    option_text: Mapped[str] = mapped_column(String(512), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    question_rule: Mapped["ExamQuestionRule"] = relationship("ExamQuestionRule", back_populates="options")
