import logging
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.exam_session import ExamSessionCreate, ExamSessionUpdate, ExamSessionResponse
from app.repositories.exam_session_repository import ExamSessionRepository
from app.repositories.exam_repository import ExamRepository
from app.repositories.user_repository import UserRepository
from app.repositories.exceptions import EntityNotFoundError
from app.services.exceptions import AuthorizationError

logger = logging.getLogger(__name__)

class ExamSessionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.session_repo = ExamSessionRepository(db)
        self.exam_repo = ExamRepository(db)
        self.user_repo = UserRepository(db)

    async def create_session(self, session_in: ExamSessionCreate) -> ExamSessionResponse:
        # Validate Exam
        exam = await self.exam_repo.get_by_id(session_in.exam_id)
        if not exam:
            raise EntityNotFoundError(f"Exam {session_in.exam_id} not found.")

        # Validate Student
        student = await self.user_repo.get_by_id(session_in.student_id)
        if not student:
            raise EntityNotFoundError(f"Student {session_in.student_id} not found.")

        if not student.role or student.role.name.upper() != "STUDENT":
            raise ValueError(f"User {session_in.student_id} is not a Student.")

        # Validate Unique active session
        existing = await self.session_repo.get_by_student_and_exam(session_in.student_id, session_in.exam_id)
        if existing:
            raise ValueError(f"Student {session_in.student_id} already has a session for Exam {session_in.exam_id}.")

        # Create
        created_obj = await self.session_repo.create(
            exam_id=session_in.exam_id,
            student_id=session_in.student_id,
            status="PENDING"
        )
        return ExamSessionResponse.model_validate(created_obj)

    async def get_session(self, session_id: int) -> ExamSessionResponse:
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            raise EntityNotFoundError(f"ExamSession {session_id} not found.")
        return ExamSessionResponse.model_validate(session)

    async def get_all_sessions(
        self,
        skip: int = 0,
        limit: int = 100,
        exam_id: Optional[int] = None,
        student_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[ExamSessionResponse]:
        sessions = await self.session_repo.get_all(
            skip=skip,
            limit=limit,
            exam_id=exam_id,
            student_id=student_id,
            status=status
        )
        return [ExamSessionResponse.model_validate(s) for s in sessions]

    async def update_session(self, session_id: int, session_in: ExamSessionUpdate) -> ExamSessionResponse:
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            raise EntityNotFoundError(f"ExamSession {session_id} not found.")

        update_data = session_in.model_dump(exclude_unset=True)
        updated_obj = await self.session_repo.update(session, **update_data)
        return ExamSessionResponse.model_validate(updated_obj)

    async def update_status(self, session_id: int, new_status: str) -> ExamSessionResponse:
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            raise EntityNotFoundError(f"ExamSession {session_id} not found.")
            
        valid_transitions = {
            "PENDING": ["RUNNING", "CANCELLED"],
            "RUNNING": ["COMPLETED", "PAUSED"],
            "PAUSED": ["RUNNING", "COMPLETED"],
            "COMPLETED": [],
            "CANCELLED": []
        }
        
        if new_status not in valid_transitions.get(session.status, []):
            raise ValueError(f"Invalid status transition from {session.status} to {new_status}")
            
        update_data = {"status": new_status}
        if new_status == "RUNNING" and session.start_time is None:
            update_data["start_time"] = datetime.now(timezone.utc)
        elif new_status in ["COMPLETED", "CANCELLED"] and session.end_time is None:
            update_data["end_time"] = datetime.now(timezone.utc)
            
        updated_obj = await self.session_repo.update(session, **update_data)
        return ExamSessionResponse.model_validate(updated_obj)

    async def delete_session(self, session_id: int) -> None:
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            raise EntityNotFoundError(f"ExamSession {session_id} not found.")
            
        if session.status in ["RUNNING", "PAUSED"]:
            raise ValueError("Cannot delete an active exam session.")
            
        await self.session_repo.delete(session_id)

    # --- CANDIDATE RUNTIME METHODS ---
    
    async def enforce_active_runtime(self, exam_id: int, user_id: int) -> ExamSessionResponse:
        existing = await self.session_repo.get_by_student_and_exam(user_id, exam_id)
        if not existing:
            raise EntityNotFoundError("Session not found.")
            
        if existing.status != "RUNNING":
            raise ValueError(f"Exam session is not active. Status: {existing.status}")
            
        if existing.start_time and existing.exam:
            current_time = datetime.now(timezone.utc)
            start_time = existing.start_time
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)
                
            elapsed = (current_time - start_time).total_seconds()
            allowed = existing.exam.duration_minutes * 60
            
            # Allow a small grace period (e.g. 5 seconds) for network latency
            if elapsed > allowed + 5:
                await self.submit_runtime_session(exam_id, user_id)
                raise ValueError("Exam session has expired and was automatically submitted.")
                
        return existing


    async def start_runtime_session(self, exam_id: int, user_id: int) -> dict:
        from app.models.exam import Exam
        from sqlalchemy import select
        
        # Verify Exam
        exam = await self.exam_repo.get_by_id(exam_id)
        if not exam:
            raise EntityNotFoundError("Exam not found.")
            
        # Auto-activate exam if scheduled_start <= now and status == READY
        current_time = datetime.now(timezone.utc)
        if exam.status == "READY" and exam.scheduled_start:
            sched_start = exam.scheduled_start.replace(tzinfo=timezone.utc) if exam.scheduled_start.tzinfo is None else exam.scheduled_start
            if sched_start <= current_time:
                from app.services.exam_service import ExamService
                exam_service = ExamService(self.db)
                try:
                    await exam_service.start_exam(exam.id, exam.created_by)
                    exam = await self.exam_repo.get_by_id(exam_id)
                except Exception as e:
                    logger.warning(f"Could not auto-activate exam {exam_id}: {e}")

        # Check Candidate Access Rules regarding scheduled_start
        if exam.scheduled_start:
            sched_start = exam.scheduled_start.replace(tzinfo=timezone.utc) if exam.scheduled_start.tzinfo is None else exam.scheduled_start
            if current_time < sched_start:
                raise ValueError("This exam has not started yet.")

        if exam.status not in ["READY", "RUNNING"]:
            raise ValueError(f"Exam is not ready to be taken. Status: {exam.status}")

        # Check existing session (Recovery)
        existing = await self.session_repo.get_by_student_and_exam(user_id, exam_id)
        
        current_time = datetime.now(timezone.utc)
        
        target_session = existing
        
        if existing:
            if existing.status == "COMPLETED":
                raise ValueError("You have already completed this exam.")
                
            # Session Recovery / Activation
            if existing.status == "PENDING" or existing.start_time is None:
                existing.status = "RUNNING"
                existing.start_time = current_time
                await self.db.commit()
                
            from app.services.runtime_state_service import RuntimeStateService
            runtime_service = RuntimeStateService(self.db)
            await runtime_service.initialize_state(existing.id)
            # Re-fetch to get eager loaded relations if necessary
            target_session = await self.session_repo.get_by_id(existing.id)
        else:
            raise ValueError("You are not assigned to this exam.")
            
        start_time = target_session.start_time
        if start_time and start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
            
        # Determine Paper Academic Duration
        sections_source = exam.section_rules if exam and exam.section_rules else (exam.question_paper.section_rules if exam and exam.question_paper else [])
        sec_paper_duration = sum(s.section_duration_minutes for s in sections_source if s.section_duration_minutes and s.section_duration_minutes > 0)
        
        paper_dur_mins = sec_paper_duration if sec_paper_duration > 0 else (exam.duration_minutes or 120)

        total_suspended = 0
        from app.services.runtime_state_service import RuntimeStateService
        rs_svc = RuntimeStateService(self.db)
        state_obj = await rs_svc.get_state(target_session.id)
        if state_obj and state_obj.execution_flags:
            total_suspended = state_obj.execution_flags.get("total_suspended_seconds", 0)

        raw_elapsed = (current_time - start_time).total_seconds() if start_time else 0
        active_elapsed = max(0, raw_elapsed - total_suspended)
        paper_time_left = max(0, int((paper_dur_mins * 60) - active_elapsed))

        schedule_time_left = paper_time_left
        if exam and exam.scheduled_end:
            sched_end = exam.scheduled_end
            if sched_end.tzinfo is None:
                sched_end = sched_end.replace(tzinfo=timezone.utc)
            schedule_time_left = max(0, int((sched_end - current_time).total_seconds()))

        time_left = min(paper_time_left, schedule_time_left)

        # Build Runtime Payload
        mode = "FILE"
        if exam.question_paper and exam.question_paper.mode:
            mode = exam.question_paper.mode

        payload = {
            "session": {
                "id": target_session.id,
                "exam_id": target_session.exam_id,
                "student_id": target_session.student_id,
                "status": target_session.status,
                "evaluation_status": target_session.evaluation_status,
                "start_time": target_session.start_time.isoformat() if target_session.start_time else None,
                "end_time": target_session.end_time.isoformat() if target_session.end_time else None
            },
            "time_left_seconds": time_left,
            "mode": mode,
            "exam_config": {
                "duration_minutes": exam.duration_minutes,
                "title": exam.title
            }
        }

        if mode == "FILE":
            payload["file_url"] = f"/runtime/file?exam_id={exam.id}"
        else:
            sections_data = []
            sections_source = exam.section_rules if exam.section_rules else (exam.question_paper.section_rules if exam.question_paper else [])
            sorted_sections = sorted(sections_source, key=lambda s: s.section_index)
            for sec in sorted_sections:
                sec_dict = {
                    "id": str(sec.id),
                    "section_index": sec.section_index,
                    "section_name": sec.section_name,
                    "section_type": sec.section_type,
                    "section_duration_minutes": sec.section_duration_minutes,
                    "navigation_policy": sec.navigation_policy,
                    "allow_return_to_previous": sec.allow_return_to_previous,
                    "lock_after_timeout": sec.lock_after_timeout,
                    "randomize_questions": sec.randomize_questions,
                    "require_completion_before_next": sec.require_completion_before_next,
                    "section_weight": sec.section_weight,
                    "instructions": sec.instructions,
                    "questions": []
                }
                questions_list = list(sec.question_rules)
                if sec.randomize_questions:
                    import random
                    rnd = random.Random(f"{target_session.id}_{sec.id}")
                    rnd.shuffle(questions_list)
                else:
                    questions_list = sorted(questions_list, key=lambda q: q.question_index)

                for q in questions_list:
                    q_dict = {
                        "id": str(q.id),
                        "question_index": q.question_index,
                        "question_type": q.question_type,
                        "text": q.question_text or "No text provided.",
                        "options": [opt.option_text for opt in q.options],
                        "marks": q.marks,
                        "image_url": q.image_url,
                        "explanation": q.explanation
                    }
                    sec_dict["questions"].append(q_dict)
                sections_data.append(sec_dict)
            payload["sections"] = sections_data

        return payload

    async def submit_runtime_session(self, exam_id: int, user_id: int) -> ExamSessionResponse:
        existing = await self.session_repo.get_by_student_and_exam(user_id, exam_id)
        if not existing:
            raise EntityNotFoundError("Session not found.")
            
        if existing.status == "COMPLETED":
            return ExamSessionResponse.model_validate(existing)
            
        existing.status = "COMPLETED"
        existing.end_time = datetime.now(timezone.utc)
        await self.db.commit()
        existing = await self.session_repo.get_by_id(existing.id)
        
        return ExamSessionResponse.model_validate(existing)

    async def get_submission_summary(self, exam_id: int, user_id: int) -> dict:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from app.models.exam_session import ExamSession
        from app.models.exam import Exam
        from app.models.exam_section_rule import ExamSectionRule
        from app.models.question_paper import QuestionPaper
        
        stmt = (
            select(ExamSession)
            .options(
                selectinload(ExamSession.exam).selectinload(Exam.section_rules).selectinload(ExamSectionRule.question_rules),
                selectinload(ExamSession.exam).selectinload(Exam.question_paper).selectinload(QuestionPaper.section_rules).selectinload(ExamSectionRule.question_rules),
                selectinload(ExamSession.candidate_answers)
            )
            .where(ExamSession.exam_id == exam_id, ExamSession.student_id == user_id)
        )
        res = await self.db.execute(stmt)
        session = res.scalars().first()
        if not session:
            raise EntityNotFoundError("Exam session not found.")

        exam = session.exam
        exam_title = exam.title if exam else "Examination"

        # Calculate total questions
        total_questions = 0
        rules_source = exam.section_rules if exam and exam.section_rules else (exam.question_paper.section_rules if exam and exam.question_paper else [])
        for sec in rules_source:
            total_questions += len(sec.question_rules)

        if total_questions == 0:
            total_questions = len(session.candidate_answers) or 1

        # Count answered questions
        answered_count = 0
        for ans in session.candidate_answers:
            data = ans.answer_data or {}
            has_ans = (
                data.get("selected") is not None or
                bool(data.get("selected_options")) or
                bool(data.get("text", "").strip())
            )
            if has_ans or ans.answer_status in ["ANSWERED", "MARKED_FOR_REVIEW"]:
                answered_count += 1

        # Calculate exact duration
        start_time = session.start_time or session.created_at
        end_time = session.end_time or datetime.now(timezone.utc)

        if start_time:
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=timezone.utc)
            duration_secs = max(1, int((end_time - start_time).total_seconds()))
        else:
            duration_secs = 1

        hours = duration_secs // 3600
        minutes = (duration_secs % 3600) // 60
        seconds = duration_secs % 60

        duration_parts = []
        if hours > 0:
            duration_parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            duration_parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if seconds > 0 or (hours == 0 and minutes == 0):
            duration_parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
        duration_formatted = ", ".join(duration_parts)

        return {
            "session_id": session.id,
            "exam_id": exam_id,
            "exam_title": exam_title,
            "status": session.status,
            "submission_time": end_time.isoformat(),
            "start_time": start_time.isoformat() if start_time else None,
            "duration_seconds": duration_secs,
            "duration_formatted": duration_formatted,
            "answered_count": answered_count,
            "total_questions": total_questions,
            "monitoring_status": "Session Complete"
        }

    async def get_exam_attempts(
        self,
        exam_id: int,
        search: Optional[str] = None,
        status_filter: Optional[str] = None,
        eval_filter: Optional[str] = None,
        special_filter: Optional[str] = None,
        sort_by: Optional[str] = "reg_num",
        sort_order: Optional[str] = "asc",
        page: int = 1,
        page_size: int = 25
    ) -> dict:
        import math
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from app.models.exam_session import ExamSession

        exam = await self.exam_repo.get_by_id(exam_id)
        if not exam:
            raise EntityNotFoundError(f"Exam {exam_id} not found.")

        stmt = select(ExamSession).options(
            selectinload(ExamSession.student),
            selectinload(ExamSession.runtime_state)
        ).where(ExamSession.exam_id == exam_id)

        res = await self.db.execute(stmt)
        sessions = res.scalars().all()

        from app.models.student import Student
        from app.models.exam_assignment import ExamAssignment
        student_records_res = await self.db.execute(select(Student))
        student_records = student_records_res.scalars().all()
        student_map = {st_rec.email.lower(): st_rec for st_rec in student_records if st_rec.email}
        student_reg_map = {st_rec.registration_number: st_rec for st_rec in student_records if st_rec.registration_number}

        total_students = len(sessions)
        present_count = 0
        absent_count = 0
        submitted_count = 0
        running_count = 0
        evaluated_count = 0
        finalized_count = 0
        draft_count = 0
        pending_count = 0

        scores_list = []

        all_processed = []

        for s in sessions:
            student = s.student
            stu_name = student.full_name if student else f"Student #{s.student_id}"
            
            stu_repo = student_map.get(student.email.lower()) if (student and student.email) else None
            reg_num = stu_repo.registration_number if (stu_repo and stu_repo.registration_number) else (getattr(student, 'registration_number', None) or f"REG-{s.student_id:04d}")
            dept = stu_repo.department if (stu_repo and stu_repo.department) else (getattr(student, 'department', None) or "Computer Science")
            prog = stu_repo.program if (stu_repo and stu_repo.program) else (getattr(student, 'program', None) or "BS Computer Science")

            r_state = s.runtime_state
            flags = (r_state.execution_flags if r_state and r_state.execution_flags else {})
            recovery_count = flags.get("recovery_count", 0)

            start_t = s.start_time
            end_t = s.end_time
            dur_used_mins = 0
            if start_t and end_t:
                dur_used_mins = max(1, int((end_t - start_t).total_seconds() / 60))

            eval_status = s.evaluation_status or "PENDING"
            obj_score = round(s.objective_score or 0.0, 2)
            subj_score = round(s.subjective_score or 0.0, 2)
            tot_max = float(exam.total_marks) if exam and exam.total_marks and exam.total_marks > 0 else 0.0
            if tot_max == 0 and exam:
                sections_src = exam.section_rules if exam.section_rules else (exam.question_paper.section_rules if exam.question_paper else [])
                for sec in sections_src:
                    tot_max += sum(float(q.marks if q.marks and q.marks > 0 else 1.0) for q in (sec.question_rules or []))
            tot_score = round(s.total_score if s.total_score is not None else (obj_score + subj_score), 2)
            pct = round((tot_score / tot_max * 100), 2) if tot_max > 0 else 0.0

            sub_method = "Automatic Time Expiry" if s.status in ["EXPIRED", "AUTO_SUBMITTED"] else ("Manual Candidate Submission" if s.end_time else "In Progress")

            # Dashboard Counts
            if s.status in ['RUNNING', 'PREPARATION']:
                running_count += 1
                present_count += 1
            elif s.status in ['SUBMITTED', 'EXPIRED', 'AUTO_SUBMITTED', 'COMPLETED']:
                submitted_count += 1
                present_count += 1
            else:
                absent_count += 1

            if eval_status == 'FINALIZED':
                finalized_count += 1
                evaluated_count += 1
                scores_list.append(tot_score)
            elif eval_status == 'DRAFT':
                draft_count += 1
                evaluated_count += 1
                scores_list.append(tot_score)
            else:
                pending_count += 1

            attempt_item = {
                "session_id": s.id,
                "student_id": s.student_id,
                "student_name": stu_name,
                "registration_number": reg_num,
                "department": dept,
                "program": prog,
                "status": s.status,
                "submission_time": s.end_time.isoformat() if s.end_time else None,
                "submission_method": sub_method,
                "duration_used_minutes": dur_used_mins,
                "recovery_count": recovery_count,
                "evaluation_status": eval_status,
                "objective_score": obj_score,
                "subjective_score": subj_score,
                "current_score": tot_score,
                "total_marks": tot_max,
                "percentage": pct
            }
            all_processed.append(attempt_item)

        avg_score = round(sum(scores_list) / len(scores_list), 2) if scores_list else 0.0
        max_score = round(max(scores_list), 2) if scores_list else 0.0
        min_score = round(min(scores_list), 2) if scores_list else 0.0
        prog_pct = round((finalized_count / max(1, total_students)) * 100, 2)

        dashboard_stats = {
            "total_students": total_students,
            "present_count": present_count,
            "absent_count": absent_count,
            "submitted_count": submitted_count,
            "running_count": running_count,
            "evaluated_count": evaluated_count,
            "finalized_count": finalized_count,
            "draft_count": draft_count,
            "pending_count": pending_count,
            "average_score": avg_score,
            "highest_score": max_score,
            "lowest_score": min_score,
            "progress_percentage": prog_pct
        }

        # Apply Filters
        filtered = []
        for a in all_processed:
            # Search
            if search:
                q_s = search.lower()
                if (q_s not in a["student_name"].lower() and 
                    q_s not in a["registration_number"].lower() and 
                    q_s not in a["department"].lower() and 
                    q_s not in a["program"].lower() and 
                    q_s not in a["status"].lower()):
                    continue

            # Status Filter
            if status_filter and status_filter.upper() != "ALL":
                sf = status_filter.upper()
                st = a["status"].upper()
                if sf in ["SUBMITTED", "COMPLETED"] and st not in ["SUBMITTED", "COMPLETED", "EXPIRED", "AUTO_SUBMITTED"]:
                    continue
                elif sf not in ["SUBMITTED", "COMPLETED"] and st != sf:
                    continue

            # Evaluation Status Filter
            if eval_filter and eval_filter.upper() != "ALL":
                ef = eval_filter.upper()
                if ef == "FINALIZED" and a["evaluation_status"] != "FINALIZED":
                    continue
                elif ef == "DRAFT" and a["evaluation_status"] != "DRAFT":
                    continue
                elif ef == "PENDING_EVALUATION" and a["evaluation_status"] != "PENDING":
                    continue
                elif ef == "EVALUATED" and a["evaluation_status"] not in ["FINALIZED", "DRAFT"]:
                    continue

            # Special Filters (Phase 6)
            if special_filter and special_filter.upper() != "ALL":
                sf = special_filter.upper()
                if sf == "HIGH_SCORE" and a["percentage"] < 80.0:
                    continue
                elif sf == "LOW_SCORE" and a["percentage"] >= 50.0:
                    continue
                elif sf == "MANUAL_SUBMISSION" and "Manual" not in a["submission_method"]:
                    continue
                elif sf == "AUTO_SUBMISSION" and "Expiry" not in a["submission_method"]:
                    continue
                elif sf == "RECOVERY_EVENTS" and a["recovery_count"] <= 0:
                    continue

            filtered.append(a)

        # Apply Sorting (Phase 7)
        rev = (sort_order.lower() == "desc") if sort_order else False
        if sort_by == "reg_num":
            filtered.sort(key=lambda x: x["registration_number"], reverse=rev)
        elif sort_by == "time":
            filtered.sort(key=lambda x: x["submission_time"] or "", reverse=rev)
        elif sort_by in ["marks", "final_score"]:
            filtered.sort(key=lambda x: x["current_score"], reverse=rev)
        elif sort_by == "objective_score":
            filtered.sort(key=lambda x: x["objective_score"], reverse=rev)
        elif sort_by == "subjective_score":
            filtered.sort(key=lambda x: x["subjective_score"], reverse=rev)
        elif sort_by == "percentage":
            filtered.sort(key=lambda x: x["percentage"], reverse=rev)
        elif sort_by == "duration":
            filtered.sort(key=lambda x: x["duration_used_minutes"], reverse=rev)
        elif sort_by == "name":
            filtered.sort(key=lambda x: x["student_name"], reverse=rev)

        # Server-side Pagination (Phase 18)
        safe_page = max(1, page)
        safe_page_size = max(1, min(500, page_size))
        start_idx = (safe_page - 1) * safe_page_size
        end_idx = start_idx + safe_page_size
        paginated_attempts = filtered[start_idx:end_idx]

        return {
            "dashboard": dashboard_stats,
            "attempts": paginated_attempts,
            "all_matching_session_ids": [item["session_id"] for item in filtered],
            "total_count": len(filtered),
            "page": safe_page,
            "page_size": safe_page_size,
            "total_pages": max(1, math.ceil(len(filtered) / safe_page_size))
        }

    async def export_exam_results(
        self,
        exam_id: int,
        export_format: str = "csv",
        search: Optional[str] = None,
        status_filter: Optional[str] = None,
        eval_filter: Optional[str] = None,
        special_filter: Optional[str] = None,
        sort_by: Optional[str] = "reg_num",
        sort_order: Optional[str] = "asc"
    ) -> dict:
        # Fetch all matching attempts without pagination
        res_data = await self.get_exam_attempts(
            exam_id=exam_id,
            search=search,
            status_filter=status_filter,
            eval_filter=eval_filter,
            special_filter=special_filter,
            sort_by=sort_by,
            sort_order=sort_order,
            page=1,
            page_size=10000
        )
        attempts = res_data["attempts"]

        if export_format.lower() == "csv":
            import io, csv
            output = io.StringIO()
            writer = csv.writer(output)
            headers = [
                "Registration Number", "Candidate Name", "Program", "Department",
                "Attempt Status", "Evaluation Status", "Objective Score", "Subjective Score",
                "Final Score", "Percentage (%)", "Submission Type", "Recovery Count",
                "Submission Time", "Duration (Mins)"
            ]
            writer.writerow(headers)

            for a in attempts:
                writer.writerow([
                    a["registration_number"],
                    a["student_name"],
                    a["program"],
                    a["department"],
                    a["status"],
                    a["evaluation_status"],
                    a["objective_score"],
                    a["subjective_score"],
                    a["current_score"],
                    f"{a['percentage']}%",
                    a["submission_method"],
                    a["recovery_count"],
                    a["submission_time"] or "N/A",
                    a["duration_used_minutes"]
                ])
            return {
                "format": "csv",
                "filename": f"Exam_{exam_id}_Results_Export.csv",
                "content": output.getvalue()
            }
        else:
            return {
                "format": "json",
                "filename": f"Exam_{exam_id}_Results_Export.json",
                "rows": attempts
            }

    async def save_evaluation(
        self,
        session_id: int,
        evaluations_list: List[dict],
        finalize: bool,
        examiner_id: int
    ) -> dict:
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            raise EntityNotFoundError(f"ExamSession {session_id} not found.")

        if session.evaluation_status == "FINALIZED":
            raise ValueError("This attempt evaluation has been finalized and locked against modifications.")

        from app.repositories.candidate_answer_repository import CandidateAnswerRepository
        from app.models.candidate_answer import CandidateAnswer
        ca_repo = CandidateAnswerRepository(self.db)

        for item in evaluations_list:
            s_idx = item.get("section_index", 0)
            q_idx = item.get("question_index", 0)
            awarded = item.get("awarded_marks")
            comments = item.get("examiner_comments", "")

            ca = await ca_repo.get_by_question(session_id, s_idx, q_idx)
            if ca:
                ca.awarded_marks = float(awarded) if awarded is not None else None
                ca.examiner_comments = comments
            else:
                new_ca = CandidateAnswer(
                    exam_session_id=session_id,
                    section_index=s_idx,
                    question_index=q_idx,
                    answer_data={},
                    answer_status="EVALUATED",
                    awarded_marks=float(awarded) if awarded is not None else None,
                    examiner_comments=comments
                )
                self.db.add(new_ca)

        await self.db.commit()

        # Recalculate total scores & evaluation status
        review_data = await self.get_attempt_review_data(session_id)
        obj_score = review_data["scoring_summary"]["mcq_marks_obtained"]
        subj_score = review_data["scoring_summary"]["subjective_marks_obtained"]
        tot_score = obj_score + subj_score

        session.objective_score = obj_score
        session.subjective_score = subj_score
        session.total_score = tot_score
        session.evaluated_at = datetime.now(timezone.utc)
        session.evaluated_by = examiner_id
        session.evaluation_status = "FINALIZED" if finalize else "DRAFT"

        await self.db.commit()
        return await self.get_attempt_review_data(session_id)

    async def get_attempt_review_data(self, session_id: int) -> dict:
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            raise EntityNotFoundError(f"ExamSession {session_id} not found.")

        student = await self.user_repo.get_by_id(session.student_id)
        exam = await self.exam_repo.get_by_id(session.exam_id)

        from app.services.candidate_answer_service import CandidateAnswerService
        from app.services.runtime_state_service import RuntimeStateService

        ans_service = CandidateAnswerService(self.db)
        state_service = RuntimeStateService(self.db)

        candidate_answers = await ans_service.get_session_answers(session_id)
        try:
            runtime_state = await state_service.get_state(session_id)
        except EntityNotFoundError:
            runtime_state = None

        # Build paper review structure with correct options & section question weight scoring
        sections_source = exam.section_rules if exam.section_rules else (exam.question_paper.section_rules if exam.question_paper else [])
        sorted_sections = sorted(sections_source, key=lambda s: s.section_index)

        sections_data = []
        total_questions = 0

        # MCQ Metrics
        mcq_total_count = 0
        mcq_correct_count = 0
        mcq_incorrect_count = 0
        mcq_unattempted_count = 0
        mcq_marks_obtained = 0.0
        mcq_max_marks = 0.0

        # Subjective Metrics
        subj_total_count = 0
        subj_marks_obtained = 0.0
        subj_max_marks = 0.0

        # Answer Map
        ca_by_key = {f"{ca.section_index}_{ca.question_index}": ca for ca in candidate_answers}

        for sec in sorted_sections:
            questions_list = sorted(list(sec.question_rules or []), key=lambda q: q.question_index)
            # True total marks for this section calculated from questions
            sec_total_marks = sum(float(q.marks if q.marks is not None and q.marks > 0 else 1.0) for q in questions_list)
            q_count = len(questions_list)
            calc_weight = round(sec_total_marks / q_count, 2) if q_count > 0 else 1.0

            sec_dict = {
                "id": str(sec.id),
                "section_index": sec.section_index,
                "section_name": sec.section_name,
                "section_type": sec.section_type,
                "section_duration_minutes": sec.section_duration_minutes,
                "section_weight": sec_total_marks,
                "total_marks": sec_total_marks,
                "calculated_weight_per_question": calc_weight,
                "questions": []
            }

            for q in questions_list:
                total_questions += 1
                q_key = f"{sec.section_index}_{q.question_index}"
                ca = ca_by_key.get(q_key)
                q_marks = float(q.marks if q.marks is not None and q.marks > 0 else 1.0)

                options_data = []
                correct_indices = []
                for idx, opt in enumerate(q.options or []):
                    options_data.append({
                        "option_index": idx,
                        "text": opt.option_text,
                        "is_correct": opt.is_correct
                    })
                    if opt.is_correct:
                        correct_indices.append(idx)

                # Objective / Subjective Calculation
                is_mcq = (q.question_type == "MCQ" or sec.section_type == "MCQ")
                item_status = "NOT_ATTEMPTED"
                student_selected_indices = []
                student_answer_text = ""
                awarded_m = ca.awarded_marks if ca and ca.awarded_marks is not None else None
                ex_comments = ca.examiner_comments if ca and ca.examiner_comments else ""

                if ca and ca.answer_data:
                    ans_data = ca.answer_data
                    if ans_data.get("selected_options"):
                        student_selected_indices = ans_data.get("selected_options")
                    elif ans_data.get("selected") is not None:
                        student_selected_indices = [ans_data.get("selected")]
                    elif ans_data.get("selected_option") is not None:
                        sel_val = ans_data.get("selected_option")
                        if isinstance(sel_val, int):
                            student_selected_indices = [sel_val]
                        elif isinstance(sel_val, str):
                            for o_i, o in enumerate(q.options or []):
                                if o.option_text.strip().lower() == sel_val.strip().lower():
                                    student_selected_indices = [o_i]
                                    break
                    student_answer_text = ans_data.get("text", "") or ""

                if is_mcq:
                    mcq_total_count += 1
                    mcq_max_marks += q_marks

                    if len(student_selected_indices) > 0:
                        if set(student_selected_indices) == set(correct_indices):
                            item_status = "CORRECT"
                            mcq_correct_count += 1
                            mcq_marks_obtained += q_marks
                        else:
                            item_status = "INCORRECT"
                            mcq_incorrect_count += 1
                    else:
                        mcq_unattempted_count += 1
                else:
                    subj_total_count += 1
                    subj_max_marks += q_marks
                    if awarded_m is not None:
                        subj_marks_obtained += awarded_m

                q_dict = {
                    "id": str(q.id),
                    "question_index": q.question_index,
                    "question_type": q.question_type,
                    "text": q.question_text or "No text provided.",
                    "options": options_data,
                    "correct_option_indices": correct_indices,
                    "calculated_marks": q_marks,
                    "marks": q_marks,
                    "max_marks": q_marks,
                    "image_url": q.image_url,
                    "explanation": q.explanation,
                    "status": item_status,
                    "student_selected_indices": student_selected_indices,
                    "student_answer_text": student_answer_text,
                    "awarded_marks": awarded_m,
                    "examiner_comments": ex_comments
                }
                sec_dict["questions"].append(q_dict)
            sections_data.append(sec_dict)

        # Map candidate answers
        answers_map = {}
        answered_count = 0
        marked_count = 0
        timeline_events = []

        if session.start_time:
            timeline_events.append({
                "timestamp": session.start_time.isoformat(),
                "title": "Examination Session Started",
                "description": f"Candidate {student.full_name if student else 'Student'} verified identity and initiated exam."
            })

        for ca in candidate_answers:
            q_key = f"{ca.section_index}_{ca.question_index}"
            ans_data = ca.answer_data or {}
            answers_map[q_key] = {
                "section_index": ca.section_index,
                "question_index": ca.question_index,
                "answer_data": ans_data,
                "answer_status": ca.answer_status,
                "is_submitted": ca.is_submitted,
                "submission_count": ca.submission_count,
                "awarded_marks": ca.awarded_marks,
                "examiner_comments": ca.examiner_comments,
                "updated_at": ca.updated_at.isoformat() if ca.updated_at else None
            }

            has_ans = (
                ans_data.get("selected") is not None or
                (ans_data.get("selected_options") and len(ans_data.get("selected_options")) > 0) or
                (ans_data.get("text") and len(ans_data.get("text").strip()) > 0)
            )
            if has_ans:
                answered_count += 1
            if ca.answer_status == 'MARKED_FOR_REVIEW':
                marked_count += 1

            if ca.updated_at:
                timeline_events.append({
                    "timestamp": ca.updated_at.isoformat(),
                    "title": f"Response Autosaved [Section {ca.section_index}, Q{ca.question_index + 1}]",
                    "description": f"Autosaved candidate response ({ca.answer_status})"
                })

        if session.end_time:
            timeline_events.append({
                "timestamp": session.end_time.isoformat(),
                "title": "Examination Submitted",
                "description": "Candidate finalized and submitted examination session."
            })

        timeline_events = sorted(timeline_events, key=lambda e: e["timestamp"])

        start_t = session.start_time or session.created_at
        end_t = session.end_time or datetime.now(timezone.utc)
        if start_t and start_t.tzinfo is None:
            start_t = start_t.replace(tzinfo=timezone.utc)
        if end_t and end_t.tzinfo is None:
            end_t = end_t.replace(tzinfo=timezone.utc)
        time_taken = max(1, int((end_t - start_t).total_seconds())) if start_t else 0

        # Fetch Student Monitoring Record and Violations/Evidence
        from app.repositories.violation_repository import ViolationRepository
        violation_repo = ViolationRepository(self.db)
        session_violations = await violation_repo.get_by_exam_session(session_id, limit=200)

        formatted_violations = []
        all_evidence = []
        accumulated_risk = 0.0
        face_alerts_count = 0
        multiple_faces_found = False
        phone_found = False
        object_alerts_count = 0

        severity_weights = {
            "CRITICAL": 0.35,
            "HIGH": 0.20,
            "MEDIUM": 0.10,
            "LOW": 0.05
        }

        # Build Explainable Violation Descriptions & Grouped Timeline
        for v in session_violations:
            accumulated_risk += severity_weights.get(v.severity, 0.05)
            if v.risk_score > 0:
                accumulated_risk = max(accumulated_risk, v.risk_score)
            
            v_type_lower = (v.violation_type or "").lower()
            if "face" in v_type_lower or "identity" in v_type_lower or "looking" in v_type_lower:
                face_alerts_count += 1
            if "multiple" in v_type_lower:
                multiple_faces_found = True
            if "phone" in v_type_lower or "mobile" in v_type_lower:
                phone_found = True
            if "object" in v_type_lower or "phone" in v_type_lower or "item" in (v.category or "").lower():
                object_alerts_count += 1

            v_evidence = []
            for ev in (v.evidence or []):
                rel_path = (ev.file_path or "").replace("\\", "/")
                if rel_path and not rel_path.startswith("/") and not rel_path.startswith("http"):
                    filename = rel_path.split("/")[-1]
                    url_path = f"/uploads/{filename}"
                else:
                    url_path = rel_path

                replay_url = None
                if getattr(ev, "replay_clip_path", None):
                    r_path = str(ev.replay_clip_path).replace("\\", "/")
                    if r_path and not r_path.startswith("/") and not r_path.startswith("http"):
                        replay_url = f"/{r_path}" if not r_path.startswith("uploads") else f"/{r_path}"
                    else:
                        replay_url = r_path
                
                ev_item = {
                    "id": ev.id,
                    "file_path": url_path,
                    "evidence_type": ev.evidence_type,
                    "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
                    "confidence_score": ev.confidence_score if ev.confidence_score is not None else (v.confidence or 0.9),
                    "is_primary": getattr(ev, "is_primary", False),
                    "replay_clip_path": replay_url,
                    "metadata": ev.metadata_payload
                }
                v_evidence.append(ev_item)
                all_evidence.append(ev_item)

            # Generate explainable why_happened description
            risk_contrib_pct = int(severity_weights.get(v.severity, 0.05) * 100)
            if "phone" in v_type_lower or "mobile" in v_type_lower:
                explain_desc = f"Mobile phone remained visible continuously in candidate frame (Risk Contribution: +{risk_contrib_pct}%)."
            elif "looking" in v_type_lower or "gaze" in v_type_lower:
                explain_desc = f"Candidate gaze/head pose diverted away from active monitor (Risk Contribution: +{risk_contrib_pct}%)."
            elif "multiple" in v_type_lower:
                explain_desc = f"Multiple individuals detected in candidate frame (Risk Contribution: +{risk_contrib_pct}%)."
            elif "no_face" in v_type_lower or "missing" in v_type_lower:
                explain_desc = f"Candidate face absent from camera field of view (Risk Contribution: +{risk_contrib_pct}%)."
            elif "identity" in v_type_lower or "unknown" in v_type_lower:
                explain_desc = f"Unregistered face / identity mismatch detected against profile (Risk Contribution: +{risk_contrib_pct}%)."
            else:
                explain_desc = v.description or f"AI detected {v.violation_type} (Risk Contribution: +{risk_contrib_pct}%)."

            formatted_violations.append({
                "id": v.id,
                "violation_type": v.violation_type,
                "category": v.category,
                "severity": v.severity,
                "risk_score": round(v.risk_score, 2),
                "risk_contribution_pct": risk_contrib_pct,
                "duration_seconds": getattr(v, "duration_seconds", 0.0) or 0.0,
                "confidence": getattr(v, "confidence", 0.9) or 0.9,
                "timestamp": v.timestamp.isoformat() if v.timestamp else None,
                "status": v.status,
                "description": explain_desc,
                "reviewer_notes": v.reviewer_notes,
                "evidence": v_evidence
            })

            # Also group onto timeline
            if v.timestamp:
                timeline_events.append({
                    "timestamp": v.timestamp.isoformat(),
                    "title": f"AI Proctoring Violation: {v.violation_type}",
                    "description": f"{explain_desc} Severity: {v.severity} | Risk Contribution: +{risk_contrib_pct}%"
                })

        final_risk_score = round(min(1.0, accumulated_risk), 2)
        if final_risk_score >= 0.8:
            risk_level = "CRITICAL"
        elif final_risk_score >= 0.55:
            risk_level = "HIGH"
        elif final_risk_score >= 0.25:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # Generate Executive AI Monitoring Summary
        try:
            from app.monitoring_integration.monitoring_summary_adapter import MonitoringSummaryAdapter
            ai_summary = MonitoringSummaryAdapter.generate_summary(
                violations=formatted_violations,
                final_risk_score=final_risk_score,
                risk_level=risk_level,
                frames_processed=session.ai_session.frames_processed if session.ai_session else 0,
                total_evidence_count=len(all_evidence)
            )
        except Exception:
            ai_summary = {
                "headline": "Candidate proctoring summary processed.",
                "statements": ["Candidate examination monitoring completed."],
                "executive_summary_text": f"Candidate examination completed with {len(session_violations)} proctoring violation(s) recorded. Overall integrity classified as {risk_level} RISK.",
                "integrity_index": int((1.0 - final_risk_score) * 100),
                "risk_level": risk_level,
                "final_risk_score": final_risk_score
            }

        monitoring_report = {
            "summary": {
                "student_id": student.id if student else session.student_id,
                "student_name": student.full_name if student else f"Student #{session.student_id}",
                "exam_id": session.exam_id,
                "session_id": session.id,
                "final_risk_score": final_risk_score,
                "risk_level": risk_level,
                "total_violations": len(session_violations),
                "pending_violations": sum(1 for v in session_violations if v.status == "PENDING"),
                "confirmed_violations": sum(1 for v in session_violations if v.status == "CONFIRMED"),
                "total_evidence_count": len(all_evidence),
                "ai_executive_summary": ai_summary["executive_summary_text"]
            },
            "ai_summary": ai_summary,
            "violations": formatted_violations,
            "evidence_snapshots": all_evidence,
            "final_risk_score": final_risk_score,
            "risk_level": risk_level
        }

        total_marks_obtained = round(mcq_marks_obtained + subj_marks_obtained, 2)
        total_max_marks = round(mcq_max_marks + subj_max_marks, 2)
        percentage = round((total_marks_obtained / total_max_marks * 100), 2) if total_max_marks > 0 else 0.0

        # Runtime flags recovery count
        r_flags = (runtime_state.execution_flags if runtime_state and runtime_state.execution_flags else {})
        recovery_count = r_flags.get("recovery_count", 0)

        return {
            "summary": {
                "session_id": session.id,
                "student_id": student.id if student else session.student_id,
                "student_name": student.full_name if student else f"Student #{session.student_id}",
                "registration_number": getattr(student, 'registration_number', '') or f"REG-{session.student_id:04d}",
                "department": getattr(student, 'department', '') or "Computer Science",
                "program": getattr(student, 'program', '') or "BS Computer Science",
                "student_email": student.email if student else "N/A",
                "exam_id": exam.id if exam else session.exam_id,
                "exam_title": exam.title if exam else "Online Examination",
                "paper_title": exam.question_paper.title if exam and exam.question_paper else "Question Paper",
                "paper_mode": exam.question_paper.mode if exam and exam.question_paper else "STRUCTURED",
                "status": session.status,
                "evaluation_status": session.evaluation_status or "PENDING",
                "started_at": session.start_time.isoformat() if session.start_time else None,
                "submitted_at": session.end_time.isoformat() if session.end_time else None,
                "duration_minutes": exam.duration_minutes if exam else 120,
                "time_taken_seconds": time_taken,
                "recovery_count": recovery_count,
                "total_questions": total_questions,
                "answered_count": answered_count,
                "unanswered_count": max(0, total_questions - answered_count),
                "marked_count": marked_count,
                "final_score": total_marks_obtained,
                "total_max_marks": total_max_marks,
                "percentage": percentage
            },
            "scoring_summary": {
                "mcq_total_questions": mcq_total_count,
                "mcq_correct_count": mcq_correct_count,
                "mcq_incorrect_count": mcq_incorrect_count,
                "mcq_unattempted_count": mcq_unattempted_count,
                "mcq_marks_obtained": round(mcq_marks_obtained, 2),
                "mcq_max_marks": round(mcq_max_marks, 2),
                "subjective_total_questions": subj_total_count,
                "subjective_marks_obtained": round(subj_marks_obtained, 2),
                "subjective_max_marks": round(subj_max_marks, 2),
                "total_marks_obtained": total_marks_obtained,
                "total_max_marks": total_max_marks,
                "percentage": percentage
            },
            "sections": sections_data,
            "answers": answers_map,
            "state": {
                "current_section_index": runtime_state.current_section_index if runtime_state else 0,
                "current_question_index": runtime_state.current_question_index if runtime_state else 0,
                "navigation_history": runtime_state.navigation_history if runtime_state else [],
                "locked_sections": runtime_state.locked_sections if runtime_state else [],
                "locked_questions": runtime_state.locked_questions if runtime_state else []
            },
            "session_metadata": {
                "browser": r_flags.get("user_agent", "Chrome / Edge (Windows)"),
                "os": "Windows 11",
                "device": r_flags.get("device_fingerprint", "Desktop Workstation"),
                "recovery_count": recovery_count,
                "submission_method": "Automatic Time Expiry" if session.status in ["EXPIRED", "AUTO_SUBMITTED"] else ("Manual Candidate Submission" if session.end_time else "In Progress")
            },
            "timeline": timeline_events,
            "monitoring_report": monitoring_report,
            "ai_evidence_placeholder": {
                "available": len(session_violations) > 0,
                "message": f"{len(session_violations)} proctoring violation(s) recorded." if session_violations else "No proctoring violations recorded during this session.",
                "face_alerts": face_alerts_count,
                "multiple_faces_detected": multiple_faces_found,
                "phone_detected": phone_found,
                "object_detection_alerts": object_alerts_count
            }
        }
