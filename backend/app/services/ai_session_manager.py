import logging
from typing import Dict, Optional, Any

from app.monitoring_integration.monitoring_session_adapter import (
    MonitoringSessionAdapter,
    MonitoringSubsystemThread,
)

logger = logging.getLogger(__name__)

# Re-export MonitoringSubsystemThread as AIEngineThread for backward compatibility with existing type checks
AIEngineThread = MonitoringSubsystemThread


class AISessionManager:
    """
    Adapter for AI Session orchestration.
    Routes all monitoring session lifecycles to ai_monitoring_playground subsystem.
    """
    _active_threads: Dict[int, Any] = MonitoringSessionAdapter._active_threads
    _main_loop: Any = None

    @classmethod
    def initialize_session(cls, exam_session_id: int, student_id: int, reference_embedding: list = None, exam_id: Optional[int] = None):
        MonitoringSessionAdapter.initialize_session(
            exam_session_id=exam_session_id,
            student_id=student_id,
            exam_id=exam_id,
            reference_embedding=reference_embedding
        )

    @classmethod
    def start_session(cls, exam_session_id: int):
        MonitoringSessionAdapter.start_session(exam_session_id)

    @classmethod
    def pause_session(cls, exam_session_id: int):
        MonitoringSessionAdapter.pause_session(exam_session_id)

    @classmethod
    def resume_session(cls, exam_session_id: int):
        MonitoringSessionAdapter.resume_session(exam_session_id)

    @classmethod
    def stop_session(cls, exam_session_id: int):
        MonitoringSessionAdapter.stop_session(exam_session_id)

    @classmethod
    def ingest_frame(cls, exam_session_id: int, frame_bgr, b64_str: Optional[str] = None, raw_jpeg_bytes: Optional[bytes] = None) -> bool:
        return MonitoringSessionAdapter.ingest_frame(exam_session_id, frame_bgr, b64_str, raw_jpeg_bytes)

    # ── Lifecycle Hooks ──────────────────────────────────────────────────────

    @classmethod
    def OnRuntimeStarted(cls, exam_session_id: int, student_id: int = 0, exam_id: Optional[int] = None, ref_emb: Optional[list] = None):
        """Lifecycle Hook: Called when backend enters RUNNING state."""
        MonitoringSessionAdapter.OnRuntimeStarted(exam_session_id, student_id, exam_id=exam_id, ref_emb=ref_emb)

    @classmethod
    def OnRuntimePaused(cls, exam_session_id: int):
        """Lifecycle Hook: Called when runtime is interrupted or paused."""
        MonitoringSessionAdapter.OnRuntimePaused(exam_session_id)

    @classmethod
    def OnRuntimeResumed(cls, exam_session_id: int):
        """Lifecycle Hook: Called when runtime recovery is approved."""
        MonitoringSessionAdapter.OnRuntimeResumed(exam_session_id)

    @classmethod
    def OnRuntimeStopped(cls, exam_session_id: int):
        """Lifecycle Hook: Called when exam is submitted, completed, or terminated."""
        MonitoringSessionAdapter.OnRuntimeStopped(exam_session_id)

