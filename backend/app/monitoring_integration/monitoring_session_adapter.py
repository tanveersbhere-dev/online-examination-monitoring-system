"""
Monitoring Session Adapter
==========================
Clean integration boundary for monitoring lifecycle events.
Decoupled from local embedded AI pipelines.
"""
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class MonitoringSubsystemThread:
    """
    Lightweight mock/placeholder thread representation for decoupled monitoring.
    """
    def __init__(self, exam_session_id: int, student_id: int = 0, exam_id: Optional[int] = None, reference_embedding: Optional[List[float]] = None) -> None:
        self.exam_session_id = exam_session_id
        self.student_id = student_id
        self.exam_id = exam_id or exam_session_id
        self.reference_embedding = reference_embedding
        self.running = False
        self.paused = False
        self.frame_counter = 0

    def is_alive(self) -> bool:
        return self.running

    def get_infer_fps(self) -> float:
        return 0.0

    def get_dropped_frames(self) -> int:
        return 0

    def get_system_health(self) -> Dict[str, Any]:
        return {
            "pipeline_status": "DECOUPLED",
            "fps": 0.0,
            "dropped_frames": 0,
            "active_processors": 0
        }

    def get_pipeline_health(self) -> Dict[str, Any]:
        return {}

    def get_events(self) -> List[Any]:
        return []

    def get_evidence_list(self) -> List[Any]:
        return []

    def get_last_frame(self) -> Optional[Any]:
        return None

    def get_last_frame_b64(self) -> Optional[str]:
        return None


class MonitoringSessionAdapter:
    """
    Central adapter orchestrating monitoring sessions without local CV pipeline execution.
    """
    _active_threads: Dict[int, Any] = {}
    _main_loop: Any = None

    @classmethod
    def initialize_session(
        cls,
        exam_session_id: int,
        student_id: int,
        exam_id: Optional[int] = None,
        reference_embedding: Optional[List[float]] = None
    ) -> None:
        logger.debug(f"[MonitoringSessionAdapter] Initializing session boundary for exam_session={exam_session_id}")
        cls._active_threads[exam_session_id] = MonitoringSubsystemThread(
            exam_session_id=exam_session_id,
            student_id=student_id,
            exam_id=exam_id,
            reference_embedding=reference_embedding
        )

    @classmethod
    def start_session(cls, exam_session_id: int) -> None:
        thread = cls._active_threads.get(exam_session_id)
        if thread:
            thread.running = True
        logger.debug(f"[MonitoringSessionAdapter] Session started for {exam_session_id}")

    @classmethod
    def pause_session(cls, exam_session_id: int) -> None:
        thread = cls._active_threads.get(exam_session_id)
        if thread:
            thread.paused = True
        logger.debug(f"[MonitoringSessionAdapter] Session paused for {exam_session_id}")

    @classmethod
    def resume_session(cls, exam_session_id: int) -> None:
        thread = cls._active_threads.get(exam_session_id)
        if thread:
            thread.paused = False
        logger.debug(f"[MonitoringSessionAdapter] Session resumed for {exam_session_id}")

    @classmethod
    def stop_session(cls, exam_session_id: int) -> None:
        logger.debug(f"[MonitoringSessionAdapter] Session stopped for {exam_session_id}")
        cls._active_threads.pop(exam_session_id, None)

    @classmethod
    def ingest_frame(cls, exam_session_id: int, frame_bgr: Any, b64_str: Optional[str] = None, raw_jpeg_bytes: Optional[bytes] = None) -> bool:
        thread = cls._active_threads.get(exam_session_id)
        if thread and thread.is_alive():
            return True
        return False

    @classmethod
    def get_thread(cls, exam_session_id: int) -> Optional[Any]:
        return cls._active_threads.get(exam_session_id)

    # ── Lifecycle Hooks ──────────────────────────────────────────────────────

    @classmethod
    def OnRuntimeStarted(cls, exam_session_id: int, student_id: int = 0, exam_id: Optional[int] = None, ref_emb: Optional[List[float]] = None) -> None:
        cls.initialize_session(exam_session_id, student_id, exam_id=exam_id, reference_embedding=ref_emb)
        cls.start_session(exam_session_id)

    @classmethod
    def OnRuntimePaused(cls, exam_session_id: int) -> None:
        cls.pause_session(exam_session_id)

    @classmethod
    def OnRuntimeResumed(cls, exam_session_id: int) -> None:
        cls.resume_session(exam_session_id)

    @classmethod
    def OnRuntimeStopped(cls, exam_session_id: int) -> None:
        cls.stop_session(exam_session_id)
