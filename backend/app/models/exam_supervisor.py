from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import BaseEntity

class ExamSupervisor(BaseEntity):
    __tablename__ = "exam_supervisors"
    
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    supervisor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    exam: Mapped["Exam"] = relationship("Exam", back_populates="supervisors")
    supervisor: Mapped["User"] = relationship("User")
