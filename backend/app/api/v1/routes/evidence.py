from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.security.permissions import RequireExaminer
from app.schemas.user_auth import UserResponse
from app.schemas.evidence import EvidenceResponse
from app.services.evidence_service import EvidenceService
from app.services.exceptions import EvidenceNotFoundError

router = APIRouter()

@router.get("", response_model=List[EvidenceResponse])
async def list_evidence(
    skip: int = 0,
    limit: int = 100,
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """List all evidence. (In a real scenario, typically filtered by exam_session_id)"""
    service = EvidenceService(db)
    return await service.get_all(skip=skip, limit=limit)

@router.get("/{evidence_id}", response_model=EvidenceResponse)
async def get_evidence(
    evidence_id: int,
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """Return metadata for a specific evidence item."""
    try:
        service = EvidenceService(db)
        return await service.get_by_id(evidence_id)
    except EvidenceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
