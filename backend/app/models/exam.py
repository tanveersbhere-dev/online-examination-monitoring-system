from datetime import datetime
from typing import List, TYPE_CHECKING
from sqlalchemy import String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import BaseEntity

if TYPE_CHECKING:
    from .user import User
    from .question_paper import QuestionPaper
    from .exam_session import ExamSession

class Exam(BaseEntity):
    __tablename__ = "exams"
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    course_name: Mapped[str] = mapped_column(String(255), nullable=False)
    question_paper_id: Mapped[int] = mapped_column(ForeignKey("question_papers.id"), nullable=False)
    scheduled_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scheduled_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="SCHEDULED", nullable=False)
    
    # Relationships
    creator: Mapped["User"] = relationship("User", back_populates="exams_created")
    question_paper: Mapped["QuestionPaper"] = relationship("QuestionPaper", back_populates="exams")
    sessions: Mapped[List["ExamSession"]] = relationship("ExamSession", back_populates="exam", cascade="all, delete-orphan")
