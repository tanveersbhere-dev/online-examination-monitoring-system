"""
Monitoring Session Context
==========================
Defines the explicit session context model for the Monitoring Unit host.

Supports two operational modes:
1. STANDALONE DEVELOPMENT MODE (default):
   - Runs completely offline/independently without the PPR system.
   - Generates safe local test identifiers (e.g. 'local_student', 'local_exam').
   - Zero database/remote side-effects.

2. PPR ATTACHMENT MODE:
   - Receives real PPR session identity context (student_id, examiner_id, exam_id, attempt_id, session_id).
   - Prepares clean data bindings for upstream/downstream PPR integration.
"""
from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional


@dataclass
class MonitoringSessionContext:
    """
    Explicit monitoring session identity and lifecycle container.
    """
    monitoring_session_id: str = field(default_factory=lambda: f"local_session_{uuid.uuid4().hex[:12]}")
    student_id: str = "local_student"
    examiner_id: Optional[str] = "local_examiner"
    exam_id: str = "local_exam"
    attempt_id: Optional[str] = "local_attempt_1"
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    status: str = "IN_PROGRESS"  # IN_PROGRESS | COMPLETED | TERMINATED | PAUSED
    mode: str = "standalone"      # standalone | ppr
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create_standalone(
        cls,
        session_id: Optional[str] = None,
        student_id: str = "local_student",
        exam_id: str = "local_exam",
        attempt_id: str = "local_attempt_1",
        examiner_id: Optional[str] = "local_examiner",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MonitoringSessionContext:
        """Create a safe standalone development session context."""
        return cls(
            monitoring_session_id=session_id or f"local_session_{uuid.uuid4().hex[:12]}",
            student_id=student_id,
            examiner_id=examiner_id,
            exam_id=exam_id,
            attempt_id=attempt_id,
            start_time=time.time(),
            status="IN_PROGRESS",
            mode="standalone",
            metadata=metadata or {"environment": "development", "source": "standalone_monitoring_unit"},
        )

    @classmethod
    def from_ppr(
        cls,
        monitoring_session_id: str,
        student_id: str,
        exam_id: str,
        attempt_id: Optional[str] = None,
        examiner_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MonitoringSessionContext:
        """Construct context from real PPR session identity attributes."""
        if not monitoring_session_id:
            raise ValueError("monitoring_session_id is required for PPR mode")
        if not student_id:
            raise ValueError("student_id is required for PPR mode")
        if not exam_id:
            raise ValueError("exam_id is required for PPR mode")

        return cls(
            monitoring_session_id=monitoring_session_id,
            student_id=student_id,
            examiner_id=examiner_id,
            exam_id=exam_id,
            attempt_id=attempt_id or f"attempt_{monitoring_session_id[:8]}",
            start_time=time.time(),
            status="IN_PROGRESS",
            mode="ppr",
            metadata=metadata or {"environment": "production", "source": "ppr_attached"},
        )

    @classmethod
    def from_env(cls) -> MonitoringSessionContext:
        """
        Factory inspecting environment variables to determine mode and parameters.
        Defaults to standalone development mode.
        """
        mode = os.environ.get("MONITORING_MODE", "standalone").strip().lower()
        if mode == "ppr":
            session_id = os.environ.get("PPR_MONITORING_SESSION_ID", f"ppr_session_{uuid.uuid4().hex[:8]}")
            student_id = os.environ.get("PPR_STUDENT_ID", "ppr_candidate")
            exam_id = os.environ.get("PPR_EXAM_ID", "ppr_examination")
            attempt_id = os.environ.get("PPR_ATTEMPT_ID", "ppr_attempt_1")
            examiner_id = os.environ.get("PPR_EXAMINER_ID")
            return cls.from_ppr(
                monitoring_session_id=session_id,
                student_id=student_id,
                exam_id=exam_id,
                attempt_id=attempt_id,
                examiner_id=examiner_id,
            )
        return cls.create_standalone()

    def to_dict(self) -> Dict[str, Any]:
        """Convert session context to dictionary representation."""
        return asdict(self)

    def close(self, status: str = "COMPLETED") -> None:
        """Mark session ended."""
        self.end_time = time.time()
        self.status = status
