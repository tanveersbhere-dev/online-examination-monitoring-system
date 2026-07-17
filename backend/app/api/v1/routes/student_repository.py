from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database.session import get_db
from app.schemas.user_auth import UserResponse
from app.security.dependencies import get_current_user
from app.schemas.student_repository import (
    StudentRepoCreate, StudentRepoUpdate, StudentRepoResponse,
    ImportPreviewResponse, StudentImportRow, BulkActionRequest
)
from app.services.student_repository_service import StudentRepositoryService

router = APIRouter()

def get_service(current_user: UserResponse = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return StudentRepositoryService(db, current_user.id)

@router.get("", response_model=dict)
async def list_students(
    skip: int = 0,
    limit: int = 100,
    search: str = None,
    student_status: str = None,
    department: str = None,
    service: StudentRepositoryService = Depends(get_service)
):
    """List students in the repository."""
    students, total = await service.list_students(skip, limit, search, student_status, department)
    return {
        "items": [StudentRepoResponse.model_validate(s).model_dump() for s in students],
        "total": total
    }

@router.get("/{student_id}", response_model=StudentRepoResponse)
async def get_student(
    student_id: int,
    service: StudentRepositoryService = Depends(get_service)
):
    """Get a specific student."""
    student = await service.get_student(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")
    return student

@router.post("", response_model=StudentRepoResponse, status_code=status.HTTP_201_CREATED)
async def create_student(
    data: StudentRepoCreate,
    service: StudentRepositoryService = Depends(get_service)
):
    """Create a new student in the repository."""
    try:
        return await service.create_student(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{student_id}", response_model=StudentRepoResponse)
async def update_student(
    student_id: int,
    data: StudentRepoUpdate,
    service: StudentRepositoryService = Depends(get_service)
):
    """Update a student."""
    try:
        return await service.update_student(student_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student(
    student_id: int,
    service: StudentRepositoryService = Depends(get_service)
):
    """Soft delete (archive) a student."""
    try:
        await service.delete_student(student_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/import/preview", response_model=ImportPreviewResponse)
async def preview_import(
    file: UploadFile = File(...),
    service: StudentRepositoryService = Depends(get_service)
):
    """Preview a CSV import."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported for now.")
        
    content = await file.read()
    decoded = content.decode('utf-8')
    return await service.preview_import(decoded)

@router.post("/import/confirm")
async def confirm_import(
    data: List[StudentImportRow],
    service: StudentRepositoryService = Depends(get_service)
):
    """Confirm and execute the import."""
    await service.confirm_import(data)
    return {"message": "Import successful"}

@router.post("/bulk-action")
async def bulk_action(
    data: BulkActionRequest,
    service: StudentRepositoryService = Depends(get_service)
):
    """Perform bulk actions."""
    await service.bulk_action(data.student_ids, data.action)
    return {"message": f"Bulk {data.action} successful"}
