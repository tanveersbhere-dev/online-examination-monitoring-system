"""
=============================================================================
CENTRAL EXAMINATION LIFECYCLE SERVICE
=============================================================================

Single authority responsible for state synchronization across the entire
examination platform:
 - Exam master state transitions (DRAFT -> READY -> SCHEDULED -> RUNNING -> PAUSED -> COMPLETED)
 - ExamSession status synchronization (PENDING -> MISSED, RUNNING -> AUTO_SUBMITTED / EXPIRED)
 - AI Engine Thread teardown (AISessionManager.OnRuntimeStopped)
 - WebSocket session termination & broadcast (ConnectionManager.close_session_connections)
 - Candidate answer objective auto-scoring & evaluation setup
 - Time-based schedule evaluation & automated expiry synchronization
=============================================================================
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from app.models.exam import Exam
from app.models.exam_session import ExamSession
from app.models.candidate_answer import CandidateAnswer
from app.models.exam_question_rule import ExamQuestionRule
from app.models.question_option import QuestionOption

from app.repositories.exam_repository import ExamRepository
from app.repositories.exam_session_repository import ExamSessionRepository
from app.repositories.exceptions import EntityNotFoundError
from app.services.exceptions import ExamNotFoundError, InvalidExamStateError

from app.services.ai_session_manager import AISessionManager
from app.websocket.connection_manager import manager
from app.websocket.websocket_events import WSEvent, WSEventType

logger = logging.getLogger(__name__)


class ExamLifecycleService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.exam_repo = ExamRepository(db)
        self.session_repo = ExamSessionRepository(db)

    @staticmethod
    def get_server_time() -> datetime:
        """Returns current server time in UTC as single source of truth."""
        return datetime.now(timezone.utc)

    async def sync_exam_lifecycle(self, exam_id: int) -> Exam:
        """
        Synchronizes an exam's state against the server clock.
        - Auto-activates READY/SCHEDULED exams when scheduled_start <= now < scheduled_end.
        - Auto-completes RUNNING/PAUSED/READY exams when now >= scheduled_end.
        """
        exam = await self.exam_repo.get_by_id(exam_id)
        if not exam:
            raise ExamNotFoundError(f"Exam {exam_id} not found.")

        server_now = self.get_server_time()

        if not exam.scheduled_start or not exam.scheduled_end:
            return exam

        sched_start = exam.scheduled_start.replace(tzinfo=timezone.utc) if exam.scheduled_start.tzinfo is None else exam.scheduled_start
        sched_end = exam.scheduled_end.replace(tzinfo=timezone.utc) if exam.scheduled_end.tzinfo is None else exam.scheduled_end

        # Case 1: Exam window has ended -> Auto-complete
        if server_now >= sched_end and exam.status in ["READY", "SCHEDULED", "RUNNING", "PAUSED"]:
            logger.info(f"[LIFECYCLE] Auto-completing expired exam {exam.id} (scheduled_end {sched_end} <= now {server_now})")
            return await self.complete_exam(exam_id, is_automated=True)

        # Case 2: Start time reached -> Auto-activate
        if sched_start <= server_now < sched_end and exam.status in ["READY", "SCHEDULED"]:
            logger.info(f"[LIFECYCLE] Auto-starting scheduled exam {exam.id} (scheduled_start {sched_start} <= now {server_now})")
            return await self.start_exam(exam_id, is_automated=True)

        return exam

    async def start_exam(self, exam_id: int, user_id: Optional[int] = None, is_automated: bool = False) -> Exam:
        """Transitions exam to RUNNING state and initializes monitoring."""
        exam = await self.exam_repo.get_by_id(exam_id)
        if not exam:
            raise ExamNotFoundError(f"Exam {exam_id} not found.")

        if exam.status not in ["READY", "SCHEDULED"]:
            if exam.status == "RUNNING":
                return exam
            raise InvalidExamStateError(f"Cannot start exam from state '{exam.status}'. Must be READY or SCHEDULED.")

        exam.status = "RUNNING"
        await self.db.commit()

        # Broadcast WebSocket start event to all supervisors / monitoring dashboards
        event = WSEvent(
            event=WSEventType.SESSION_STARTED.value,
            timestamp=self.get_server_time(),
            exam_session_id=exam.id,
            payload={"exam_id": exam.id, "title": exam.title, "status": "RUNNING"}
        )
        await manager.broadcast_all(event)
        logger.info(f"[LIFECYCLE] Exam {exam.id} successfully transitioned to RUNNING.")
        return exam

    async def complete_exam(self, exam_id: int, user_id: Optional[int] = None, is_automated: bool = False) -> Exam:
        """
        Master completion & teardown method.
        Synchronizes all child sessions, terminates AI threads, closes WebSocket rooms,
        grades objective questions, and sets Exam.status to COMPLETED.
        """
        exam = await self.exam_repo.get_by_id(exam_id)
        if not exam:
            raise ExamNotFoundError(f"Exam {exam_id} not found.")

        if exam.status == "COMPLETED":
            logger.info(f"[LIFECYCLE] Exam {exam_id} is already COMPLETED.")
            return exam

        server_now = self.get_server_time()
        exam.status = "COMPLETED"

        # Fetch all ExamSessions for this exam
        session_stmt = (
            select(ExamSession)
            .options(
                selectinload(ExamSession.candidate_answers),
                selectinload(ExamSession.runtime_state)
            )
            .where(ExamSession.exam_id == exam_id)
        )
        session_res = await self.db.execute(session_stmt)
        sessions = list(session_res.scalars().all())

        for session in sessions:
            old_status = session.status

            if old_status == "PENDING":
                session.status = "MISSED"
                session.end_time = server_now
            elif old_status in ["RUNNING", "PAUSED", "PREPARATION"]:
                session.status = "AUTO_SUBMITTED"
                session.end_time = server_now

            # 1. Stop AI Engine Thread for session
            try:
                AISessionManager.OnRuntimeStopped(session.id)
            except Exception as e:
                logger.warning(f"[LIFECYCLE] Error stopping AI thread for session {session.id}: {e}")

            # 2. Objective Auto-Grading for candidate answers
            try:
                await self._auto_grade_session_answers(session)
            except Exception as e:
                logger.warning(f"[LIFECYCLE] Error auto-grading session {session.id}: {e}")

            # 3. Notify and close WebSockets for session
            try:
                event = WSEvent(
                    event=WSEventType.SESSION_COMPLETED.value,
                    timestamp=server_now,
                    exam_session_id=session.id,
                    payload={
                        "exam_id": exam_id,
                        "session_id": session.id,
                        "status": session.status,
                        "message": "Examination window has concluded."
                    }
                )
                await manager.broadcast(event)
                await manager.close_session_connections(session.id)
            except Exception as e:
                logger.warning(f"[LIFECYCLE] Error closing WebSockets for session {session.id}: {e}")

        await self.db.commit()
        await self.db.refresh(exam)

        logger.info(f"[LIFECYCLE] Master completion done for Exam {exam.id}. Processed {len(sessions)} student session(s).")
        return exam

    async def _auto_grade_session_answers(self, session: ExamSession):
        """Auto-grades objective MCQ questions for an exam session."""
        if not session.candidate_answers:
            session.objective_score = 0.0
            session.total_score = (session.subjective_score or 0.0)
            return

        # Fetch question rules with options for this exam or its question paper
        exam = session.exam or await self.exam_repo.get_by_id(session.exam_id)
        qp_id = exam.question_paper_id if exam else None

        q_rules_stmt = (
            select(ExamQuestionRule)
            .options(selectinload(ExamQuestionRule.options))
            .where(
                or_(
                    ExamQuestionRule.exam_id == session.exam_id,
                    ExamQuestionRule.question_paper_id == qp_id
                )
            )
        )
        q_res = await self.db.execute(q_rules_stmt)
        q_rules = list(q_res.scalars().all())

        rule_map = {q.question_index: q for q in q_rules}

        total_mcq_score = 0.0
        for ans in session.candidate_answers:
            if not ans.answer_data:
                continue

            selected_option_idx = ans.answer_data.get("selected_option")
            if selected_option_idx is None:
                continue

            # Match question rule by question_index
            q_rule = rule_map.get(ans.question_index)
            if q_rule and q_rule.question_type == "MCQ" and q_rule.options:
                if 0 <= selected_option_idx < len(q_rule.options):
                    chosen_opt = q_rule.options[selected_option_idx]
                    if chosen_opt.is_correct:
                        total_mcq_score += float(q_rule.marks or 1.0)
                        ans.marks_awarded = float(q_rule.marks or 1.0)
                    else:
                        ans.marks_awarded = 0.0

        session.objective_score = round(total_mcq_score, 2)
        session.total_score = round(session.objective_score + (session.subjective_score or 0.0), 2)
        session.evaluated_at = self.get_server_time()

    async def process_expired_exams(self) -> int:
        """
        Scans for expired exams and auto-completes them.
        Returns count of exams processed.
        """
        server_now = self.get_server_time()
        stmt = (
            select(Exam)
            .where(
                Exam.status.in_(["READY", "SCHEDULED", "RUNNING", "PAUSED"]),
                Exam.scheduled_end.isnot(None),
                Exam.scheduled_end <= server_now
            )
        )
        res = await self.db.execute(stmt)
        expired_exams = list(res.scalars().all())

        count = 0
        for exam in expired_exams:
            try:
                await self.complete_exam(exam.id, is_automated=True)
                count += 1
            except Exception as e:
                logger.error(f"[LIFECYCLE] Failed to auto-complete expired exam {exam.id}: {e}")

        return count
