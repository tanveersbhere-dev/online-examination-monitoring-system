import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.question_paper import QuestionPaperResponse, QuestionPaperUpdate
from app.schemas.user_auth import UserResponse
from app.services.question_paper_service import QuestionPaperService
from app.security.dependencies import get_current_user
from app.security.permissions import RoleChecker
from app.services.exceptions import QuestionPaperNotFoundError, AuthorizationError

router = APIRouter()

# Allow Admin or Examiner to manage papers
RequireManager = Depends(RoleChecker(["Admin", "Examiner"]))

@router.post("/", response_model=QuestionPaperResponse, status_code=status.HTTP_201_CREATED)
async def upload_question_paper(
    title: str = Form(...),
    course_name: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = RequireManager
):
    service = QuestionPaperService(db)
    try:
        paper = await service.create_paper(title, course_name, file, current_user)
        return paper
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/", response_model=List[QuestionPaperResponse])
async def get_question_papers(
    skip: int = 0,
    limit: int = 100,
    course_name: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)  # Anyone authenticated can view list
):
    service = QuestionPaperService(db)
    return await service.get_papers(skip, limit, course_name)

@router.get("/{paper_id}", response_model=QuestionPaperResponse)
async def get_question_paper(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    service = QuestionPaperService(db)
    try:
        return await service.get_paper(paper_id)
    except QuestionPaperNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/{paper_id}/download")
async def download_question_paper(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    service = QuestionPaperService(db)
    try:
        paper = await service.get_paper(paper_id)
        if not os.path.exists(paper.file_path):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File physically missing on server.")
        return FileResponse(path=paper.file_path, filename=os.path.basename(paper.file_path))
    except QuestionPaperNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.put("/{paper_id}", response_model=QuestionPaperResponse)
async def update_question_paper(
    paper_id: int,
    update_data: QuestionPaperUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = RequireManager
):
    service = QuestionPaperService(db)
    try:
        return await service.update_paper(paper_id, update_data, current_user)
    except QuestionPaperNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question_paper(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = RequireManager
):
    service = QuestionPaperService(db)
    try:
        await service.delete_paper(paper_id, current_user)
    except QuestionPaperNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
