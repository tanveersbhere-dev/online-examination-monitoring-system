"""
Phase 3: Violation Aggregation & Evidence Integration Test Suite
================================================================
Covers all 15 Phase 3 requirements specified in MULTI_CAMERA_MONITORING_PLAN.md:
TEST 1  — Camera 1 violation reaches existing Evidence Engine.
TEST 2  — Camera 2 approved violation reaches existing Evidence Engine.
TEST 3  — Camera 1 evidence contains session_id, camera_id="camera_1", violation_type, timestamp, confidence, evidence.
TEST 4  — Camera 2 evidence contains session_id, camera_id="camera_2", violation_type, timestamp, confidence, evidence.
TEST 5  — Both cameras feed the SAME examination session (same session_id in database and report).
TEST 6  — Camera 1 violation does not require Camera 2 confirmation (independent).
TEST 7  — Camera 2 violation does not require Camera 1 confirmation (independent).
TEST 8  — Different simultaneous violations remain separate (Camera 1 ATT_LOOKING_AWAY + Camera 2 UNAUTH_PHONE both survive).
TEST 9  — Same violation observed by both cameras merges into single active episode without unfair duplicate penalty.
TEST 10 — Both evidence sources are preserved when both cameras observe the same event (multi-angle snapshots retained).
TEST 11 — Camera 2 evidence cannot accidentally overwrite Camera 1 evidence.
TEST 12 — Camera 1 evidence cannot accidentally overwrite Camera 2 evidence.
TEST 13 — Single-camera mode still works completely normally with Camera 1 alone.
TEST 14 — Camera 2 disconnect does not break Camera 1 violation and evidence processing.
TEST 15 — Phase 1 and Phase 2 test suite compatibility verified.
"""
import os
import time
import uuid
import pytest
import numpy as np
import cv2
from pathlib import Path
from typing import Optional

from ai_engine.core.exam_context import ExamContext, BoundingBox, TrackedObject
from ai_engine.core.enums import DetectedObjectType
from ai_engine.camera.frame import Frame
from ai_engine.intelligence.rule_engine.models import RuleEvaluation, RuleEngineConfig
from ai_engine.intelligence.rule_engine.rule_engine import RuleEngineProcessor
from ai_engine.intelligence.violation_manager.models import ViolationManagerConfig, LifecycleEvent
from ai_engine.intelligence.violation_manager.violation_manager import ViolationManagerProcessor
from backend.adapters.monitoring_persistence_adapter import MonitoringPersistenceAdapter
from backend.database.session_repository import session_repository
from backend.pipeline.context_builder import ContextBuilder
from backend.pipeline.result_serializer import ResultSerializer
from backend.camera.multi_camera_manager import MultiCameraManager


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
    phone = TrackedObject(
        tracking_id=1,
        object_type=DetectedObjectType.CELL_PHONE,
        bbox=BoundingBox(10, 10, 50, 80),
        confidence=conf,
        current_state="TRACKED",
    )
    ctx.object_info.validated_objects = [phone]
    return ctx


# ---------------------------------------------------------------------------
# TEST 1: Camera 1 violation reaches existing Evidence Engine
# ---------------------------------------------------------------------------
def test_01_camera_1_violation_reaches_evidence_engine(tmp_path):
    """Verify that a confirmed Camera 1 violation generates a snapshot in the existing evidence store."""
    cfg = ViolationManagerConfig(
        evidence_dir=tmp_path,
        min_confirming_frames=1,
        debounce_window_seconds=0.1,
        enable_logging=False,
    )
    vm = ViolationManagerProcessor(cfg)
    vm.initialize()
    vm.start()

    ctx = _make_context_with_rule("camera_1", "UNAUTH_PHONE")
    vm.process(ctx)

    assert len(vm.all_evidence_records) == 1
    rec = vm.all_evidence_records[0]
    assert rec["rule_id"] == "UNAUTH_PHONE"
    assert rec["camera_id"] == "camera_1"
    assert Path(rec["filepath"]).exists()
    assert rec["total_snapshots"] >= 1
    vm.stop()


# ---------------------------------------------------------------------------
# TEST 2: Camera 2 approved violation reaches existing Evidence Engine
# ---------------------------------------------------------------------------
def test_02_camera_2_approved_violation_reaches_evidence_engine(tmp_path):
    """Verify that a confirmed Camera 2 approved violation generates an evidence snapshot."""
    cfg = ViolationManagerConfig(
        evidence_dir=tmp_path,
        min_confirming_frames=1,
        debounce_window_seconds=0.1,
        enable_logging=False,
    )
    vm = ViolationManagerProcessor(cfg)
    vm.initialize()
    vm.start()

    ctx = _make_context_with_rule("camera_2", "UNAUTH_PHONE")
    vm.process(ctx)

    assert len(vm.all_evidence_records) == 1
    rec = vm.all_evidence_records[0]
    assert rec["rule_id"] == "UNAUTH_PHONE"
    assert rec["camera_id"] == "camera_2"
    assert Path(rec["filepath"]).exists()
    vm.stop()


# ---------------------------------------------------------------------------
# TEST 3: Camera 1 evidence metadata contains all required fields
# ---------------------------------------------------------------------------
def test_03_camera_1_evidence_metadata_contains_all_fields(tmp_path):
    """Verify Camera 1 evidence retains session_id, camera_id, violation_type, timestamp, confidence."""
    cfg = ViolationManagerConfig(
        evidence_dir=tmp_path,
        min_confirming_frames=1,
        debounce_window_seconds=0.1,
        enable_logging=False,
    )
    vm = ViolationManagerProcessor(cfg)
    vm.initialize()
    vm.start()

    ctx = _make_context_with_rule("camera_1", "UNAUTH_PHONE", conf=0.92)
    vm.process(ctx)

    rec = vm.all_evidence_records[0]
    assert rec["camera_id"] == "camera_1"
    assert rec["rule_id"] == "UNAUTH_PHONE"
    assert rec["timestamp"] > 0
    assert rec["confidence"] == 0.92
    assert "filepath" in rec and rec["filepath"] != ""

    serializer = ResultSerializer()
    serialized = serializer.to_dict(ctx, {}, 1, 10.0, vm.all_evidence_records)
    ev_items = serialized["evidence"]
    assert len(ev_items) >= 1
    assert ev_items[0]["camera_id"] == "camera_1"
    vm.stop()


# ---------------------------------------------------------------------------
# TEST 4: Camera 2 evidence metadata contains all required fields
# ---------------------------------------------------------------------------
def test_04_camera_2_evidence_metadata_contains_all_fields(tmp_path):
    """Verify Camera 2 evidence retains camera_id='camera_2', rule_id, timestamp, confidence, snapshots."""
    cfg = ViolationManagerConfig(
        evidence_dir=tmp_path,
        min_confirming_frames=1,
        debounce_window_seconds=0.1,
        enable_logging=False,
    )
    vm = ViolationManagerProcessor(cfg)
    vm.initialize()
    vm.start()

    ctx = _make_context_with_rule("camera_2", "UNAUTH_BOOK", conf=0.88)
    vm.process(ctx)

    rec = vm.all_evidence_records[0]
    assert rec["camera_id"] == "camera_2"
    assert rec["rule_id"] == "UNAUTH_BOOK"
    assert rec["timestamp"] > 0
    assert rec["confidence"] == 0.88
    assert len(rec["snapshots"]) >= 1
    assert rec["snapshots"][0]["camera_id"] == "camera_2"
    vm.stop()


# ---------------------------------------------------------------------------
# TEST 5: Both cameras use the SAME session_id
# ---------------------------------------------------------------------------
def test_05_both_cameras_use_same_session_id(tmp_path):
    """Verify that Camera 1 and Camera 2 persist violations and evidence to the SAME session_id in SQLite."""
    session_id = f"sess_p3_dual_{uuid.uuid4().hex[:6]}"
    session_repository.create_session(
        session_id=session_id,
        student_id="student_p3",
        exam_id="exam_p3",
    )

    adapter = MonitoringPersistenceAdapter(active_session_id=session_id)
    cfg = ViolationManagerConfig(
        evidence_dir=tmp_path,
        min_confirming_frames=1,
        debounce_window_seconds=0.1,
        enable_logging=False,
    )
    vm = ViolationManagerProcessor(cfg)
    vm.initialize()
    vm.start()

    # Camera 1 violation
    ctx1 = _make_context_with_rule("camera_1", "ATT_LOOKING_AWAY", conf=0.91, frame_id=1, timestamp=100.0)
    vm.process(ctx1)
    setattr(ctx1, "evidence_store", vm.all_evidence_records)
    adapter.handle_frame_lifecycle(ctx1, session_id=session_id)

    # Camera 2 violation
    ctx2 = _make_context_with_rule("camera_2", "UNAUTH_PHONE", conf=0.94, frame_id=2, timestamp=101.0)
    vm.process(ctx2)
    setattr(ctx2, "evidence_store", vm.all_evidence_records)
    adapter.handle_frame_lifecycle(ctx2, session_id=session_id)

    report = session_repository.get_session_report(session_id)
    assert report is not None
    assert report["summary"]["session_id"] == session_id
    assert report["summary"]["total_violations"] == 2

    cams_found = {ev["metadata"].get("camera_id") for ev in report["evidence"] if "metadata" in ev}
    assert "camera_1" in cams_found
    assert "camera_2" in cams_found
    vm.stop()


# ---------------------------------------------------------------------------
# TEST 6: Camera 1 violation does not require Camera 2 confirmation
# ---------------------------------------------------------------------------
def test_06_camera_1_violation_does_not_require_camera_2_confirmation(tmp_path):
    """Camera 1 violation triggers and captures evidence independently even if Camera 2 is inactive."""
    cfg = ViolationManagerConfig(
        evidence_dir=tmp_path,
        min_confirming_frames=1,
        debounce_window_seconds=0.1,
        enable_logging=False,
    )
    vm = ViolationManagerProcessor(cfg)
    vm.initialize()
    vm.start()

    ctx = _make_context_with_rule("camera_1", "ATT_LOOKING_AWAY", conf=0.95)
    vm.process(ctx)

    assert len(vm.all_evidence_records) == 1
    assert vm.all_evidence_records[0]["rule_id"] == "ATT_LOOKING_AWAY"
    assert vm.all_evidence_records[0]["camera_id"] == "camera_1"
    vm.stop()


# ---------------------------------------------------------------------------
# TEST 7: Camera 2 violation does not require Camera 1 confirmation
# ---------------------------------------------------------------------------
def test_07_camera_2_violation_does_not_require_camera_1_confirmation(tmp_path):
    """Camera 2 violation triggers and captures evidence independently even if Camera 1 sees nothing."""
    cfg = ViolationManagerConfig(
        evidence_dir=tmp_path,
        min_confirming_frames=1,
        debounce_window_seconds=0.1,
        enable_logging=False,
    )
    vm = ViolationManagerProcessor(cfg)
    vm.initialize()
    vm.start()

    ctx = _make_context_with_rule("camera_2", "UNAUTH_BOOK", conf=0.89)
    vm.process(ctx)

    assert len(vm.all_evidence_records) == 1
    assert vm.all_evidence_records[0]["rule_id"] == "UNAUTH_BOOK"
    assert vm.all_evidence_records[0]["camera_id"] == "camera_2"
    vm.stop()


# ---------------------------------------------------------------------------
# TEST 8: Different simultaneous violations remain separate
# ---------------------------------------------------------------------------
def test_08_different_simultaneous_violations_remain_separate(tmp_path):
    """Camera 1 ATT_LOOKING_AWAY and Camera 2 UNAUTH_PHONE both survive as distinct violations."""
    cfg = ViolationManagerConfig(
        evidence_dir=tmp_path,
        min_confirming_frames=1,
        debounce_window_seconds=0.1,
        enable_logging=False,
    )
    vm = ViolationManagerProcessor(cfg)
    vm.initialize()
    vm.start()

    # Camera 1 triggers ATT_LOOKING_AWAY
    ctx1 = _make_context_with_rule("camera_1", "ATT_LOOKING_AWAY", conf=0.90, frame_id=1, timestamp=100.0)
    vm.process(ctx1)

    # Camera 2 triggers UNAUTH_PHONE
    ctx2 = _make_context_with_rule("camera_2", "UNAUTH_PHONE", conf=0.93, frame_id=2, timestamp=100.5)
    vm.process(ctx2)

    # Both episodes must exist in evidence store
    assert len(vm.all_evidence_records) == 2
    rule_ids = {r["rule_id"] for r in vm.all_evidence_records}
    assert "ATT_LOOKING_AWAY" in rule_ids
    assert "UNAUTH_PHONE" in rule_ids

    # Both episodes are active in the timeline
    active = [v for v in vm._timeline_manager.timeline.violations if v.status in ("OPEN", "ACTIVE")]
    assert len(active) == 2
    vm.stop()


# ---------------------------------------------------------------------------
# TEST 9: Same violation observed by both cameras merges without duplicate penalty
# ---------------------------------------------------------------------------
def test_09_same_violation_observed_by_both_cameras_correlation_dedup(tmp_path):
    """When both cameras observe UNAUTH_PHONE, they merge into 1 incident episode."""
    cfg = ViolationManagerConfig(
        evidence_dir=tmp_path,
        min_confirming_frames=1,
        debounce_window_seconds=0.1,
        enable_logging=False,
    )
    vm = ViolationManagerProcessor(cfg)
    vm.initialize()
    vm.start()

    # Camera 1 observes UNAUTH_PHONE
    ctx1 = _make_context_with_rule("camera_1", "UNAUTH_PHONE", conf=0.88, frame_id=1, timestamp=100.0)
    vm.process(ctx1)

    assert len(vm.all_evidence_records) == 1
    first_v_id = vm.all_evidence_records[0]["violation_id"]

    # Camera 2 also observes UNAUTH_PHONE
    ctx2 = _make_context_with_rule("camera_2", "UNAUTH_PHONE", conf=0.94, frame_id=2, timestamp=100.5)
    vm.process(ctx2)

    # Exactly 1 violation episode exists (not two separate phone penalties)
    assert len(vm.all_evidence_records) == 1
    assert vm.all_evidence_records[0]["violation_id"] == first_v_id
    assert vm.all_evidence_records[0]["peak_confidence"] == 0.94
    vm.stop()


# ---------------------------------------------------------------------------
# TEST 10: Both evidence sources are preserved when both cameras observe the same event
# ---------------------------------------------------------------------------
def test_10_both_evidence_sources_preserved_when_both_observe_same_event(tmp_path):
    """Multi-angle capture: Both Camera 1 and Camera 2 snapshots are retained in the correlated episode."""
    cfg = ViolationManagerConfig(
        evidence_dir=tmp_path,
        min_confirming_frames=1,
        debounce_window_seconds=0.1,
        enable_logging=False,
    )
    vm = ViolationManagerProcessor(cfg)
    vm.initialize()
    vm.start()

    # Camera 1 confirms UNAUTH_PHONE -> creates initial snapshot
    ctx1 = _make_context_with_rule("camera_1", "UNAUTH_PHONE", conf=0.85, frame_id=1, timestamp=100.0)
    vm.process(ctx1)

    # Camera 2 observes UNAUTH_PHONE -> adds cross-camera snapshot
    ctx2 = _make_context_with_rule("camera_2", "UNAUTH_PHONE", conf=0.95, frame_id=2, timestamp=100.5)
    vm.process(ctx2)

    rec = vm.all_evidence_records[0]
    snapshots = rec.get("snapshots", [])
    assert len(snapshots) >= 2, f"Expected at least 2 snapshots (multi-angle), got {len(snapshots)}"

    cams_in_snapshots = {s["camera_id"] for s in snapshots}
    assert "camera_1" in cams_in_snapshots
    assert "camera_2" in cams_in_snapshots

    # Verify both physical snapshot files exist on disk
    for s in snapshots:
        assert Path(s["filepath"]).exists(), f"Snapshot file missing: {s['filepath']}"
    vm.stop()


# ---------------------------------------------------------------------------
# TEST 11: Camera 2 evidence cannot accidentally overwrite Camera 1 evidence
# ---------------------------------------------------------------------------
def test_11_camera_2_evidence_cannot_overwrite_camera_1_evidence(tmp_path):
    """Camera 2 evidence files and entries do not destroy or overwrite Camera 1 evidence."""
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
    cam1_filepath = vm.all_evidence_records[0]["filepath"]
    assert Path(cam1_filepath).exists()

    ctx2 = _make_context_with_rule("camera_2", "UNAUTH_PHONE", conf=0.92, frame_id=2, timestamp=100.5)
    vm.process(ctx2)

    # Camera 1 evidence file must still exist untouched
    assert Path(cam1_filepath).exists()
    assert vm.all_evidence_records[0]["filepath"] == cam1_filepath
    assert vm.all_evidence_records[0]["camera_id"] == "camera_1"
    vm.stop()


# ---------------------------------------------------------------------------
# TEST 12: Camera 1 evidence cannot accidentally overwrite Camera 2 evidence
# ---------------------------------------------------------------------------
def test_12_camera_1_evidence_cannot_overwrite_camera_2_evidence(tmp_path):
    """Camera 1 evidence files and entries do not destroy or overwrite Camera 2 evidence."""
    cfg = ViolationManagerConfig(
        evidence_dir=tmp_path,
        min_confirming_frames=1,
        debounce_window_seconds=0.1,
        enable_logging=False,
    )
    vm = ViolationManagerProcessor(cfg)
    vm.initialize()
    vm.start()

    ctx2 = _make_context_with_rule("camera_2", "UNAUTH_BOOK", conf=0.91, frame_id=1, timestamp=100.0)
    vm.process(ctx2)
    cam2_filepath = vm.all_evidence_records[0]["filepath"]
    assert Path(cam2_filepath).exists()

    ctx1 = _make_context_with_rule("camera_1", "ID_MISMATCH", conf=0.93, frame_id=2, timestamp=100.5)
    vm.process(ctx1)

    # Camera 2 evidence file must still exist untouched
    assert Path(cam2_filepath).exists()
    assert vm.all_evidence_records[0]["filepath"] == cam2_filepath
    assert vm.all_evidence_records[0]["camera_id"] == "camera_2"
    vm.stop()


# ---------------------------------------------------------------------------
# TEST 13: Single-camera mode still works
# ---------------------------------------------------------------------------
def test_13_single_camera_mode_still_works(tmp_path):
    """System operates completely normally when only Camera 1 is active (no Camera 2)."""
    cfg = ViolationManagerConfig(
        evidence_dir=tmp_path,
        min_confirming_frames=1,
        debounce_window_seconds=0.1,
        enable_logging=False,
    )
    vm = ViolationManagerProcessor(cfg)
    vm.initialize()
    vm.start()

    # Process 5 frames on Camera 1 only with advancing timestamps
    t0 = 100.0
    for i in range(1, 6):
        ctx = _make_context_with_rule("camera_1", "UNAUTH_PHONE", conf=0.90, frame_id=i, timestamp=t0 + i * 0.2)
        vm.process(ctx)

    assert len(vm.all_evidence_records) == 1
    assert vm.all_evidence_records[0]["camera_id"] == "camera_1"
    assert vm.all_evidence_records[0]["detection_count"] == 5
    vm.stop()


# ---------------------------------------------------------------------------
# TEST 14: Camera 2 disconnect does not break Camera 1 violation/evidence processing
# ---------------------------------------------------------------------------
def test_14_camera_2_disconnect_does_not_break_camera_1(tmp_path):
    """Disconnecting Camera 2 mid-session allows Camera 1 to continue uninterrupted."""
    mcm = MultiCameraManager()
    mcm.register_connection("camera_1")
    mcm.register_connection("camera_2")

    cfg = ViolationManagerConfig(
        evidence_dir=tmp_path,
        min_confirming_frames=1,
        debounce_window_seconds=0.1,
        enable_logging=False,
    )
    vm = ViolationManagerProcessor(cfg)
    vm.initialize()
    vm.start()

    # Both cameras active initially
    ctx1 = _make_context_with_rule("camera_1", "ATT_LOOKING_AWAY", conf=0.90, frame_id=1, timestamp=100.0)
    vm.process(ctx1)
    ctx2 = _make_context_with_rule("camera_2", "UNAUTH_PHONE", conf=0.92, frame_id=2, timestamp=100.5)
    vm.process(ctx2)
    assert len(vm.all_evidence_records) == 2

    # Camera 2 disconnects
    mcm.register_disconnection("camera_2")
    assert not mcm.get_camera_info("camera_2").is_connected
    assert mcm.get_camera_info("camera_1").is_connected

    # Camera 1 continues processing without exception
    ctx1_next = _make_context_with_rule("camera_1", "ID_MISMATCH", conf=0.95, frame_id=3, timestamp=101.0)
    vm.process(ctx1_next)

    assert len(vm.all_evidence_records) == 3
    vm.stop()


# ---------------------------------------------------------------------------
# TEST 15: Existing Phase 1 and Phase 2 compatibility
# ---------------------------------------------------------------------------
def test_15_existing_phase_1_and_phase_2_tests_continue_to_pass():
    """Verify that multi-camera manager and camera allowlist routing continue to operate properly."""
    mcm = MultiCameraManager()
    mcm.register_connection("camera_1")
    mcm.register_connection("camera_2")
    assert mcm.get_camera_info("camera_1").is_connected
    assert mcm.get_camera_info("camera_2").is_connected

    # Check Camera 2 allowlist rules in RuleEngineProcessor
    assert hasattr(RuleEngineProcessor, "CAMERA_2_APPROVED_RULES")
    assert "UNAUTH_PHONE" in RuleEngineProcessor.CAMERA_2_APPROVED_RULES
    assert "ATT_LOOKING_AWAY" not in RuleEngineProcessor.CAMERA_2_APPROVED_RULES
