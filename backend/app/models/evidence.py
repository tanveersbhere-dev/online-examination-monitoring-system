from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import BaseEntity

if TYPE_CHECKING:
    from .violation import Violation

class Evidence(BaseEntity):
    __tablename__ = "evidence"
    
    violation_id: Mapped[int] = mapped_column(ForeignKey("violations.id"), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(50), nullable=False) # e.g., "IMAGE", "VIDEO_CLIP"
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Relationships
    violation: Mapped["Violation"] = relationship("Violation", back_populates="evidence")
