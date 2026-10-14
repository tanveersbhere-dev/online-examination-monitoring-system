from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

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
        student = await service.create_student(data)
        res = StudentRepoResponse.model_validate(student)
        res.has_face_image = bool(student.face_image_path)
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/with-photo", response_model=StudentRepoResponse, status_code=status.HTTP_201_CREATED)
async def create_student_with_photo(
    registration_number: str = Form(...),
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(None),
    department: str = Form(None),
    program: str = Form(None),
    semester: int = Form(None),
    batch: str = Form(None),
    section: str = Form(None),
    face_image: UploadFile = File(None),
    service: StudentRepositoryService = Depends(get_service)
):
    """Create student with optional reference photo."""
    try:
        data = StudentRepoCreate(
            registration_number=registration_number,
            full_name=full_name,
            email=email,
            phone=phone,
            department=department,
            program=program,
            semester=semester,
            batch=batch,
            section=section
        )
        image_bytes = await face_image.read() if face_image else None
        image_fn = face_image.filename if face_image else None
        student = await service.create_student_with_image(data, image_bytes, image_fn)
        res = StudentRepoResponse.model_validate(student)
        res.has_face_image = bool(student.face_image_path)
        return res
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
        student = await service.update_student(student_id, data)
        res = StudentRepoResponse.model_validate(student)
        res.has_face_image = bool(student.face_image_path)
        return res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{student_id}")
async def delete_student(
    student_id: int,
    service: StudentRepositoryService = Depends(get_service)
):
    """Soft delete (archive) a student."""
    try:
        await service.delete_student(student_id)
        return {"message": "Student archived successfully"}
    except ValueError as e:
        status_code = status.HTTP_404_NOT_FOUND if "not found" in str(e).lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(e))

@router.post("/{student_id}/reactivate", response_model=StudentRepoResponse)
async def reactivate_student(
    student_id: int,
    service: StudentRepositoryService = Depends(get_service)
):
    """Reactivate an archived student."""
    try:
        student = await service.reactivate_student(student_id)
        res = StudentRepoResponse.model_validate(student)
        res.has_face_image = bool(student.face_image_path)
        return res
    except ValueError as e:
        status_code = status.HTTP_404_NOT_FOUND if "not found" in str(e).lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(e))

@router.post("/import/preview", response_model=ImportPreviewResponse)
async def preview_import(
    file: UploadFile = File(...),
    service: StudentRepositoryService = Depends(get_service)
):
    """Preview a CSV import."""
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV (.csv) files are supported.")
        
    try:
        content = await file.read()
        try:
            decoded = content.decode('utf-8-sig')
        except UnicodeDecodeError:
            decoded = content.decode('latin-1')
        return await service.preview_import(decoded)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to parse CSV file: {str(e)}")

@router.post("/import/confirm")
async def confirm_import(
    data: Optional[str] = Form(None),
    photos_zip: UploadFile = File(None),
    json_data: Optional[List[StudentImportRow]] = None,
    service: StudentRepositoryService = Depends(get_service)
):
    """Confirm and execute the import with optional photos ZIP."""
    import json
    rows: List[StudentImportRow] = []
    if json_data:
        rows = json_data
    elif data:
        parsed = json.loads(data)
        rows = [StudentImportRow.model_validate(r) for r in parsed]

    zip_bytes = await photos_zip.read() if photos_zip else None
    await service.confirm_import(rows, zip_bytes)
    return {"message": "Import successful"}

@router.post("/bulk-action")
async def bulk_action(
    data: BulkActionRequest,
    service: StudentRepositoryService = Depends(get_service)
):
    """Perform bulk actions."""
    try:
        await service.bulk_action(data.student_ids, data.action)
        return {"message": f"Bulk {data.action} successful"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
