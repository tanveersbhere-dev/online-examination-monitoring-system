import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.security.permissions import RequireExaminer
from app.schemas.user_auth import UserResponse
from app.schemas.report import ReportSummaryItem, MonitoringReportResponse
from app.services.report_service import ReportService

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("", response_model=List[ReportSummaryItem])
async def list_reports(
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """List all completed exam sessions available for review."""
    service = ReportService(db)
    return await service.get_completed_reports_summary()

@router.get("/{exam_session_id}", response_model=MonitoringReportResponse)
async def get_report(
    exam_session_id: int,
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """Return the complete monitoring report for a specific exam session."""
    service = ReportService(db)
    report = await service.get_report(exam_session_id)
    if not report:
        logger.warning(f"Failed to generate report for ExamSession {exam_session_id} - Not found or not completed.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Report for ExamSession {exam_session_id} not found or exam is not completed."
        )
    logger.info(f"Report generated and viewed for ExamSession {exam_session_id} by Examiner {current_user.id}")
    return report

@router.get("/student/{student_id}", response_model=None)
async def get_student_analytics(
    student_id: int,
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """Return analytical data for a specific student across all completed exams."""
    service = ReportService(db)
    return await service.get_student_analytics(student_id)
