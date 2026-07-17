from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database.session import get_db
from app.schemas.user_auth import UserResponse
from app.security.permissions import RequireAdmin
from app.services.admin_service import AdminService
from app.schemas.admin import (
    SystemSettingUpdate, SystemSettingResponse, SystemLogResponse, AdminDashboardStats
)

router = APIRouter()

@router.get("/dashboard", response_model=AdminDashboardStats)
async def get_dashboard_stats(
    current_user: UserResponse = RequireAdmin,
    db: AsyncSession = Depends(get_db)
):
    """Get high-level metrics for the entire platform."""
    service = AdminService(db)
    return await service.get_dashboard_stats()

@router.get("/logs", response_model=List[SystemLogResponse])
async def get_system_logs(
    limit: int = 100,
    current_user: UserResponse = RequireAdmin,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve recent system logs."""
    service = AdminService(db)
    return await service.get_system_logs(limit)

@router.get("/settings", response_model=List[SystemSettingResponse])
async def get_platform_settings(
    current_user: UserResponse = RequireAdmin,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve all global platform settings."""
    service = AdminService(db)
    return await service.get_all_settings()

@router.put("/settings/{key}", response_model=SystemSettingResponse)
async def update_platform_setting(
    key: str,
    data: SystemSettingUpdate,
    current_user: UserResponse = RequireAdmin,
    db: AsyncSession = Depends(get_db)
):
    """Create or update a global platform setting by key."""
    service = AdminService(db)
    setting = await service.update_setting(key, data)
    if not setting:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update setting")
    return setting
