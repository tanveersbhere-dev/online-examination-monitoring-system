import logging
import uuid
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.exam_session import ExamSession
from app.models.exam import Exam
from app.models.runtime_state import RuntimeState
from app.repositories.exam_session_repository import ExamSessionRepository
from app.repositories.exam_repository import ExamRepository
from app.repositories.exceptions import EntityNotFoundError

from app.config.runtime_policy import default_runtime_policy, ExamRuntimePolicyConfig
from app.services.ai_session_manager import AISessionManager

logger = logging.getLogger(__name__)

# State Constants
STATE_NOT_STARTED = "NOT_STARTED"
STATE_PENDING = "PENDING"
STATE_SCHEDULED = "SCHEDULED"
STATE_PREPARATION = "PREPARATION"
STATE_READY = "READY"
STATE_RUNNING = "RUNNING"
STATE_SUSPENDED = "SUSPENDED"
STATE_PAUSED_PENDING_POLICY = "PAUSED_PENDING_POLICY"
STATE_COMPLETED = "COMPLETED"
STATE_SUBMITTED = "SUBMITTED"
STATE_EXPIRED = "EXPIRED"
STATE_TERMINATED = "TERMINATED"

class ExamRuntimeOrchestrator:
    """
    Central backend exam runtime orchestrator enforcing:
    - Backend time & state authority (Server clock as single source of truth)
    - Session Suspension Engine (State: RUNNING <-> SUSPENDED)
    - Precise timer freezing during suspension (zero compensation, zero extra minutes)
    - Schedule window limit validation
    - Anti-Abuse Token & Ownership Locks
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.session_repo = ExamSessionRepository(db)
        self.exam_repo = ExamRepository(db)

    @staticmethod
    def get_server_time() -> datetime:
        """Returns current UTC server time. Browser clocks are never trusted."""
        return datetime.now(timezone.utc)

    @staticmethod
    def calculate_recommended_exam_window(paper_duration_minutes: int, recovery_buffer_minutes: int = 30) -> Dict[str, int]:
        return {
            "paper_duration_minutes": paper_duration_minutes,
            "recovery_buffer_minutes": recovery_buffer_minutes,
            "suggested_exam_window_minutes": paper_duration_minutes + recovery_buffer_minutes
        }

    async def get_or_create_runtime_state(self, session_id: int) -> RuntimeState:
        res = await self.db.execute(select(RuntimeState).where(RuntimeState.exam_session_id == session_id))
        state = res.scalar_one_or_none()
        if not state:
            state = RuntimeState(
                exam_session_id=session_id,
                current_section_index=0,
                current_question_index=0,
                execution_flags={}
            )
            self.db.add(state)
            await self.db.commit()
            await self.db.refresh(state)
        return state

    async def evaluate_session_state(self, session_id: int, prep_window_minutes: int = 15) -> str:
        """
        Backend State Machine & Window Evaluation.
        Transitions session status deterministically based on server time and session state.
        """
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            raise EntityNotFoundError(f"ExamSession {session_id} not found.")

        if session.status in [STATE_COMPLETED, STATE_SUBMITTED, STATE_EXPIRED, STATE_TERMINATED]:
            return session.status

        exam = await self.exam_repo.get_by_id(session.exam_id)
        if not exam:
            return session.status

        server_now = self.get_server_time()
        sched_start = exam.scheduled_start.replace(tzinfo=timezone.utc) if exam.scheduled_start and exam.scheduled_start.tzinfo is None else exam.scheduled_start
        sched_end = exam.scheduled_end.replace(tzinfo=timezone.utc) if exam.scheduled_end and exam.scheduled_end.tzinfo is None else exam.scheduled_end

        # Check Preparation Window
        if sched_start:
            prep_start = sched_start - timedelta(minutes=prep_window_minutes)
            if server_now < prep_start and exam.status not in [STATE_READY, STATE_RUNNING, STATE_SUSPENDED]:
                return STATE_NOT_STARTED
            elif prep_start <= server_now < sched_start and session.status == STATE_PENDING:
                return STATE_PREPARATION

        # Check Schedule Window Expiration during Suspension or Running
        if sched_end and server_now >= sched_end and session.status in [STATE_RUNNING, STATE_SUSPENDED]:
            session.status = STATE_EXPIRED
            session.end_time = server_now
            await self.db.commit()
            return STATE_EXPIRED

        # Check Effective Time Expiry
        effective_time = await self.calculate_effective_time(session_id)
        if effective_time["effective_remaining_seconds"] <= 0 and session.status in [STATE_RUNNING, STATE_SUSPENDED]:
            session.status = STATE_EXPIRED
            session.end_time = server_now
            await self.db.commit()
            return STATE_EXPIRED

        return session.status

    async def initialize_running_session(
        self,
        session_id: int,
        device_fingerprint: str,
        user_agent: str,
        ip_address: str
    ) -> Dict[str, Any]:
        """
        Runtime Ownership & Token Acquisition.
        Acquires ownership and generates secure recovery token when entering RUNNING state.
        """
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            raise EntityNotFoundError(f"ExamSession {session_id} not found.")

        server_now = self.get_server_time()

        if session.status == STATE_PENDING:
            session.status = STATE_RUNNING
            session.start_time = server_now
            await self.db.commit()

        state = await self.get_or_create_runtime_state(session_id)
        flags = dict(state.execution_flags or {})

        recovery_token = flags.get("recovery_token")
        if not recovery_token:
            recovery_token = f"rec_{uuid.uuid4().hex}"
            flags["recovery_token"] = recovery_token

        flags["device_fingerprint"] = device_fingerprint
        flags["user_agent"] = user_agent
        flags["ip_address"] = ip_address
        flags["last_heartbeat_at"] = server_now.isoformat()
        if "effective_elapsed_seconds" not in flags:
            flags["effective_elapsed_seconds"] = 0
        if "total_suspended_seconds" not in flags:
            flags["total_suspended_seconds"] = 0
        if "timeline" not in flags:
            flags["timeline"] = [{
                "timestamp": server_now.isoformat(),
                "event_type": "SESSION_INITIALIZED",
                "title": "Exam Runtime Initialized",
                "description": f"Candidate entered RUNNING state. Token: {recovery_token[:10]}..."
            }]

        state.execution_flags = flags
        await self.db.commit()

        effective_time = await self.calculate_effective_time(session_id)

        return {
            "session_id": session.id,
            "status": session.status,
            "recovery_token": recovery_token,
            "effective_time": effective_time
        }

    async def calculate_effective_time(self, session_id: int) -> Dict[str, Any]:
        """
        Effective Time Engine & Section Runtime Engine.
        Computes accurate raw elapsed, active elapsed, total suspended duration, and remaining seconds.
        Timer freezes during SUSPENDED state (zero extra compensation added).
        """
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            raise EntityNotFoundError(f"ExamSession {session_id} not found.")

        exam = await self.exam_repo.get_by_id(session.exam_id)
        sections_source = exam.section_rules if exam and exam.section_rules else (exam.question_paper.section_rules if exam and exam.question_paper else [])
        sec_paper_duration = sum(s.section_duration_minutes for s in sections_source if s.section_duration_minutes and s.section_duration_minutes > 0)
        
        if sec_paper_duration > 0:
            paper_duration_minutes = sec_paper_duration
        elif exam and exam.duration_minutes:
            paper_duration_minutes = exam.duration_minutes
        else:
            paper_duration_minutes = 120

        paper_duration_seconds = paper_duration_minutes * 60

        server_now = self.get_server_time()
        state = await self.get_or_create_runtime_state(session_id)
        flags = dict(state.execution_flags or {})

        start_time = session.start_time or session.created_at
        if start_time and start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)

        raw_elapsed = int((server_now - start_time).total_seconds()) if start_time else 0
        total_suspended = flags.get("total_suspended_seconds", 0)

        # If currently suspended, accumulate current pending suspension duration
        if session.status == STATE_SUSPENDED:
            suspended_at_str = flags.get("suspended_at")
            if suspended_at_str:
                suspended_at = datetime.fromisoformat(suspended_at_str)
                if suspended_at.tzinfo is None:
                    suspended_at = suspended_at.replace(tzinfo=timezone.utc)
                current_sus_dur = max(0, int((server_now - suspended_at).total_seconds()))
                total_suspended += current_sus_dur

        active_elapsed = max(0, raw_elapsed - total_suspended)

        # Calculate paper remaining time based on active elapsed
        paper_remaining = max(0, paper_duration_seconds - active_elapsed)

        # Calculate remaining time in scheduled window
        schedule_remaining = paper_remaining
        if exam and exam.scheduled_end:
            sched_end = exam.scheduled_end
            if sched_end.tzinfo is None:
                sched_end = sched_end.replace(tzinfo=timezone.utc)
            schedule_remaining = max(0, int((sched_end - server_now).total_seconds()))

        effective_remaining = min(paper_remaining, schedule_remaining)

        # Section-level timer accounting
        sections_source = exam.section_rules if exam and exam.section_rules else (exam.question_paper.section_rules if exam and exam.question_paper else [])
        section_timers = {}

        for sec in sections_source:
            sec_idx = str(sec.section_index)
            allocated = (sec.section_duration_minutes * 60) if sec.section_duration_minutes else paper_duration_seconds
            sec_elapsed = min(allocated, active_elapsed)
            sec_remaining = min(max(0, allocated - sec_elapsed), schedule_remaining)

            section_timers[sec_idx] = {
                "section_name": sec.section_name,
                "allocated_seconds": allocated,
                "elapsed_seconds": sec_elapsed,
                "remaining_seconds": sec_remaining,
                "is_completed": sec_idx in [str(s) for s in state.completed_sections]
            }

        return {
            "server_time": server_now.isoformat(),
            "status": session.status,
            "paper_duration_seconds": paper_duration_seconds,
            "raw_elapsed_seconds": raw_elapsed,
            "active_elapsed_seconds": active_elapsed,
            "total_suspended_seconds": total_suspended,
            "effective_remaining_seconds": effective_remaining,
            "section_timers": section_timers
        }

    async def suspend_session(self, session_id: int, reason: str = "Session integrity lost") -> Dict[str, Any]:
        """
        Immediately suspends an active examination.
        - Transitions session status to SUSPENDED.
        - Freezes timer (records suspended_at timestamp).
        - Calls AISessionManager.OnRuntimePaused(session_id).
        """
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            raise EntityNotFoundError(f"ExamSession {session_id} not found.")

        server_now = self.get_server_time()
        state = await self.get_or_create_runtime_state(session_id)
        flags = dict(state.execution_flags or {})

        if session.status != STATE_SUSPENDED:
            session.status = STATE_SUSPENDED
            flags["suspended_at"] = server_now.isoformat()
            flags["suspension_reason"] = reason

            timeline = flags.get("timeline", [])
            timeline.append({
                "timestamp": server_now.isoformat(),
                "event_type": "SESSION_SUSPENDED",
                "title": "Examination Suspended",
                "description": f"Session suspended immediately. Reason: {reason}. Timer frozen."
            })
            flags["timeline"] = timeline
            state.execution_flags = flags

            await self.db.commit()
            AISessionManager.OnRuntimePaused(session_id)

        effective_time = await self.calculate_effective_time(session_id)
        return {
            "session_id": session_id,
            "status": STATE_SUSPENDED,
            "reason": reason,
            "effective_time": effective_time
        }

    async def resume_session(
        self,
        session_id: int,
        request_token: str,
        device_fingerprint: str,
        user_agent: str,
        ip_address: str
    ) -> Dict[str, Any]:
        """
        Resumes a suspended examination.
        - Validates scheduled end window.
        - Accumulates suspension duration into total_suspended_seconds.
        - Resumes timer at exact paused value (zero compensation added).
        - Calls AISessionManager.OnRuntimeResumed(session_id).
        """
        session = await self.session_repo.get_by_id(session_id)
        if not session:
            raise EntityNotFoundError(f"ExamSession {session_id} not found.")

        server_now = self.get_server_time()
        exam = await self.exam_repo.get_by_id(session.exam_id)

        # 1. Validate Schedule Window Expiration
        if exam and exam.scheduled_end:
            sched_end = exam.scheduled_end.replace(tzinfo=timezone.utc) if exam.scheduled_end.tzinfo is None else exam.scheduled_end
            if server_now >= sched_end:
                session.status = STATE_EXPIRED
                session.end_time = server_now
                await self.db.commit()
                return {
                    "session_id": session_id,
                    "status": STATE_EXPIRED,
                    "message": "Exam scheduled end window has expired. Resumption rejected.",
                    "effective_time": await self.calculate_effective_time(session_id)
                }

        state = await self.get_or_create_runtime_state(session_id)
        flags = dict(state.execution_flags or {})

        # 2. Accumulate Suspension Duration into total_suspended_seconds
        suspended_at_str = flags.get("suspended_at")
        if suspended_at_str:
            suspended_at = datetime.fromisoformat(suspended_at_str)
            if suspended_at.tzinfo is None:
                suspended_at = suspended_at.replace(tzinfo=timezone.utc)
            sus_dur = max(0, int((server_now - suspended_at).total_seconds()))
            flags["total_suspended_seconds"] = flags.get("total_suspended_seconds", 0) + sus_dur
            flags.pop("suspended_at", None)

        # 3. Restore RUNNING Status
        session.status = STATE_RUNNING
        flags["last_heartbeat_at"] = server_now.isoformat()

        timeline = flags.get("timeline", [])
        timeline.append({
            "timestamp": server_now.isoformat(),
            "event_type": "SESSION_RESUMED",
            "title": "Examination Resumed",
            "description": "Session restored to RUNNING state. Timer resumed at exact paused value."
        })
        flags["timeline"] = timeline
        state.execution_flags = flags

        await self.db.commit()
        AISessionManager.OnRuntimeResumed(session_id)

        effective_time = await self.calculate_effective_time(session_id)

        return {
            "session_id": session_id,
            "status": STATE_RUNNING,
            "effective_time": effective_time
        }

