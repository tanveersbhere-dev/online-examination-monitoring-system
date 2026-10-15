"""
Comprehensive Test Suite for Phase 4 — Adaptive Calibration Engine.
"""
import unittest
import time
import numpy as np

from ai_engine.core.exam_context import ExamContext, FaceInfo, HeadPoseInfo, EyeInfo, TrackedObject, BoundingBox
from ai_engine.core.enums import DetectedObjectType
from ai_engine.camera.frame import Frame
from ai_engine.calibration.baseline_profile import CandidateBaseline, HeadPoseBaseline, CalibrationQualityScore
from ai_engine.calibration.calibration_metrics import CalibrationMetricsAccumulator
from ai_engine.calibration.calibration_engine import CalibrationEngineProcessor
from ai_engine.calibration.calibration_manager import CalibrationManager
from backend.pipeline.orchestrator import MonitoringPipelineOrchestrator

class TestAdaptiveCalibration(unittest.TestCase):

    def setUp(self):
        self.orchestrator = MonitoringPipelineOrchestrator()
        self.orchestrator.initialize()
        self.blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    def test_01_metrics_accumulator_and_baseline_creation(self):
        """Test accumulation of calibration metrics and creation of CandidateBaseline profile."""
        acc = CalibrationMetricsAccumulator()
        img = np.ones((480, 640, 3), dtype=np.uint8) * 120

        # Simulate 50 frames with candidate sitting naturally at yaw=12 deg
        for _ in range(50):
            acc.add_frame(
                face_detected=True,
                face_confidence=0.95,
                bbox=[200, 100, 240, 240],
                yaw=12.0,
                pitch=2.0,
                roll=0.0,
                gaze_vector=[0.0, 0.0],
                ear=0.28,
                bgr_frame=img
            )

        baseline = acc.compute_baseline(timestamp=time.time())
        self.assertIsInstance(baseline, CandidateBaseline)
        self.assertAlmostEqual(baseline.head_pose.average_yaw, 12.0, delta=0.5)
        self.assertEqual(baseline.quality.rating, "EXCELLENT")
        self.assertGreaterEqual(baseline.quality.overall_score, 80.0)

    def test_02_severe_event_abort_during_calibration(self):
        """Test that severe events (prohibited object, multiple faces) abort calibration."""
        engine = CalibrationEngineProcessor(calibration_duration_seconds=30.0)
        engine.initialize()

        context = ExamContext()
        context.current_frame = Frame.from_bgr_image(self.blank_frame, frame_id=1)
        context.face_info = FaceInfo(face_detected=True, confidence=0.95, face_count=1)

        # Inject phone object
        phone = TrackedObject(
            tracking_id=1, object_type=DetectedObjectType.CELL_PHONE,
            bbox=BoundingBox(x=100, y=100, width=50, height=50), confidence=0.88,
            current_state="TRACKED", first_detection_timestamp=time.time(),
            last_detection_timestamp=time.time(), visible_duration=1.0,
            consecutive_frames=1, lost_frames=0, motion_status="STATIONARY"
        )
        obj_info = context.object_info
        obj_info.tracked_objects = [phone]
        context.object_info = obj_info

        engine.process(context)
        self.assertIsNotNone(engine.aborted_reason)
        self.assertIn("Prohibited object", engine.aborted_reason)

    def test_03_adaptive_threshold_false_positive_reduction(self):
        """Test that candidate naturally at yaw=12 deg does NOT trigger ATT_LOOKING_AWAY when calibrated."""
        manager = CalibrationManager()
        baseline = CandidateBaseline(
            head_pose=HeadPoseBaseline(average_yaw=12.0, average_pitch=0.0, average_roll=0.0),
            quality=CalibrationQualityScore(overall_score=95.0, rating="EXCELLENT")
        )
        manager.complete_calibration(baseline)

        context = ExamContext()
        context.current_frame = Frame.from_bgr_image(self.blank_frame, frame_id=1)
        context.face_info = FaceInfo(face_detected=True, confidence=0.95, face_count=1, presence_state="PRESENT")
        context.head_pose_info = HeadPoseInfo(yaw=12.0, pitch=0.0, roll=0.0, success=True) # Candidate at baseline

        # Evaluate calibration deltas
        calib_dict = manager.evaluate_runtime_frame(context)
        context.calibration_info = calib_dict

        self.orchestrator._processors['RuleEngine'].processor._last_evaluation_time = 0.0
        self.orchestrator._run_step('ObservationFusion', context)
        self.orchestrator._run_step('RuleEngine', context)

        triggered = [e.rule_id for e in context.rule_results.evaluations if e.triggered]
        # ATT_LOOKING_AWAY should NOT be triggered because candidate is at their natural baseline
        self.assertNotIn("ATT_LOOKING_AWAY", triggered)

    def test_04_drift_adaptation_ema(self):
        """Test slow posture drift adaptation via EMA vs rejection of sudden movements."""
        manager = CalibrationManager(ema_alpha=0.1)
        baseline = CandidateBaseline(
            head_pose=HeadPoseBaseline(average_yaw=10.0, average_pitch=0.0, average_roll=0.0),
            quality=CalibrationQualityScore(overall_score=90.0, rating="EXCELLENT")
        )
        manager.complete_calibration(baseline)

        context = ExamContext()
        context.current_frame = Frame.from_bgr_image(self.blank_frame, frame_id=1)

        # 1. Slow drift: Candidate posture slightly moves to yaw=12.0 deg (within 8 deg delta)
        context.face_info = FaceInfo(face_detected=True, confidence=0.95, face_count=1, presence_state="PRESENT")
        context.head_pose_info = HeadPoseInfo(yaw=12.0, pitch=0.0, roll=0.0, success=True)

        manager.evaluate_runtime_frame(context)
        # Baseline average yaw should slowly adapt towards 12.0 via EMA
        self.assertGreater(manager.baseline.head_pose.average_yaw, 10.0)

        # 2. Sudden large turn: Yaw jumps to 35.0 deg (> 8 deg delta)
        context.head_pose_info = HeadPoseInfo(yaw=35.0, pitch=0.0, roll=0.0, success=True)
        prev_avg = manager.baseline.head_pose.average_yaw

        manager.evaluate_runtime_frame(context)
        # Baseline average yaw should NOT adapt for sudden large turn
        self.assertEqual(manager.baseline.head_pose.average_yaw, prev_avg)

    def test_05_reset_conditions(self):
        """Test reset triggers on candidate identity mismatch or extended tracking loss."""
        manager = CalibrationManager()
        baseline = CandidateBaseline(quality=CalibrationQualityScore(overall_score=90.0, rating="EXCELLENT"))
        manager.complete_calibration(baseline)

        context = ExamContext()
        context.current_frame = Frame.from_bgr_image(self.blank_frame, frame_id=1)

        # Identity mismatch with enrolled profile
        context.face_info = FaceInfo(
            face_detected=True,
            confidence=0.95,
            reference_embedding=[0.1] * 512,
            identity_consistent=False
        )
        manager.evaluate_runtime_frame(context)

        self.assertEqual(manager.status, "RECALIBRATION_REQUIRED")

        # Reset manager and test continuous face loss
        manager.complete_calibration(baseline)
        context.face_info = FaceInfo(face_detected=False, presence_state="MISSING")
        manager._calibrated_absence_start_time = time.time() - 11.0
        manager.evaluate_runtime_frame(context)
        self.assertEqual(manager.status, "RECALIBRATION_REQUIRED")

if __name__ == "__main__":
    unittest.main()
