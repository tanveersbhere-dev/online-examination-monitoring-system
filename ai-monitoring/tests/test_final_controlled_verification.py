import time
import pytest
import numpy as np
from typing import List

from ai_engine.core.exam_context import (
    ExamContext, FaceInfo, HeadPoseInfo, EyeInfo, ObjectInfo, BoundingBox, TrackedObject
)
from ai_engine.core.enums import DetectedObjectType
from ai_engine.camera.frame import Frame
from ai_engine.calibration.calibration_engine import CalibrationEngineProcessor
from ai_engine.calibration.calibration_manager import CalibrationManager
from ai_engine.calibration.baseline_profile import CandidateBaseline
from ai_engine.intelligence.behavior_engine.composite_behavior import format_composite_incident_title
from backend.pipeline.orchestrator import MonitoringPipelineOrchestrator


def test_A_calibration_full_accumulation_and_formats():
    """Verify calibration reaches 100% with both BoundingBox dataclass and tuple formats, and LAPTOP does not abort."""
    manager = CalibrationManager()
    engine = CalibrationEngineProcessor(
        target_samples=30,
        warmup_duration_seconds=0.1,
        calibration_duration_seconds=30.0
    )
    engine.initialize()
    manager.start_calibration()
    engine.start_time = time.time() - 4.0  # warmup + duration passed

    # 1. Feed frames alternating between BoundingBox dataclass and tuple bbox
    for i in range(1, 31):
        ctx = ExamContext()
        ctx.current_frame = Frame.from_bgr_image(np.zeros((480, 640, 3), dtype=np.uint8), frame_id=i)
        bbox = BoundingBox(200.0, 100.0, 240.0, 240.0) if i % 2 == 0 else (200.0, 100.0, 240.0, 240.0)
        
        ctx.face_info = FaceInfo(
            face_detected=True,
            confidence=0.95,
            bbox=bbox,
            face_count=1,
            presence_state="PRESENT"
        )
        ctx.head_pose_info = HeadPoseInfo(yaw=0.5, pitch=-1.0, roll=0.0, success=True)
        ctx.eye_info = EyeInfo(
            combined_gaze=(0.02, -0.01, 1.0),
            average_ear=0.28,
            gaze_confidence=0.92,
            left_iris_center=(0.4, 0.4),
            right_iris_center=(0.6, 0.4),
            blink_detected=False
        )
        # Inject LAPTOP into tracked objects: must NOT abort
        laptop_obj = TrackedObject(
            tracking_id=1, object_type=DetectedObjectType.LAPTOP,
            bbox=BoundingBox(10, 10, 100, 100), confidence=0.85
        )
        ctx.object_info = ObjectInfo(current_detections=[], filtered_detections=[], tracked_objects=[laptop_obj])

        engine.process(ctx)
        manager.update_auto_progress(
            stage=engine.stage,
            progress_pct=engine.progress_percentage,
            valid_samples=engine.valid_samples,
            target_samples=engine.target_samples
        )
        if engine.is_completed:
            manager.complete_calibration(engine.finalize_baseline())

    assert engine.aborted_reason is None, f"Calibration aborted unexpectedly: {engine.aborted_reason}"
    assert engine.valid_samples == 30, f"Expected 30 samples, got {engine.valid_samples}"
    assert engine.is_completed is True, "Calibration failed to complete"
    assert manager.status == "CALIBRATED", f"Expected CALIBRATED, got {manager.status}"
    assert manager.baseline is not None, "Baseline is missing"


def test_A_calibration_safety_abort_on_cell_phone():
    """Verify that CELL_PHONE still safely aborts calibration as intended."""
    engine = CalibrationEngineProcessor(target_samples=30, warmup_duration_seconds=0.0)
    engine.initialize()
    ctx = ExamContext()
    ctx.current_frame = Frame.from_bgr_image(np.zeros((480, 640, 3), dtype=np.uint8), frame_id=1)
    ctx.face_info = FaceInfo(face_detected=True, confidence=0.95, bbox=(200, 100, 240, 240), face_count=1)
    
    phone_obj = TrackedObject(
        tracking_id=2, object_type=DetectedObjectType.CELL_PHONE,
        bbox=BoundingBox(10, 10, 50, 50), confidence=0.90
    )
    ctx.object_info = ObjectInfo(current_detections=[], filtered_detections=[], tracked_objects=[phone_obj])
    
    engine.process(ctx)
    assert engine.aborted_reason is not None
    assert "Prohibited object 'CELL_PHONE'" in engine.aborted_reason


def test_B_off_screen_attention_lifecycle():
    """Verify normal gaze, left/right looking away, and downward gaze once calibrated."""
    orch = MonitoringPipelineOrchestrator()
    orch.initialize()
    orch.start()

    manager = orch._calibration_manager
    engine = orch._calibration_engine
    orch.start_calibration()
    engine.start_time = time.time() - 5.0

    # Calibrate with 30 valid frames
    for i in range(1, 31):
        ctx = ExamContext()
        ctx.current_frame = Frame.from_bgr_image(np.zeros((480, 640, 3), dtype=np.uint8), frame_id=i)
        ctx.face_info = FaceInfo(face_detected=True, confidence=0.95, bbox=(200, 100, 240, 240), face_count=1, presence_state="PRESENT")
        ctx.head_pose_info = HeadPoseInfo(yaw=0.0, pitch=0.0, roll=0.0, success=True)
        ctx.eye_info = EyeInfo(combined_gaze=(0.0, 0.0, 1.0), average_ear=0.28, gaze_confidence=0.95, left_iris_center=(0.4, 0.4), right_iris_center=(0.6, 0.4), blink_detected=False)
        ctx.object_info = ObjectInfo()
        orch._update_calibrated_attention(ctx)

    assert manager.status == "CALIBRATED"

    # Scenario 1: Normal on-screen
    ctx_normal = ExamContext()
    ctx_normal.current_frame = Frame.from_bgr_image(np.zeros((480, 640, 3), dtype=np.uint8), frame_id=31)
    ctx_normal.face_info = FaceInfo(face_detected=True, confidence=0.95, bbox=(200, 100, 240, 240), face_count=1, presence_state="PRESENT")
    ctx_normal.head_pose_info = HeadPoseInfo(yaw=0.0, pitch=0.0, roll=0.0, success=True)
    ctx_normal.eye_info = EyeInfo(combined_gaze=(0.01, 0.01, 1.0), average_ear=0.28, gaze_confidence=0.95, left_iris_center=(0.4, 0.4), right_iris_center=(0.6, 0.4), blink_detected=False)
    ctx_normal.object_info = ObjectInfo()
    orch._update_calibrated_attention(ctx_normal)
    orch._processors['RuleEngine'].processor._last_evaluation_time = 0.0
    orch._run_step('ObservationFusion', ctx_normal)
    orch._run_step('RuleEngine', ctx_normal)
    trig_normal = [e.rule_id for e in ctx_normal.rule_results.evaluations if e.triggered]
    assert "ATT_LOOKING_AWAY" not in trig_normal
    assert "ATT_DOWNWARD_GAZE" not in trig_normal

    # Scenario 2: Strong left deviation
    ctx_left = ExamContext()
    ctx_left.current_frame = Frame.from_bgr_image(np.zeros((480, 640, 3), dtype=np.uint8), frame_id=32)
    ctx_left.face_info = FaceInfo(face_detected=True, confidence=0.95, bbox=(200, 100, 240, 240), face_count=1, presence_state="PRESENT")
    ctx_left.head_pose_info = HeadPoseInfo(yaw=-25.0, pitch=0.0, roll=0.0, success=True)
    ctx_left.eye_info = EyeInfo(combined_gaze=(-0.65, 0.0, 1.0), average_ear=0.28, gaze_confidence=0.95, left_iris_center=(0.4, 0.4), right_iris_center=(0.6, 0.4), blink_detected=False)
    ctx_left.object_info = ObjectInfo()
    orch._update_calibrated_attention(ctx_left)
    orch._processors['RuleEngine'].processor._last_evaluation_time = 0.0
    orch._run_step('ObservationFusion', ctx_left)
    orch._run_step('RuleEngine', ctx_left)
    trig_left = [e.rule_id for e in ctx_left.rule_results.evaluations if e.triggered]
    assert "ATT_LOOKING_AWAY" in trig_left

    # Scenario 3: Strong downward deviation
    ctx_down = ExamContext()
    ctx_down.current_frame = Frame.from_bgr_image(np.zeros((480, 640, 3), dtype=np.uint8), frame_id=33)
    ctx_down.face_info = FaceInfo(face_detected=True, confidence=0.95, bbox=(200, 100, 240, 240), face_count=1, presence_state="PRESENT")
    ctx_down.head_pose_info = HeadPoseInfo(yaw=0.0, pitch=-22.0, roll=0.0, success=True)
    ctx_down.eye_info = EyeInfo(combined_gaze=(0.0, 0.55, 1.0), average_ear=0.28, gaze_confidence=0.95, left_iris_center=(0.4, 0.4), right_iris_center=(0.6, 0.4), blink_detected=False)
    ctx_down.object_info = ObjectInfo()
    orch._update_calibrated_attention(ctx_down)
    orch._processors['RuleEngine'].processor._last_evaluation_time = 0.0
    orch._run_step('ObservationFusion', ctx_down)
    orch._run_step('RuleEngine', ctx_down)
    trig_down = [e.rule_id for e in ctx_down.rule_results.evaluations if e.triggered]
    assert "ATT_DOWNWARD_GAZE" in trig_down


def test_C_audio_device_only_naming():
    """Verify standalone audio detection is titled 'Unauthorized Audio Device' without mentioning Phone."""
    title = format_composite_incident_title(
        violation_type="COMM_EARPHONES",
        contributing_rules=["COMM_EARPHONES"],
        objects=[{"type": "COMM_EARPHONES", "confidence": 0.90}]
    )
    assert title == "Unauthorized Audio Device"
    assert "Phone" not in title


def test_D_phone_only_naming():
    """Verify phone detection retains standard phone title."""
    title = format_composite_incident_title(
        violation_type="UNAUTH_PHONE",
        contributing_rules=["UNAUTH_PHONE"],
        objects=[{"type": "CELL_PHONE", "confidence": 0.90}]
    )
    assert title == "Unauthorized Cell Phone"


def test_E_simultaneous_phone_and_audio_naming():
    """Verify simultaneous active phone and audio device results in 'Phone + Unauthorized Audio Device'."""
    title = format_composite_incident_title(
        violation_type="COMM_EARPHONES",
        contributing_rules=["UNAUTH_PHONE", "COMM_EARPHONES"],
        objects=[{"type": "CELL_PHONE", "confidence": 0.90}, {"type": "COMM_EARPHONES", "confidence": 0.90}]
    )
    assert title == "Phone + Unauthorized Audio Device"
