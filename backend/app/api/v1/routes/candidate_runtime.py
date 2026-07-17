from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.security.dependencies import get_current_user
from app.schemas.user_auth import UserResponse
from app.services.exam_session_service import ExamSessionService
from app.repositories.exceptions import EntityNotFoundError

router = APIRouter()

@router.post("/start", response_model=Dict[str, Any])
async def start_runtime_session(
    exam_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Initialize or resume an exam runtime session.
    """
    try:
        service = ExamSessionService(db)
        result = await service.start_runtime_session(exam_id, current_user.id)
        
        # We will append the mock JSON payload for the UI here to respect the existing UI
        result["questions"] = [
            {
                "id": "q1",
                "text": "What is the primary role of the Application Layer in the OSI model?",
                "options": [
                    "Routing packets",
                    "Network interface",
                    "End-user application interaction",
                    "Bit transmission"
                ]
            },
            {
                "id": "q2",
                "text": "Explain the difference between TCP and UDP.",
                "options": [
                    "TCP is connectionless, UDP is connection-oriented",
                    "TCP is reliable, UDP is faster but unreliable",
                    "TCP is for streaming, UDP is for file transfer",
                    "There is no difference"
                ]
            },
            {
                "id": "q3",
                "text": "Which HTTP method is idempotent?",
                "options": ["POST", "PUT", "PATCH", "CONNECT"]
            },
            {
                "id": "q4",
                "text": "What does ACID stand for in databases?",
                "options": [
                    "Atomicity, Consistency, Isolation, Durability",
                    "Accuracy, Consistency, Information, Data",
                    "Atomicity, Concurrency, Isolation, Durability",
                    "Association, Connection, Integration, Data"
                ]
            }
        ]
        
        return result
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/heartbeat", status_code=status.HTTP_200_OK)
async def runtime_heartbeat(
    exam_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Heartbeat to keep session alive and sync state.
    """
    # Just verify session is active, no heavy writes to avoid DB locks
    service = ExamSessionService(db)
    existing = await service.session_repo.get_by_student_and_exam(current_user.id, exam_id)
    if not existing or existing.status != "RUNNING":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No running session found.")
    return {"status": "ok"}


@router.post("/submit", status_code=status.HTTP_200_OK)
async def submit_runtime_session(
    exam_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit and conclude the exam session.
    """
    try:
        service = ExamSessionService(db)
        session_obj = await service.submit_runtime_session(exam_id, current_user.id)
        return {"detail": "Exam submitted successfully", "session_id": session_obj.id}
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
