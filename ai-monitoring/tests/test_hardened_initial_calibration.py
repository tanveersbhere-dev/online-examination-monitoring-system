"""
Test Suite: Hardened Initial Attention Calibration & Anti-Poisoning Verification
================================================================================
Verifies:
  TEST 1 - Normal Neutral Calibration (reaches 30/30, 100%, CALIBRATED / READY, valid baseline created)
  TEST 2 - Looking Far Left During Calibration (frames rejected, calibration does NOT complete)
  TEST 3 - Looking Far Right During Calibration (frames rejected, calibration does NOT complete)
  TEST 4 - Looking Significantly Down During Calibration (frames rejected, calibration does NOT complete)
  TEST 5 - Blink / Low Gaze Quality (frames rejected, sample count preserved)
  TEST 6 - Mixed Session (10 valid -> looking away pause -> 20 valid -> reaches 30/30 CALIBRATED)
  TEST 7 - Post-Calibration Off-Screen Detection (ATT_LOOKING_AWAY triggers reliably after valid calibration)
  TEST 8 - Existing Recalibration Regression (historical absence safe, unenrolled identity safe, >10s continuous loss recalibrates)
"""
import time
import pytest
import numpy as np

from ai_engine.core.exam_context import (
    ExamContext, FaceInfo, HeadPoseInfo, EyeInfo, BoundingBox
)
from ai_engine.camera.frame import Frame
from ai_engine.calibration.calibration_engine import CalibrationEngineProcessor
from ai_engine.calibration.calibration_manager import CalibrationManager
from backend.pipeline.orchestrator import MonitoringPipelineOrchestrator


def _make_context(
    face_detected=True,
    conf=0.95,
    face_width=150.0,
    pose_success=True,
    yaw=0.0,
    pitch=0.0,
    roll=0.0,
    has_iris=True,
    gaze_confidence=0.90,
    g_x=0.0,
    g_y=0.0,
    blink=False,
    ear=0.28,
    frame_id=1
):
    ctx = ExamContext()
    ctx.current_frame = Frame.from_bgr_image(np.zeros((480, 640, 3), dtype=np.uint8), frame_id=frame_id, timestamp=time.time())
    ctx.face_info = FaceInfo(
        face_detected=face_detected,
        confidence=conf,
        bbox=BoundingBox(100, 100, face_width, face_width),
        face_count=1 if face_detected else 0,
        presence_state="PRESENT" if face_detected else "MISSING",
        identity_consistent=True
    )
    ctx.head_pose_info = HeadPoseInfo(yaw=yaw, pitch=pitch, roll=roll, success=pose_success)
    ctx.eye_info = EyeInfo(
        left_iris_center=(0.4, 0.4) if has_iris else None,
        right_iris_center=(0.6, 0.4) if has_iris else None,
        gaze_confidence=gaze_confidence,
        combined_gaze=(g_x, g_y, 1.0),
        blink_detected=blink,
        average_ear=ear
    )
    return ctx


def test_01_normal_neutral_calibration():
    """TEST 1: Candidate looks neutrally at the screen -> calibration reaches 30/30 and CALIBRATED."""
    engine = CalibrationEngineProcessor(target_samples=30, warmup_duration_seconds=0.1, calibration_duration_seconds=30.0)
    engine.initialize()
    engine.start_time = time.time() - 4.0

    for i in range(1, 31):
        ctx = _make_context(yaw=1.0, pitch=-2.0, g_x=0.05, g_y=0.02, frame_id=i)
        engine.process(ctx)

    assert engine.valid_samples == 30
    assert engine.is_completed is True
    assert engine.stage == "READY"
    baseline = engine.finalize_baseline()
    assert baseline.samples_collected == 30
    assert baseline.stage == "READY"


def test_01b_upright_roll_representations_and_tilt():
    """Verify roll near 0°, +180°, and -180° are accepted as upright, while genuine tilt is rejected."""
    engine = CalibrationEngineProcessor(target_samples=10, warmup_duration_seconds=0.1, calibration_duration_seconds=30.0)
    engine.initialize()
    engine.start_time = time.time() - 4.0

    # 1. Roll near 0° -> accepted
    ctx_0 = _make_context(roll=2.0)
    assert engine._is_valid_initial_calibration_frame(
        True, 0.95, 120.0, True, 0.0, 0.0, 2.0, True, 0.90, 0.0, 0.0, False, 0.28
    ) is True

    # 2. Roll near +180° (e.g. +179.5°) -> accepted
    assert engine._is_valid_initial_calibration_frame(
        True, 0.95, 120.0, True, 0.0, 0.0, 179.5, True, 0.90, 0.0, 0.0, False, 0.28
    ) is True

    # 3. Roll near -180° (e.g. -179.7°) -> accepted
    assert engine._is_valid_initial_calibration_frame(
        True, 0.95, 120.0, True, 0.0, 0.0, -179.7, True, 0.90, 0.0, 0.0, False, 0.28
    ) is True

    # 4. Large roll / sideways head tilt (e.g. 50°) -> rejected
    assert engine._is_valid_initial_calibration_frame(
        True, 0.95, 120.0, True, 0.0, 0.0, 50.0, True, 0.90, 0.0, 0.0, False, 0.28
    ) is False


def test_01c_normal_seated_yaw_accepted():
    """Verify normal seated yaw (-25°) is accepted, while clear off-screen yaw (-35°) is rejected."""
    engine = CalibrationEngineProcessor(target_samples=10, warmup_duration_seconds=0.1, calibration_duration_seconds=30.0)
    engine.initialize()

    # Yaw = -25.0° (normal seated angle at laptop) -> accepted
    assert engine._is_valid_initial_calibration_frame(
        True, 0.95, 120.0, True, -25.0, -8.0, 179.6, True, 0.90, -0.10, 0.0, False, 0.28
    ) is True

    # Yaw = -35.0° (turned off-screen) -> rejected
    assert engine._is_valid_initial_calibration_frame(
        True, 0.95, 120.0, True, -35.0, 0.0, 179.6, True, 0.90, -0.60, 0.0, False, 0.28
    ) is False


def test_02_looking_far_left_during_calibration():
    """TEST 2: Looking far left (yaw = -35°, g_x = -0.60) is rejected; calibration does not complete."""
    engine = CalibrationEngineProcessor(target_samples=30, warmup_duration_seconds=0.1, calibration_duration_seconds=30.0)
    engine.initialize()
    engine.start_time = time.time() - 4.0

    for i in range(1, 40):
        ctx = _make_context(yaw=-35.0, pitch=0.0, g_x=-0.60, g_y=0.0, frame_id=i)
        engine.process(ctx)

    assert engine.valid_samples == 0
    assert engine.is_completed is False


def test_03_looking_far_right_during_calibration():
    """TEST 3: Looking far right (yaw = +35°, g_x = +0.55) is rejected; calibration does not complete."""
    engine = CalibrationEngineProcessor(target_samples=30, warmup_duration_seconds=0.1, calibration_duration_seconds=30.0)
    engine.initialize()
    engine.start_time = time.time() - 4.0

    for i in range(1, 40):
        ctx = _make_context(yaw=35.0, pitch=0.0, g_x=0.55, g_y=0.0, frame_id=i)
        engine.process(ctx)

    assert engine.valid_samples == 0
    assert engine.is_completed is False


def test_04_looking_significantly_down_during_calibration():
    """TEST 4: Looking down (pitch = -32°, g_y = +0.55) is rejected; calibration does not complete."""
    engine = CalibrationEngineProcessor(target_samples=30, warmup_duration_seconds=0.1, calibration_duration_seconds=30.0)
    engine.initialize()
    engine.start_time = time.time() - 4.0

    for i in range(1, 40):
        ctx = _make_context(yaw=0.0, pitch=-25.0, g_x=0.0, g_y=0.45, frame_id=i)
        engine.process(ctx)

    assert engine.valid_samples == 0
    assert engine.is_completed is False


def test_05_blink_low_gaze_quality():
    """TEST 5: Blinking frames or missing iris are rejected while preserving existing valid samples."""
    engine = CalibrationEngineProcessor(target_samples=30, warmup_duration_seconds=0.1, calibration_duration_seconds=30.0)
    engine.initialize()
    engine.start_time = time.time() - 4.0

    # 5 valid neutral frames
    for i in range(1, 6):
        ctx = _make_context(yaw=0.0, pitch=0.0, g_x=0.0, g_y=0.0, frame_id=i)
        engine.process(ctx)
    assert engine.valid_samples == 5

    # 10 blinking / low confidence frames
    for i in range(6, 16):
        ctx_blink = _make_context(blink=True, ear=0.10, has_iris=False, gaze_confidence=0.20, frame_id=i)
        engine.process(ctx_blink)

    # Valid sample count is preserved exactly at 5
    assert engine.valid_samples == 5
    assert engine.is_completed is False


def test_06_mixed_session_looking_away_and_resuming():
    """TEST 6: 10 valid -> looking away pause -> 20 valid -> completes 30/30 CALIBRATED."""
    engine = CalibrationEngineProcessor(target_samples=30, warmup_duration_seconds=0.1, calibration_duration_seconds=30.0)
    engine.initialize()
    engine.start_time = time.time() - 4.0

    # Phase 1: 10 valid samples
    for i in range(1, 11):
        ctx = _make_context(yaw=1.0, pitch=-1.0, g_x=0.02, g_y=0.01, frame_id=i)
        engine.process(ctx)
    assert engine.valid_samples == 10

    # Phase 2: Candidate looks away left for 15 frames (rejected, no reset)
    for i in range(11, 26):
        ctx_away = _make_context(yaw=-35.0, pitch=0.0, g_x=-0.70, g_y=0.0, frame_id=i)
        engine.process(ctx_away)
    assert engine.valid_samples == 10
    assert engine.is_completed is False

    # Phase 3: Candidate returns neutral; finishes remaining 20 samples
    for i in range(26, 46):
        ctx_back = _make_context(yaw=0.0, pitch=0.0, g_x=0.0, g_y=0.0, frame_id=i)
        engine.process(ctx_back)

    assert engine.valid_samples == 30
    assert engine.is_completed is True
    assert engine.stage == "READY"


def test_07_post_calibration_off_screen_detection():
    """TEST 7: After neutral calibration baseline is created, ATT_LOOKING_AWAY triggers on off-screen gaze."""
    orch = MonitoringPipelineOrchestrator()
    orch.initialize()
    orch.start()

    # Step 1: Calibrate with 30 neutral frames
    for i in range(1, 31):
        ctx_cal = _make_context(yaw=0.0, pitch=0.0, g_x=0.0, g_y=0.0, frame_id=i)
        orch._update_calibrated_attention(ctx_cal)

    assert orch.calibration_manager.status == "CALIBRATED"

    # Step 2: Test off-screen right deviation (yaw = +36°, gaze = +0.75)
    ctx_test = _make_context(yaw=36.0, pitch=0.0, g_x=0.75, g_y=0.0, frame_id=31)
    orch._update_calibrated_attention(ctx_test)
    orch._processors["ObservationFusion"].processor.process(ctx_test)
    orch._processors["RuleEngine"].processor._last_evaluation_time = 0.0
    orch._processors["RuleEngine"].processor.process(ctx_test)

    triggered = [e.rule_id for e in ctx_test.rule_results.evaluations if e.triggered]
    assert "ATT_LOOKING_AWAY" in triggered


def test_08_existing_recalibration_regression():
    """TEST 8: Historical absence & unenrolled identity are safe; genuine continuous loss >10s triggers reset."""
    mgr = CalibrationManager()
    engine = CalibrationEngineProcessor(target_samples=30, warmup_duration_seconds=0.1)
    engine.initialize()
    engine.start_time = time.time() - 4.0

    for i in range(1, 31):
        engine.process(_make_context(yaw=0.0, pitch=0.0, g_x=0.0, g_y=0.0, frame_id=i))
    mgr.complete_calibration(engine.finalize_baseline())
    assert mgr.status == "CALIBRATED"

    # 1. Historical absence (> 30s) while face is present -> remains CALIBRATED
    ctx_hist = _make_context()
    ctx_hist.face_info.absent_duration = 30.0
    mgr.evaluate_runtime_frame(ctx_hist)
    assert mgr.status == "CALIBRATED"

    # 2. Unenrolled identity inconsistency -> remains CALIBRATED
    ctx_unenroll = _make_context()
    ctx_unenroll.face_info.reference_embedding = None
    ctx_unenroll.face_info.identity_consistent = False
    mgr.evaluate_runtime_frame(ctx_unenroll)
    assert mgr.status == "CALIBRATED"

    # 3. Genuine continuous face loss for > 10 seconds -> RECALIBRATION_REQUIRED
    ctx_missing = _make_context(face_detected=False)
    mgr._calibrated_absence_start_time = time.time() - 11.0
    mgr.evaluate_runtime_frame(ctx_missing)
    assert mgr.status == "RECALIBRATION_REQUIRED"
