from typing import List, TYPE_CHECKING
from sqlalchemy import String, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import BaseEntity

if TYPE_CHECKING:
    from .user import User
    from .exam import Exam
    from .exam_section_rule import ExamSectionRule
    from .exam_question_rule import ExamQuestionRule

class QuestionPaper(BaseEntity):
    __tablename__ = "question_papers"
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    course_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    mode: Mapped[str] = mapped_column(String(50), nullable=False, default="FILE") # FILE, STRUCTURED
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    
    file_path: Mapped[str] = mapped_column(String(512), nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=True, default=0)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=True, default="application/pdf")
    
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="DRAFT") # DRAFT, READY, LOCKED, ARCHIVED
    
    # Relationships
    uploader: Mapped["User"] = relationship("User", back_populates="papers_uploaded")
    exams: Mapped[List["Exam"]] = relationship("Exam", back_populates="question_paper")
    
    section_rules: Mapped[List["ExamSectionRule"]] = relationship("ExamSectionRule", back_populates="question_paper", cascade="all, delete-orphan")
    question_rules: Mapped[List["ExamQuestionRule"]] = relationship("ExamQuestionRule", back_populates="question_paper", cascade="all, delete-orphan")
