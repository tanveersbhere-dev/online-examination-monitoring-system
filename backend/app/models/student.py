import uuid
from sqlalchemy import Integer, String, DateTime, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import BaseEntity

class Student(BaseEntity):
    __tablename__ = "students"

    uuid: Mapped[str] = mapped_column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True, nullable=False)
    examiner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Core Identity Fields
    registration_number: Mapped[str] = mapped_column(String(100), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False) # ACTIVE, PENDING, ARCHIVED, SUSPENDED
    
    # Optional Academic Fields
    roll_number: Mapped[str] = mapped_column(String(100), nullable=True)
    department: Mapped[str] = mapped_column(String(100), nullable=True)
    program: Mapped[str] = mapped_column(String(100), nullable=True)
    semester: Mapped[int] = mapped_column(Integer, nullable=True)
    batch: Mapped[str] = mapped_column(String(50), nullable=True)
    section: Mapped[str] = mapped_column(String(50), nullable=True)

    # Reference Image & Face Embedding (Optional)
    face_image_path: Mapped[str] = mapped_column(String(512), nullable=True)
    face_embedding: Mapped[str] = mapped_column(String, nullable=True)
    embedding_version: Mapped[str] = mapped_column(String(50), default="v1", nullable=True)

    # Constraint to prevent duplicates per examiner
    __table_args__ = (
        UniqueConstraint("examiner_id", "registration_number", name="uq_examiner_student_reg"),
    )

    # If we need backref in the future, we can add it to the User model,
    # but since it's one-way ownership, this might suffice for now.
    examiner: Mapped["User"] = relationship("User", foreign_keys=[examiner_id])
