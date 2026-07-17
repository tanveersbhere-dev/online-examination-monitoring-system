from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class SystemSettingBase(BaseModel):
    key: str
    value: str
    description: Optional[str] = None
    is_public: bool = False

class SystemSettingCreate(SystemSettingBase):
    pass

class SystemSettingUpdate(BaseModel):
    value: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None

class SystemSettingResponse(SystemSettingBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class SystemLogResponse(BaseModel):
    id: int
    level: str
    message: str
    source: str
    timestamp: datetime

    class Config:
        from_attributes = True

class AdminDashboardStats(BaseModel):
    total_users: int
    total_exams: int
    total_violations: int
    active_sessions: int
    system_health: str
