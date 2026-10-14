"""
Integration Tests: AI Monitoring Subsystem Bridge
=================================================
Verifies that MonitoringIntegrationAdapter correctly bridges the Main Examination System
and the ai_monitoring_playground subsystem.
"""
import pytest
import numpy as np
import time
from unittest.mock import MagicMock, patch

from app.monitoring_integration.monitoring_contracts import (
    MonitoringSeverity,
    MonitoringStatus,
    NormalizedMonitoringEvent,
    EVENT_TYPE_MAPPING,
    SEVERITY_MAPPING,
)
from app.monitoring_integration.face_embedding_service import FaceEmbeddingService
from app.monitoring_integration.monitoring_event_normalizer import MonitoringEventNormalizer
from app.monitoring_integration.monitoring_summary_adapter import MonitoringSummaryAdapter
from app.monitoring_integration.monitoring_session_adapter import (
    MonitoringSessionAdapter,
    MonitoringSubsystemThread,
)


def test_monitoring_contracts_mapping():
    """Verify event types and severities map correctly."""
    assert EVENT_TYPE_MAPPING["UNAUTH_PHONE"] == "MOBILE_PHONE"
    assert EVENT_TYPE_MAPPING["ID_MULTIPLE_FACES"] == "MULTIPLE_PERSONS"
    assert EVENT_TYPE_MAPPING["ATT_LOOKING_AWAY"] == "LOOKING_AWAY"
    assert EVENT_TYPE_MAPPING["COMM_EARPHONES"] == "EARPHONES_DETECTED"
    assert EVENT_TYPE_MAPPING["ENV_CAM_OCCLUDED"] == "CAMERA_OBSTRUCTION"

    assert SEVERITY_MAPPING["ELEVATED"] == "HIGH"
    assert SEVERITY_MAPPING["CRITICAL"] == "CRITICAL"
    assert SEVERITY_MAPPING["NORMAL"] == "LOW"


def test_face_embedding_similarity():
    """Verify cosine similarity calculation."""
    emb1 = [1.0, 0.0, 0.0]
    emb2 = [1.0, 0.0, 0.0]
    sim = FaceEmbeddingService.compute_similarity(emb1, emb2)
    assert pytest.approx(sim, 0.001) == 1.0

    emb3 = [0.0, 1.0, 0.0]
    sim_ortho = FaceEmbeddingService.compute_similarity(emb1, emb3)
    assert pytest.approx(sim_ortho, 0.001) == 0.0


def test_monitoring_event_normalizer():
    """Verify frame_result dict is properly normalized and dispatched."""
    mock_frame_result = {
        "violations": [
            {
                "type": "UNAUTH_PHONE",
                "severity": "CRITICAL",
                "confidence": 0.95,
                "timestamp": time.time(),
                "description": "Phone detected"
            }
        ],
        "lifecycle_events": [
            {
                "type": "ATT_LOOKING_AWAY",
                "severity": "MEDIUM",
                "confidence": 0.88,
                "started_at": time.time(),
                "transition": "STARTED"
            }
        ]
    }

    with patch("app.monitoring_integration.monitoring_event_normalizer.AIEventProcessor.process_event") as mock_proc:
        events = MonitoringEventNormalizer.process_frame_result(
            frame_result=mock_frame_result,
            exam_session_id=101,
            student_id=202,
            main_loop=None,
            evidence_path="uploads/ev_test.jpg"
        )
        assert len(events) == 2
        event_types = {e.event_type for e in events}
        assert "MOBILE_PHONE" in event_types
        assert "LOOKING_AWAY" in event_types


def test_monitoring_summary_adapter():
    """Verify executive summary generation."""
    summary = MonitoringSummaryAdapter.generate_summary(
        violations=[{"type": "MOBILE_PHONE", "severity": "CRITICAL"}],
        final_risk_score=0.85,
        risk_level="CRITICAL",
        frames_processed=150,
        total_evidence_count=3
    )
    assert summary["risk_level"] == "CRITICAL"
    assert summary["integrity_index"] == 15
    assert "critical" in summary["headline"].lower()
    assert summary["frames_processed"] == 150
    assert summary["total_evidence_count"] == 3


def test_monitoring_session_adapter_lifecycle():
    """Verify session adapter lifecycle initialization, start, frame ingest, and stop."""
    session_id = 999
    student_id = 888

    MonitoringSessionAdapter.initialize_session(session_id, student_id)
    assert session_id in MonitoringSessionAdapter._active_threads

    thread = MonitoringSessionAdapter.get_thread(session_id)
    assert thread is not None
    assert thread.exam_session_id == session_id

    # Test dummy frame push
    dummy_img = np.zeros((480, 640, 3), dtype=np.uint8)
    # Thread not started yet, ingest_frame returns False
    assert not MonitoringSessionAdapter.ingest_frame(session_id, dummy_img)

    MonitoringSessionAdapter.stop_session(session_id)
    assert session_id not in MonitoringSessionAdapter._active_threads
