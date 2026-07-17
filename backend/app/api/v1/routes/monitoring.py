from fastapi import APIRouter, Depends, HTTPException, status
from app.security.permissions import RequireAuthenticated, RequireExaminer
from app.schemas.user_auth import UserResponse
from app.schemas.monitoring import MonitoringStatusResponse, MonitoringCurrentResponse
from app.services.monitoring_service import MonitoringService

router = APIRouter()

@router.get("/status", response_model=MonitoringStatusResponse)
async def get_status(
    exam_session_id: int,
    current_user: UserResponse = RequireExaminer
):
    """Retrieve the high-level status of an active exam session."""
    return MonitoringService.get_status(exam_id=exam_session_id)

from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db

@router.get("/current", response_model=MonitoringCurrentResponse)
async def get_current(
    exam_session_id: int,
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve detailed current metrics of an active exam session."""
    return await MonitoringService.get_current(exam_session_id, db)
