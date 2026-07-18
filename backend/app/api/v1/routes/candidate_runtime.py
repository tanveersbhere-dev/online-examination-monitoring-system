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


from app.schemas.runtime_state import RuntimeStateResponse

@router.get("/state", response_model=RuntimeStateResponse)
async def get_runtime_state(
    exam_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current runtime state for the active session"""
    try:
        service = ExamSessionService(db)
        session = await service.session_repo.get_by_student_and_exam(current_user.id, exam_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
            
        from app.services.runtime_state_service import RuntimeStateService
        state_service = RuntimeStateService(db)
        return await state_service.get_state(session.id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.put("/state/position", response_model=RuntimeStateResponse)
async def update_runtime_position(
    exam_id: int,
    section_index: int,
    question_index: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current execution position in the runtime state"""
    try:
        service = ExamSessionService(db)
        session = await service.session_repo.get_by_student_and_exam(current_user.id, exam_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
            
        from app.services.runtime_state_service import RuntimeStateService
        state_service = RuntimeStateService(db)
        return await state_service.update_position(session.id, section_index, question_index)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


from app.schemas.candidate_answer import CandidateAnswerResponse, CandidateAnswerUpdate
from typing import List

@router.get("/answers", response_model=List[CandidateAnswerResponse])
async def get_candidate_answers(
    exam_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all saved answers for the active exam session."""
    try:
        service = ExamSessionService(db)
        session = await service.session_repo.get_by_student_and_exam(current_user.id, exam_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
            
        from app.services.candidate_answer_service import CandidateAnswerService
        ans_service = CandidateAnswerService(db)
        return await ans_service.get_session_answers(session.id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/answers/{section_index}/{question_index}", response_model=CandidateAnswerResponse)
async def save_candidate_answer(
    exam_id: int,
    section_index: int,
    question_index: int,
    answer_in: CandidateAnswerUpdate,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Save or update a candidate's answer for a specific question."""
    try:
        service = ExamSessionService(db)
        session = await service.session_repo.get_by_student_and_exam(current_user.id, exam_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
            
        if session.status != "RUNNING":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Exam session is not active.")
            
        from app.services.candidate_answer_service import CandidateAnswerService
        ans_service = CandidateAnswerService(db)
        return await ans_service.save_answer(session.id, section_index, question_index, answer_in)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
