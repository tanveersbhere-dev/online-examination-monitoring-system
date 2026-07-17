import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.models.system_setting import SystemSetting
from app.models.system_log import SystemLog
from app.models.user import User
from app.models.exam import Exam
from app.models.violation import Violation
from app.models.exam_session import ExamSession

from app.schemas.admin import (
    SystemSettingCreate, SystemSettingUpdate, SystemSettingResponse, 
    SystemLogResponse, AdminDashboardStats
)

logger = logging.getLogger(__name__)

class AdminService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard_stats(self) -> AdminDashboardStats:
        user_count = await self.db.execute(select(func.count(User.id)))
        exam_count = await self.db.execute(select(func.count(Exam.id)))
        violation_count = await self.db.execute(select(func.count(Violation.id)))
        active_sessions = await self.db.execute(
            select(func.count(ExamSession.id)).where(ExamSession.status == "IN_PROGRESS")
        )

        return AdminDashboardStats(
            total_users=user_count.scalar() or 0,
            total_exams=exam_count.scalar() or 0,
            total_violations=violation_count.scalar() or 0,
            active_sessions=active_sessions.scalar() or 0,
            system_health="Operational"
        )

    async def get_system_logs(self, limit: int = 100) -> List[SystemLog]:
        query = select(SystemLog).order_by(SystemLog.timestamp.desc()).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_all_settings(self) -> List[SystemSetting]:
        query = select(SystemSetting).order_by(SystemSetting.key)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_setting_by_key(self, key: str) -> Optional[SystemSetting]:
        query = select(SystemSetting).where(SystemSetting.key == key)
        result = await self.db.execute(query)
        return result.scalars().first()

    async def update_setting(self, key: str, update_data: SystemSettingUpdate) -> Optional[SystemSetting]:
        setting = await self.get_setting_by_key(key)
        if not setting:
            # Upsert behavior for simplicity
            setting = SystemSetting(key=key, value=update_data.value or "")
            self.db.add(setting)
        
        if update_data.value is not None:
            setting.value = update_data.value
        if update_data.description is not None:
            setting.description = update_data.description
        if update_data.is_public is not None:
            setting.is_public = update_data.is_public

        await self.db.commit()
        await self.db.refresh(setting)
        return setting
