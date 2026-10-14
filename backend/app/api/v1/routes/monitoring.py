from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.security.permissions import RequireAuthenticated, RequireExaminer
from app.schemas.user_auth import UserResponse
from app.schemas.monitoring import (
    MonitoringStatusResponse,
    MonitoringCurrentResponse,
    ActiveMonitoringSessionItem,
    MonitoringHealthResponse
)
from app.services.monitoring_service import MonitoringService
from app.models.exam_session import ExamSession
from app.models.exam import Exam
from app.core.config import settings

router = APIRouter()

async def _authorize_monitoring_access(exam_session_id: int, current_user: UserResponse, db: AsyncSession):
    """
    Authorize access to session monitoring data.
    - Admins: Unrestricted
    - Examiners: Must be creator or supervisor of the exam
    - Students: Only allowed if ENABLE_STUDENT_MONITORING_PREVIEW is True and session belongs to them
    """
    role_name = (current_user.role.name if current_user.role else "").upper()
    if role_name == "ADMIN":
        return

    exam_session_res = await db.execute(
        select(ExamSession)
        .options(selectinload(ExamSession.exam).selectinload(Exam.supervisors))
        .where(ExamSession.id == exam_session_id)
    )
    exam_session = exam_session_res.scalars().first()
    if not exam_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam session not found.")

    if role_name == "EXAMINER":
        is_creator = exam_session.exam and exam_session.exam.created_by == current_user.id
        is_supervisor = any(s.supervisor_id == current_user.id for s in getattr(exam_session.exam, "supervisors", [])) if exam_session.exam else False
        if not (is_creator or is_supervisor):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to monitor this exam session.")
        return

    if role_name == "STUDENT":
        if not settings.ENABLE_STUDENT_MONITORING_PREVIEW:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student live monitoring preview is disabled.")
        if exam_session.student_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized access to this session.")
        return

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized role.")

@router.get("/status", response_model=MonitoringStatusResponse)
async def get_status(
    exam_session_id: int,
    current_user: UserResponse = RequireAuthenticated,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve the high-level status of an active exam session."""
    await _authorize_monitoring_access(exam_session_id, current_user, db)
    return MonitoringService.get_status(exam_id=exam_session_id)

@router.get("/current", response_model=MonitoringCurrentResponse)
async def get_current(
    exam_session_id: int,
    current_user: UserResponse = RequireAuthenticated,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve detailed current metrics and timeline of an active exam session."""
    await _authorize_monitoring_access(exam_session_id, current_user, db)
    return await MonitoringService.get_current(exam_session_id, db)

@router.get("/active-sessions", response_model=List[ActiveMonitoringSessionItem])
async def get_active_sessions(
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """
    List all currently RUNNING exam sessions that the examiner is authorized to supervise.
    """
    is_admin = bool(current_user.role and current_user.role.name.upper() == "ADMIN")
    return await MonitoringService.get_active_sessions(
        db=db,
        examiner_id=current_user.id,
        is_admin=is_admin
    )

@router.get("/health/{exam_session_id}", response_model=MonitoringHealthResponse)
async def get_session_health(
    exam_session_id: int,
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve real-time monitoring health and processor diagnostic status for an active session.
    """
    return await MonitoringService.get_session_health(
        exam_session_id=exam_session_id,
        db=db
    )
