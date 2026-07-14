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
    def get_current(exam_id: int) -> MonitoringCurrentResponse:
        # MOCK: Retrieve current subsystem metrics.
        return MonitoringCurrentResponse(
            current_face_status="DETECTED",
            current_gaze="CENTER",
            current_head_pose="FRONTAL",
            object_detection_summary={"phones_detected": 0, "multiple_persons": False},
            environment_summary={"lighting": "OPTIMAL", "background_noise": "LOW"}
        )
