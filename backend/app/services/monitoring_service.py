import logging
from typing import Dict, Any
from app.schemas.monitoring import MonitoringStatusResponse, MonitoringCurrentResponse

logger = logging.getLogger(__name__)

class MonitoringService:
    """
    Service for exposing AI Engine context to REST endpoints.
    Reads exclusively from AISessionManager or ExamContext placeholders.
    """

    @staticmethod
    def get_status(exam_id: int) -> MonitoringStatusResponse:
        # MOCK: In a full system, this queries the AI Engine's ExamContext or AISessionManager for `exam_id`.
        # The prompt requires us to strictly decouple. We are returning dummy state simulating the AI outputs.
        return MonitoringStatusResponse(
            exam_status="RUNNING",
            ai_session_status="ACTIVE",
            current_risk_level="MEDIUM",
            current_risk_score=45.5,
            current_student_status="ATTENTIVE"
        )

    @staticmethod
    async def get_current(exam_id: int, db: Any) -> MonitoringCurrentResponse:
        from sqlalchemy import select, desc
        from app.models.ai_event import AIEvent
        from app.models.violation import Violation
        
        # Fetch recent AI Events (last 50 for timeline)
        stmt_events = select(AIEvent).where(AIEvent.exam_session_id == exam_id).order_by(desc(AIEvent.timestamp)).limit(50)
        result_events = await db.execute(stmt_events)
        ai_events = result_events.scalars().all()
        
        # Fetch active violations (Unresolved)
        stmt_violations = select(Violation).where(
            Violation.exam_session_id == exam_id,
            Violation.status.in_(["PENDING", "REVIEWED"])
        ).order_by(desc(Violation.timestamp))
        result_violations = await db.execute(stmt_violations)
        violations = result_violations.scalars().all()
        
        # Calculate Risk Score (simplified heuristic)
        risk_score = 0.0
        if violations:
            critical = sum(1 for v in violations if v.severity == "CRITICAL")
            high = sum(1 for v in violations if v.severity == "HIGH")
            medium = sum(1 for v in violations if v.severity == "MEDIUM")
            risk_score = min(100.0, (critical * 30) + (high * 15) + (medium * 5))
            
        timeline_events = []
        for e in ai_events:
            desc_text = e.payload.get("description", e.event_type)
            timeline_events.append({
                "event_type": e.event_type,
                "timestamp": e.timestamp,
                "severity": e.severity,
                "description": desc_text
            })
            
        active_v = []
        for v in violations:
            active_v.append({
                "id": v.id,
                "violation_type": v.violation_type,
                "severity": v.severity,
                "timestamp": v.timestamp
            })
            
        return MonitoringCurrentResponse(
            current_risk_score=risk_score,
            current_face_status="ACTIVE",
            current_gaze="CENTER",
            current_head_pose="FRONTAL",
            object_detection_summary={"phones_detected": 0, "multiple_persons": False},
            environment_summary={"lighting": "OPTIMAL", "background_noise": "LOW"},
            active_violations=active_v,
            timeline_events=timeline_events
        )
