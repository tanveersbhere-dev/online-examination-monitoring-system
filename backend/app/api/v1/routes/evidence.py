from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.security.permissions import RequireExaminer, RequireAuthenticated
from app.schemas.user_auth import UserResponse
from app.schemas.evidence import EvidenceCreate, EvidenceUpdate, EvidenceResponse
from app.services.evidence_service import EvidenceService, EvidenceNotFoundError
from app.repositories.exceptions import EntityNotFoundError

router = APIRouter()

@router.post("", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
async def create_evidence(
    evidence_in: EvidenceCreate,
    current_user: UserResponse = RequireAuthenticated,
    db: AsyncSession = Depends(get_db)
):
    """Create a new evidence record tied to a violation."""
    service = EvidenceService(db)
    try:
        return await service.create_evidence(evidence_in)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("", response_model=List[EvidenceResponse])
async def filter_evidence(
    violation_id: Optional[int] = None,
    evidence_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """Filter evidence by violation or type. Requires Admin/Examiner."""
    service = EvidenceService(db)
    return await service.filter_evidence(
        violation_id=violation_id,
        evidence_type=evidence_type,
        skip=skip,
        limit=limit
    )

@router.get("/{evidence_id}", response_model=EvidenceResponse)
async def get_evidence(
    evidence_id: int,
    current_user: UserResponse = RequireAuthenticated,
    db: AsyncSession = Depends(get_db)
):
    """Return complete details for a specific evidence record."""
    try:
        service = EvidenceService(db)
        return await service.get_by_id(evidence_id)
    except EvidenceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.patch("/{evidence_id}", response_model=EvidenceResponse)
async def update_evidence(
    evidence_id: int,
    update_data: EvidenceUpdate,
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """Update evidence (e.g. metadata or file paths). Immutable if violation CONFIRMED."""
    try:
        service = EvidenceService(db)
        return await service.update_evidence(evidence_id, update_data)
    except EvidenceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evidence(
    evidence_id: int,
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """Delete an evidence record. Immutable if violation CONFIRMED."""
    try:
        service = EvidenceService(db)
        await service.delete_evidence(evidence_id)
    except EvidenceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
