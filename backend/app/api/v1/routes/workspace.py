from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database.session import get_db
from app.schemas.user_auth import UserResponse
from app.schemas.workspace import (
    DashboardSummaryResponse, WorkspacePreferenceResponse, WorkspacePreferenceUpdate,
    ActivityResponse, NotificationResponse, NotificationReadUpdate, GlobalSearchResult
)
from app.services.workspace_service import WorkspaceService
from app.security.dependencies import get_current_user

router = APIRouter()

@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the aggregated dashboard summary data."""
    service = WorkspaceService(db)
    return await service.get_dashboard_summary(current_user.id)

@router.get("/activities", response_model=List[ActivityResponse])
async def get_activities(
    limit: int = 20,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get recent activities."""
    service = WorkspaceService(db)
    activities = await service.get_recent_activities(current_user.id, limit=limit)
    return activities

@router.get("/notifications", response_model=List[NotificationResponse])
async def get_notifications(
    limit: int = 20,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get recent notifications."""
    service = WorkspaceService(db)
    notifications = await service.get_recent_notifications(current_user.id, limit=limit)
    return notifications

@router.put("/notifications/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: int,
    data: NotificationReadUpdate,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark a notification as read or unread."""
    service = WorkspaceService(db)
    notif = await service.mark_notification_read(current_user.id, notification_id, data.is_read)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notif

@router.get("/preferences", response_model=WorkspacePreferenceResponse)
async def get_preferences(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user workspace preferences."""
    service = WorkspaceService(db)
    pref = await service.get_or_create_preferences(current_user.id)
    return pref

@router.put("/preferences", response_model=WorkspacePreferenceResponse)
async def update_preferences(
    data: WorkspacePreferenceUpdate,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user workspace preferences."""
    service = WorkspaceService(db)
    pref = await service.update_preferences(current_user.id, data)
    return pref

@router.get("/search", response_model=List[GlobalSearchResult])
async def global_search(
    q: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Global search foundation endpoint."""
    # Foundation only. Returns empty for now, to be extended by future modules.
    return []
