from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.security.permissions import RequireExaminer, RequireAuthenticated
from app.schemas.user_auth import UserResponse
from app.schemas.violation import ViolationCreate, ViolationUpdate, ViolationResponse
from app.services.violation_service import ViolationService
from app.services.exceptions import ViolationNotFoundError
from app.repositories.exceptions import EntityNotFoundError

router = APIRouter()

@router.post("", response_model=ViolationResponse, status_code=status.HTTP_201_CREATED)
async def create_violation(
    violation_in: ViolationCreate,
    current_user: UserResponse = RequireAuthenticated,
    db: AsyncSession = Depends(get_db)
):
    """Create a new violation (usually by AI system)."""
    service = ViolationService(db)
    try:
        return await service.create_violation(violation_in)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("", response_model=List[ViolationResponse])
async def filter_violations(
    exam_id: Optional[int] = None,
    student_id: Optional[int] = None,
    severity: Optional[str] = None,
    violation_type: Optional[str] = None,
    violation_status: Optional[str] = Query(None, alias="status"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """Filter violations with multiple optional parameters. Requires Admin/Examiner."""
    service = ViolationService(db)
    return await service.filter_violations(
        exam_id=exam_id,
        student_id=student_id,
        severity=severity,
        violation_type=violation_type,
        status=violation_status,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit
    )

@router.get("/{violation_id}", response_model=ViolationResponse)
async def get_violation(
    violation_id: int,
    current_user: UserResponse = RequireAuthenticated,
    db: AsyncSession = Depends(get_db)
):
    """Return complete details for a specific violation."""
    try:
        service = ViolationService(db)
        return await service.get_by_id(violation_id)
    except ViolationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.patch("/{violation_id}", response_model=ViolationResponse)
async def update_violation(
    violation_id: int,
    update_data: ViolationUpdate,
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """Update violation details, primarily used for examiner review and status updates."""
    try:
        service = ViolationService(db)
        return await service.update_violation(violation_id, update_data)
    except ViolationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{violation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_violation(
    violation_id: int,
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """Delete a violation (only if not CONFIRMED). Requires Admin/Examiner."""
    try:
        service = ViolationService(db)
        await service.delete_violation(violation_id)
    except ViolationNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
