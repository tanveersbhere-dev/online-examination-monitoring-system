import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.monitoring import (
    MonitoringStatusResponse,
    MonitoringCurrentResponse,
    ActiveMonitoringSessionItem,
    MonitoringHealthResponse,
    ViolationSchema,
    TimelineEventSchema
)
from app.models.exam_session import ExamSession
from app.models.exam import Exam
from app.models.student import Student
from app.models.user import User
from app.models.ai_session import AISession
from app.models.violation import Violation
from app.models.ai_event import AIEvent
from app.services.ai_session_manager import AISessionManager

logger = logging.getLogger(__name__)

class MonitoringService:
    """
    Service for exposing monitoring status and database-backed events without local CV pipeline execution.
    """

    @staticmethod
    def get_status(exam_id: int) -> MonitoringStatusResponse:
        thread = AISessionManager._active_threads.get(exam_id)
        thread_alive = bool(thread and thread.is_alive())
        return MonitoringStatusResponse(
            exam_status="RUNNING" if thread_alive else "INACTIVE",
            ai_session_status="ACTIVE" if thread_alive else "OFFLINE",
            current_risk_level="LOW",
            current_risk_score=0.0,
            current_student_status="ATTENTIVE" if thread_alive else "OFFLINE"
        )

    @staticmethod
    async def get_current(exam_session_id: int, db: AsyncSession) -> MonitoringCurrentResponse:
        # Fetch recent AI Events (last 50 for timeline)
        stmt_events = (
            select(AIEvent)
            .where(AIEvent.exam_session_id == exam_session_id)
            .order_by(desc(AIEvent.timestamp))
            .limit(50)
        )
        result_events = await db.execute(stmt_events)
        ai_events = result_events.scalars().all()

        # Fetch active violations (Unresolved)
        stmt_violations = (
            select(Violation)
            .where(
                and_(
                    Violation.exam_session_id == exam_session_id,
                    Violation.status.in_(["PENDING", "REVIEWED"])
                )
            )
            .order_by(desc(Violation.timestamp))
        )
        result_violations = await db.execute(stmt_violations)
        violations = result_violations.scalars().all()

        face_status = "VERIFIED"
        gaze_dir = "CENTER"
        head_pose = "FRONTAL"
        object_summary = {"phones_detected": 0, "multiple_persons": False}

        # Calculate Risk Score from DB & AISession
        risk_score = 0.0
        ai_sess_stmt = select(AISession).join(ExamSession).where(ExamSession.id == exam_session_id)
        ai_sess_res = await db.execute(ai_sess_stmt)
        ai_sess = ai_sess_res.scalar_one_or_none()
        if ai_sess and ai_sess.current_risk:
            risk_score = ai_sess.current_risk
        elif violations:
            critical = sum(1 for v in violations if v.severity == "CRITICAL")
            high = sum(1 for v in violations if v.severity == "HIGH")
            medium = sum(1 for v in violations if v.severity == "MEDIUM")
            risk_score = min(100.0, (critical * 35) + (high * 20) + (medium * 10))

        timeline_events = []
        for e in ai_events:
            desc_text = e.payload.get("description", e.event_type) if isinstance(e.payload, dict) else e.event_type
            timeline_events.append(TimelineEventSchema(
                event_type=e.event_type,
                timestamp=e.timestamp,
                severity=e.severity,
                description=desc_text
            ))

        active_v = []
        for v in violations:
            active_v.append(ViolationSchema(
                id=v.id,
                violation_type=v.violation_type,
                severity=v.severity,
                timestamp=v.timestamp
            ))

        return MonitoringCurrentResponse(
            current_risk_score=risk_score,
            current_face_status=face_status,
            current_gaze=gaze_dir,
            current_head_pose=head_pose,
            object_detection_summary=object_summary,
            environment_summary={"lighting": "OPTIMAL", "background_noise": "LOW"},
            active_violations=active_v,
            timeline_events=timeline_events
        )

    @staticmethod
    async def get_active_sessions(
        db: AsyncSession,
        examiner_id: int,
        is_admin: bool = False
    ) -> List[ActiveMonitoringSessionItem]:
        """
        Retrieves all RUNNING exam sessions for exams owned by or supervised by the examiner.
        """
        stmt = (
            select(ExamSession)
            .options(
                selectinload(ExamSession.exam),
                selectinload(ExamSession.student),
                selectinload(ExamSession.ai_session),
                selectinload(ExamSession.violations)
            )
            .join(Exam, ExamSession.exam_id == Exam.id)
            .where(ExamSession.status == "RUNNING")
        )

        if not is_admin:
            stmt = stmt.where(Exam.created_by == examiner_id)

        res = await db.execute(stmt)
        sessions = res.scalars().all()

        student_records_res = await db.execute(select(Student))
        student_records = student_records_res.scalars().all()
        student_map = {st.email.lower(): st for st in student_records if st.email}

        items = []
        for s in sessions:
            student_user = s.student
            stu_profile = student_map.get(student_user.email.lower()) if (student_user and student_user.email) else None
            reg_no = (
                getattr(stu_profile, "registration_number", None)
                or getattr(student_user, "registration_number", None)
                or f"REG-{s.student_id:04d}"
            )

            thread = AISessionManager._active_threads.get(s.id)
            thread_alive = bool(thread and thread.is_alive())

            risk = 0.0
            if s.ai_session and s.ai_session.current_risk:
                risk = s.ai_session.current_risk
            elif s.violations:
                risk = max((v.risk_score for v in s.violations), default=0.0)

            risk_level = "CRITICAL" if risk >= 75 else "HIGH" if risk >= 50 else "MEDIUM" if risk >= 25 else "LOW"

            unresolved = [v for v in (s.violations or []) if v.status in ["PENDING", "REVIEWED"] and v.resolved_at is None]
            latest_v = s.violations[-1].description if s.violations else "Monitoring Active - No Incidents"

            items.append(ActiveMonitoringSessionItem(
                session_id=s.id,
                exam_id=s.exam_id,
                exam_title=s.exam.title if s.exam else f"Exam #{s.exam_id}",
                student_id=s.student_id,
                student_name=student_user.full_name if student_user else f"Student #{s.student_id}",
                student_reg_no=reg_no,
                start_time=s.start_time,
                session_status=s.status,
                monitoring_status="ACTIVE" if thread_alive else (s.ai_session.monitoring_status if s.ai_session else "INACTIVE"),
                current_risk=round(risk, 1),
                risk_level=risk_level,
                active_violations_count=len(unresolved),
                total_violations_count=len(s.violations or []),
                latest_event=latest_v,
                camera_status="CONNECTED" if thread_alive else "DISCONNECTED"
            ))

        return items

    @staticmethod
    async def get_session_health(exam_session_id: int, db: AsyncSession) -> MonitoringHealthResponse:
        """
        Retrieves monitoring diagnostics status for an active session.
        """
        thread = AISessionManager._active_threads.get(exam_session_id)
        thread_alive = bool(thread and thread.is_alive())

        # Load from DB
        ai_sess_stmt = select(AISession).join(ExamSession).where(ExamSession.id == exam_session_id)
        ai_sess_res = await db.execute(ai_sess_stmt)
        ai_sess = ai_sess_res.scalar_one_or_none()

        monitoring_status = "ACTIVE" if thread_alive else "OFFLINE"
        frames_count = 0
        risk = 0.0
        if ai_sess:
            monitoring_status = ai_sess.monitoring_status if not thread_alive else "ACTIVE"
            frames_count = ai_sess.frames_processed or 0
            risk = ai_sess.current_risk or 0.0

        return MonitoringHealthResponse(
            exam_session_id=exam_session_id,
            thread_alive=thread_alive,
            monitoring_status=monitoring_status,
            frames_processed=frames_count,
            current_risk=risk,
            processor_health={}
        )
