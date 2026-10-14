from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database.session import get_db
from app.security.permissions import RequireExaminer, RequireAuthenticated
from app.schemas.user_auth import UserResponse
from app.schemas.exam_session import ExamSessionCreate, ExamSessionUpdate, ExamSessionResponse
from app.services.exam_session_service import ExamSessionService
from app.repositories.exceptions import EntityNotFoundError

router = APIRouter()

class StatusUpdateRequest(BaseModel):
    status: str

@router.post("", response_model=ExamSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_exam_session(
    session_in: ExamSessionCreate,
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """Create a new exam session for a student. Requires Admin or Examiner role."""
    service = ExamSessionService(db)
    try:
        return await service.create_session(session_in)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("", response_model=List[ExamSessionResponse])
async def list_exam_sessions(
    skip: int = 0,
    limit: int = 100,
    exam_id: Optional[int] = None,
    student_id: Optional[int] = None,
    session_status: Optional[str] = None,
    current_user: UserResponse = RequireAuthenticated,
    db: AsyncSession = Depends(get_db)
):
    """List exam sessions with optional filtering."""
    service = ExamSessionService(db)
    return await service.get_all_sessions(skip=skip, limit=limit, exam_id=exam_id, student_id=student_id, status=session_status)

@router.get("/{session_id}/review")
async def get_attempt_review(
    session_id: int,
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """
    Read-only attempt review endpoint for Examiners.
    Retrieves full attempt summary, paper definition with correct answers, 
    candidate submitted answers, runtime state history, session metadata, 
    and timeline events.
    """
    service = ExamSessionService(db)
    try:
        return await service.get_attempt_review_data(session_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

class EvaluationItemRequest(BaseModel):
    section_index: int
    question_index: int
    awarded_marks: Optional[float] = None
    examiner_comments: Optional[str] = ""

class EvaluationSaveRequest(BaseModel):
    evaluations: List[EvaluationItemRequest] = []
    finalize: Optional[bool] = False

@router.post("/{session_id}/evaluate")
async def save_attempt_evaluation(
    session_id: int,
    req: EvaluationSaveRequest,
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """Save draft evaluation or update subjective question scores for an attempt."""
    service = ExamSessionService(db)
    try:
        evals_list = [e.model_dump() for e in req.evaluations]
        return await service.save_evaluation(
            session_id=session_id,
            evaluations_list=evals_list,
            finalize=bool(req.finalize),
            examiner_id=current_user.id
        )
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/{session_id}/finalize-evaluation")
async def finalize_attempt_evaluation(
    session_id: int,
    req: Optional[EvaluationSaveRequest] = None,
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """Finalize evaluation for an attempt, locking it against future changes."""
    service = ExamSessionService(db)
    try:
        evals_list = [e.model_dump() for e in (req.evaluations if req and req.evaluations else [])]
        return await service.save_evaluation(
            session_id=session_id,
            evaluations_list=evals_list,
            finalize=True,
            examiner_id=current_user.id
        )
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/{session_id}", response_model=ExamSessionResponse)
async def get_exam_session(
    session_id: int,
    current_user: UserResponse = RequireAuthenticated,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific exam session by ID."""
    service = ExamSessionService(db)
    try:
        return await service.get_session(session_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.put("/{session_id}", response_model=ExamSessionResponse)
async def update_exam_session(
    session_id: int,
    session_in: ExamSessionUpdate,
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """Update exam session details. Requires Admin or Examiner role."""
    service = ExamSessionService(db)
    try:
        return await service.update_session(session_id, session_in)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.patch("/{session_id}/status", response_model=ExamSessionResponse)
async def update_session_status(
    session_id: int,
    status_update: StatusUpdateRequest,
    current_user: UserResponse = RequireAuthenticated,
    db: AsyncSession = Depends(get_db)
):
    """Transition exam session status."""
    service = ExamSessionService(db)
    try:
        return await service.update_status(session_id, status_update.status)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exam_session(
    session_id: int,
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """Delete an exam session if it is not active. Requires Admin or Examiner role."""
    service = ExamSessionService(db)
    try:
        await service.delete_session(session_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
