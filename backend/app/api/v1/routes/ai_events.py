import logging
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.security.dependencies import get_current_user
from app.models.user import User
from app.repositories.exam_session_repository import ExamSessionRepository
from app.schemas.cv_event import CVEventIngestRequest
from app.schemas.ai_event import AIEventDTO
from app.services.ai_event_processor import AIEventProcessor

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Verify CV Integration API is responsive."""
    return {"status": "ok", "message": "CV Integration Gateway is online."}

@router.post("/ingest", status_code=status.HTTP_202_ACCEPTED)
async def ingest_cv_event(
    request: CVEventIngestRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Ingests an external CV detection event.
    Authenticates, normalizes, and pipes it to the AIEventProcessor in the background.
    """
    exam_session_repo = ExamSessionRepository(db)
    exam_session = await exam_session_repo.get_by_id(request.session_id)
    
    if not exam_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam Session not found"
        )
        
    role_name = current_user.role.name.upper()

    # RBAC: Session Ownership Validation
    if role_name == "STUDENT" and exam_session.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to post events for this session"
        )
    elif role_name == "EXAMINER" and exam_session.exam.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to supervise this session"
        )
    # Admin bypassed

    # Normalization
    normalized_event_type = request.event_type.strip().upper()
    
    # Map to DTO
    dto = AIEventDTO(
        event_type=normalized_event_type,
        timestamp=request.timestamp,
        exam_session_id=request.session_id,
        severity="INFO", # Default, overridden by Processor based on EVENT_CONFIG
        source_module="ExternalCVEnhancer",
        confidence=request.confidence,
        payload=request.metadata
    )

    # Queue for processing (non-blocking)
    background_tasks.add_task(AIEventProcessor.process_event, dto)
    
    return {"status": "accepted", "message": "Event queued for processing"}
