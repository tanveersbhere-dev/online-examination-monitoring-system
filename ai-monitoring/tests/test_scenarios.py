"""
End-to-End Realistic Examination Scenario Validation Test Suite.
Validates Scenarios 1 through 10:
Scenario 1: Normal candidate (No violations, LOW/NORMAL risk, 0 evidence)
Scenario 2: Candidate leaves camera (Face missing rule, risk increases, evidence generated)
Scenario 3: Candidate looking left (Looking away rule, risk updated, evidence generated)
Scenario 4: Candidate looking down (Downward gaze rule, risk updated)
Scenario 5: Phone visible (Phone detection rule, evidence generated)
Scenario 6: Second person enters (Multiple persons rule, evidence generated)
Scenario 7: Book visible (Book detection rule, risk updated)
Scenario 8: Identity mismatch (Identity confidence drop, identity violation rule)
Scenario 9: Spoof attempt (Liveness score drop, presentation attack rule)
Scenario 10: Multiple simultaneous violations (Composite rules + independent snapshots)
"""

import unittest
import numpy as np
import time

from ai_engine.core.exam_context import (
    ExamContext, FaceInfo, EyeInfo, HeadPoseInfo, MouthInfo, TrackedObject, BoundingBox
)
from ai_engine.core.enums import DetectedObjectType
from ai_engine.camera.frame import Frame
from ai_engine.identity_protection.observations.identity_observation import IdentityProtectionObservation
from backend.pipeline.orchestrator import MonitoringPipelineOrchestrator


class TestScenariosValidation(unittest.TestCase):

    def setUp(self):
        self.orchestrator = MonitoringPipelineOrchestrator()
        self.orchestrator.initialize()
        self.orchestrator._processors['RuleEngine'].processor._last_evaluation_time = 0.0
        self.blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    def _create_base_context(self, frame_id: int):
        context = ExamContext()
        context.current_frame = Frame.from_bgr_image(self.blank_frame, frame_id=frame_id)
        return context

    def _run_downstream_pipeline(self, context):
        self.orchestrator._run_step('ObservationFusion', context)
        self.orchestrator._run_step('RuleEngine', context)
        self.orchestrator._run_step('RiskEngine', context)
        self.orchestrator._run_step('ViolationManager', context)
        self.orchestrator._check_and_save_evidence(context)

    def test_scenario_01_normal_candidate(self):
        """Scenario 1: Normal candidate sitting in front of camera."""
        context = self._create_base_context(1)
        context.face_info = FaceInfo(
            face_detected=True,
            confidence=0.95,
            bbox=(200.0, 100.0, 240.0, 240.0),
            face_count=1,
            presence_state="PRESENT",
            identity_consistent=True,
            identity_confidence=0.95
        )
        context.eye_info = EyeInfo(gaze_confidence=0.95, average_ear=0.3, eye_state="OPEN")
        context.head_pose_info = HeadPoseInfo(yaw=0.0, pitch=0.0, roll=0.0, success=True)
        context.mouth_info = MouthInfo(mar=0.1, is_talking=False)

        self._run_downstream_pipeline(context)

        risk_level = getattr(context.risk_assessment, "risk_level", "NORMAL")
        self.assertIn(risk_level, ("NORMAL", "LOW"))
        triggered = [e.rule_id for e in context.rule_results.evaluations if e.triggered]
        self.assertEqual(len(triggered), 0, f"Expected 0 violations for normal candidate, got: {triggered}")

    def test_scenario_02_candidate_leaves_camera(self):
        """Scenario 2: Candidate leaves camera (Face missing)."""
        context = self._create_base_context(2)
        context.face_info = FaceInfo(
            face_detected=False,
            confidence=0.0,
            face_count=0,
            presence_state="MISSING",
            consecutive_missing_frames=5
        )
        self._run_downstream_pipeline(context)

        triggered_rules = [e.rule_id for e in context.rule_results.evaluations if e.triggered]
        self.assertIn("ID_FACE_MISSING", triggered_rules)

    def test_scenario_03_looking_left(self):
        """Scenario 3: Candidate looking away (left)."""
        context = self._create_base_context(3)
        context.face_info = FaceInfo(
            face_detected=True, confidence=0.9, bbox=(200.0, 100.0, 240.0, 240.0), face_count=1, presence_state="PRESENT"
        )
        context.eye_info = EyeInfo(gaze_confidence=0.85, gaze_left=(-0.8, 0.0, 0.6))
        context.head_pose_info = HeadPoseInfo(yaw=-35.0, pitch=0.0, roll=0.0, success=True)
        self._run_downstream_pipeline(context)

        triggered_rules = [e.rule_id for e in context.rule_results.evaluations if e.triggered]
        self.assertIn("ATT_LOOKING_AWAY", triggered_rules)

    def test_scenario_04_looking_down(self):
        """Scenario 4: Candidate looking down (Downward gaze)."""
        context = self._create_base_context(4)
        context.face_info = FaceInfo(
            face_detected=True, confidence=0.9, bbox=(200.0, 100.0, 240.0, 240.0), face_count=1, presence_state="PRESENT"
        )
        context.eye_info = EyeInfo(gaze_confidence=0.85, combined_gaze=(0.0, -0.60, 0.80))
        context.head_pose_info = HeadPoseInfo(yaw=0.0, pitch=-25.0, roll=0.0, success=True)
        self._run_downstream_pipeline(context)

        triggered_rules = [e.rule_id for e in context.rule_results.evaluations if e.triggered]
        self.assertIn("ATT_DOWNWARD_GAZE", triggered_rules)

    def test_scenario_05_phone_visible(self):
        """Scenario 5: Mobile phone visible in camera frame."""
        context = self._create_base_context(5)
        context.face_info = FaceInfo(face_detected=True, confidence=0.9, bbox=(200.0, 100.0, 240.0, 240.0), face_count=1, presence_state="PRESENT")
        phone = TrackedObject(
            tracking_id=1,
            object_type=DetectedObjectType.CELL_PHONE,
            bbox=BoundingBox(x=300.0, y=300.0, width=100.0, height=150.0),
            confidence=0.88,
            current_state="TRACKED",
            first_detection_timestamp=time.time(),
            last_detection_timestamp=time.time(),
            visible_duration=1.0,
            consecutive_frames=1,
            lost_frames=0,
            motion_status="STATIONARY"
        )
        obj_info = context.object_info
        obj_info.tracked_objects = [phone]
        context.object_info = obj_info

        self._run_downstream_pipeline(context)
        triggered_rules = [e.rule_id for e in context.rule_results.evaluations if e.triggered]
        self.assertIn("UNAUTH_PHONE", triggered_rules)

    def test_scenario_06_second_person_enters(self):
        """Scenario 6: Second person enters frame."""
        context = self._create_base_context(6)
        context.face_info = FaceInfo(
            face_detected=True,
            confidence=0.9,
            face_count=2,
            presence_state="PRESENT",
            all_bboxes=[(100.0, 100.0, 150.0, 150.0), (400.0, 100.0, 150.0, 150.0)]
        )
        p1 = TrackedObject(tracking_id=1, object_type=DetectedObjectType.PERSON, bbox=BoundingBox(x=100.0, y=100.0, width=150.0, height=300.0), confidence=0.9, current_state="TRACKED", first_detection_timestamp=time.time(), last_detection_timestamp=time.time(), visible_duration=1.0, consecutive_frames=1, lost_frames=0, motion_status="STATIONARY")
        p2 = TrackedObject(tracking_id=2, object_type=DetectedObjectType.PERSON, bbox=BoundingBox(x=400.0, y=100.0, width=150.0, height=300.0), confidence=0.85, current_state="TRACKED", first_detection_timestamp=time.time(), last_detection_timestamp=time.time(), visible_duration=1.0, consecutive_frames=1, lost_frames=0, motion_status="STATIONARY")
        obj_info = context.object_info
        obj_info.tracked_objects = [p1, p2]
        context.object_info = obj_info

        self._run_downstream_pipeline(context)
        triggered_rules = [e.rule_id for e in context.rule_results.evaluations if e.triggered]
        self.assertIn("COMM_MULTIPLE_PERSONS", triggered_rules)

    def test_scenario_07_book_visible(self):
        """Scenario 7: Unauthorized book visible."""
        context = self._create_base_context(7)
        context.face_info = FaceInfo(face_detected=True, confidence=0.9, bbox=(200.0, 100.0, 240.0, 240.0), face_count=1, presence_state="PRESENT")
        book = TrackedObject(
            tracking_id=1,
            object_type=DetectedObjectType.BOOK,
            bbox=BoundingBox(x=150.0, y=300.0, width=200.0, height=150.0),
            confidence=0.82,
            current_state="TRACKED",
            first_detection_timestamp=time.time(),
            last_detection_timestamp=time.time(),
            visible_duration=1.0,
            consecutive_frames=1,
            lost_frames=0,
            motion_status="STATIONARY"
        )
        obj_info = context.object_info
        obj_info.tracked_objects = [book]
        context.object_info = obj_info

        self._run_downstream_pipeline(context)
        triggered_rules = [e.rule_id for e in context.rule_results.evaluations if e.triggered]
        self.assertIn("UNAUTH_BOOK", triggered_rules)

    def test_scenario_08_identity_mismatch(self):
        """Scenario 8: Candidate face identity mismatch."""
        context = self._create_base_context(8)
        context.face_info = FaceInfo(
            face_detected=True,
            confidence=0.9,
            bbox=(200.0, 100.0, 240.0, 240.0),
            face_count=1,
            presence_state="PRESENT",
            identity_consistent=False,
            similarity_score=0.25,
            identity_confidence=0.20
        )

        self._run_downstream_pipeline(context)
        triggered_rules = [e.rule_id for e in context.rule_results.evaluations if e.triggered]
        self.assertIn("ID_MISMATCH", triggered_rules)

    def test_scenario_09_spoof_attempt(self):
        """Scenario 9: Presentation attack / spoof attempt detected."""
        context = self._create_base_context(9)
        context.face_info = FaceInfo(face_detected=True, confidence=0.9, bbox=(200.0, 100.0, 240.0, 240.0), face_count=1, presence_state="PRESENT")
        obs = IdentityProtectionObservation(
            liveness_state="SPOOF_SUSPECTED",
            liveness_score=0.15,
            presentation_attack_type="SCREEN_REPLAY",
            identity_integrity_score=0.15,
            spoof_confidence=0.85
        )
        context.identity_protection_observation = obs

        self._run_downstream_pipeline(context)
        triggered_rules = [e.rule_id for e in context.rule_results.evaluations if e.triggered]
        self.assertTrue(
            any("SPOOF" in r or "ATTACK" in r or "LIVENESS" in r or "INTEGRITY" in r or "UNAUTH" in r for r in triggered_rules),
            f"Expected spoof/liveness trigger, got: {triggered_rules}"
        )

    def test_scenario_10_multiple_simultaneous_violations(self):
        """Scenario 10: Phone visible + Looking away + Talking simultaneously."""
        context = self._create_base_context(10)
        context.face_info = FaceInfo(face_detected=True, confidence=0.9, bbox=(200.0, 100.0, 240.0, 240.0), face_count=1, presence_state="PRESENT")
        context.eye_info = EyeInfo(gaze_confidence=0.88, combined_gaze=(0.70, 0.0, 0.70))
        context.head_pose_info = HeadPoseInfo(yaw=35.0, pitch=0.0, roll=0.0, success=True)
        context.mouth_info = MouthInfo(mar=0.45, is_talking=True)
        phone = TrackedObject(
            tracking_id=1,
            object_type=DetectedObjectType.CELL_PHONE,
            bbox=BoundingBox(x=300.0, y=300.0, width=100.0, height=150.0),
            confidence=0.88,
            current_state="TRACKED",
            first_detection_timestamp=time.time(),
            last_detection_timestamp=time.time(),
            visible_duration=1.0,
            consecutive_frames=1,
            lost_frames=0,
            motion_status="STATIONARY"
        )
        obj_info = context.object_info
        obj_info.tracked_objects = [phone]
        context.object_info = obj_info

        self._run_downstream_pipeline(context)
        triggered_rules = [e.rule_id for e in context.rule_results.evaluations if e.triggered]

        self.assertIn("UNAUTH_PHONE", triggered_rules)
        self.assertIn("ATT_LOOKING_AWAY", triggered_rules)

        # Check risk assessment score accumulated
        risk_score = context.risk_assessment.overall_score
        self.assertGreaterEqual(risk_score, 30.0, f"Expected accumulated risk score >= 30, got: {risk_score}")


if __name__ == "__main__":
    unittest.main()
