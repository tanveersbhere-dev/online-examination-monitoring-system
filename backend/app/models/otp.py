from datetime import datetime
from sqlalchemy import String, Integer, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from app.database.base import BaseEntity

if TYPE_CHECKING:
    from .user import User

class OTP(BaseEntity):
    __tablename__ = "otps"
    
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    otp_code: Mapped[str] = mapped_column(String(6), nullable=False)
    purpose: Mapped[str] = mapped_column(String(50), nullable=False) # e.g., 'REGISTRATION', 'PASSWORD_RESET', 'EMAIL_CHANGE'
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    resend_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_email: Mapped[str] = mapped_column(String(255), nullable=True) # Used specifically for EMAIL_CHANGE
    
    user: Mapped["User"] = relationship("User", back_populates="otps")
