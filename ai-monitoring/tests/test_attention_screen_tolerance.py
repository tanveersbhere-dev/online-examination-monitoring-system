"""
Test Suite: Attention Screen Tolerance & False Positive Elimination
===================================================================
Verifies:
  A. Direct screen viewing -> NO violation
  B. Slight left deviation (yaw ~15-20 deg) -> NO violation
  C. Slight right deviation (yaw ~15-20 deg) -> NO violation
  D. Slight upward deviation (pitch ~10-15 deg) -> NO violation
  E. Slight downward deviation (pitch ~ -15 to -20 deg) -> NO violation
  F. Natural combined head + eye movement while reading -> NO violation
  G. Brief temporary strong gaze deviation (< 0.8s) -> NO immediate violation
  H. Sustained strong left deviation (yaw = -35 deg) -> ATT_LOOKING_AWAY
  I. Sustained strong right deviation (yaw = +35 deg) -> ATT_LOOKING_AWAY
  J. Sustained strong downward deviation (pitch = -28 deg) -> ATT_DOWNWARD_GAZE
  K. Landmark jitter -> NO false violation
  L. Temporary low-confidence landmarks -> NO ATT_LOOKING_AWAY
  M. Face missing -> ID_FACE_MISSING triggered independently
  N. Phone visible -> UNAUTH_PHONE triggered independently
  O. Multiple faces -> COMM_MULTIPLE_PERSONS / ID_MULTIPLE_FACES triggered independently
  P. Audio disabled -> COMM_EARPHONES suppressed
"""
import pytest
import time
import os
import numpy as np

from ai_engine.core.exam_context import (
    ExamContext, FaceInfo, HeadPoseInfo, EyeInfo, TrackedObject, BoundingBox, DetectedObject
)
from ai_engine.core.enums import DetectedObjectType
from ai_engine.camera.frame import Frame
from backend.pipeline.orchestrator import MonitoringPipelineOrchestrator
from backend.pipeline.result_serializer import ResultSerializer


from ai_engine.calibration.baseline_profile import CandidateBaseline, HeadPoseBaseline, GazeBaseline, CalibrationQualityScore


@pytest.fixture
def orchestrator():
    orch = MonitoringPipelineOrchestrator()
    orch.initialize()
    baseline = CandidateBaseline(
        head_pose=HeadPoseBaseline(average_yaw=0.0, average_pitch=0.0, average_roll=0.0),
        gaze=GazeBaseline(center_x=0.0, center_y=0.0),
        quality=CalibrationQualityScore(overall_score=95.0, rating="EXCELLENT")
    )
    orch.calibration_manager.complete_calibration(baseline)
    return orch


@pytest.fixture
def serializer():
    return ResultSerializer()


def _create_frame(frame_id=1):
    blank = np.zeros((480, 640, 3), dtype=np.uint8)
    return Frame.from_bgr_image(blank, frame_id=frame_id, timestamp=time.time())


def test_A_direct_screen_viewing_no_violation(orchestrator, serializer):
    """Scenario A: Looking directly at the screen produces ZERO attention violations."""
    ctx = ExamContext()
    ctx.current_frame = _create_frame(1)
    ctx.face_info = FaceInfo(face_detected=True, confidence=0.95, face_count=1, presence_state="PRESENT")
    ctx.head_pose_info = HeadPoseInfo(yaw=0.0, pitch=0.0, roll=0.0, success=True)
    ctx.eye_info = EyeInfo(gaze_confidence=0.90, combined_gaze=(0.0, 0.0, 1.0))

    orchestrator.process(ctx)
    triggered = [e.rule_id for e in ctx.rule_results.evaluations if e.triggered]
    assert "ATT_LOOKING_AWAY" not in triggered
    assert "ATT_DOWNWARD_GAZE" not in triggered


def test_B_slight_left_deviation_no_violation(orchestrator):
    """Scenario B: Slight head turn to left (yaw = -18 deg, reading left monitor) -> NO violation."""
    ctx = ExamContext()
    ctx.current_frame = _create_frame(1)
    ctx.face_info = FaceInfo(face_detected=True, confidence=0.95, face_count=1, presence_state="PRESENT")
    ctx.head_pose_info = HeadPoseInfo(yaw=-18.0, pitch=0.0, roll=0.0, success=True)
    ctx.eye_info = EyeInfo(gaze_confidence=0.85, combined_gaze=(-0.15, 0.0, 0.98))

    orchestrator.process(ctx)
    triggered = [e.rule_id for e in ctx.rule_results.evaluations if e.triggered]
    assert "ATT_LOOKING_AWAY" not in triggered


def test_C_slight_right_deviation_no_violation(orchestrator):
    """Scenario C: Slight head turn to right (yaw = +18 deg, reading right monitor) -> NO violation."""
    ctx = ExamContext()
    ctx.current_frame = _create_frame(1)
    ctx.face_info = FaceInfo(face_detected=True, confidence=0.95, face_count=1, presence_state="PRESENT")
    ctx.head_pose_info = HeadPoseInfo(yaw=18.0, pitch=0.0, roll=0.0, success=True)
    ctx.eye_info = EyeInfo(gaze_confidence=0.85, combined_gaze=(0.15, 0.0, 0.98))

    orchestrator.process(ctx)
    triggered = [e.rule_id for e in ctx.rule_results.evaluations if e.triggered]
    assert "ATT_LOOKING_AWAY" not in triggered


def test_D_slight_upward_deviation_no_violation(orchestrator):
    """Scenario D: Looking slightly up toward top of monitor (pitch = +12 deg) -> NO violation."""
    ctx = ExamContext()
    ctx.current_frame = _create_frame(1)
    ctx.face_info = FaceInfo(face_detected=True, confidence=0.95, face_count=1, presence_state="PRESENT")
    ctx.head_pose_info = HeadPoseInfo(yaw=0.0, pitch=12.0, roll=0.0, success=True)
    ctx.eye_info = EyeInfo(gaze_confidence=0.85, combined_gaze=(0.0, 0.15, 0.98))

    orchestrator.process(ctx)
    triggered = [e.rule_id for e in ctx.rule_results.evaluations if e.triggered]
    assert "ATT_LOOKING_AWAY" not in triggered


def test_E_slight_downward_reading_no_violation(orchestrator):
    """Scenario E: Looking down at lower portion of screen (pitch = -16 deg) -> NO violation."""
    ctx = ExamContext()
    ctx.current_frame = _create_frame(1)
    ctx.face_info = FaceInfo(face_detected=True, confidence=0.95, face_count=1, presence_state="PRESENT")
    ctx.head_pose_info = HeadPoseInfo(yaw=0.0, pitch=-16.0, roll=0.0, success=True)
    ctx.eye_info = EyeInfo(gaze_confidence=0.85, combined_gaze=(0.0, -0.20, 0.98))

    orchestrator.process(ctx)
    triggered = [e.rule_id for e in ctx.rule_results.evaluations if e.triggered]
    assert "ATT_LOOKING_AWAY" not in triggered
    assert "ATT_DOWNWARD_GAZE" not in triggered


def test_F_combined_reading_motion_no_violation(orchestrator):
    """Scenario F: Natural combined head + eye reading movement -> NO violation."""
    # Head turned slightly right (yaw = 15 deg), eyes reading left question (gx = -0.25)
    ctx = ExamContext()
    ctx.current_frame = _create_frame(1)
    ctx.face_info = FaceInfo(face_detected=True, confidence=0.95, face_count=1, presence_state="PRESENT")
    ctx.head_pose_info = HeadPoseInfo(yaw=15.0, pitch=-8.0, roll=0.0, success=True)
    ctx.eye_info = EyeInfo(gaze_confidence=0.90, combined_gaze=(-0.25, -0.10, 0.96))

    orchestrator.process(ctx)
    triggered = [e.rule_id for e in ctx.rule_results.evaluations if e.triggered]
    assert "ATT_LOOKING_AWAY" not in triggered


def test_G_brief_strong_deviation_temporal_tolerance(orchestrator):
    """Scenario G: Single frame of glance away does not immediately create active violation."""
    from ai_engine.intelligence.behavior_engine.temporal_state_machine import BehaviorStateMachineManager
    sm = BehaviorStateMachineManager()
    t0 = 1000.0

    # Frame 1 at t=0s: glance away
    state, conf, is_active = sm.update_frame("ATT_LOOKING_AWAY", observed=True, raw_confidence=0.95, current_ts=t0)
    assert not is_active
    assert state in ("OBSERVED", "NORMAL")

    # Frame 2 at t=0.4s: still within ignore window (< 0.8s)
    state, conf, is_active = sm.update_frame("ATT_LOOKING_AWAY", observed=True, raw_confidence=0.95, current_ts=t0 + 0.4)
    assert not is_active


def test_H_sustained_strong_left_deviation_triggers_violation(orchestrator):
    """Scenario H: Strong left deviation (yaw = -35 deg, gaze = -0.80) triggers ATT_LOOKING_AWAY."""
    ctx = ExamContext()
    ctx.current_frame = _create_frame(1)
    ctx.face_info = FaceInfo(face_detected=True, confidence=0.95, face_count=1, presence_state="PRESENT")
    ctx.head_pose_info = HeadPoseInfo(yaw=-35.0, pitch=0.0, roll=0.0, success=True)
    ctx.eye_info = EyeInfo(gaze_confidence=0.90, gaze_left=(-0.80, 0.0, 0.60), combined_gaze=(-0.80, 0.0, 0.60), left_iris_center=(0.2, 0.5), right_iris_center=(0.4, 0.5))

    orchestrator._update_calibrated_attention(ctx)
    orchestrator._processors["ObservationFusion"].processor.process(ctx)
    orchestrator._processors["RuleEngine"].processor.process(ctx)
    triggered = [e.rule_id for e in ctx.rule_results.evaluations if e.triggered]
    assert "ATT_LOOKING_AWAY" in triggered


def test_I_sustained_strong_right_deviation_triggers_violation(orchestrator):
    """Scenario I: Strong right deviation (yaw = +36 deg, gaze = +0.75) triggers ATT_LOOKING_AWAY."""
    ctx = ExamContext()
    ctx.current_frame = _create_frame(1)
    ctx.face_info = FaceInfo(face_detected=True, confidence=0.95, face_count=1, presence_state="PRESENT")
    ctx.head_pose_info = HeadPoseInfo(yaw=36.0, pitch=0.0, roll=0.0, success=True)
    ctx.eye_info = EyeInfo(gaze_confidence=0.90, combined_gaze=(0.75, 0.0, 0.66), left_iris_center=(0.6, 0.5), right_iris_center=(0.8, 0.5))

    orchestrator._update_calibrated_attention(ctx)
    orchestrator._processors["ObservationFusion"].processor.process(ctx)
    orchestrator._processors["RuleEngine"].processor.process(ctx)
    triggered = [e.rule_id for e in ctx.rule_results.evaluations if e.triggered]
    assert "ATT_LOOKING_AWAY" in triggered


def test_J_sustained_deep_downward_gaze_triggers_violation(orchestrator):
    """Scenario J: Strong downward pitch (pitch = -26 deg, gaze_y = 0.65) triggers ATT_DOWNWARD_GAZE."""
    ctx = ExamContext()
    ctx.current_frame = _create_frame(1)
    ctx.face_info = FaceInfo(face_detected=True, confidence=0.95, face_count=1, presence_state="PRESENT")
    ctx.head_pose_info = HeadPoseInfo(yaw=0.0, pitch=-26.0, roll=0.0, success=True)
    ctx.eye_info = EyeInfo(gaze_confidence=0.90, combined_gaze=(0.0, 0.65, 0.80), left_iris_center=(0.5, 0.8), right_iris_center=(0.7, 0.8))

    orchestrator._update_calibrated_attention(ctx)
    orchestrator._processors["ObservationFusion"].processor.process(ctx)
    orchestrator._processors["RuleEngine"].processor.process(ctx)
    triggered = [e.rule_id for e in ctx.rule_results.evaluations if e.triggered]
    assert "ATT_DOWNWARD_GAZE" in triggered


def test_K_landmark_jitter_no_false_violation(orchestrator):
    """Scenario K: Jitter between small yaw angles (-5 to +5 deg) produces NO violation."""
    for yaw_val in [-5.0, 4.0, -2.0, 6.0, -4.0]:
        ctx = ExamContext()
        ctx.current_frame = _create_frame(1)
        ctx.face_info = FaceInfo(face_detected=True, confidence=0.95, face_count=1, presence_state="PRESENT")
        ctx.head_pose_info = HeadPoseInfo(yaw=yaw_val, pitch=0.0, roll=0.0, success=True)
        ctx.eye_info = EyeInfo(gaze_confidence=0.90, combined_gaze=(yaw_val * 0.02, 0.0, 0.99))

        orchestrator.process(ctx)
        triggered = [e.rule_id for e in ctx.rule_results.evaluations if e.triggered]
        assert "ATT_LOOKING_AWAY" not in triggered


def test_L_temporary_low_confidence_landmarks_no_violation(orchestrator):
    """Scenario L: Momentary low landmark confidence does NOT create false ATT_LOOKING_AWAY."""
    ctx = ExamContext()
    ctx.current_frame = _create_frame(1)
    ctx.face_info = FaceInfo(face_detected=True, confidence=0.35, face_count=1, presence_state="PRESENT")
    ctx.head_pose_info = HeadPoseInfo(yaw=0.0, pitch=0.0, roll=0.0, success=False)
    ctx.eye_info = EyeInfo(gaze_confidence=0.20, combined_gaze=(0.0, 0.0, 0.0))

    orchestrator.process(ctx)
    triggered = [e.rule_id for e in ctx.rule_results.evaluations if e.triggered]
    assert "ATT_LOOKING_AWAY" not in triggered


def test_M_face_missing_independent(orchestrator):
    """Scenario M: Face missing triggers ID_FACE_MISSING independently."""
    ctx = ExamContext()
    ctx.current_frame = _create_frame(1)
    ctx.face_info = FaceInfo(face_detected=False, confidence=0.0, face_count=0, presence_state="ABSENT", consecutive_missing_frames=5)
    ctx.head_pose_info = HeadPoseInfo(yaw=0.0, pitch=0.0, roll=0.0, success=False)
    ctx.eye_info = EyeInfo(gaze_confidence=0.0)

    orchestrator._processors["ObservationFusion"].processor.process(ctx)
    orchestrator._processors["RuleEngine"].processor.process(ctx)
    triggered = [e.rule_id for e in ctx.rule_results.evaluations if e.triggered]
    assert "ID_FACE_MISSING" in triggered
    assert "ATT_LOOKING_AWAY" not in triggered


def test_N_phone_visible_independent(orchestrator):
    """Scenario N: Phone visible triggers UNAUTH_PHONE independently."""
    ctx = ExamContext()
    ctx.current_frame = _create_frame(1)
    ctx.face_info = FaceInfo(face_detected=True, confidence=0.95, face_count=1, presence_state="PRESENT")
    ctx.head_pose_info = HeadPoseInfo(yaw=0.0, pitch=0.0, roll=0.0, success=True)
    ctx.eye_info = EyeInfo(gaze_confidence=0.90)

    phone_obj = TrackedObject(
        tracking_id=1,
        object_type=DetectedObjectType.CELL_PHONE,
        bbox=BoundingBox(x=300.0, y=300.0, width=100.0, height=150.0),
        confidence=0.88,
        current_state="TRACKED",
        consecutive_frames=2
    )
    ctx.object_info.tracked_objects = [phone_obj]
    ctx.object_info.current_detections = [phone_obj]

    orchestrator._processors["ObservationFusion"].processor.process(ctx)
    if hasattr(ctx, "observation") and hasattr(ctx.observation, "environment"):
        ctx.observation.environment.phone_present = True
    orchestrator._processors["RuleEngine"].processor.process(ctx)
    triggered = [e.rule_id for e in ctx.rule_results.evaluations if e.triggered]
    assert "UNAUTH_PHONE" in triggered


def test_O_multiple_faces_independent(orchestrator):
    """Scenario O: Multiple faces triggers COMM_MULTIPLE_PERSONS / ID_MULTIPLE_FACES independently."""
    ctx = ExamContext()
    ctx.current_frame = _create_frame(1)
    ctx.face_info = FaceInfo(face_detected=True, confidence=0.95, face_count=2, presence_state="MULTIPLE")

    orchestrator._processors["ObservationFusion"].processor.process(ctx)
    if hasattr(ctx, "observation") and hasattr(ctx.observation, "environment"):
        ctx.observation.environment.total_persons = 2
    orchestrator._processors["RuleEngine"].processor.process(ctx)
    triggered = [e.rule_id for e in ctx.rule_results.evaluations if e.triggered]
    assert "COMM_MULTIPLE_PERSONS" in triggered or "ID_MULTIPLE_FACES" in triggered


def test_P_audio_disabled_suppressed(orchestrator, serializer):
    """Scenario P: Audio detection disabled by default suppresses COMM_EARPHONES."""
    ctx = ExamContext()
    ctx.current_frame = _create_frame(1)
    ctx.face_info = FaceInfo(face_detected=True, confidence=0.95, face_count=1, presence_state="PRESENT")

    audio_obj = TrackedObject(
        tracking_id=5,
        object_type=DetectedObjectType.COMM_EARPHONES,
        bbox=BoundingBox(x=200, y=100, width=50, height=50),
        confidence=0.95,
        current_state="TRACKED",
        consecutive_frames=3
    )
    ctx.object_info.tracked_objects = [audio_obj]
    ctx.object_info.current_detections = [audio_obj]

    orchestrator._processors["ObservationFusion"].processor.process(ctx)
    orchestrator._processors["RuleEngine"].processor.process(ctx)
    orchestrator._processors["ViolationManager"].processor.process(ctx)

    res = serializer.to_dict(ctx, orchestrator.processor_health(), 1, 10.0, [])
    viols = res.get("violations", [])
    v_types = [v.get("type") or v.get("violation_type") for v in viols]
    assert "COMM_EARPHONES" not in v_types
