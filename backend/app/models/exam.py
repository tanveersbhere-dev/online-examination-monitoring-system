from datetime import datetime
from typing import List, TYPE_CHECKING
from sqlalchemy import String, Integer, ForeignKey, DateTime, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import BaseEntity
import uuid as uuid_pkg

if TYPE_CHECKING:
    from .user import User
    from .question_paper import QuestionPaper
    from .exam_session import ExamSession
    from .exam_section_rule import ExamSectionRule
    from .exam_question_rule import ExamQuestionRule

class Exam(BaseEntity):
    __tablename__ = "exams"
    
    uuid: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid_pkg.uuid4()))
    exam_code: Mapped[str] = mapped_column(String(50), nullable=False, default=lambda: f"EXAM-{str(uuid_pkg.uuid4())[:8].upper()}")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    
    # Draft workflow: nullable ForeignKeys and Schedules
    question_paper_id: Mapped[int] = mapped_column(ForeignKey("question_papers.id"), nullable=True)
    scheduled_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    
    # Academic Information
    course_name: Mapped[str] = mapped_column(String(255), nullable=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=True)
    semester: Mapped[int] = mapped_column(Integer, nullable=True)
    session_name: Mapped[str] = mapped_column(String(100), nullable=True)
    
    # Configuration
    passing_marks: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    total_marks: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    negative_marking: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_submit: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    grace_period: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    late_join: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    randomization: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Level 1 Runtime Assessment Rules
    allow_resume_after_disconnect: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    global_navigation: Mapped[str] = mapped_column(String(50), nullable=False, default="FREE") # SEQUENTIAL, FREE
    randomize_sections: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    randomize_questions: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_review_before_submit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    show_remaining_time: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    show_question_numbers: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    show_marks: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    # JSON Configurations
    monitoring_config: Mapped[dict] = mapped_column(JSON, nullable=True)
    instructions: Mapped[dict] = mapped_column(JSON, nullable=True)
    browser_rules: Mapped[dict] = mapped_column(JSON, nullable=True)

    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="DRAFT", nullable=False)
    
    # Relationships
    creator: Mapped["User"] = relationship("User", back_populates="exams_created")
    question_paper: Mapped["QuestionPaper"] = relationship("QuestionPaper", back_populates="exams")
    sessions: Mapped[List["ExamSession"]] = relationship("ExamSession", back_populates="exam", cascade="all, delete-orphan")
    assignments: Mapped[List["ExamAssignment"]] = relationship("ExamAssignment", back_populates="exam", cascade="all, delete-orphan")
    supervisors: Mapped[List["ExamSupervisor"]] = relationship("ExamSupervisor", back_populates="exam", cascade="all, delete-orphan")
    
    section_rules: Mapped[List["ExamSectionRule"]] = relationship("ExamSectionRule", back_populates="exam", cascade="all, delete-orphan")
    question_rules: Mapped[List["ExamQuestionRule"]] = relationship("ExamQuestionRule", back_populates="exam", cascade="all, delete-orphan")
