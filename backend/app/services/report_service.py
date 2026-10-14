import logging
from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.exam import Exam
from app.models.exam_session import ExamSession
from app.models.violation import Violation
from app.schemas.report import (
    ReportSummaryItem,
    MonitoringReportResponse,
    StudentInfo,
    ExamInfo,
    SessionSummary,
    RiskSummary,
    ViolationTimelineItem,
    EvidenceGalleryItem,
    EvidenceItem,
    ReportStatistics,
    StudentAnalyticsResponse,
    StudentExamHistoryItem
)

logger = logging.getLogger(__name__)

class ReportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_completed_reports_summary(self) -> List[ReportSummaryItem]:
        query = (
            select(ExamSession)
            .options(
                selectinload(ExamSession.exam),
                selectinload(ExamSession.student),
                selectinload(ExamSession.violations)
            )
            .filter(ExamSession.status == "COMPLETED")
        )
        result = await self.db.execute(query)
        sessions = result.scalars().all()

        summaries = []
        for session in sessions:
            duration = None
            if session.start_time and session.end_time:
                duration = (session.end_time - session.start_time).total_seconds() / 60.0

            highest_risk = 0.0
            if session.violations:
                highest_risk = max(v.risk_score for v in session.violations)

            summaries.append(
                ReportSummaryItem(
                    exam_session_id=session.id,
                    exam_name=session.exam.title,
                    student_name=session.student.full_name,
                    date=session.start_time,
                    duration_minutes=duration,
                    final_risk_score=highest_risk,
                    total_violations=len(session.violations)
                )
            )
        return summaries

    async def get_report(self, exam_session_id: int) -> Optional[MonitoringReportResponse]:
        query = (
            select(ExamSession)
            .options(
                selectinload(ExamSession.exam).selectinload(Exam.question_paper),
                selectinload(ExamSession.student),
                selectinload(ExamSession.ai_session),
                selectinload(ExamSession.violations).selectinload(Violation.evidence)
            )
            .filter(ExamSession.id == exam_session_id, ExamSession.status == "COMPLETED")
        )
        result = await self.db.execute(query)
        session = result.scalar_one_or_none()

        if not session:
            return None

        # 1. Student Info
        student_info = StudentInfo(
            student_name=session.student.full_name,
            student_id=session.student.id,
            email=session.student.email
        )

        # 2. Exam Info
        exam = session.exam
        course_title = (exam.course_name or "").strip()
        if not course_title and exam.question_paper and exam.question_paper.course_name:
            course_title = exam.question_paper.course_name.strip()
        if not course_title:
            course_title = "Unassigned"

        exam_info = ExamInfo(
            exam_name=exam.title,
            course=course_title,
            start_time=exam.scheduled_start,
            end_time=exam.scheduled_end,
            duration_minutes=float(exam.duration_minutes) if exam.duration_minutes is not None else 0.0
        )

        # 3. Session Summary
        duration = None
        if session.start_time and session.end_time:
            duration = (session.end_time - session.start_time).total_seconds() / 60.0

        session_summary = SessionSummary(
            final_status=session.status,
            total_monitoring_duration_minutes=duration,
            ai_session_status=session.ai_session.state if session.ai_session else "NONE"
        )

        # 4 & 7. Calculate Statistics & Risk Summary
        stats = ReportStatistics()
        stats.total_violations = len(session.violations)

        # Sort violations chronologically
        sorted_violations = sorted(session.violations, key=lambda v: v.timestamp)

        timeline_items = []
        gallery = []
        total_risk = 0.0
        SEVERITY_ORDER = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}

        for v in sorted_violations:
            total_risk += v.risk_score
            stats.highest_risk_score = max(stats.highest_risk_score, v.risk_score)
            
            # Map violation types strictly to requested metrics
            v_type = v.violation_type.upper()
            if "PHONE" in v_type or "MOBILE" in v_type:
                stats.total_phone_detections += 1
            elif "BOOK" in v_type or "NOTEBOOK" in v_type or "PAPER" in v_type:
                stats.total_book_detections += 1
            elif "MULTIPLE" in v_type:
                stats.total_multiple_person += 1
            elif "GAZE" in v_type or "LOOK" in v_type or "ATTENTION" in v_type:
                stats.total_looking_away += 1
            elif "IDENTITY" in v_type or "UNKNOWN" in v_type or "MISMATCH" in v_type:
                stats.total_identity_events += 1
            elif "ABSENCE" in v_type or "NO_FACE" in v_type or "MISSING" in v_type:
                stats.total_face_absence += 1
            elif "EARPHONE" in v_type or "HEADPHONE" in v_type:
                stats.total_earphone_events += 1

            # Populate Evidence Gallery with full metadata & POSIX paths
            if v.evidence:
                snapshots = []
                for e in v.evidence:
                    stats.total_snapshots += 1
                    posix_path = (e.file_path or "").replace("\\", "/")
                    replay_posix = (e.replay_clip_path or "").replace("\\", "/") if e.replay_clip_path else None
                    snapshots.append(
                        EvidenceItem(
                            timestamp=e.timestamp,
                            evidence_type=e.evidence_type,
                            file_path=posix_path,
                            violation_id=v.id,
                            violation_type=v.violation_type,
                            confidence_score=e.confidence_score if e.confidence_score is not None else (v.confidence or 0.9),
                            risk_score=v.risk_score,
                            is_primary=getattr(e, 'is_primary', False),
                            replay_clip_path=replay_posix
                        )
                    )
                first_conf = v.evidence[0].confidence_score if (v.evidence and v.evidence[0].confidence_score is not None) else 0.9
                gallery.append(
                    EvidenceGalleryItem(
                        violation_id=v.id,
                        violation_type=v.violation_type,
                        timestamp=v.timestamp,
                        confidence_score=first_conf,
                        risk_score=v.risk_score,
                        snapshots=snapshots
                    )
                )

        # Timeline Merging Algorithm: Merge consecutive duplicate violations within 30s gap into single continuous event
        if sorted_violations:
            curr_group = [sorted_violations[0]]
            for v in sorted_violations[1:]:
                prev_v = curr_group[-1]
                time_gap = (v.timestamp - prev_v.timestamp).total_seconds()
                if v.violation_type == prev_v.violation_type and time_gap <= 30.0:
                    curr_group.append(v)
                else:
                    timeline_items.append(self._create_aggregated_timeline_item(curr_group, SEVERITY_ORDER))
                    curr_group = [v]
            if curr_group:
                timeline_items.append(self._create_aggregated_timeline_item(curr_group, SEVERITY_ORDER))

        timeline = timeline_items

        stats.average_risk_score = total_risk / stats.total_violations if stats.total_violations > 0 else 0.0

        def get_risk_level_string(score: float) -> str:
            if score >= 75: return "CRITICAL"
            if score >= 50: return "HIGH"
            if score >= 25: return "MEDIUM"
            return "LOW"

        risk_summary = RiskSummary(
            final_risk_score=stats.highest_risk_score,
            highest_risk_level=get_risk_level_string(stats.highest_risk_score),
            average_risk_level=get_risk_level_string(stats.average_risk_score),
            total_violations=stats.total_violations
        )

        # 8. Recommendation Engine (Rule-based)
        highest_level = risk_summary.highest_risk_level
        recommendation = "No Action Required"
        if highest_level == "MEDIUM":
            recommendation = "Examiner Review Recommended"
        elif highest_level == "HIGH":
            recommendation = "Manual Review Required"
        elif highest_level == "CRITICAL":
            recommendation = "Strong Evidence of Suspicious Behaviour"

        return MonitoringReportResponse(
            exam_session_id=session.id,
            student_info=student_info,
            exam_info=exam_info,
            session_summary=session_summary,
            risk_summary=risk_summary,
            timeline=timeline,
            evidence_gallery=gallery,
            statistics=stats,
            recommendation=recommendation
        )

    def _create_aggregated_timeline_item(self, group: List[Violation], severity_order: dict) -> ViolationTimelineItem:
        first_v = group[0]
        last_v = group[-1]
        start_ts = first_v.timestamp
        end_ts = last_v.timestamp
        span_duration = round((end_ts - start_ts).total_seconds(), 1)
        db_duration = sum(float(getattr(v, 'duration_seconds', 0.0) or 0.0) for v in group)
        duration = round(max(span_duration, db_duration, 1.5 if len(group) == 1 else len(group) * 1.5), 1)
        occurrences = len(group)
        max_risk = max(v.risk_score for v in group)
        highest_sev = max(group, key=lambda v: severity_order.get(v.severity.upper(), 0)).severity

        desc = first_v.description
        if occurrences > 1:
            desc = f"{first_v.violation_type} detected ({occurrences} occurrences over {int(duration)}s)"

        return ViolationTimelineItem(
            timestamp=start_ts,
            end_timestamp=end_ts if occurrences > 1 else None,
            violation_id=first_v.id,
            violation_type=first_v.violation_type,
            category=first_v.category,
            severity=highest_sev,
            risk_score=max_risk,
            max_risk_score=max_risk,
            duration_seconds=duration,
            occurrences=occurrences,
            short_description=desc
        )

    async def get_student_analytics(self, student_id: int) -> StudentAnalyticsResponse:
        from app.schemas.report import StudentAnalyticsResponse, StudentExamHistoryItem

        query = (
            select(ExamSession)
            .options(
                selectinload(ExamSession.exam),
                selectinload(ExamSession.violations)
            )
            .filter(ExamSession.student_id == student_id, ExamSession.status == "COMPLETED")
        )
        result = await self.db.execute(query)
        sessions = result.scalars().all()

        total_exams = len(sessions)
        total_violations_all = 0
        sum_risk_scores = 0.0

        history = []

        for session in sessions:
            duration = None
            if session.start_time and session.end_time:
                duration = (session.end_time - session.start_time).total_seconds() / 60.0

            highest_risk = 0.0
            violations_count = len(session.violations)
            
            if violations_count > 0:
                highest_risk = max(v.risk_score for v in session.violations)
                
            total_violations_all += violations_count
            sum_risk_scores += highest_risk

            history.append(
                StudentExamHistoryItem(
                    exam_session_id=session.id,
                    exam_name=session.exam.title,
                    date=session.start_time,
                    duration_minutes=duration,
                    highest_risk_score=highest_risk,
                    total_violations=violations_count
                )
            )

        average_risk = (sum_risk_scores / total_exams) if total_exams > 0 else 0.0

        # Sort history chronologically descending
        history.sort(key=lambda x: x.date if x.date else datetime.min, reverse=True)

        return StudentAnalyticsResponse(
            student_id=student_id,
            total_exams_taken=total_exams,
            average_risk_score=average_risk,
            total_violations_across_exams=total_violations_all,
            exam_history=history
        )
