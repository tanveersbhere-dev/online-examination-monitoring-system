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
from app.services.exceptions import QuestionPaperNotFoundError, AuthorizationError, InvalidExamStateError

logger = logging.getLogger(__name__)

class QuestionPaperService:
    def __init__(self, db: AsyncSession):
        self.repository = QuestionPaperRepository(db)
        
        # Ensure upload directory exists
        self.upload_dir = os.path.join(settings.UPLOAD_DIR, "question_papers")
        os.makedirs(self.upload_dir, exist_ok=True)

    def _check_ownership(self, paper: QuestionPaper, current_user: UserResponse):
        """Checks if the user has permission to modify the paper."""
        if current_user.role and current_user.role.name.upper() == "ADMIN":
            return
        if paper.uploaded_by != current_user.id:
            raise AuthorizationError("You do not have permission to modify this question paper.")

    def _validate_file(self, file: UploadFile) -> str:
        """Validates file extension and basic mime type."""
        allowed_extensions = {".pdf", ".docx", ".txt"}
        file_ext = os.path.splitext(file.filename)[1].lower() if file.filename else ""
        if file_ext not in allowed_extensions:
            raise ValueError(f"Unsupported file extension: {file_ext}. Allowed: {', '.join(allowed_extensions)}")
        
        # Basic MIME type validation
        mime_type = file.content_type or "application/octet-stream"
        if "pdf" not in mime_type and "word" not in mime_type and "text" not in mime_type:
            raise ValueError(f"Unsupported MIME type: {mime_type}")
            
        return file_ext, mime_type

    async def create_paper(
        self, title: str, course_name: str, file: UploadFile, current_user: UserResponse, description: Optional[str] = None
    ) -> QuestionPaper:
        """Saves the file to disk and creates a DB record."""
        # Note: Route dependency should ensure only Admin/Examiner get here.
        file_ext, mime_type = self._validate_file(file)
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(self.upload_dir, unique_filename)
        
        try:
            # Save file to disk
            file_size_bytes = 0
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            file_size_bytes = os.path.getsize(file_path)
                
            # Create DB record
            paper = await self.repository.create(
                title=title,
                course_name=course_name,
                description=description,
                uploaded_by=current_user.id,
                file_path=file_path,
                file_size_bytes=file_size_bytes,
                mime_type=mime_type,
                revision=1,
                status="DRAFT"
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

    async def get_papers(
        self, skip: int = 0, limit: int = 100, course_name: Optional[str] = None, current_user: Optional[UserResponse] = None
    ) -> List[QuestionPaper]:
        """Lists papers, optionally filtering by course and user ownership."""
        uploaded_by = None
        if current_user and current_user.role and current_user.role.name.upper() == "EXAMINER":
            uploaded_by = current_user.id

        if course_name:
            return await self.repository.get_by_course(course_name, skip, limit, uploaded_by=uploaded_by)
        return await self.repository.get_all_papers(skip, limit, uploaded_by=uploaded_by)

    async def check_paper_in_use(self, paper: QuestionPaper) -> bool:
        """Checks if a paper is in active use by an ongoing examination or student attempts, or explicitly locked."""
        # Only explicitly locked or archived papers cannot be modified directly
        if paper.status in ["LOCKED", "ARCHIVED"]:
            return True
            
        from app.models.exam import Exam
        from app.models.exam_session import ExamSession
        from sqlalchemy import select, func

        # Check if an active live exam is in progress
        exam_res = await self.repository.db.execute(
            select(Exam.id).where(
                Exam.question_paper_id == paper.id,
                Exam.status.in_(["RUNNING", "PAUSED"])
            )
        )
        if exam_res.scalars().first():
            return True

        # Check if any student attempt sessions exist for this paper
        session_res = await self.repository.db.execute(
            select(func.count(ExamSession.id))
            .join(Exam, ExamSession.exam_id == Exam.id)
            .where(Exam.question_paper_id == paper.id)
        )
        if (session_res.scalar() or 0) > 0:
            return True

        return False

    async def update_paper(
        self, paper_id: int, update_data: QuestionPaperUpdate, current_user: UserResponse
    ) -> QuestionPaper:
        """Updates a paper's metadata."""
        paper = await self.get_paper(paper_id)
        self._check_ownership(paper, current_user)
        
        if await self.check_paper_in_use(paper):
            raise InvalidExamStateError("This question paper is in active use by an examination attempt and cannot be modified. To make changes, please create a duplicate or new paper.")
        
        update_dict = update_data.model_dump(exclude_unset=True)
        updated_paper = await self.repository.update(paper, **update_dict)
        logger.info(f"Question paper {paper_id} updated by user {current_user.id}.")
        return updated_paper

    async def update_paper_file(
        self, paper_id: int, file: UploadFile, current_user: UserResponse
    ) -> QuestionPaper:
        """Updates a paper's physical file and increments the revision counter."""
        paper = await self.get_paper(paper_id)
        self._check_ownership(paper, current_user)
        
        if await self.check_paper_in_use(paper):
            raise InvalidExamStateError("This question paper is in active use by an examination attempt and cannot be modified. To make changes, please create a duplicate or new paper.")
        
        file_ext, mime_type = self._validate_file(file)
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        new_file_path = os.path.join(self.upload_dir, unique_filename)
        
        try:
            with open(new_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            file_size_bytes = os.path.getsize(new_file_path)
            
            # Delete old file
            old_file_path = paper.file_path
            if old_file_path and os.path.exists(old_file_path):
                try:
                    os.remove(old_file_path)
                except OSError as e:
                    logger.warning(f"Could not delete old file {old_file_path}: {e}")
            
            # Update DB record with new file, size, mime, and bumped revision
            updated_paper = await self.repository.update(
                paper,
                file_path=new_file_path,
                file_size_bytes=file_size_bytes,
                mime_type=mime_type,
                revision=paper.revision + 1
            )
            logger.info(f"Question paper {paper_id} file updated by user {current_user.id}. Revision is now {updated_paper.revision}.")
            return updated_paper
            
        except Exception as e:
            if os.path.exists(new_file_path):
                os.remove(new_file_path)
            raise e

    async def delete_paper(self, paper_id: int, current_user: UserResponse) -> None:
        """Deletes a paper from the DB and the filesystem."""
        paper = await self.get_paper(paper_id)
        self._check_ownership(paper, current_user)
        
        if await self.check_paper_in_use(paper):
            raise InvalidExamStateError("This question paper is in active use by an examination attempt and cannot be deleted.")
        
        file_path = paper.file_path
        
        # Delete from DB
        await self.repository.delete(paper_id)
        
        # Delete from filesystem
        if file_path:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Deleted file {file_path}")
            except OSError as e:
                logger.error(f"Failed to delete file {file_path}: {e}")
        
        logger.info(f"Question paper {paper_id} deleted by user {current_user.id}.")

    async def duplicate_paper(self, paper_id: int, current_user: UserResponse) -> QuestionPaper:
        """Creates an editable DRAFT duplicate of an existing paper."""
        paper = await self.get_paper(paper_id)
        self._check_ownership(paper, current_user)
        
        new_title = f"Copy of {paper.title}"
        if len(new_title) > 200:
            new_title = new_title[:195] + "..."
            
        new_paper = await self.repository.create(
            title=new_title,
            course_name=paper.course_name,
            description=paper.description,
            uploaded_by=current_user.id,
            mode=paper.mode,
            version=1,
            status="DRAFT"
        )
        
        if paper.mode == "STRUCTURED":
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload
            from app.models.exam_section_rule import ExamSectionRule
            from app.models.exam_question_rule import ExamQuestionRule
            from app.models.question_option import QuestionOption

            query = select(ExamSectionRule).options(
                selectinload(ExamSectionRule.question_rules).selectinload(ExamQuestionRule.options)
            ).where(ExamSectionRule.question_paper_id == paper.id)
            
            rules_res = await self.repository.db.execute(query)
            groups = rules_res.scalars().all()
            
            for g in groups:
                new_g = ExamSectionRule(
                    question_paper_id=new_paper.id,
                    section_index=g.section_index,
                    section_name=g.section_name,
                    section_type=g.section_type,
                    section_duration_minutes=g.section_duration_minutes,
                    navigation_policy=g.navigation_policy,
                    allow_return_to_previous=g.allow_return_to_previous,
                    lock_after_timeout=g.lock_after_timeout,
                    randomize_questions=g.randomize_questions,
                    require_completion_before_next=g.require_completion_before_next,
                    section_weight=g.section_weight,
                    instructions=g.instructions
                )
                self.repository.db.add(new_g)
                await self.repository.db.flush()
                
                for q in g.question_rules:
                    new_q = ExamQuestionRule(
                        question_paper_id=new_paper.id,
                        section_rule_id=new_g.id,
                        question_index=q.question_index,
                        question_type=q.question_type,
                        marks=q.marks,
                        is_required=q.is_required,
                        question_text=q.question_text,
                        image_url=q.image_url,
                        explanation=q.explanation,
                        difficulty=q.difficulty,
                        character_limit=q.character_limit,
                        word_limit=q.word_limit,
                        attachment_allowed=q.attachment_allowed,
                        autosave=q.autosave,
                        individual_submission=q.individual_submission,
                        editable_after_submission=q.editable_after_submission,
                        allow_multiple_submissions=q.allow_multiple_submissions,
                        max_submission_count=q.max_submission_count,
                        allow_editing_until_final=q.allow_editing_until_final,
                        instructions=q.instructions
                    )
                    self.repository.db.add(new_q)
                    await self.repository.db.flush()
                    
                    for opt in q.options:
                        new_opt = QuestionOption(
                            question_rule_id=new_q.id,
                            option_text=opt.option_text,
                            is_correct=opt.is_correct
                        )
                        self.repository.db.add(new_opt)

            await self.repository.db.commit()
        elif paper.file_path and os.path.exists(paper.file_path):
            file_ext = os.path.splitext(paper.file_path)[1].lower()
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            new_file_path = os.path.join(self.upload_dir, unique_filename)
            shutil.copyfile(paper.file_path, new_file_path)
            file_size_bytes = os.path.getsize(new_file_path)
            
            await self.repository.update(
                new_paper,
                file_path=new_file_path,
                file_size_bytes=file_size_bytes,
                mime_type=paper.mime_type
            )
            
        logger.info(f"Question paper {paper_id} duplicated as {new_paper.id} by user {current_user.id}.")
        return new_paper

    async def publish_paper(self, paper_id: int, current_user: UserResponse) -> QuestionPaper:
        """Transitions paper from DRAFT to READY."""
        paper = await self.get_paper(paper_id)
        self._check_ownership(paper, current_user)
        
        if paper.status != "DRAFT":
            raise InvalidExamStateError("Only DRAFT papers can be published.")
            
        updated_paper = await self.repository.update(paper, status="READY")
        logger.info(f"Question paper {paper_id} published to READY by user {current_user.id}.")
        return updated_paper

    async def lock_paper(self, paper_id: int, current_user: UserResponse) -> QuestionPaper:
        """Transitions paper from READY to LOCKED."""
        paper = await self.get_paper(paper_id)
        self._check_ownership(paper, current_user)
        
        if paper.status != "READY":
            raise InvalidExamStateError("Only READY papers can be locked.")
            
        updated_paper = await self.repository.update(paper, status="LOCKED")
        logger.info(f"Question paper {paper_id} locked by user {current_user.id}.")
        return updated_paper

    async def archive_paper(self, paper_id: int, current_user: UserResponse) -> QuestionPaper:
        """Transitions paper from LOCKED to ARCHIVED."""
        paper = await self.get_paper(paper_id)
        self._check_ownership(paper, current_user)
        
        if paper.status != "LOCKED":
            raise InvalidExamStateError("Only LOCKED papers can be archived.")
            
        updated_paper = await self.repository.update(paper, status="ARCHIVED")
        logger.info(f"Question paper {paper_id} archived by user {current_user.id}.")
        return updated_paper
