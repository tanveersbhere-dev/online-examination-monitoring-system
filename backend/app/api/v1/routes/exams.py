from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.security.permissions import RequireExaminer, RequireAuthenticated
from app.security.dependencies import get_current_user
from app.schemas.exam import ExamCreate, ExamUpdate, ExamResponse, QuestionPaperResponse, AssignStudentsRequest
from app.schemas.runtime_rules import RuntimeRulesUpdate
from app.schemas.user_auth import UserResponse
from app.services.exam_service import ExamService
from app.services.exceptions import ExamNotFoundError, InvalidExamStateError, ScheduleConflictError, QuestionPaperError, AISessionError
from app.repositories.exceptions import EntityNotFoundError

router = APIRouter()


# --- EXAMS ---

@router.post("", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
async def create_exam(
    exam_in: ExamCreate,
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """Create a new exam. Requires EXAMINER role."""
    try:
        service = ExamService(db)
        return await service.create_exam(creator_id=current_user.id, exam_in=exam_in)
    except QuestionPaperError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ScheduleConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

@router.get("", response_model=List[ExamResponse])
async def get_exams(
    skip: int = 0,
    limit: int = 100,
    course_name: Optional[str] = None,
    status: Optional[str] = None,
    current_user: UserResponse = RequireAuthenticated,
    db: AsyncSession = Depends(get_db)
):
    """List all exams. Requires valid authentication."""
    service = ExamService(db)
    return await service.get_all_exams(skip=skip, limit=limit, course_name=course_name, status=status)

@router.get("/upcoming", response_model=List[ExamResponse])
async def get_upcoming_exams(
    skip: int = 0,
    limit: int = 100,
    current_user: UserResponse = RequireAuthenticated,
    db: AsyncSession = Depends(get_db)
):
    """List upcoming scheduled exams."""
    service = ExamService(db)
    return await service.get_upcoming_exams(skip=skip, limit=limit)

@router.get("/{exam_id}", response_model=ExamResponse)
async def get_exam(
    exam_id: int,
    current_user: UserResponse = RequireAuthenticated,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific exam."""
    try:
        service = ExamService(db)
        return await service.get_exam(exam_id)
    except ExamNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.put("/{exam_id}", response_model=ExamResponse)
async def update_exam(
    exam_id: int,
    exam_in: ExamUpdate,
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """Update exam configuration. Requires EXAMINER role."""
    try:
        service = ExamService(db)
        return await service.update_exam(exam_id, current_user.id, exam_in)
    except ExamNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidExamStateError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ScheduleConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

@router.put("/{exam_id}/runtime-rules", response_model=ExamResponse)
async def update_runtime_rules(
    exam_id: int,
    rules_in: RuntimeRulesUpdate,
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """Update runtime rules configuration. Requires EXAMINER role."""
    try:
        service = ExamService(db)
        return await service.update_runtime_rules(exam_id=exam_id, creator_id=current_user.id, rules_in=rules_in)
    except ExamNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exam(
    exam_id: int,
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """Delete an exam. Requires EXAMINER role."""
    try:
        service = ExamService(db)
        await service.delete_exam(exam_id, current_user.id)
    except ExamNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidExamStateError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/{exam_id}/students", status_code=status.HTTP_200_OK)
async def assign_students(
    exam_id: int,
    request: AssignStudentsRequest,
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """Assign existing students to an exam. Requires EXAMINER role."""
    try:
        service = ExamService(db)
        added_count = await service.assign_repository_students(exam_id, request.student_ids, current_user.id)
        return {"detail": f"Successfully assigned {added_count} students to the exam."}
    except ExamNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

# --- AI SESSION LIFECYCLE ---

@router.patch("/{exam_id}/start", response_model=ExamResponse)
async def start_exam(
    exam_id: int,
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """Start an exam and initialize AI Session."""
    try:
        service = ExamService(db)
        return await service.start_exam(exam_id, current_user.id)
    except ExamNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidExamStateError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except AISessionError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.patch("/{exam_id}/pause", response_model=ExamResponse)
async def pause_exam(
    exam_id: int,
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """Pause an active exam and its AI Session."""
    try:
        service = ExamService(db)
        return await service.pause_exam(exam_id, current_user.id)
    except ExamNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidExamStateError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except AISessionError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.patch("/{exam_id}/resume", response_model=ExamResponse)
async def resume_exam(
    exam_id: int,
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """Resume a paused exam and its AI Session."""
    try:
        service = ExamService(db)
        return await service.resume_exam(exam_id, current_user.id)
    except ExamNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidExamStateError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except AISessionError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.patch("/{exam_id}/complete", response_model=ExamResponse)
async def complete_exam(
    exam_id: int,
    current_user: UserResponse = RequireExaminer,
    db: AsyncSession = Depends(get_db)
):
    """Complete an exam and gracefully shutdown the AI Session."""
    try:
        service = ExamService(db)
        return await service.complete_exam(exam_id, current_user.id)
    except ExamNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidExamStateError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except AISessionError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/{exam_id}/questions", status_code=status.HTTP_200_OK)
async def get_exam_questions(
    exam_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get mocked structured questions for the exam (for FYP demonstration)."""
    # Verify exam exists
    service = ExamService(db)
    exam = await service.get_exam(exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
        
    return {
        "questions": [
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
    }
