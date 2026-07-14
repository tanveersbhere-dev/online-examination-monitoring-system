from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.security.permissions import RequireExaminer
from app.schemas.user_auth import UserResponse
from app.schemas.violation import ViolationResponse
from app.services.violation_service import ViolationService
from app.services.exceptions import ViolationNotFoundError

router = APIRouter()

@router.get("", response_model=List[ViolationResponse])
async def list_violations(
    exam_session_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """List all violations for a specific exam session."""
    service = ViolationService(db)
    return await service.get_all_by_session(exam_session_id=exam_session_id, skip=skip, limit=limit)

@router.get("/{violation_id}", response_model=ViolationResponse)
async def get_violation(
    violation_id: int,
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """Return complete details for a specific violation."""
    try:
        service = ViolationService(db)
        return await service.get_by_id(violation_id)
    except ViolationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
