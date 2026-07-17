from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import BaseEntity

class ExamAssignment(BaseEntity):
    __tablename__ = "exam_assignments"
    
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    
    exam: Mapped["Exam"] = relationship("Exam", back_populates="assignments")
    student: Mapped["Student"] = relationship("Student")
