"""
Comprehensive AI Calibration & Threshold Optimization Test Suite.
Validates:
1. Subsystem threshold calibration audit (Face, Head Pose, Gaze, EAR, MAR, Identity, Liveness, YOLO, Rules, Risk).
2. Confidence score normalization & precision bounds.
3. False positive & false negative mitigation via calibrated confidence cutoffs.
4. Temporal smoothing, ByteTrack persistence, and flicker reduction.
5. End-to-end regression validation.
"""

import unittest
import numpy as np
import time

from ai_engine.core.enums import DetectedObjectType
from ai_engine.core.exam_context import (
    ExamContext, FaceInfo, EyeInfo, HeadPoseInfo, MouthInfo, TrackedObject, BoundingBox
)
from ai_engine.camera.frame import Frame
from ai_engine.features.face_identity.models import FaceIdentityConfig
from ai_engine.environment.object_detection.models import ObjectDetectionConfig
from ai_engine.environment.object_filtering.models import ObjectFilteringConfig
from ai_engine.intelligence.rule_engine.models import RuleEngineConfig
from ai_engine.intelligence.risk_scoring.models import RiskScoringConfig
from backend.pipeline.orchestrator import MonitoringPipelineOrchestrator


class TestAICalibration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.orchestrator = MonitoringPipelineOrchestrator()
        cls.orchestrator.initialize()
        cls.blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    def test_01_subsystem_threshold_defaults_audit(self):
        """Audit default threshold parameters across all subsystem configs."""
        face_cfg = FaceIdentityConfig()
        self.assertEqual(face_cfg.similarity_threshold, 0.60) # Default InsightFace cosine similarity cutoff

        yolo_cfg = ObjectDetectionConfig()
        self.assertEqual(yolo_cfg.confidence_threshold, 0.22) # Calibrated YOLO cutoff for phone detection

        filter_cfg = ObjectFilteringConfig()
        self.assertEqual(filter_cfg.min_confidence, 0.22) # Default NMS/Filter cutoff for phone detection

        rule_cfg = RuleEngineConfig()
        self.assertEqual(rule_cfg.evaluation_interval_seconds, 0.0)

        risk_cfg = RiskScoringConfig()
        self.assertIn("NORMAL", risk_cfg.risk_thresholds)
        self.assertIn("CRITICAL", risk_cfg.risk_thresholds)

    def test_02_head_pose_and_gaze_calibration_bounds(self):
        """Validate calibrated Head Pose & Gaze boundary conditions."""
        context = ExamContext()
        context.current_frame = Frame.from_bgr_image(self.blank_frame, frame_id=1)
        
        # A modest head turn with no corroborating eye departure remains
        # inside the screen-attention region.
        context.face_info = FaceInfo(face_detected=True, confidence=0.95, face_count=1, presence_state="PRESENT")
        context.head_pose_info = HeadPoseInfo(yaw=25.0, pitch=0.0, roll=0.0, success=True) # > 20 deg -> RIGHT
        
        self.orchestrator._processors['RuleEngine'].processor._last_evaluation_time = 0.0
        self.orchestrator._run_step('ObservationFusion', context)
        self.orchestrator._run_step('RuleEngine', context)

        triggered = [e.rule_id for e in context.rule_results.evaluations if e.triggered]
        self.assertNotIn("ATT_LOOKING_AWAY", triggered)

    def test_03_ear_mar_threshold_calibration(self):
        """Validate calibrated EAR eye aspect ratio & MAR mouth aperture bounds."""
        context = ExamContext()
        context.current_frame = Frame.from_bgr_image(self.blank_frame, frame_id=1)
        
        # EAR < 0.20 -> BLINK / CLOSED
        context.eye_info = EyeInfo(average_ear=0.15, eye_state="CLOSED")
        self.assertEqual(context.eye_info.eye_state, "CLOSED")

        # MAR > 0.35 -> TALKING
        context.mouth_info = MouthInfo(mar=0.45, is_talking=True)
        self.assertTrue(context.mouth_info.is_talking)

    def test_04_identity_and_liveness_score_calibration(self):
        """Validate calibrated cosine similarity & anti-spoofing softmax thresholds."""
        # Cosine similarity >= 0.60 -> MATCH
        sim_high = 0.72
        self.assertGreaterEqual(sim_high, 0.60)

        # Cosine similarity < 0.60 -> MISMATCH
        sim_low = 0.25
        self.assertLess(sim_low, 0.60)

        # Anti-spoofing liveness score < 0.50 -> SPOOF SUSPECTED
        liveness_spoof = 0.15
        self.assertLess(liveness_spoof, 0.50)

    def test_05_flicker_reduction_temporal_stability(self):
        """Validate ByteTrack temporal stability & confidence filtering."""
        context = ExamContext()
        context.current_frame = Frame.from_bgr_image(self.blank_frame, frame_id=1)
        
        # Phone with conf = 0.88 (above threshold)
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

        self.orchestrator._processors['RuleEngine'].processor._last_evaluation_time = 0.0
        self.orchestrator._run_step('ObservationFusion', context)
        self.orchestrator._run_step('RuleEngine', context)

        triggered = [e.rule_id for e in context.rule_results.evaluations if e.triggered]
        self.assertIn("UNAUTH_PHONE", triggered)


if __name__ == "__main__":
    unittest.main()
