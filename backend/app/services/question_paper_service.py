import os
import uuid
import shutil
import logging
from typing import List, Optional
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.question_paper import QuestionPaper
from app.repositories.question_paper_repository import QuestionPaperRepository
from app.schemas.question_paper import QuestionPaperUpdate
from app.schemas.user_auth import UserResponse
from app.services.exceptions import QuestionPaperNotFoundError, AuthorizationError

logger = logging.getLogger(__name__)

class QuestionPaperService:
    def __init__(self, db: AsyncSession):
        self.repository = QuestionPaperRepository(db)
        
        # Ensure upload directory exists
        self.upload_dir = os.path.join(settings.UPLOAD_DIR, "question_papers")
        os.makedirs(self.upload_dir, exist_ok=True)

    def _check_ownership(self, paper: QuestionPaper, current_user: UserResponse):
        """Checks if the user has permission to modify the paper."""
        if current_user.role and current_user.role.name == "Admin":
            return
        if paper.uploaded_by != current_user.id:
            raise AuthorizationError("You do not have permission to modify this question paper.")

    async def create_paper(
        self, title: str, course_name: str, file: UploadFile, current_user: UserResponse
    ) -> QuestionPaper:
        """Saves the file to disk and creates a DB record."""
        # Note: Route dependency should ensure only Admin/Examiner get here.
        file_ext = os.path.splitext(file.filename)[1] if file.filename else ""
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(self.upload_dir, unique_filename)
        
        try:
            # Save file to disk
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
                
            # Create DB record
            paper = await self.repository.create(
                title=title,
                course_name=course_name,
                uploaded_by=current_user.id,
                file_path=file_path
            )
            logger.info(f"Question paper '{title}' created successfully by user {current_user.id}.")
            return paper
        except Exception as e:
            logger.error(f"Failed to create question paper: {e}")
            # Clean up file if DB insertion failed
            if os.path.exists(file_path):
                os.remove(file_path)
            raise

    async def get_paper(self, paper_id: int) -> QuestionPaper:
        """Retrieves a paper by ID."""
        paper = await self.repository.get_by_id(paper_id)
        if not paper:
            raise QuestionPaperNotFoundError(f"QuestionPaper with id {paper_id} not found.")
        return paper

    async def get_papers(self, skip: int = 0, limit: int = 100, course_name: Optional[str] = None) -> List[QuestionPaper]:
        """Lists papers, optionally filtering by course."""
        if course_name:
            return await self.repository.get_by_course(course_name, skip, limit)
        return await self.repository.get_all_papers(skip, limit)

    async def update_paper(
        self, paper_id: int, update_data: QuestionPaperUpdate, current_user: UserResponse
    ) -> QuestionPaper:
        """Updates a paper's metadata."""
        paper = await self.get_paper(paper_id)
        self._check_ownership(paper, current_user)
        
        update_dict = update_data.model_dump(exclude_unset=True)
        updated_paper = await self.repository.update(paper, **update_dict)
        logger.info(f"Question paper {paper_id} updated by user {current_user.id}.")
        return updated_paper

    async def delete_paper(self, paper_id: int, current_user: UserResponse) -> None:
        """Deletes a paper from the DB and the filesystem."""
        paper = await self.get_paper(paper_id)
        self._check_ownership(paper, current_user)
        
        file_path = paper.file_path
        
        # Delete from DB
        await self.repository.delete(paper_id)
        
        # Delete from filesystem
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted file {file_path}")
        except OSError as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
        
        logger.info(f"Question paper {paper_id} deleted by user {current_user.id}.")
