from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional
from sqlalchemy import String, ForeignKey, DateTime, Float, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import BaseEntity

if TYPE_CHECKING:
    from .violation import Violation

class Evidence(BaseEntity):
    __tablename__ = "evidence"
    
    violation_id: Mapped[int] = mapped_column(ForeignKey("violations.id"), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(50), nullable=False) # e.g., "IMAGE", "VIDEO_CLIP", "METADATA"
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    replay_clip_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    
    # Relationships
    violation: Mapped["Violation"] = relationship("Violation", back_populates="evidence")
