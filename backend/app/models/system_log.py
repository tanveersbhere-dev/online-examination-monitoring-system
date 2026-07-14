from datetime import datetime
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import BaseEntity

class SystemLog(BaseEntity):
    __tablename__ = "system_logs"
    
    level: Mapped[str] = mapped_column(String(20), nullable=False) # INFO, WARNING, ERROR
    message: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False) # Which module produced this
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
