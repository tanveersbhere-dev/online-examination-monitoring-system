from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database.session import get_db
from app.security.permissions import RequireExaminer, RequireAuthenticated
from app.schemas.user_auth import UserResponse
from app.schemas.ai_session import AISessionCreate, AISessionUpdate, AISessionResponse
from app.services.ai_session_service import AISessionService
from app.repositories.exceptions import EntityNotFoundError

router = APIRouter()

class StatusUpdateRequest(BaseModel):
    status: str

@router.post("", response_model=AISessionResponse, status_code=status.HTTP_201_CREATED)
async def create_ai_session(
    session_in: AISessionCreate,
    current_user: UserResponse = RequireAuthenticated,
    db: AsyncSession = Depends(get_db)
):
    """Start a new AI session for an active exam session."""
    service = AISessionService(db)
    try:
        return await service.start_session(session_in)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("", response_model=List[AISessionResponse])
async def list_ai_sessions(
    skip: int = 0,
    limit: int = 100,
    session_state: Optional[str] = None,
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """List AI monitoring sessions with optional state filtering. Requires Admin/Examiner."""
    service = AISessionService(db)
    return await service.get_all_sessions(skip=skip, limit=limit, state=session_state)

@router.get("/{session_id}", response_model=AISessionResponse)
async def get_ai_session(
    session_id: int,
    current_user: UserResponse = RequireAuthenticated,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific AI session by ID."""
    service = AISessionService(db)
    try:
        return await service.get_session(session_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.patch("/{session_id}/status", response_model=AISessionResponse)
async def update_ai_session_status(
    session_id: int,
    status_update: StatusUpdateRequest,
    current_user: UserResponse = RequireAuthenticated,
    db: AsyncSession = Depends(get_db)
):
    """Transition AI session state (e.g., RUNNING, PAUSED, COMPLETED)."""
    service = AISessionService(db)
    try:
        return await service.update_status(session_id, status_update.status)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ai_session(
    session_id: int,
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """Delete an AI session if it is not active. Requires Admin or Examiner role."""
    service = AISessionService(db)
    try:
        await service.delete_session(session_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
