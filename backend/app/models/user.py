from typing import List, TYPE_CHECKING, Optional
from datetime import datetime
from sqlalchemy import String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import BaseEntity

if TYPE_CHECKING:
    from .role import Role
    from .exam import Exam
    from .question_paper import QuestionPaper
    from .exam_session import ExamSession

class User(BaseEntity):
    __tablename__ = "users"
    
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Candidate-specific fields
    father_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True)
    credential_expiry_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    account_status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False)
    
    # Face Enrollment fields
    face_image_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    face_embedding: Mapped[Optional[str]] = mapped_column(String, nullable=True) # JSON serialized
    embedding_version: Mapped[Optional[str]] = mapped_column(String(50), default="v1", nullable=True)
    registration_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    role: Mapped["Role"] = relationship("Role", back_populates="users")
    exams_created: Mapped[List["Exam"]] = relationship("Exam", back_populates="creator", cascade="all, delete-orphan")
    papers_uploaded: Mapped[List["QuestionPaper"]] = relationship("QuestionPaper", back_populates="uploader", cascade="all, delete-orphan")
    exam_sessions: Mapped[List["ExamSession"]] = relationship("ExamSession", back_populates="student", cascade="all, delete-orphan")
