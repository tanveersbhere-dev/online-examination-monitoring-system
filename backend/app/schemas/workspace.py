from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# --- Preferences ---
class WorkspacePreferenceResponse(BaseModel):
    theme: str
    language: str
    timezone: str
    sidebar_collapsed: bool

    class Config:
        from_attributes = True

class WorkspacePreferenceUpdate(BaseModel):
    theme: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    sidebar_collapsed: Optional[bool] = None

# --- Activities ---
class ActivityResponse(BaseModel):
    id: int
    action_type: str
    description: str
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

# --- Notifications ---
class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    is_read: bool
    severity: str
    created_at: datetime

    class Config:
        from_attributes = True

class NotificationReadUpdate(BaseModel):
    is_read: bool

# --- Dashboard Summary ---
class StatCard(BaseModel):
    label: str
    value: str
    sub: str
    icon_name: str
    accent_color: str
    path: Optional[str] = None

class UpcomingExam(BaseModel):
    id: int
    name: str
    course: str
    scheduled_date: Optional[datetime] = None
    students_count: int

class DashboardSummaryResponse(BaseModel):
    stats: List[StatCard]
    upcoming_exams: List[UpcomingExam]
    recent_activities: List[ActivityResponse]
    recent_notifications: List[NotificationResponse]
    system_status: str

# --- Global Search ---
class GlobalSearchResult(BaseModel):
    id: int
    resource_type: str
    title: str
    subtitle: str
    url: str
