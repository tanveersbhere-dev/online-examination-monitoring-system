from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.security.permissions import RequireExaminer
from app.models.user import User
from app.services.exam_service import ExamService
from app.schemas.exam_domain import (
    ExamCreate, 
    ExamUpdate, 
    ExamResponse,
    ExamAssignmentRequest,
    ExamSupervisorRequest
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

def get_exam_service(db: AsyncSession = Depends(get_db)) -> ExamService:
    return ExamService(db)

@router.post("/", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
async def create_draft_exam(
    exam_in: ExamCreate,
    current_user: User = RequireExaminer,
    service: ExamService = Depends(get_exam_service)
) -> Any:
    """Create a new draft exam."""
    return await service.create_draft_exam(current_user.id, exam_in)

@router.get("/", response_model=List[ExamResponse])
async def list_exams(
    skip: int = 0,
    limit: int = 100,
    current_user: User = RequireExaminer,
    service: ExamService = Depends(get_exam_service)
) -> Any:
    """List all exams owned by the current examiner."""
    return await service.list_domain_exams(current_user.id, skip, limit)

@router.get("/{exam_id}", response_model=ExamResponse)
async def get_exam(
    exam_id: int,
    current_user: User = RequireExaminer,
    service: ExamService = Depends(get_exam_service)
) -> Any:
    """Get a specific exam by ID."""
    return await service.get_domain_exam(exam_id, current_user.id)

@router.put("/{exam_id}", response_model=ExamResponse)
async def update_exam(
    exam_id: int,
    exam_in: ExamUpdate,
    current_user: User = RequireExaminer,
    service: ExamService = Depends(get_exam_service)
) -> Any:
    """Update a draft exam's properties and configurations."""
    return await service.update_domain_exam(exam_id, current_user.id, exam_in)

@router.get("/{exam_id}/students", response_model=List[int])
async def get_assigned_students(
    exam_id: int,
    current_user: User = RequireExaminer,
    service: ExamService = Depends(get_exam_service)
) -> Any:
    """Get assigned students for an exam."""
    return await service.get_assigned_students(exam_id, current_user.id)

@router.post("/{exam_id}/students", status_code=status.HTTP_200_OK)
async def assign_students(
    exam_id: int,
    assignment_req: ExamAssignmentRequest,
    current_user: User = RequireExaminer,
    service: ExamService = Depends(get_exam_service)
) -> Any:
    """Assign students from the repository to this exam."""
    count = await service.assign_repository_students(exam_id, assignment_req.student_ids, current_user.id)
    return {"message": f"Successfully assigned {count} students."}

@router.post("/{exam_id}/supervisors", status_code=status.HTTP_200_OK)
async def assign_supervisors(
    exam_id: int,
    supervisor_req: ExamSupervisorRequest,
    current_user: User = RequireExaminer,
    service: ExamService = Depends(get_exam_service)
) -> Any:
    """Assign supervisors to this exam."""
    count = await service.assign_supervisors(exam_id, supervisor_req.supervisor_ids, current_user.id)
    return {"message": f"Successfully assigned {count} supervisors."}

@router.post("/{exam_id}/publish", response_model=ExamResponse)
async def publish_exam(
    exam_id: int,
    current_user: User = RequireExaminer,
    service: ExamService = Depends(get_exam_service)
) -> Any:
    """Publish a draft exam, transitioning it to READY state."""
    return await service.publish_exam(exam_id, current_user.id)
