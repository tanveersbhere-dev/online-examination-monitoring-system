"""
Automated Test Suite: Multiple-Person Counting and Arm-Sliver Suppression

Covers all 8 required scenarios:
1. Normal single student sitting still (no violation).
2. Single student extending arm / writing / gesturing (arm sliver suppressed, no violation).
3. Single student with multi-scale nested person boxes (subsumed box suppressed, count=1).
4. Genuine two people side-by-side (multiple-person violation triggers).
5. Genuine two people with one partially visible (not suppressed indiscriminately, triggers).
6. Temporal persistence requirement for second person (transient rejected, persistent confirmed).
7. Single-face stability (single face remains stable, count=1).
8. Multi-camera behavior (camera_1 and camera_2 isolated, proper routing).
"""
import unittest
import time
import numpy as np

from ai_engine.core.exam_context import (
    ExamContext, FaceInfo, ObjectInfo, TrackedObject, DetectedObject, BoundingBox
)
from ai_engine.camera.frame import Frame
from ai_engine.core.enums import DetectedObjectType
from ai_engine.environment.object_filtering.filtering_processor import FilteringProcessor
from ai_engine.environment.object_filtering.models import ObjectFilteringConfig
from ai_engine.environment.object_validation.temporal_buffer import TemporalConfirmationBuffer
from ai_engine.environment.object_validation.validation_processor import ObjectValidationProcessor
from ai_engine.environment.object_validation.models import ObjectValidationConfig
from ai_engine.intelligence.observation_fusion.fusion_processor import FusionProcessor
from ai_engine.intelligence.observation_fusion.models import ObservationFusionConfig
from ai_engine.intelligence.rule_engine.rules import MultiplePersonsPresentRule, MultipleFacesRule
from ai_engine.intelligence.rule_engine.models import RuleEngineConfig


class TestPersonCountingAndArmSuppression(unittest.TestCase):

    def setUp(self):
        self.filter_cfg = ObjectFilteringConfig(enable_logging=False)
        self.filtering_processor = FilteringProcessor(self.filter_cfg)
        self.filtering_processor.initialize()
        self.filtering_processor.start()

        self.val_cfg = ObjectValidationConfig(enable_logging=False)
        self.validation_processor = ObjectValidationProcessor(self.val_cfg)
        self.validation_processor.initialize()

        self.fusion_cfg = ObservationFusionConfig(enable_face=True, enable_environment=True, enable_audio=False)
        self.fusion_processor = FusionProcessor(self.fusion_cfg)
        self.fusion_processor.initialize()

        self.rule_cfg = RuleEngineConfig()
        self.multi_person_rule = MultiplePersonsPresentRule()
        self.multi_face_rule = MultipleFacesRule()
        self.blank_img = np.zeros((720, 1280, 3), dtype=np.uint8)

    # -------------------------------------------------------------------------
    # Scenario 1: Normal single student sitting still
    # -------------------------------------------------------------------------
    def test_01_single_student_normal(self):
        """Single student seated in front of camera: count is exactly 1, no violation."""
        context = ExamContext()
        context.current_frame = Frame.from_bgr_image(self.blank_img, frame_id=1, camera_id="camera_1")

        fi = context.face_info
        fi.face_detected = True
        fi.face_count = 1
        fi.bbox = (500, 100, 200, 220)
        fi.all_bboxes = [(500, 100, 200, 220)]
        context.face_info = fi

        # Student body
        student_obj = TrackedObject(
            tracking_id=1,
            object_type=DetectedObjectType.PERSON,
            confidence=0.92,
            bbox=BoundingBox(300, 60, 700, 650)
        )
        oi = context.object_info
        oi.validated_objects = [student_obj]
        context.object_info = oi

        self.fusion_processor.process(context)
        obs = context.observation
        self.assertEqual(obs.environment.total_persons, 1)

        triggered, conf, reason = self.multi_person_rule.evaluate(obs, self.rule_cfg)
        self.assertFalse(triggered, f"Expected no violation, got: {reason}")
        self.assertEqual(conf, 0.0)

    # -------------------------------------------------------------------------
    # Scenario 2: Single student extending arm / gesturing
    # -------------------------------------------------------------------------
    def test_02_single_student_arm_extension_suppressed(self):
        """Student extending arm creates a small subordinate PERSON detection: suppressed."""
        context = ExamContext()
        context.current_frame = Frame.from_bgr_image(self.blank_img, frame_id=1, camera_id="camera_1")

        fi = context.face_info
        fi.face_detected = True
        fi.face_count = 1
        fi.bbox = (500, 100, 200, 220)
        fi.all_bboxes = [(500, 100, 200, 220)]
        context.face_info = fi

        # Dominant student body
        student_obj = TrackedObject(
            tracking_id=1,
            object_type=DetectedObjectType.PERSON,
            confidence=0.91,
            bbox=BoundingBox(350, 60, 680, 640)  # Area = 435,200
        )
        # Small arm sliver on desk (representative of real false-positive DB evidence)
        arm_obj = TrackedObject(
            tracking_id=2,
            object_type=DetectedObjectType.PERSON,
            confidence=0.62,
            bbox=BoundingBox(0, 380, 160, 210)  # Area = 33,600 (ratio = 0.077, no face)
        )
        oi = context.object_info
        oi.validated_objects = [student_obj, arm_obj]
        context.object_info = oi

        self.fusion_processor.process(context)
        obs = context.observation
        self.assertEqual(obs.environment.total_persons, 1, "Arm sliver should not increment total_persons")

        triggered, conf, reason = self.multi_person_rule.evaluate(obs, self.rule_cfg)
        self.assertFalse(triggered, f"Arm sliver caused false multiple-person violation: {reason}")

    # -------------------------------------------------------------------------
    # Scenario 3: Single student with multi-scale nested person boxes
    # -------------------------------------------------------------------------
    def test_03_multiscale_nested_person_boxes_filtered(self):
        """Nested/subsumed person boxes of the same student are filtered by NMS (IoS > 0.50)."""
        # Outer student body
        outer_box = DetectedObject(
            object_type=DetectedObjectType.PERSON,
            confidence=0.88,
            bbox=BoundingBox(300, 50, 700, 650)  # Area = 455,000
        )
        # Nested torso/shoulder candidate box
        inner_box = DetectedObject(
            object_type=DetectedObjectType.PERSON,
            confidence=0.74,
            bbox=BoundingBox(380, 120, 450, 480)  # Area = 216,000, 100% inside outer_box
        )

        context = ExamContext()
        context.current_frame = Frame.from_bgr_image(self.blank_img, frame_id=1, camera_id="camera_1")
        oi = context.object_info
        oi.current_detections = [outer_box, inner_box]
        context.object_info = oi

        self.filtering_processor.process(context)
        filtered = context.object_info.filtered_detections

        # Inner nested box must be suppressed by IoS NMS
        self.assertEqual(len(filtered), 1, "Nested person box should be suppressed during NMS")
        self.assertEqual(filtered[0].bbox.width, 700)

        # Confirm downstream fusion also reports total_persons = 1
        oi = context.object_info
        oi.validated_objects = filtered
        context.object_info = oi

        self.fusion_processor.process(context)
        obs = context.observation
        self.assertEqual(obs.environment.total_persons, 1)

        triggered, _, reason = self.multi_person_rule.evaluate(obs, self.rule_cfg)
        self.assertFalse(triggered, f"Nested boxes caused false violation: {reason}")

    # -------------------------------------------------------------------------
    # Scenario 4: Genuine two people side-by-side
    # -------------------------------------------------------------------------
    def test_04_genuine_two_people_side_by_side(self):
        """Two genuine people sitting/standing side by side: violation reliably triggers."""
        context = ExamContext()
        context.current_frame = Frame.from_bgr_image(self.blank_img, frame_id=1, camera_id="camera_1")

        fi = context.face_info
        fi.face_detected = True
        fi.face_count = 2
        fi.bbox = (200, 100, 180, 200)
        fi.all_bboxes = [(200, 100, 180, 200), (750, 110, 180, 200)]
        context.face_info = fi

        person1 = TrackedObject(
            tracking_id=1,
            object_type=DetectedObjectType.PERSON,
            confidence=0.90,
            bbox=BoundingBox(80, 60, 520, 620)
        )
        person2 = TrackedObject(
            tracking_id=2,
            object_type=DetectedObjectType.PERSON,
            confidence=0.88,
            bbox=BoundingBox(650, 70, 500, 610)
        )
        oi = context.object_info
        oi.validated_objects = [person1, person2]
        context.object_info = oi

        self.fusion_processor.process(context)
        obs = context.observation
        self.assertEqual(obs.environment.total_persons, 2)

        triggered, conf, reason = self.multi_person_rule.evaluate(obs, self.rule_cfg)
        self.assertTrue(triggered, "Genuine two people must trigger multiple-person violation")
        self.assertGreaterEqual(conf, 0.90)

    # -------------------------------------------------------------------------
    # Scenario 5: Genuine two people with one partially visible
    # -------------------------------------------------------------------------
    def test_05_partially_visible_second_person_detected(self):
        """Second person entering frame with their own face is NOT suppressed as an arm."""
        context = ExamContext()
        context.current_frame = Frame.from_bgr_image(self.blank_img, frame_id=1, camera_id="camera_1")

        # Face detection sees 2 faces (student + leaning intruder)
        fi = context.face_info
        fi.face_detected = True
        fi.face_count = 2
        fi.bbox = (400, 100, 190, 210)
        fi.all_bboxes = [(400, 100, 190, 210), (950, 120, 160, 170)]
        context.face_info = fi

        primary_student = TrackedObject(
            tracking_id=1,
            object_type=DetectedObjectType.PERSON,
            confidence=0.92,
            bbox=BoundingBox(250, 60, 650, 640)  # Area = 416,000
        )
        # Second person partially leaning in (smaller box, but has detected face)
        leaning_person = TrackedObject(
            tracking_id=2,
            object_type=DetectedObjectType.PERSON,
            confidence=0.78,
            bbox=BoundingBox(900, 80, 220, 350)  # Area = 77,000 (has face inside)
        )
        oi = context.object_info
        oi.validated_objects = [primary_student, leaning_person]
        context.object_info = oi

        self.fusion_processor.process(context)
        obs = context.observation
        self.assertEqual(obs.environment.total_persons, 2, "Partially visible person with face must be counted")

        triggered, conf, reason = self.multi_person_rule.evaluate(obs, self.rule_cfg)
        self.assertTrue(triggered, "Partially visible second person must trigger multiple-person violation")

    # -------------------------------------------------------------------------
    # Scenario 6: Temporal persistence requirement for second person
    # -------------------------------------------------------------------------
    def test_06_second_person_temporal_persistence_requirement(self):
        """Transient second person (< 8 frames) is rejected; persistent (>= 8 frames) confirms."""
        buf = TemporalConfirmationBuffer(self.val_cfg)

        # Frame 1: Establish student track (trk_1)
        base_ts = 1000.0
        for f in range(8):
            ts = base_ts + f * 0.1
            confirmed, frames, dur, reason = buf.update_and_evaluate(
                track_id=1,
                object_type="PERSON",
                confidence=0.88,
                current_ts=ts,
                camera_id="camera_1"
            )
        self.assertTrue(confirmed, "Student track 1 should be confirmed after 8 frames")

        # Simulate brief missing frame on student track 1 (active_keys_seen is empty)
        buf.age_missing_tracks(active_keys_seen=set(), current_camera_id="camera_1")

        # New transient second person track appears (trk_2)
        # Must NOT inherit confirmation from track 1
        ts_new = base_ts + 1.0
        confirmed_p2, frames_p2, dur_p2, reason_p2 = buf.update_and_evaluate(
            track_id=2,
            object_type="PERSON",
            confidence=0.70,
            current_ts=ts_new,
            camera_id="camera_1"
        )
        self.assertFalse(confirmed_p2, "Transient second person must NOT inherit instant confirmation")
        self.assertEqual(frames_p2, 1)

        # Track 2 persists for 8 frames -> becomes confirmed
        for f in range(1, 8):
            ts_p2 = ts_new + f * 0.1
            confirmed_p2, frames_p2, dur_p2, reason_p2 = buf.update_and_evaluate(
                track_id=2,
                object_type="PERSON",
                confidence=0.75,
                current_ts=ts_p2,
                camera_id="camera_1"
            )
        self.assertTrue(confirmed_p2, "Persistent second person must be confirmed after 8 frames")

    # -------------------------------------------------------------------------
    # Scenario 7: Single-face stability
    # -------------------------------------------------------------------------
    def test_07_single_face_stability(self):
        """Single face present: ID_MULTIPLE_FACES and COMM_MULTIPLE_PERSONS do not trigger."""
        context = ExamContext()
        context.current_frame = Frame.from_bgr_image(self.blank_img, frame_id=1, camera_id="camera_1")

        fi = context.face_info
        fi.face_detected = True
        fi.face_count = 1
        fi.bbox = (500, 100, 200, 220)
        fi.all_bboxes = [(500, 100, 200, 220)]
        context.face_info = fi

        student = TrackedObject(
            tracking_id=1,
            object_type=DetectedObjectType.PERSON,
            confidence=0.90,
            bbox=BoundingBox(300, 50, 600, 600)
        )
        oi = context.object_info
        oi.validated_objects = [student]
        context.object_info = oi

        self.fusion_processor.process(context)
        obs = context.observation
        self.assertEqual(obs.face.face_count, 1)
        self.assertEqual(obs.environment.total_persons, 1)

        trig_face, _, _ = self.multi_face_rule.evaluate(obs, self.rule_cfg)
        trig_comm, _, _ = self.multi_person_rule.evaluate(obs, self.rule_cfg)
        self.assertFalse(trig_face, "Single face must not trigger MultipleFacesRule")
        self.assertFalse(trig_comm, "Single face must not trigger MultiplePersonsPresentRule")

    # -------------------------------------------------------------------------
    # Scenario 8: Multi-camera behavior
    # -------------------------------------------------------------------------
    def test_08_multi_camera_isolation(self):
        """Camera 1 and Camera 2 track spaces remain strictly isolated with no cross-camera false alerts."""
        buf = TemporalConfirmationBuffer(self.val_cfg)

        # Track 1 on camera 1
        for f in range(8):
            confirmed_cam1, _, _, _ = buf.update_and_evaluate(
                track_id=1,
                object_type="PERSON",
                confidence=0.85,
                current_ts=100.0 + f * 0.1,
                camera_id="camera_1"
            )
        self.assertTrue(confirmed_cam1)

        # Track 1 on camera 2 (different camera, same integer track_id from separate tracker)
        # It must start from frame 1 in camera 2 track memory
        confirmed_cam2, frames_cam2, _, _ = buf.update_and_evaluate(
            track_id=1,
            object_type="PERSON",
            confidence=0.85,
            current_ts=100.0,
            camera_id="camera_2"
        )
        self.assertFalse(confirmed_cam2, "Camera 2 track must have separate temporal lifecycle")
        self.assertEqual(frames_cam2, 1)


if __name__ == "__main__":
    unittest.main()

