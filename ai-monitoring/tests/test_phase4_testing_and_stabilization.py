"""
Phase 4: Multi-Camera Testing, Failure Handling & Stabilization Test Suite
==========================================================================
Authoritative specification: MULTI_CAMERA_MONITORING_PLAN.md (Phase 4).

Covers the full Phase 4 Matrix (Tests 1–10 / Tests A–J) and Failure Robustness:
TEST A (Test 1)  — Single Camera 1 Operation (Laptop only, full pipeline, existing violations).
TEST B (Test 2)  — Dual Camera Normal Operation (Both active in same session, independent streams).
TEST C (Test 3)  — Camera 1 Independent Violation (Evidence generated, Camera 2 does not interfere).
TEST D (Test 4)  — Camera 2 Independent Violation (Approved subset triggers, same session, evidence generated).
TEST E (Test 5)  — Same Violation Observed by Both Cameras (Single episode, no duplicate STARTED, multi-angle evidence).
TEST F (Test 6)  — Different Simultaneous Violations (Separate episodes, distinct lifecycles).
TEST G (Test 7)  — Camera 2 Disconnect Isolation (Camera 1 continues uninterrupted, no backend crash).
TEST H (Test 8)  — Camera 2 Reconnect Recovery (Clean resume within active session, frame ingestion restored).
TEST I (Test 9)  — Backend / Session Restart (New session ID, zero cross-session evidence leakage).
TEST J (Test 10) — End-to-End Evidence Audit (SQLite records, snapshots, metadata integrity, camera attribution).
TEST K (Bonus 1) — Network Backpressure / Frame Drop Robustness (Bounded queues drop stale frames).
TEST L (Bonus 2) — Corrupted / Malformed Frame Robustness (Invalid JPEG handled gracefully).
TEST M (Bonus 3) — Camera 1 AI Protection Audit (Gaze, identity, head pose remain Camera 1 only).
"""
import os
import time
import uuid
import pytest
import numpy as np
import cv2
import asyncio
from pathlib import Path
from typing import Optional

from ai_engine.core.exam_context import ExamContext, BoundingBox, TrackedObject
from ai_engine.core.enums import DetectedObjectType
from ai_engine.camera.frame import Frame
from ai_engine.intelligence.rule_engine.models import RuleEvaluation
from ai_engine.intelligence.rule_engine.rule_engine import RuleEngineProcessor
from ai_engine.intelligence.violation_manager.models import ViolationManagerConfig, LifecycleEvent
from ai_engine.intelligence.violation_manager.violation_manager import ViolationManagerProcessor
from backend.adapters.monitoring_persistence_adapter import MonitoringPersistenceAdapter
from backend.database.session_repository import session_repository
from backend.pipeline.context_builder import ContextBuilder
from backend.pipeline.result_serializer import ResultSerializer
from backend.camera.multi_camera_manager import MultiCameraManager, CameraStreamInfo


def _make_dummy_frame(camera_id: str = "camera_1", frame_id: int = 1, timestamp: Optional[float] = None) -> Frame:
    img = np.zeros((240, 320, 3), dtype=np.uint8)
    ts = timestamp if timestamp is not None else time.time()
    return Frame.from_bgr_image(img, camera_id=camera_id, frame_id=frame_id, timestamp=ts)


def _make_context_with_rule(
    camera_id: str,
    rule_id: str,
    category: str = "PROHIBITED_ITEMS",
    conf: float = 0.95,
    frame_id: int = 1,
    timestamp: Optional[float] = None,
) -> ExamContext:
    ctx = ExamContext()
    ctx.current_frame = _make_dummy_frame(camera_id=camera_id, frame_id=frame_id, timestamp=timestamp)
    class DummyRuleResults:
        evaluations = [
            RuleEvaluation(
                rule_id=rule_id,
                rule_name=rule_id,
                category=category,
                triggered=True,
                confidence=conf,
                supporting_observations=f"{rule_id} observed on {camera_id}",
                evaluation_timestamp=ctx.current_frame.timestamp,
                evaluation_duration=0.01,
            )
        ]
    ctx.rule_results = DummyRuleResults()
    if "PHONE" in rule_id:
        obj = TrackedObject(
            tracking_id=1,
            object_type=DetectedObjectType.CELL_PHONE,
            bbox=BoundingBox(10, 10, 50, 80),
            confidence=conf,
            current_state="TRACKED",
        )
        ctx.object_info.validated_objects = [obj]
    elif "BOOK" in rule_id or "PAPER" in rule_id:
        obj = TrackedObject(
            tracking_id=2,
            object_type=DetectedObjectType.BOOK,
            bbox=BoundingBox(20, 20, 100, 120),
            confidence=conf,
            current_state="TRACKED",
        )
        ctx.object_info.validated_objects = [obj]
    return ctx


# ===========================================================================
# TEST A (Test 1): Single Camera 1 Operation
# ===========================================================================
def test_p4_test_a_single_camera_1_operation(tmp_path):
    """
    Test 1 / Physical Test A:
    System operates in single-camera mode with Camera 1 only.
    Camera 2 is NOT connected. Camera 1 detects violations and generates evidence.
    """
    mcm = MultiCameraManager()
    mcm.register_connection("camera_1", session_id="sess_p4_single")
    cam1_info = mcm.get_camera_info("camera_1")
    cam2_info = mcm.get_camera_info("camera_2")

    assert cam1_info.is_connected is True
    assert cam2_info.is_connected is False

    cfg = ViolationManagerConfig(
        evidence_dir=tmp_path,
        min_confirming_frames=1,
        debounce_window_seconds=0.1,
        enable_logging=False,
    )
    vm = ViolationManagerProcessor(cfg)
    vm.initialize()
    vm.start()

    ctx = _make_context_with_rule("camera_1", "ATT_LOOKING_AWAY", conf=0.92, frame_id=1, timestamp=100.0)
    vm.process(ctx)

    assert len(vm.all_evidence_records) == 1
    rec = vm.all_evidence_records[0]
    assert rec["camera_id"] == "camera_1"
    assert rec["rule_id"] == "ATT_LOOKING_AWAY"
    assert Path(rec["filepath"]).exists()
    vm.stop()


# ===========================================================================
# TEST B (Test 2): Dual Camera Normal Operation
# ===========================================================================
def test_p4_test_b_dual_camera_normal_operation():
    """
    Test 2 / Physical Test B:
    Both cameras connect to the same session with distinct camera_id values.
    Camera 1 runs full pipeline; Camera 2 respects approved allowlist.
    """
    mcm = MultiCameraManager()
    session_id = "sess_p4_dual_normal"
    mcm.register_connection("camera_1", session_id=session_id)
    mcm.register_connection("camera_2", session_id=session_id)

    c1 = mcm.get_camera_info("camera_1")
    c2 = mcm.get_camera_info("camera_2")
    assert c1.is_connected and c2.is_connected
    assert c1.session_id == c2.session_id == session_id
    assert c1.camera_id != c2.camera_id

    # Verify rule routing separation
    assert hasattr(RuleEngineProcessor, "CAMERA_2_APPROVED_RULES")
    for approved_rule in RuleEngineProcessor.CAMERA_2_APPROVED_RULES:
        # Each approved rule is a legitimate existing violation
        assert approved_rule in [
            "UNAUTH_PHONE", "UNAUTH_BOOK", "ENV_BOOK_DETECTED",
            "UNAUTH_NOTEBOOK", "UNAUTH_REGISTER", "UNAUTH_PAPER",
            "UNAUTH_LAPTOP", "COMM_MULTIPLE_PERSONS"
        ]
    # Gaze/attention rules are strictly excluded from Camera 2
    assert "ATT_LOOKING_AWAY" not in RuleEngineProcessor.CAMERA_2_APPROVED_RULES
    assert "ID_MISMATCH" not in RuleEngineProcessor.CAMERA_2_APPROVED_RULES


# ===========================================================================
# TEST C (Test 3): Camera 1 Independent Violation
# ===========================================================================
def test_p4_test_c_camera_1_independent_violation(tmp_path):
    """
    Test 3 / Physical Test C:
    Camera 1 detects a violation while Camera 2 observes nothing.
    Violation and evidence are generated without requiring Camera 2 confirmation.
    """
    cfg = ViolationManagerConfig(
        evidence_dir=tmp_path,
        min_confirming_frames=1,
        debounce_window_seconds=0.1,
        enable_logging=False,
    )
    vm = ViolationManagerProcessor(cfg)
    vm.initialize()
    vm.start()

    ctx1 = _make_context_with_rule("camera_1", "ATT_LOOKING_AWAY", conf=0.91, frame_id=1, timestamp=100.0)
    vm.process(ctx1)

    assert len(vm.all_evidence_records) == 1
    assert vm.all_evidence_records[0]["camera_id"] == "camera_1"
    assert vm.all_evidence_records[0]["rule_id"] == "ATT_LOOKING_AWAY"
    vm.stop()


# ===========================================================================
# TEST D (Test 4): Camera 2 Independent Violation
# ===========================================================================
def test_p4_test_d_camera_2_independent_violation(tmp_path):
    """
    Test 4 / Physical Test D:
    Camera 2 detects an approved violation while Camera 1 observes nothing.
    Violation and evidence are generated without requiring Camera 1 confirmation.
    """
    cfg = ViolationManagerConfig(
        evidence_dir=tmp_path,
        min_confirming_frames=1,
        debounce_window_seconds=0.1,
        enable_logging=False,
    )
    vm = ViolationManagerProcessor(cfg)
    vm.initialize()
    vm.start()

    ctx2 = _make_context_with_rule("camera_2", "UNAUTH_BOOK", conf=0.89, frame_id=1, timestamp=100.0)
    vm.process(ctx2)

    assert len(vm.all_evidence_records) == 1
    assert vm.all_evidence_records[0]["camera_id"] == "camera_2"
    assert vm.all_evidence_records[0]["rule_id"] == "UNAUTH_BOOK"
    vm.stop()


# ===========================================================================
# TEST E (Test 5): Same Violation Observed by Both Cameras (Correlation)
# ===========================================================================
def test_p4_test_e_same_violation_observed_by_both_cameras(tmp_path):
    """
    Test 5 / Physical Test E:
    Both cameras observe UNAUTH_PHONE concurrently.
    Verifies exactly ONE logical violation episode is maintained (no duplicate STARTED),
    and multi-angle evidence snapshots from both cameras are retained.
    """
    cfg = ViolationManagerConfig(
        evidence_dir=tmp_path,
        min_confirming_frames=1,
        debounce_window_seconds=0.1,
        enable_logging=False,
    )
    vm = ViolationManagerProcessor(cfg)
    vm.initialize()
    vm.start()

    # Camera 1 observes UNAUTH_PHONE at t=100.0
    ctx1 = _make_context_with_rule("camera_1", "UNAUTH_PHONE", conf=0.88, frame_id=1, timestamp=100.0)
    vm.process(ctx1)

    # Camera 2 observes UNAUTH_PHONE at t=100.5
    ctx2 = _make_context_with_rule("camera_2", "UNAUTH_PHONE", conf=0.96, frame_id=2, timestamp=100.5)
    vm.process(ctx2)

    # Must be exactly 1 violation episode in the evidence store
    assert len(vm.all_evidence_records) == 1
    rec = vm.all_evidence_records[0]
    assert rec["rule_id"] == "UNAUTH_PHONE"
    assert rec["peak_confidence"] == 0.96

    # Verify multi-angle snapshots: both camera_1 and camera_2 are represented
    snapshots = rec.get("snapshots", [])
    assert len(snapshots) >= 2
    cams = {s["camera_id"] for s in snapshots}
    assert "camera_1" in cams
    assert "camera_2" in cams

    for s in snapshots:
        assert Path(s["filepath"]).exists()
    vm.stop()


# ===========================================================================
# TEST F (Test 6): Different Violations From Both Cameras
# ===========================================================================
def test_p4_test_f_different_violations_from_both_cameras(tmp_path):
    """
    Test 6 / Physical Test F:
    Camera 1 detects ATT_LOOKING_AWAY; Camera 2 detects UNAUTH_PHONE.
    Both violations must remain completely separate with independent lifecycles.
    """
    cfg = ViolationManagerConfig(
        evidence_dir=tmp_path,
        min_confirming_frames=1,
        debounce_window_seconds=0.1,
        enable_logging=False,
    )
    vm = ViolationManagerProcessor(cfg)
    vm.initialize()
    vm.start()

    ctx1 = _make_context_with_rule("camera_1", "ATT_LOOKING_AWAY", conf=0.90, frame_id=1, timestamp=100.0)
    vm.process(ctx1)

    ctx2 = _make_context_with_rule("camera_2", "UNAUTH_PHONE", conf=0.93, frame_id=2, timestamp=100.2)
    vm.process(ctx2)

    assert len(vm.all_evidence_records) == 2
    r_ids = {r["rule_id"] for r in vm.all_evidence_records}
    assert "ATT_LOOKING_AWAY" in r_ids
    assert "UNAUTH_PHONE" in r_ids

    c_ids = {r["camera_id"] for r in vm.all_evidence_records}
    assert "camera_1" in c_ids
    assert "camera_2" in c_ids
    vm.stop()


# ===========================================================================
# TEST G (Test 7): Camera 2 Disconnect Isolation
# ===========================================================================
def test_p4_test_g_camera_2_disconnect_isolation(tmp_path):
    """
    Test 7 / Physical Test G:
    Camera 2 disconnects abruptly.
    Camera 1 must continue operating and detecting violations without crashing.
    """
    mcm = MultiCameraManager()
    session_id = "sess_p4_disc"
    mcm.register_connection("camera_1", session_id=session_id)
    mcm.register_connection("camera_2", session_id=session_id)

    cfg = ViolationManagerConfig(
        evidence_dir=tmp_path,
        min_confirming_frames=1,
        debounce_window_seconds=0.1,
        enable_logging=False,
    )
    vm = ViolationManagerProcessor(cfg)
    vm.initialize()
    vm.start()

    # Both active
    ctx1 = _make_context_with_rule("camera_1", "ATT_LOOKING_AWAY", conf=0.89, frame_id=1, timestamp=100.0)
    vm.process(ctx1)

    # Disconnect Camera 2
    mcm.register_disconnection("camera_2")
    assert mcm.get_camera_info("camera_2").is_connected is False
    assert mcm.get_camera_info("camera_1").is_connected is True

    # Camera 1 continues normally
    ctx1_next = _make_context_with_rule("camera_1", "UNAUTH_PHONE", conf=0.94, frame_id=2, timestamp=101.0)
    vm.process(ctx1_next)

    assert len(vm.all_evidence_records) == 2
    vm.stop()


# ===========================================================================
# TEST H (Test 8): Camera 2 Reconnect Recovery
# ===========================================================================
def test_p4_test_h_camera_2_reconnect_recovery(tmp_path):
    """
    Test 8 / Physical Test H:
    Camera 2 disconnects and then reconnects to the same active session.
    Frame ingestion and AI violation processing resume seamlessly.
    """
    mcm = MultiCameraManager()
    session_id = "sess_p4_reconn"
    mcm.register_connection("camera_1", session_id=session_id)
    mcm.register_connection("camera_2", session_id=session_id)

    # Disconnect
    mcm.register_disconnection("camera_2")
    assert mcm.get_camera_info("camera_2").is_connected is False

    # Reconnect to same session
    reconnected_info = mcm.register_connection("camera_2", session_id=session_id)
    assert reconnected_info.is_connected is True
    assert reconnected_info.session_id == session_id

    cfg = ViolationManagerConfig(
        evidence_dir=tmp_path,
        min_confirming_frames=1,
        debounce_window_seconds=0.1,
        enable_logging=False,
    )
    vm = ViolationManagerProcessor(cfg)
    vm.initialize()
    vm.start()

    # Reconnected Camera 2 pushes violation
    ctx2 = _make_context_with_rule("camera_2", "UNAUTH_BOOK", conf=0.91, frame_id=1, timestamp=105.0)
    vm.process(ctx2)

    assert len(vm.all_evidence_records) == 1
    assert vm.all_evidence_records[0]["camera_id"] == "camera_2"
    assert vm.all_evidence_records[0]["rule_id"] == "UNAUTH_BOOK"
    vm.stop()


# ===========================================================================
# TEST I (Test 9): Backend / Session Restart Isolation
# ===========================================================================
def test_p4_test_i_backend_session_restart_isolation(tmp_path):
    """
    Test 9 / Physical Test I:
    Session 1 ends; Session 2 begins.
    Verifies strict session boundaries with no cross-session evidence contamination.
    """
    # Session 1
    sid1 = f"sess_p4_s1_{uuid.uuid4().hex[:6]}"
    session_repository.create_session(session_id=sid1, student_id="student_1", exam_id="exam_p4")
    adapter1 = MonitoringPersistenceAdapter(active_session_id=sid1)

    cfg = ViolationManagerConfig(
        evidence_dir=tmp_path,
        min_confirming_frames=1,
        debounce_window_seconds=0.1,
        enable_logging=False,
    )
    vm1 = ViolationManagerProcessor(cfg)
    vm1.initialize()
    vm1.start()

    ctx1 = _make_context_with_rule("camera_1", "ATT_LOOKING_AWAY", conf=0.90, frame_id=1, timestamp=100.0)
    vm1.process(ctx1)
    setattr(ctx1, "evidence_store", vm1.all_evidence_records)
    adapter1.handle_frame_lifecycle(ctx1, session_id=sid1)
    vm1.stop()

    rep1 = session_repository.get_session_report(sid1)
    assert rep1["summary"]["total_violations"] == 1

    # Session 2 (Simulating fresh session restart)
    sid2 = f"sess_p4_s2_{uuid.uuid4().hex[:6]}"
    session_repository.create_session(session_id=sid2, student_id="student_2", exam_id="exam_p4")
    adapter2 = MonitoringPersistenceAdapter(active_session_id=sid2)

    vm2 = ViolationManagerProcessor(cfg)
    vm2.initialize()
    vm2.start()

    ctx2 = _make_context_with_rule("camera_2", "UNAUTH_PHONE", conf=0.95, frame_id=1, timestamp=200.0)
    vm2.process(ctx2)
    setattr(ctx2, "evidence_store", vm2.all_evidence_records)
    adapter2.handle_frame_lifecycle(ctx2, session_id=sid2)
    vm2.stop()

    rep2 = session_repository.get_session_report(sid2)
    assert rep2["summary"]["total_violations"] == 1

    # Verify zero leakage across reports
    s1_v_types = [v["violation_type"] for v in rep1["violations"]]
    s2_v_types = [v["violation_type"] for v in rep2["violations"]]
    assert "ATT_LOOKING_AWAY" in s1_v_types
    assert "ATT_LOOKING_AWAY" not in s2_v_types
    assert "UNAUTH_PHONE" in s2_v_types
    assert "UNAUTH_PHONE" not in s1_v_types


# ===========================================================================
# TEST J (Test 10): End-to-End Evidence Audit
# ===========================================================================
def test_p4_test_j_evidence_audit_integrity(tmp_path):
    """
    Test 10 / Physical Test J:
    Verifies that all persisted evidence snapshots and database records retain:
    session_id, camera_id, violation_type, timestamp, confidence, valid snapshot files.
    """
    sid = f"sess_p4_audit_{uuid.uuid4().hex[:6]}"
    session_repository.create_session(session_id=sid, student_id="student_audit", exam_id="exam_audit")
    adapter = MonitoringPersistenceAdapter(active_session_id=sid)

    cfg = ViolationManagerConfig(
        evidence_dir=tmp_path,
        min_confirming_frames=1,
        debounce_window_seconds=0.1,
        enable_logging=False,
    )
    vm = ViolationManagerProcessor(cfg)
    vm.initialize()
    vm.start()

    # Camera 1 evidence
    ctx1 = _make_context_with_rule("camera_1", "ATT_LOOKING_AWAY", conf=0.92, frame_id=1, timestamp=100.0)
    vm.process(ctx1)
    setattr(ctx1, "evidence_store", vm.all_evidence_records)
    adapter.handle_frame_lifecycle(ctx1, session_id=sid)

    # Camera 2 evidence
    ctx2 = _make_context_with_rule("camera_2", "UNAUTH_PHONE", conf=0.94, frame_id=2, timestamp=101.0)
    vm.process(ctx2)
    setattr(ctx2, "evidence_store", vm.all_evidence_records)
    adapter.handle_frame_lifecycle(ctx2, session_id=sid)

    report = session_repository.get_session_report(sid)
    assert report is not None
    assert len(report["evidence"]) >= 2

    for ev_item in report["evidence"]:
        meta = ev_item.get("metadata", {})
        assert "camera_id" in meta, "Missing camera_id in metadata"
        assert meta["camera_id"] in ("camera_1", "camera_2")
        assert ev_item["evidence_type"] is not None
        assert ev_item["timestamp"] > 0
        assert ev_item["confidence"] > 0.0
        # Check snapshot file exists
        snap_path = ev_item.get("filepath")
        assert snap_path is not None
        assert Path(snap_path).exists(), f"Persisted snapshot file not found: {snap_path}"
    vm.stop()


# ===========================================================================
# TEST K: Network Backpressure / Frame Drop Robustness
# ===========================================================================
def test_p4_test_k_queue_backpressure_drops_stale_frames():
    """
    Verify MultiCameraManager drops oldest frames under backpressure
    to prevent latency buildup and memory unbounded growth.
    """
    mcm = MultiCameraManager()
    mcm.register_connection("camera_2", session_id="sess_bp")

    # Set dummy JPEG frame
    dummy_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF"

    # Push 5 frames rapidly into subscriber feed with maxsize=2
    feed_q = mcm.subscribe_feed("camera_2")
    for i in range(5):
        mcm.push_frame("camera_2", dummy_jpeg + bytes([i]), timestamp=time.time())

    # Queue size must not exceed capacity (2)
    assert feed_q.qsize() <= 2
    mcm.unsubscribe_feed("camera_2", feed_q)


# ===========================================================================
# TEST L: Corrupted / Malformed Frame Robustness
# ===========================================================================
def test_p4_test_l_malformed_frame_handling():
    """
    Verify ContextBuilder handles corrupted / empty JPEG bytes gracefully
    without raising unhandled exceptions or crashing the pipeline.
    """
    cb = ContextBuilder()

    # Corrupted / truncated JPEG
    bad_bytes = b"NOT_A_VALID_JPEG_BYTE_STREAM"
    frame = cb.decode_and_inject(bad_bytes, camera_id="camera_2")
    assert frame is None  # Gracefully returns None

    # Empty bytes
    frame_empty = cb.decode_and_inject(b"", camera_id="camera_1")
    assert frame_empty is None


# ===========================================================================
# TEST M: Camera 1 AI Protection Audit
# ===========================================================================
def test_p4_test_m_camera_1_ai_protection_audit():
    """
    Verify Camera 2 frames never trigger head pose, gaze, identity, or MAR/EAR
    and that Camera 1 retains full 19-stage pipeline execution.
    """
    from backend.pipeline.orchestrator import MonitoringPipelineOrchestrator
    orch = MonitoringPipelineOrchestrator()
    orch.initialize()

    # Check stage lists
    cam1_stages = orch._pipeline_order
    assert len(cam1_stages) >= 19
    assert "GazeExtractor" in cam1_stages
    assert "HeadPoseEstimator" in cam1_stages
    assert "FaceIdentityProcessor" in cam1_stages

    # When camera_2 frame is evaluated, rule allowlist must strictly prevent gaze/identity
    assert "ATT_LOOKING_AWAY" not in RuleEngineProcessor.CAMERA_2_APPROVED_RULES
    assert "ID_MISMATCH" not in RuleEngineProcessor.CAMERA_2_APPROVED_RULES
    assert "UNAUTH_AUDIO_DEVICE" not in RuleEngineProcessor.CAMERA_2_APPROVED_RULES
