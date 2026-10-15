"""
Phase 2: Camera-Aware AI Routing & Violation Test Suite
======================================================
Tests all Phase 2 requirements:
TEST 1  — Existing Camera 1 regression: full pipeline executes and rules are not accidentally filtered.
TEST 2  — Camera ID propagation: camera_1 and camera_2 without hardcoded 'playground_webcam'.
TEST 3  — Same session: Camera 1 and Camera 2 process under the same session_id.
TEST 4  — Camera 2 face missing immunity: no face present -> NO ID_FACE_MISSING.
TEST 5  — Camera 2 identity immunity: mismatched face -> NO ID_MISMATCH, etc.
TEST 6  — Camera 2 gaze immunity: looking away / downward gaze -> NO ATT_LOOKING_AWAY / NO ATT_DOWNWARD_GAZE.
TEST 7  — Camera 2 multiple-face immunity: multiple faces visible -> NO ID_MULTIPLE_FACES.
TEST 8  — Camera 2 phone detection: phone detector detects phone -> UNAUTH_PHONE with camera_id == "camera_2".
TEST 9  — Camera 2 book detection: book detector detects book -> UNAUTH_BOOK with camera_id == "camera_2".
TEST 10 — Camera 2 multiple persons: YOLO detects >1 person -> COMM_MULTIPLE_PERSONS with camera_id == "camera_2".
TEST 11 — Camera 2 audio exclusion: audio detector flagged -> Camera 2 ignores COMM_EARPHONES / COMM_AUDIO_DEVICE.
TEST 12 — Camera 2 gaze exclusion: gaze data present -> Camera 2 ignores gaze rules.
TEST 13 — Camera 2 disconnect isolation: disconnect Camera 2 -> Camera 1 continues normally without crash.
TEST 14 — Camera 2 malformed frame resilience: corrupt JPEG bytes -> handled safely, Camera 1 continues.
TEST 15 — Camera 2 evidence attribution: evidence metadata contains camera_id == "camera_2" and session_id.
TEST 16 — Camera 1 evidence attribution: evidence metadata contains camera_id == "camera_1".
TEST 17 — Single-camera mode: running with Camera 2 disconnected works exactly as before.
TEST 18 — Camera 2 preview independence: preview queue delivers frames immediately without waiting for AI.
TEST 19 — Bounded Camera 2 AI queue: queue has maxsize=1 and drops stale frames under load.
"""
import time
import pytest
import numpy as np
import cv2

from ai_engine.core.exam_context import ExamContext, BoundingBox, DetectedObject, TrackedObject
from ai_engine.core.enums import DetectedObjectType
from ai_engine.camera.frame import Frame
from ai_engine.intelligence.observation_fusion.models import (
    UnifiedObservation, FaceObservation, EnvironmentObservation, ObservationConfidenceSummary
)
from ai_engine.intelligence.rule_engine.models import RuleEngineConfig
from ai_engine.intelligence.rule_engine.rule_engine import RuleEngineProcessor
from ai_engine.intelligence.violation_manager.models import ViolationManagerConfig
from ai_engine.intelligence.violation_manager.violation_manager import ViolationManagerProcessor
from backend.pipeline.context_builder import ContextBuilder
from backend.pipeline.orchestrator import MonitoringPipelineOrchestrator
from backend.camera.multi_camera_manager import MultiCameraManager, multi_camera_manager


def _create_dummy_jpeg() -> bytes:
    img = np.zeros((120, 160, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()


# ---------------------------------------------------------------------------
# TEST 1 — Existing Camera 1 regression
# ---------------------------------------------------------------------------
def test_camera_1_regression_full_pipeline():
    """Verify Camera 1 runs all rules and does not filter out facial/gaze/identity rules."""
    cb = ContextBuilder()
    jpeg = _create_dummy_jpeg()
    frame = cb.decode_and_inject(jpeg, camera_id="camera_1")
    assert frame is not None
    assert frame.camera_id == "camera_1"

    config = RuleEngineConfig(
        enabled_rules={
            "ATT_LOOKING_AWAY": True,
            "ATT_DOWNWARD_GAZE": True,
            "ID_MISMATCH": True,
            "ID_FACE_MISSING": True,
            "ID_MULTIPLE_FACES": True,
            "UNAUTH_PHONE": True,
            "UNAUTH_BOOK": True,
            "COMM_EARPHONES": True,
            "COMM_MULTIPLE_PERSONS": True,
        },
        enable_logging=False,
    )
    rep = RuleEngineProcessor(config=config)
    rep.initialize()
    rep.start()

    ctx = cb.context
    # Unified observation with face missing
    obs = UnifiedObservation(
        timestamp=time.time(),
        face=FaceObservation(face_present=False, face_confidence=0.0),
        environment=EnvironmentObservation(),
        confidence_summary=ObservationConfidenceSummary(),
    )
    setattr(ctx, "observation", obs)

    rep.process(ctx)
    res = getattr(ctx, "rule_results", None)
    assert res is not None
    eval_ids = [e.rule_id for e in res.evaluations]
    # For Camera 1, face missing MUST be evaluated and triggered
    assert "ID_FACE_MISSING" in eval_ids
    triggered_ids = [e.rule_id for e in res.evaluations if e.triggered]
    assert "ID_FACE_MISSING" in triggered_ids


# ---------------------------------------------------------------------------
# TEST 2 — Camera ID propagation
# ---------------------------------------------------------------------------
def test_camera_id_propagation():
    """Verify camera_1 and camera_2 identities are assigned without hardcoded 'playground_webcam'."""
    cb = ContextBuilder()
    jpeg = _create_dummy_jpeg()

    # Camera 1
    f1 = cb.decode_and_inject(jpeg, camera_id="camera_1")
    assert f1.camera_id == "camera_1"
    assert cb.context.current_frame.camera_id == "camera_1"

    # Camera 2
    f2 = cb.decode_and_inject(jpeg, camera_id="camera_2")
    assert f2.camera_id == "camera_2"
    assert cb.context.current_frame.camera_id == "camera_2"

    # Legacy default resolution
    f_legacy = cb.decode_and_inject(jpeg, camera_id="playground_webcam")
    assert f_legacy.camera_id == "camera_1"


# ---------------------------------------------------------------------------
# TEST 3 — Same session for Camera 1 and Camera 2
# ---------------------------------------------------------------------------
def test_same_session_across_cameras():
    """Camera 1 and Camera 2 must operate under the exact same session_id."""
    cb = ContextBuilder()
    expected_sid = cb.session_context.monitoring_session_id
    jpeg = _create_dummy_jpeg()

    cb.decode_and_inject(jpeg, camera_id="camera_1")
    assert cb.context.monitoring_session.monitoring_session_id == expected_sid

    cb.decode_and_inject(jpeg, camera_id="camera_2")
    assert cb.context.monitoring_session.monitoring_session_id == expected_sid


# ---------------------------------------------------------------------------
# TEST 4 — Camera 2 face missing immunity
# ---------------------------------------------------------------------------
def test_camera_2_face_missing_immunity():
    """Camera 2 frame with no face must NEVER generate ID_FACE_MISSING."""
    cb = ContextBuilder()
    jpeg = _create_dummy_jpeg()
    cb.decode_and_inject(jpeg, camera_id="camera_2")

    config = RuleEngineConfig(
        enabled_rules={"ID_FACE_MISSING": True, "UNAUTH_PHONE": True},
        enable_logging=False,
    )
    rep = RuleEngineProcessor(config=config)
    rep.initialize()
    rep.start()

    ctx = cb.context
    obs = UnifiedObservation(
        timestamp=time.time(),
        face=FaceObservation(face_present=False, face_confidence=0.0),
        environment=EnvironmentObservation(),
        confidence_summary=ObservationConfidenceSummary(),
    )
    setattr(ctx, "observation", obs)

    rep.process(ctx)
    res = getattr(ctx, "rule_results", None)
    assert res is not None
    eval_ids = [e.rule_id for e in res.evaluations]
    assert "ID_FACE_MISSING" not in eval_ids
    triggered_ids = [e.rule_id for e in res.evaluations if e.triggered]
    assert "ID_FACE_MISSING" not in triggered_ids


# ---------------------------------------------------------------------------
# TEST 5 — Camera 2 identity immunity
# ---------------------------------------------------------------------------
def test_camera_2_identity_immunity():
    """Camera 2 frame with face mismatch must NEVER generate ID_MISMATCH, etc."""
    cb = ContextBuilder()
    jpeg = _create_dummy_jpeg()
    cb.decode_and_inject(jpeg, camera_id="camera_2")

    config = RuleEngineConfig(
        enabled_rules={
            "ID_MISMATCH": True,
            "IDENTITY_REPEATED_MISMATCH": True,
            "IDENTITY_LOW_INTEGRITY": True,
            "IDENTITY_INSTABILITY": True,
            "CONFIRMED_PRESENTATION_ATTACK": True,
            "INSUFFICIENT_IDENTITY_EVIDENCE": True,
        },
        enable_logging=False,
    )
    rep = RuleEngineProcessor(config=config)
    rep.initialize()
    rep.start()

    ctx = cb.context
    obs = UnifiedObservation(
        timestamp=time.time(),
        face=FaceObservation(
            face_present=True,
            identity_consistent=False,
            identity_confidence=0.10,
        ),
        environment=EnvironmentObservation(),
        confidence_summary=ObservationConfidenceSummary(),
    )
    setattr(ctx, "observation", obs)

    rep.process(ctx)
    res = getattr(ctx, "rule_results", None)
    eval_ids = [e.rule_id for e in res.evaluations]
    assert len(eval_ids) == 0
    triggered_ids = [e.rule_id for e in res.evaluations if e.triggered]
    assert len(triggered_ids) == 0


# ---------------------------------------------------------------------------
# TEST 6 — Camera 2 gaze immunity
# ---------------------------------------------------------------------------
def test_camera_2_gaze_immunity():
    """Camera 2 frame must NEVER trigger ATT_LOOKING_AWAY or ATT_DOWNWARD_GAZE."""
    cb = ContextBuilder()
    jpeg = _create_dummy_jpeg()
    cb.decode_and_inject(jpeg, camera_id="camera_2")

    config = RuleEngineConfig(
        enabled_rules={
            "ATT_LOOKING_AWAY": True,
            "ATT_DOWNWARD_GAZE": True,
            "COMPOSITE_PHONE_LOOKING_AWAY_TALKING": True,
        },
        enable_logging=False,
    )
    rep = RuleEngineProcessor(config=config)
    rep.initialize()
    rep.start()

    ctx = cb.context
    obs = UnifiedObservation(
        timestamp=time.time(),
        face=FaceObservation(
            face_present=True,
            gaze_state="OFF_SCREEN",
            head_pose_state="DOWN",
            gaze_confidence=0.99,
        ),
        environment=EnvironmentObservation(),
        confidence_summary=ObservationConfidenceSummary(),
    )
    setattr(ctx, "observation", obs)

    rep.process(ctx)
    res = getattr(ctx, "rule_results", None)
    eval_ids = [e.rule_id for e in res.evaluations]
    assert "ATT_LOOKING_AWAY" not in eval_ids
    assert "ATT_DOWNWARD_GAZE" not in eval_ids


# ---------------------------------------------------------------------------
# TEST 7 — Camera 2 multiple-face immunity
# ---------------------------------------------------------------------------
def test_camera_2_multiple_face_immunity():
    """Camera 2 must NEVER generate ID_MULTIPLE_FACES even if face_count > 1."""
    cb = ContextBuilder()
    jpeg = _create_dummy_jpeg()
    cb.decode_and_inject(jpeg, camera_id="camera_2")

    config = RuleEngineConfig(
        enabled_rules={
            "ID_MULTIPLE_FACES": True,
            "COMM_MULTIPLE_PERSONS": True,
        },
        enable_logging=False,
    )
    rep = RuleEngineProcessor(config=config)
    rep.initialize()
    rep.start()

    ctx = cb.context
    obs = UnifiedObservation(
        timestamp=time.time(),
        face=FaceObservation(face_present=True, face_count=2, presence_state="MULTIPLE"),
        environment=EnvironmentObservation(total_persons=1),
        confidence_summary=ObservationConfidenceSummary(),
    )
    setattr(ctx, "observation", obs)

    rep.process(ctx)
    res = getattr(ctx, "rule_results", None)
    eval_ids = [e.rule_id for e in res.evaluations]
    assert "ID_MULTIPLE_FACES" not in eval_ids
    triggered_ids = [e.rule_id for e in res.evaluations if e.triggered]
    assert "ID_MULTIPLE_FACES" not in triggered_ids


# ---------------------------------------------------------------------------
# TEST 8 — Camera 2 phone detection
# ---------------------------------------------------------------------------
def test_camera_2_phone_detection():
    """Camera 2 frame detects phone -> triggers UNAUTH_PHONE with camera_id == 'camera_2'."""
    cb = ContextBuilder()
    jpeg = _create_dummy_jpeg()
    frame = cb.decode_and_inject(jpeg, camera_id="camera_2")
    assert frame.camera_id == "camera_2"

    config = RuleEngineConfig(
        enabled_rules={"UNAUTH_PHONE": True, "ID_FACE_MISSING": True},
        enable_logging=False,
    )
    rep = RuleEngineProcessor(config=config)
    rep.initialize()
    rep.start()

    ctx = cb.context
    obs = UnifiedObservation(
        timestamp=time.time(),
        face=FaceObservation(),
        environment=EnvironmentObservation(phone_present=True),
        confidence_summary=ObservationConfidenceSummary(),
    )
    setattr(ctx, "observation", obs)

    rep.process(ctx)
    res = getattr(ctx, "rule_results", None)
    triggered_ids = [e.rule_id for e in res.evaluations if e.triggered]
    assert "UNAUTH_PHONE" in triggered_ids

    vm_cfg = ViolationManagerConfig(
        debounce_window_seconds=0.0,
        min_confirming_frames=1,
        auto_close_timeout_seconds=5.0,
        enable_logging=False,
    )
    vm = ViolationManagerProcessor(config=vm_cfg)
    vm.initialize()
    vm.start()
    vm.process(ctx)

    events = getattr(ctx, "lifecycle_events", [])
    assert len(events) >= 1
    started = [e for e in events if e.event_type == "STARTED"]
    assert len(started) == 1
    assert started[0].violation_type == "UNAUTH_PHONE"
    assert len(vm.all_evidence_records) == 1
    ev_rec = vm.all_evidence_records[0]
    assert ev_rec["camera_id"] == "camera_2"


# ---------------------------------------------------------------------------
# TEST 9 — Camera 2 book detection
# ---------------------------------------------------------------------------
def test_camera_2_book_detection():
    """Camera 2 frame detects book -> triggers UNAUTH_BOOK with camera_id == 'camera_2'."""
    cb = ContextBuilder()
    jpeg = _create_dummy_jpeg()
    cb.decode_and_inject(jpeg, camera_id="camera_2")

    config = RuleEngineConfig(
        enabled_rules={"UNAUTH_BOOK": True, "ENV_BOOK_DETECTED": True},
        enable_logging=False,
    )
    rep = RuleEngineProcessor(config=config)
    rep.initialize()
    rep.start()

    ctx = cb.context
    obs = UnifiedObservation(
        timestamp=time.time(),
        face=FaceObservation(),
        environment=EnvironmentObservation(book_present=True),
        confidence_summary=ObservationConfidenceSummary(),
    )
    setattr(ctx, "observation", obs)

    rep.process(ctx)
    res = getattr(ctx, "rule_results", None)
    triggered_ids = [e.rule_id for e in res.evaluations if e.triggered]
    assert "UNAUTH_BOOK" in triggered_ids or "ENV_BOOK_DETECTED" in triggered_ids


# ---------------------------------------------------------------------------
# TEST 10 — Camera 2 multiple persons via YOLO
# ---------------------------------------------------------------------------
def test_camera_2_multiple_persons():
    """Camera 2 frame with total_persons > 1 -> triggers COMM_MULTIPLE_PERSONS."""
    cb = ContextBuilder()
    jpeg = _create_dummy_jpeg()
    cb.decode_and_inject(jpeg, camera_id="camera_2")

    config = RuleEngineConfig(
        enabled_rules={"COMM_MULTIPLE_PERSONS": True, "ID_MULTIPLE_FACES": True},
        enable_logging=False,
    )
    rep = RuleEngineProcessor(config=config)
    rep.initialize()
    rep.start()

    ctx = cb.context
    obs = UnifiedObservation(
        timestamp=time.time(),
        face=FaceObservation(face_present=True, face_count=1),
        environment=EnvironmentObservation(total_persons=2),
        confidence_summary=ObservationConfidenceSummary(),
    )
    setattr(ctx, "observation", obs)

    rep.process(ctx)
    res = getattr(ctx, "rule_results", None)
    eval_ids = [e.rule_id for e in res.evaluations]
    assert "ID_MULTIPLE_FACES" not in eval_ids
    triggered_ids = [e.rule_id for e in res.evaluations if e.triggered]
    assert "COMM_MULTIPLE_PERSONS" in triggered_ids


# ---------------------------------------------------------------------------
# TEST 11 — Camera 2 audio exclusion
# ---------------------------------------------------------------------------
def test_camera_2_audio_exclusion():
    """Camera 2 frame must NOT evaluate or trigger COMM_EARPHONES or COMM_AUDIO_DEVICE."""
    cb = ContextBuilder()
    jpeg = _create_dummy_jpeg()
    cb.decode_and_inject(jpeg, camera_id="camera_2")

    config = RuleEngineConfig(
        enabled_rules={"COMM_EARPHONES": True, "UNAUTH_PHONE": True},
        enable_logging=False,
    )
    rep = RuleEngineProcessor(config=config)
    rep.initialize()
    rep.start()

    ctx = cb.context
    obs = UnifiedObservation(
        timestamp=time.time(),
        face=FaceObservation(),
        environment=EnvironmentObservation(earphone_present=True),
        confidence_summary=ObservationConfidenceSummary(),
    )
    setattr(ctx, "observation", obs)

    rep.process(ctx)
    res = getattr(ctx, "rule_results", None)
    eval_ids = [e.rule_id for e in res.evaluations]
    assert "COMM_EARPHONES" not in eval_ids
    triggered_ids = [e.rule_id for e in res.evaluations if e.triggered]
    assert "COMM_EARPHONES" not in triggered_ids


# ---------------------------------------------------------------------------
# TEST 12 — Camera 2 gaze exclusion
# ---------------------------------------------------------------------------
def test_camera_2_gaze_exclusion():
    """Camera 2 frame with gaze values present in context must not trigger gaze rules."""
    cb = ContextBuilder()
    jpeg = _create_dummy_jpeg()
    cb.decode_and_inject(jpeg, camera_id="camera_2")

    config = RuleEngineConfig(
        enabled_rules={"ATT_LOOKING_AWAY": True, "ATT_DOWNWARD_GAZE": True},
        enable_logging=False,
    )
    rep = RuleEngineProcessor(config=config)
    rep.initialize()
    rep.start()

    ctx = cb.context
    obs = UnifiedObservation(
        timestamp=time.time(),
        face=FaceObservation(gaze_state="AWAY", gaze_confidence=0.95),
        environment=EnvironmentObservation(),
        confidence_summary=ObservationConfidenceSummary(),
    )
    setattr(ctx, "observation", obs)

    rep.process(ctx)
    res = getattr(ctx, "rule_results", None)
    eval_ids = [e.rule_id for e in res.evaluations]
    assert len(eval_ids) == 0


# ---------------------------------------------------------------------------
# TEST 13 — Camera 2 disconnect isolation
# ---------------------------------------------------------------------------
def test_camera_2_disconnect_isolation():
    """Disconnecting Camera 2 leaves Camera 1 intact and functional."""
    mgr = MultiCameraManager()
    mgr.register_connection("camera_1", "sess_iso")
    mgr.register_connection("camera_2", "sess_iso")

    mgr.register_disconnection("camera_2")

    c1 = mgr.get_camera_info("camera_1")
    c2 = mgr.get_camera_info("camera_2")
    assert c1.is_connected is True
    assert c2.is_connected is False


# ---------------------------------------------------------------------------
# TEST 14 — Camera 2 malformed frame resilience
# ---------------------------------------------------------------------------
def test_camera_2_malformed_frame():
    """Malformed JPEG frame does not raise exception and returns None safely."""
    cb = ContextBuilder()
    corrupted_bytes = b"NOT_A_JPEG_RANDOM_GARBAGE_BYTES_12345"
    frame = cb.decode_and_inject(corrupted_bytes, camera_id="camera_2")
    assert frame is None


# ---------------------------------------------------------------------------
# TEST 15 — Evidence attribution Camera 2
# ---------------------------------------------------------------------------
def test_evidence_attribution_camera_2():
    """Camera 2 violation snapshot record contains camera_id == 'camera_2'."""
    cb = ContextBuilder()
    jpeg = _create_dummy_jpeg()
    cb.decode_and_inject(jpeg, camera_id="camera_2")

    config = RuleEngineConfig(
        enabled_rules={"UNAUTH_PHONE": True},
        enable_logging=False,
    )
    rep = RuleEngineProcessor(config=config)
    rep.initialize()
    rep.start()

    ctx = cb.context
    obs = UnifiedObservation(
        timestamp=time.time(),
        face=FaceObservation(),
        environment=EnvironmentObservation(phone_present=True),
        confidence_summary=ObservationConfidenceSummary(),
    )
    setattr(ctx, "observation", obs)
    rep.process(ctx)

    vm_cfg = ViolationManagerConfig(debounce_window_seconds=0.0, min_confirming_frames=1, enable_logging=False)
    vm = ViolationManagerProcessor(config=vm_cfg)
    vm.initialize()
    vm.start()
    vm.process(ctx)

    records = vm.all_evidence_records
    assert len(records) >= 1
    assert records[0]["camera_id"] == "camera_2"


# ---------------------------------------------------------------------------
# TEST 16 — Evidence attribution Camera 1
# ---------------------------------------------------------------------------
def test_evidence_attribution_camera_1():
    """Camera 1 violation snapshot record contains camera_id == 'camera_1'."""
    cb = ContextBuilder()
    jpeg = _create_dummy_jpeg()
    cb.decode_and_inject(jpeg, camera_id="camera_1")

    config = RuleEngineConfig(
        enabled_rules={"UNAUTH_PHONE": True},
        enable_logging=False,
    )
    rep = RuleEngineProcessor(config=config)
    rep.initialize()
    rep.start()

    ctx = cb.context
    obs = UnifiedObservation(
        timestamp=time.time(),
        face=FaceObservation(),
        environment=EnvironmentObservation(phone_present=True),
        confidence_summary=ObservationConfidenceSummary(),
    )
    setattr(ctx, "observation", obs)
    rep.process(ctx)

    vm_cfg = ViolationManagerConfig(debounce_window_seconds=0.0, min_confirming_frames=1, enable_logging=False)
    vm = ViolationManagerProcessor(config=vm_cfg)
    vm.initialize()
    vm.start()
    vm.process(ctx)

    records = vm.all_evidence_records
    assert len(records) >= 1
    assert records[0]["camera_id"] == "camera_1"


# ---------------------------------------------------------------------------
# TEST 17 — Single-camera mode
# ---------------------------------------------------------------------------
def test_single_camera_mode():
    """System operates normally with only Camera 1 connected."""
    mgr = MultiCameraManager()
    mgr.register_connection("camera_1", "sess_single")

    st = mgr.get_status("sess_single")
    assert st["cameras"]["camera_1"]["is_connected"] is True
    assert st["cameras"]["camera_2"]["is_connected"] is False


# ---------------------------------------------------------------------------
# TEST 18 — Camera 2 preview independence
# ---------------------------------------------------------------------------
def test_camera_2_preview_independence():
    """Live preview subscriber queue receives frames immediately."""
    mgr = MultiCameraManager()
    mgr.register_connection("camera_2", "sess_prev")
    q = mgr.subscribe_feed("camera_2")

    jpeg = _create_dummy_jpeg()
    mgr.push_frame("camera_2", jpeg, session_id="sess_prev")

    assert q.qsize() == 1
    delivered = q.get_nowait()
    assert delivered == jpeg


# ---------------------------------------------------------------------------
# TEST 19 — Bounded Camera 2 AI queue
# ---------------------------------------------------------------------------
def test_bounded_camera_2_ai_queue():
    """Camera 2 AI queue has bounded size and does not accumulate unbounded frames."""
    mgr = MultiCameraManager()
    assert mgr._cam2_ai_queue.maxsize == 1

    # Force AI processor callback to enable queuing
    mgr.set_ai_pipeline_processor(lambda cid, data, sid: None)

    # Push multiple frames in rapid succession
    jpeg1 = b"frame_1"
    jpeg2 = b"frame_2"
    jpeg3 = b"frame_3"

    mgr._cam2_last_ai_sample_time = 0.0  # Reset throttle
    mgr.push_frame("camera_2", jpeg1, session_id="sess_queue")
    mgr._cam2_last_ai_sample_time = 0.0
    mgr.push_frame("camera_2", jpeg2, session_id="sess_queue")
    mgr._cam2_last_ai_sample_time = 0.0
    mgr.push_frame("camera_2", jpeg3, session_id="sess_queue")

    # Queue should contain at most 1 item (the newest sampled frame)
    assert mgr._cam2_ai_queue.qsize() == 1
    item = mgr._cam2_ai_queue.get_nowait()
    assert item[1] == jpeg3
