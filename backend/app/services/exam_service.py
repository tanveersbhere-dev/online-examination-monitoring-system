import os
import uuid
import logging
from typing import List, Optional
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.exam_session import ExamSession

from app.core.config import settings
from app.models.exam import Exam
from app.repositories.exam_repository import ExamRepository
from app.repositories.question_paper_repository import QuestionPaperRepository
from app.repositories.exceptions import EntityNotFoundError
from app.models.exam_assignment import ExamAssignment
from app.models.exam_supervisor import ExamSupervisor
from app.models.student import Student
from app.services.ai_session_manager import AISessionManager
from app.services.exceptions import (
    ExamNotFoundError, 
    InvalidExamStateError, 
    ScheduleConflictError, 
    QuestionPaperError,
    AISessionError
)
from app.schemas.exam import ExamCreate, ExamUpdate as OldExamUpdate, ExamResponse as OldExamResponse, QuestionPaperResponse
from app.schemas.exam_domain import ExamCreate as DomainExamCreate, ExamUpdate as DomainExamUpdate, ExamResponse as DomainExamResponse
from app.schemas.runtime_rules import RuntimeRulesUpdate

logger = logging.getLogger(__name__)

class ExamService:
    ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}

    def __init__(self, db: AsyncSession):
        self.db = db
        self.exam_repo = ExamRepository(db)
        self.paper_repo = QuestionPaperRepository(db)
        
        if not os.path.exists(settings.UPLOAD_DIR):
            os.makedirs(settings.UPLOAD_DIR)



    # --- EXAM LIFECYCLE MANAGEMENT (LEGACY) ---

    async def create_exam(self, creator_id: int, exam_in: ExamCreate) -> OldExamResponse:
        paper = await self.paper_repo.get_by_id(exam_in.question_paper_id)
        if not paper:
            raise QuestionPaperError(f"Question Paper {exam_in.question_paper_id} does not exist.")

        await self._check_schedule_conflict(
            course_name=exam_in.course_name,
            start=exam_in.scheduled_start,
            end=exam_in.scheduled_end
        )

        exam = await self.exam_repo.create(
            title=exam_in.title,
            course_name=exam_in.course_name,
            question_paper_id=exam_in.question_paper_id,
            scheduled_start=exam_in.scheduled_start,
            scheduled_end=exam_in.scheduled_end,
            duration_minutes=exam_in.duration_minutes,
            created_by=creator_id,
            status="DRAFT"
        )
        
        logger.info(f"Exam created successfully: ID {exam.id}")
        return OldExamResponse.model_validate(exam)

    async def _check_schedule_conflict(self, course_name, start, end, exclude_exam_id=None):
        query = select(Exam).filter(
            Exam.course_name == course_name,
            Exam.status.notin_(["CANCELLED", "COMPLETED"]),
            Exam.scheduled_start < end,
            Exam.scheduled_end > start
        )
        if exclude_exam_id:
            query = query.filter(Exam.id != exclude_exam_id)
            
        result = await self.db.execute(query)
        conflicts = result.scalars().all()
        if conflicts:
            raise ScheduleConflictError(f"Exam scheduling conflicts with existing exam(s) for course {course_name}.")

    async def get_exam(self, exam_id: int) -> OldExamResponse:
        try:
            exam = await self.exam_repo.get_by_id(exam_id)
            if not exam:
                raise ExamNotFoundError(f"Exam {exam_id} not found.")
            resp = OldExamResponse.model_validate(exam)
            
            # Get assigned students count
            count_result = await self.db.execute(select(func.count(ExamSession.id)).where(ExamSession.exam_id == exam_id))
            resp.assigned_students_count = count_result.scalar() or 0
            
            resp.ai_session_status = "ACTIVE" if exam.status in ["RUNNING", "PAUSED"] else "INACTIVE"
            return resp
        except EntityNotFoundError:
            raise ExamNotFoundError(f"Exam {exam_id} not found.")

    async def get_all_exams(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        course_name: Optional[str] = None, 
        status: Optional[str] = None
    ) -> List[OldExamResponse]:
        exams = await self.exam_repo.get_all(skip=skip, limit=limit, course_name=course_name, status=status)
        
        # Get assigned students counts
        counts = await self.db.execute(select(ExamSession.exam_id, func.count(ExamSession.id)).group_by(ExamSession.exam_id))
        count_map = {row[0]: row[1] for row in counts.all()}
        
        responses = []
        for e in exams:
            resp = OldExamResponse.model_validate(e)
            resp.assigned_students_count = count_map.get(e.id, 0)
            resp.ai_session_status = "ACTIVE" if e.status in ["RUNNING", "PAUSED"] else "INACTIVE"
            responses.append(resp)
        return responses

    async def get_upcoming_exams(self, skip: int = 0, limit: int = 100) -> List[OldExamResponse]:
        from datetime import datetime, timezone
        current_time = datetime.now(timezone.utc)
        exams = await self.exam_repo.get_upcoming_exams(current_time=current_time, skip=skip, limit=limit)
        
        # Get assigned students counts
        counts = await self.db.execute(select(ExamSession.exam_id, func.count(ExamSession.id)).group_by(ExamSession.exam_id))
        count_map = {row[0]: row[1] for row in counts.all()}
        
        responses = []
        for e in exams:
            resp = OldExamResponse.model_validate(e)
            resp.assigned_students_count = count_map.get(e.id, 0)
            resp.ai_session_status = "ACTIVE" if e.status in ["RUNNING", "PAUSED"] else "INACTIVE"
            responses.append(resp)
        return responses

    async def update_exam(self, exam_id: int, user_id: int, exam_in: OldExamUpdate) -> OldExamResponse:
        exam = await self.exam_repo.get_by_id(exam_id)
        if not exam or exam.created_by != user_id:
            raise ExamNotFoundError(f"Exam {exam_id} not found or unauthorized.")
            
        if exam.status not in ["DRAFT", "SCHEDULED"]:
            raise InvalidExamStateError("Cannot update exam configurations once it is ready or running.")

        update_data = exam_in.model_dump(exclude_unset=True)
        new_start = update_data.get('scheduled_start', exam.scheduled_start)
        new_end = update_data.get('scheduled_end', exam.scheduled_end)
        
        if 'scheduled_start' in update_data or 'scheduled_end' in update_data:
            if new_end <= new_start:
                raise ValueError("scheduled_end must be after scheduled_start")
            await self._check_schedule_conflict(
                course_name=exam.course_name,
                start=new_start,
                end=new_end,
                exclude_exam_id=exam.id
            )

        updated_exam = await self.exam_repo.update(exam, **update_data)
        logger.info(f"Exam updated: ID {exam_id}")
        return OldExamResponse.model_validate(updated_exam)

    async def delete_exam(self, exam_id: int, user_id: int) -> None:
        exam = await self.exam_repo.get_by_id(exam_id)
        if not exam or exam.created_by != user_id:
            raise ExamNotFoundError(f"Exam {exam_id} not found or unauthorized.")
            
        if exam.status in ["READY", "RUNNING", "PAUSED"]:
            raise InvalidExamStateError("Cannot delete an exam that is currently active or ready. Cancel it first.")
            
        await self.exam_repo.delete(exam_id)
        logger.info(f"Exam deleted: ID {exam_id}")

    async def assign_students(self, exam_id: int, student_ids: List[int]) -> int:
        exam = await self.exam_repo.get_by_id(exam_id)
        if not exam:
            raise ExamNotFoundError(f"Exam {exam_id} not found.")
            
        # Get existing sessions to avoid duplicates
        existing_sessions_result = await self.db.execute(select(ExamSession.student_id).where(ExamSession.exam_id == exam_id))
        existing_student_ids = set(existing_sessions_result.scalars().all())
        
        new_student_ids = [sid for sid in student_ids if sid not in existing_student_ids]
        
        for sid in new_student_ids:
            new_session = ExamSession(exam_id=exam_id, student_id=sid)
            self.db.add(new_session)
            
        await self.db.commit()
        return len(new_student_ids)

    # --- MODULE 4 EXAM DOMAIN LIFECYCLE (DRAFT WORKFLOW) ---

    async def create_draft_exam(self, creator_id: int, exam_in: DomainExamCreate) -> DomainExamResponse:
        data = exam_in.model_dump()
        exam = await self.exam_repo.create(
            created_by=creator_id,
            status="DRAFT",
            **data
        )
        logger.info(f"Draft Exam created successfully: ID {exam.id}")
        return DomainExamResponse.model_validate(exam)

    async def update_domain_exam(self, exam_id: int, creator_id: int, exam_in: DomainExamUpdate) -> DomainExamResponse:
        exam = await self.exam_repo.get_by_id(exam_id)
        if not exam:
            raise ExamNotFoundError(f"Exam {exam_id} not found.")
        if exam.created_by != creator_id:
            raise ExamNotFoundError(f"Exam {exam_id} not found.")
            
        update_data = exam_in.model_dump(exclude_unset=True)
        updated_exam = await self.exam_repo.update(exam, **update_data)
        logger.info(f"Workspace Exam {exam_id} updated by user {creator_id}")
        return DomainExamResponse.model_validate(updated_exam)

    async def update_runtime_rules(self, exam_id: int, creator_id: int, rules_in: RuntimeRulesUpdate) -> OldExamResponse:
        from app.services.validators.runtime_rules_validator import RuntimeRulesValidator
        from app.models.exam_section_rule import ExamSectionRule
        from app.models.exam_question_rule import ExamQuestionRule

        exam = await self.exam_repo.get_by_id(exam_id)
        if not exam:
            raise ExamNotFoundError(f"Exam {exam_id} not found.")
        if exam.created_by != creator_id:
            raise ExamNotFoundError(f"Exam {exam_id} not found.")
            
        RuntimeRulesValidator.validate(rules_in)
        
        # Level 1 Rules update
        if rules_in.allow_resume_after_disconnect is not None:
            exam.allow_resume_after_disconnect = rules_in.allow_resume_after_disconnect
        if rules_in.global_navigation is not None:
            exam.global_navigation = rules_in.global_navigation
        if rules_in.randomize_sections is not None:
            exam.randomize_sections = rules_in.randomize_sections
        if rules_in.randomize_questions is not None:
            exam.randomize_questions = rules_in.randomize_questions
        if rules_in.allow_review_before_submit is not None:
            exam.allow_review_before_submit = rules_in.allow_review_before_submit
        if rules_in.show_remaining_time is not None:
            exam.show_remaining_time = rules_in.show_remaining_time
        if rules_in.show_question_numbers is not None:
            exam.show_question_numbers = rules_in.show_question_numbers
        if rules_in.show_marks is not None:
            exam.show_marks = rules_in.show_marks
            
        # Level 2 & 3 Rules update
        # Clear existing
        await self.db.execute(select(ExamSectionRule).filter(ExamSectionRule.exam_id == exam_id)) # fetch to trigger cascade, or manual delete
        # Instead of manual cascade management, rely on SQLAlchemy or delete explicitly
        for s in exam.section_rules:
            await self.db.delete(s)
        await self.db.flush()

        for s_in in rules_in.sections:
            section = ExamSectionRule(
                exam_id=exam.id,
                section_index=s_in.section_index,
                section_name=s_in.section_name,
                section_type=s_in.section_type,
                section_duration_minutes=s_in.section_duration_minutes,
                navigation_policy=s_in.navigation_policy,
                allow_return_to_previous=s_in.allow_return_to_previous,
                lock_after_timeout=s_in.lock_after_timeout,
                randomize_questions=s_in.randomize_questions,
                require_completion_before_next=s_in.require_completion_before_next,
                section_weight=s_in.section_weight,
                instructions=s_in.instructions
            )
            exam.section_rules.append(section)
            
            for q_in in s_in.question_rules:
                question = ExamQuestionRule(
                    exam_id=exam.id,
                    question_index=q_in.question_index,
                    question_type=q_in.question_type,
                    marks=q_in.marks,
                    is_required=q_in.is_required,
                    character_limit=q_in.character_limit,
                    word_limit=q_in.word_limit,
                    attachment_allowed=q_in.attachment_allowed,
                    question_timer_seconds=q_in.question_timer_seconds,
                    autosave=q_in.autosave,
                    individual_submission=q_in.individual_submission,
                    editable_after_submission=q_in.editable_after_submission,
                    allow_multiple_submissions=q_in.allow_multiple_submissions,
                    max_submission_count=q_in.max_submission_count,
                    allow_editing_until_final=q_in.allow_editing_until_final,
                    lock_immediately_after_submission=q_in.lock_immediately_after_submission,
                    show_correctness_immediately=q_in.show_correctness_immediately,
                    instructions=q_in.instructions
                )
                section.question_rules.append(question)
                
        await self.db.commit()
        await self.db.refresh(exam)
        return OldExamResponse.model_validate(exam)

    async def get_domain_exam(self, exam_id: int, user_id: int) -> DomainExamResponse:
        exam = await self.exam_repo.get_by_id(exam_id)
        if not exam:
            raise ExamNotFoundError(f"Exam {exam_id} not found.")
        # Optional: check if user_id is creator or assigned supervisor
        return DomainExamResponse.model_validate(exam)

    async def list_domain_exams(self, user_id: int, skip: int = 0, limit: int = 100) -> List[DomainExamResponse]:
        query = select(Exam).where(Exam.created_by == user_id).order_by(Exam.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return [DomainExamResponse.model_validate(e) for e in result.scalars().all()]

    async def get_assigned_students(self, exam_id: int, user_id: int) -> List[int]:
        exam = await self.exam_repo.get_by_id(exam_id)
        if not exam or exam.created_by != user_id:
            raise ExamNotFoundError("Exam not found or unauthorized.")
            
        result = await self.db.execute(select(ExamAssignment.student_id).where(ExamAssignment.exam_id == exam_id))
        return list(result.scalars().all())

    async def assign_repository_students(self, exam_id: int, student_ids: List[int], user_id: int) -> int:
        exam = await self.exam_repo.get_by_id(exam_id)
        if not exam or exam.created_by != user_id:
            raise ExamNotFoundError("Exam not found or unauthorized.")
            
        # Get existing assignments to avoid duplicates
        existing_result = await self.db.execute(select(ExamAssignment.student_id).where(ExamAssignment.exam_id == exam_id))
        existing_ids = set(existing_result.scalars().all())
        
        # We should also verify that the students belong to this user (examiner) in the Student repository
        students_result = await self.db.execute(select(Student.id).where(Student.examiner_id == user_id, Student.id.in_(student_ids)))
        valid_student_ids = set(students_result.scalars().all())
        
        new_ids = [sid for sid in valid_student_ids if sid not in existing_ids]
        
        for sid in new_ids:
            self.db.add(ExamAssignment(exam_id=exam_id, student_id=sid))
            
        await self.db.commit()
        return len(new_ids)

    async def assign_supervisors(self, exam_id: int, supervisor_ids: List[int], user_id: int) -> int:
        exam = await self.exam_repo.get_by_id(exam_id)
        if not exam or exam.created_by != user_id:
            raise ExamNotFoundError("Exam not found or unauthorized.")
            
        existing_result = await self.db.execute(select(ExamSupervisor.supervisor_id).where(ExamSupervisor.exam_id == exam_id))
        existing_ids = set(existing_result.scalars().all())
        
        new_ids = [sid for sid in supervisor_ids if sid not in existing_ids]
        
        for sid in new_ids:
            self.db.add(ExamSupervisor(exam_id=exam_id, supervisor_id=sid))
            
        await self.db.commit()
        return len(new_ids)

    async def publish_exam(self, exam_id: int, user_id: int) -> DomainExamResponse:
        from sqlalchemy.orm import selectinload
        from app.models.question_paper import QuestionPaper
        from app.models.exam_section_rule import ExamSectionRule
        from app.models.exam_question_rule import ExamQuestionRule
        
        # We need to eager load the question paper and its nested rules
        query = select(Exam).options(
            selectinload(Exam.question_paper).selectinload(QuestionPaper.section_rules).selectinload(ExamSectionRule.question_rules).selectinload(ExamQuestionRule.options),
            selectinload(Exam.section_rules)
        ).where(Exam.id == exam_id)
        
        result = await self.db.execute(query)
        exam = result.scalar_one_or_none()
        
        if not exam or exam.created_by != user_id:
            raise ExamNotFoundError("Exam not found or unauthorized.")
            
        if exam.status != "DRAFT":
            raise InvalidExamStateError("Only DRAFT exams can be published to READY.")
            
        # Validation checks
        if not exam.scheduled_start or not exam.scheduled_end or not exam.duration_minutes:
            raise InvalidExamStateError("Cannot publish without schedule and duration.")
            
        if not exam.question_paper_id:
            raise InvalidExamStateError("Cannot publish without a question paper.")
            
        # STRUCTURED MODE CLONING LOGIC
        if exam.question_paper and exam.question_paper.mode == "STRUCTURED":
            # Clear any existing exam_id rules just in case
            await self.db.execute(select(ExamSectionRule).where(ExamSectionRule.exam_id == exam_id))
            for s in exam.section_rules:
                await self.db.delete(s)
            await self.db.flush()
            
            # Deep clone from question_paper to exam
            from app.models.exam_section_rule import ExamSectionRule
            from app.models.exam_question_rule import ExamQuestionRule
            
            for src_section in exam.question_paper.section_rules:
                new_section = ExamSectionRule(
                    exam_id=exam.id,
                    question_paper_id=None, # This belongs purely to the exam now
                    section_index=src_section.section_index,
                    section_name=src_section.section_name,
                    section_type=src_section.section_type,
                    section_duration_minutes=src_section.section_duration_minutes,
                    navigation_policy=src_section.navigation_policy,
                    allow_return_to_previous=src_section.allow_return_to_previous,
                    lock_after_timeout=src_section.lock_after_timeout,
                    randomize_questions=src_section.randomize_questions,
                    require_completion_before_next=src_section.require_completion_before_next,
                    section_weight=src_section.section_weight,
                    instructions=src_section.instructions
                )
                self.db.add(new_section)
                await self.db.flush() # flush to get new_section.id
                
                for src_question in src_section.question_rules:
                    new_question = ExamQuestionRule(
                        exam_id=exam.id,
                        question_paper_id=None,
                        section_rule_id=new_section.id,
                        question_index=src_question.question_index,
                        question_type=src_question.question_type,
                        marks=src_question.marks,
                        is_required=src_question.is_required,
                        question_text=src_question.question_text,
                        image_url=src_question.image_url,
                        explanation=src_question.explanation,
                        difficulty=src_question.difficulty,
                        character_limit=src_question.character_limit,
                        word_limit=src_question.word_limit,
                        attachment_allowed=src_question.attachment_allowed,
                        autosave=src_question.autosave,
                        individual_submission=src_question.individual_submission,
                        editable_after_submission=src_question.editable_after_submission,
                        allow_multiple_submissions=src_question.allow_multiple_submissions,
                        max_submission_count=src_question.max_submission_count,
                        allow_editing_until_final=src_question.allow_editing_until_final,
                        lock_immediately_after_submission=src_question.lock_immediately_after_submission,
                        show_correctness_immediately=src_question.show_correctness_immediately,
                        instructions=src_question.instructions
                    )
                    self.db.add(new_question)
                    
                    # We don't necessarily clone QuestionOptions into a new table because the options belong to the question rule 
                    # WAIT, the options belong to ExamQuestionRule. Since we created a new ExamQuestionRule, we MUST clone the options!
                    await self.db.flush() # get new_question.id
                    
                    from app.models.question_option import QuestionOption
                    for src_opt in src_question.options:
                        new_opt = QuestionOption(
                            question_rule_id=new_question.id,
                            option_text=src_opt.option_text,
                            is_correct=src_opt.is_correct
                        )
                        self.db.add(new_opt)
            
            # Record the version
            exam.question_paper_version = exam.question_paper.version
            
        exam.status = "READY"
        await self.db.commit()
        await self.db.refresh(exam)
        return DomainExamResponse.model_validate(exam)

    # --- AI ORCHESTRATION & STATE MANAGEMENT ---

    async def _change_status(self, exam_id: int, new_status: str) -> OldExamResponse:
        exam = await self.exam_repo.get_by_id(exam_id)
        if not exam:
            raise ExamNotFoundError(f"Exam {exam_id} not found.")
        updated_exam = await self.exam_repo.update(exam, status=new_status)
        
        resp = OldExamResponse.model_validate(updated_exam)
        resp.ai_session_status = "ACTIVE" if updated_exam.status in ["RUNNING", "PAUSED"] else "INACTIVE"
        return resp

    async def start_exam(self, exam_id: int, user_id: int) -> OldExamResponse:
        exam = await self.exam_repo.get_by_id(exam_id)
        if not exam or exam.created_by != user_id:
            raise ExamNotFoundError(f"Exam {exam_id} not found or unauthorized.")
        if exam.status not in ["SCHEDULED", "READY"]:
            raise InvalidExamStateError(f"Cannot start exam from state {exam.status}.")

        try:
            # AI Orchestration
            AISessionManager.initialize_session(exam.id, user_id)
            AISessionManager.start_session(exam.id)
            return await self._change_status(exam.id, "RUNNING")
        except Exception as e:
            logger.error(f"Failed to start AI Session for exam {exam_id}: {e}")
            raise AISessionError("Failed to start AI Session.") from e

    async def pause_exam(self, exam_id: int, user_id: int) -> OldExamResponse:
        exam = await self.exam_repo.get_by_id(exam_id)
        if not exam or exam.created_by != user_id:
            raise ExamNotFoundError(f"Exam {exam_id} not found or unauthorized.")
        if exam.status != "RUNNING":
            raise InvalidExamStateError("Only RUNNING exams can be paused.")
            
        try:
            AISessionManager.pause_session(exam.id)
            return await self._change_status(exam.id, "PAUSED")
        except Exception as e:
            logger.error(f"Failed to pause AI Session for exam {exam_id}: {e}")
            raise AISessionError("Failed to pause AI Session.") from e

    async def resume_exam(self, exam_id: int, user_id: int) -> OldExamResponse:
        exam = await self.exam_repo.get_by_id(exam_id)
        if not exam or exam.created_by != user_id:
            raise ExamNotFoundError(f"Exam {exam_id} not found or unauthorized.")
        if exam.status != "PAUSED":
            raise InvalidExamStateError("Only PAUSED exams can be resumed.")
            
        try:
            AISessionManager.resume_session(exam.id)
            return await self._change_status(exam.id, "RUNNING")
        except Exception as e:
            logger.error(f"Failed to resume AI Session for exam {exam_id}: {e}")
            raise AISessionError("Failed to resume AI Session.") from e

    async def complete_exam(self, exam_id: int, user_id: int) -> OldExamResponse:
        exam = await self.exam_repo.get_by_id(exam_id)
        if not exam or exam.created_by != user_id:
            raise ExamNotFoundError(f"Exam {exam_id} not found or unauthorized.")
        if exam.status not in ["RUNNING", "PAUSED"]:
            raise InvalidExamStateError("Only RUNNING or PAUSED exams can be completed.")
            
        try:
            AISessionManager.stop_session(exam.id)
            return await self._change_status(exam.id, "COMPLETED")
        except Exception as e:
            logger.error(f"Failed to stop AI Session for exam {exam_id}: {e}")
            raise AISessionError("Failed to cleanly stop AI Session.") from e
