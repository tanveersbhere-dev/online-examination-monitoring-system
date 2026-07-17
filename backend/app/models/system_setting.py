from sqlalchemy import String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import BaseEntity

class SystemSetting(BaseEntity):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
