"""
Comprehensive Object Detection & Proctoring Capability Test Suite.
Validates:
1. YOLODetector initialization, COCO mapping & inference.
2. Proctoring object classes (Person, Phone, Book, Laptop, Monitor, Keyboard, Mouse, Smartwatch, Headphones, Notebook, Paper).
3. ObjectFilter filtering & duplicate suppression.
4. ByteTrack object tracking persistence.
5. ObservationFusion integration & Rule Engine activation.
6. Real-world scenarios A through J.
"""

import unittest
import numpy as np
import time

from ai_engine.core.enums import DetectedObjectType
from ai_engine.core.exam_context import (
    ExamContext, FaceInfo, DetectedObject, TrackedObject, BoundingBox
)
from ai_engine.camera.frame import Frame
from ai_engine.environment.object_detection.yolo_detector import YOLODetector
from ai_engine.environment.object_detection.models import ObjectDetectionConfig
from ai_engine.environment.object_filtering.filtering_processor import FilteringProcessor
from ai_engine.environment.object_filtering.models import ObjectFilteringConfig
from ai_engine.environment.object_tracking.bytetrack_tracker import ByteTrackTracker
from ai_engine.environment.object_tracking.models import ObjectTrackingConfig
from backend.pipeline.orchestrator import MonitoringPipelineOrchestrator


class TestObjectDetection(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import os
        os.environ["AUDIO_DEVICE_DETECTION_ENABLED"] = "true"
        cls.config = ObjectDetectionConfig()
        cls.detector = YOLODetector(cls.config)
        cls.detector.initialize()
        cls.blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    @classmethod
    def tearDownClass(cls):
        import os
        os.environ.pop("AUDIO_DEVICE_DETECTION_ENABLED", None)

    def test_01_yolo_detector_initialization_and_mapping(self):
        """Verify YOLODetector initializes cleanly, COCO laptop/material classes are suppressed, and Fused detector maps authoritative classes."""
        self.assertTrue(self.detector._initialized)
        
        # Test class mapping in general YOLODetector (laptop, book, notebook, paper suppressed to prevent duplicate detections)
        self.assertEqual(self.detector._map_class_id(0), DetectedObjectType.PERSON)
        self.assertEqual(self.detector._map_class_id(67), DetectedObjectType.CELL_PHONE)
        self.assertEqual(self.detector._map_class_id(66), DetectedObjectType.KEYBOARD)
        self.assertEqual(self.detector._map_class_id(64), DetectedObjectType.MOUSE)
        self.assertEqual(self.detector._map_class_id(72), DetectedObjectType.MONITOR)
        self.assertEqual(self.detector._map_class_id(74), DetectedObjectType.SMARTWATCH)
        # Suppressed from general detector to prevent duplicates
        self.assertEqual(self.detector._map_class_id(63), DetectedObjectType.UNKNOWN)
        self.assertEqual(self.detector._map_class_id(73), DetectedObjectType.UNKNOWN)
        self.assertEqual(self.detector._map_class_id(75), DetectedObjectType.UNKNOWN)
        self.assertEqual(self.detector._map_class_id(76), DetectedObjectType.UNKNOWN)
        self.assertEqual(self.detector._map_class_id(999), DetectedObjectType.UNKNOWN)

        # Verify Fused detector maps authoritative classes
        from ai_engine.environment.object_detection.fused_detector import FusedLaptopMaterialDetector
        fused = FusedLaptopMaterialDetector()
        self.assertEqual(fused._map_class_id(0), DetectedObjectType.UNAUTHORIZED_MATERIAL)
        self.assertEqual(fused._map_class_id(1), DetectedObjectType.LAPTOP)
        self.assertEqual(fused._map_class_id(2), DetectedObjectType.UNKNOWN)

    def test_02_object_filtering_processor(self):
        """Verify ObjectFilter filters low-confidence detections and duplicates."""
        config = ObjectFilteringConfig(min_confidence=0.5, iou_threshold=0.5)
        filter_proc = FilteringProcessor(config)
        filter_proc.initialize()

        context = ExamContext()
        context.current_frame = Frame.from_bgr_image(self.blank_frame, frame_id=1)
        
        d1 = DetectedObject(object_type=DetectedObjectType.CELL_PHONE, confidence=0.85, bbox=BoundingBox(x=100, y=100, width=50, height=50))
        d2 = DetectedObject(object_type=DetectedObjectType.CELL_PHONE, confidence=0.30, bbox=BoundingBox(x=300, y=300, width=50, height=50)) # Low conf
        
        obj_info = context.object_info
        obj_info.current_detections = [d1, d2]
        context.object_info = obj_info

        filter_proc.process(context)
        
        filtered = context.object_info.filtered_detections
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].object_type, DetectedObjectType.CELL_PHONE)
        self.assertGreaterEqual(filtered[0].confidence, 0.5)

    def test_03_bytetrack_object_tracking_persistence(self):
        """Verify ByteTrack maintains tracking persistence and assigns tracking IDs."""
        config = ObjectTrackingConfig()
        tracker = ByteTrackTracker(config)
        tracker.initialize()

        context = ExamContext()
        context.current_frame = Frame.from_bgr_image(self.blank_frame, frame_id=1)
        
        d1 = DetectedObject(object_type=DetectedObjectType.CELL_PHONE, confidence=0.88, bbox=BoundingBox(x=100, y=100, width=50, height=50))
        
        obj_info = context.object_info
        obj_info.filtered_detections = [d1]
        context.object_info = obj_info

        tracker.process(context)
        
        tracked = context.object_info.tracked_objects
        self.assertEqual(len(tracked), 1)
        self.assertGreaterEqual(tracked[0].tracking_id, 1)

    def test_04_proctoring_scenario_phone(self):
        """Scenario B: Mobile Phone detection & UNAUTH_PHONE rule activation."""
        orchestrator = MonitoringPipelineOrchestrator()
        orchestrator.initialize()
        orchestrator._processors['RuleEngine'].processor._last_evaluation_time = 0.0

        context = ExamContext()
        context.current_frame = Frame.from_bgr_image(self.blank_frame, frame_id=1)
        context.face_info = FaceInfo(face_detected=True, confidence=0.95, face_count=1, presence_state="PRESENT")

        phone = TrackedObject(
            tracking_id=1, object_type=DetectedObjectType.CELL_PHONE,
            bbox=BoundingBox(x=200, y=200, width=80, height=120), confidence=0.89,
            current_state="TRACKED", first_detection_timestamp=time.time(),
            last_detection_timestamp=time.time(), visible_duration=1.0,
            consecutive_frames=1, lost_frames=0, motion_status="STATIONARY"
        )
        obj_info = context.object_info
        obj_info.tracked_objects = [phone]
        context.object_info = obj_info

        orchestrator._run_step('ObservationFusion', context)
        orchestrator._run_step('RuleEngine', context)
        orchestrator._run_step('RiskEngine', context)

        triggered = [e.rule_id for e in context.rule_results.evaluations if e.triggered]
        self.assertIn("UNAUTH_PHONE", triggered)
        self.assertGreaterEqual(context.risk_assessment.overall_score, 25.0)

    def test_05_proctoring_scenario_multiple_persons(self):
        """Scenario D: Second Person enters frame & COMM_MULTIPLE_PERSONS rule activation."""
        orchestrator = MonitoringPipelineOrchestrator()
        orchestrator.initialize()
        orchestrator._processors['RuleEngine'].processor._last_evaluation_time = 0.0

        context = ExamContext()
        context.current_frame = Frame.from_bgr_image(self.blank_frame, frame_id=1)
        context.face_info = FaceInfo(face_detected=True, confidence=0.9, face_count=2, presence_state="PRESENT")

        p1 = TrackedObject(tracking_id=1, object_type=DetectedObjectType.PERSON, bbox=BoundingBox(x=100, y=100, width=150, height=300), confidence=0.92, current_state="TRACKED", first_detection_timestamp=time.time(), last_detection_timestamp=time.time(), visible_duration=1.0, consecutive_frames=1, lost_frames=0, motion_status="STATIONARY")
        p2 = TrackedObject(tracking_id=2, object_type=DetectedObjectType.PERSON, bbox=BoundingBox(x=400, y=100, width=150, height=300), confidence=0.88, current_state="TRACKED", first_detection_timestamp=time.time(), last_detection_timestamp=time.time(), visible_duration=1.0, consecutive_frames=1, lost_frames=0, motion_status="STATIONARY")

        obj_info = context.object_info
        obj_info.tracked_objects = [p1, p2]
        context.object_info = obj_info

        orchestrator._run_step('ObservationFusion', context)
        orchestrator._run_step('RuleEngine', context)

        triggered = [e.rule_id for e in context.rule_results.evaluations if e.triggered]
        self.assertIn("COMM_MULTIPLE_PERSONS", triggered)

    def test_06_proctoring_scenario_headphones(self):
        """Scenario J: Headphones detected & COMM_EARPHONES/HEADPHONES rule activation when enabled."""
        orchestrator = MonitoringPipelineOrchestrator()
        orchestrator.initialize()
        rule_proc = orchestrator._processors['RuleEngine'].processor
        rule_proc.config.enabled_rules["COMM_EARPHONES"] = True
        rule_proc.config.enabled_rules["COMM_HEADPHONES"] = True
        rule_proc._last_evaluation_time = 0.0

        context = ExamContext()
        context.current_frame = Frame.from_bgr_image(self.blank_frame, frame_id=1)
        context.face_info = FaceInfo(face_detected=True, confidence=0.95, face_count=1, presence_state="PRESENT")

        hp = TrackedObject(
            tracking_id=1, object_type=DetectedObjectType.HEADPHONES,
            bbox=BoundingBox(x=200, y=100, width=100, height=100), confidence=0.86,
            current_state="TRACKED", first_detection_timestamp=time.time(),
            last_detection_timestamp=time.time(), visible_duration=1.0,
            consecutive_frames=1, lost_frames=0, motion_status="STATIONARY"
        )
        obj_info = context.object_info
        obj_info.tracked_objects = [hp]
        context.object_info = obj_info

        orchestrator._run_step('ObservationFusion', context)
        orchestrator._run_step('RuleEngine', context)

        triggered = [e.rule_id for e in context.rule_results.evaluations if e.triggered]
        self.assertTrue(
            any("COMM" in r or "HEADPHONE" in r or "EARPHONE" in r for r in triggered),
            f"Expected headphone rule trigger, got: {triggered}"
        )

    def test_07_all_audio_devices_normalize_to_comm_earphones(self):
        """Verify earbuds, wired earphones, neckbands, and headphones all normalize to COMM_EARPHONES."""
        orchestrator = MonitoringPipelineOrchestrator()
        orchestrator.initialize()
        rule_proc = orchestrator._processors['RuleEngine'].processor
        rule_proc.config.enabled_rules["COMM_EARPHONES"] = True
        rule_proc.config.enabled_rules["COMM_HEADPHONES"] = True

        devices = [
            DetectedObjectType.EARBUDS,
            DetectedObjectType.HEADPHONES,
            DetectedObjectType.NECKBAND,
            DetectedObjectType.COMM_EARPHONES,
        ]

        for dev_type in devices:
            for frame_id in [1, 2]:
                rule_proc._last_evaluation_time = 0.0
                context = ExamContext()
                context.current_frame = Frame.from_bgr_image(self.blank_frame, frame_id=frame_id)
                context.face_info = FaceInfo(face_detected=True, confidence=0.95, face_count=1, presence_state="PRESENT")

                audio_obj = TrackedObject(
                    tracking_id=1, object_type=dev_type,
                    bbox=BoundingBox(x=200, y=100, width=50, height=50), confidence=0.90,
                    current_state="TRACKED", first_detection_timestamp=time.time(),
                    last_detection_timestamp=time.time(), visible_duration=1.0,
                    consecutive_frames=frame_id, lost_frames=0, motion_status="STATIONARY"
                )
                obj_info = context.object_info
                obj_info.tracked_objects = [audio_obj]
                context.object_info = obj_info

                orchestrator._run_step('ObjectValidator', context)
                orchestrator._run_step('ObservationFusion', context)
                orchestrator._run_step('RuleEngine', context)

            triggered = [e.rule_id for e in context.rule_results.evaluations if e.triggered]
            self.assertIn("COMM_EARPHONES", triggered, f"Expected COMM_EARPHONES trigger for {dev_type}, got: {triggered}")

    def test_08_no_earphone_device_no_violation(self):
        """Verify frame with no earphone device does not trigger an earphone violation."""
        orchestrator = MonitoringPipelineOrchestrator()
        orchestrator.initialize()
        orchestrator._processors['RuleEngine'].processor._last_evaluation_time = 0.0

        context = ExamContext()
        context.current_frame = Frame.from_bgr_image(self.blank_frame, frame_id=1)
        context.face_info = FaceInfo(face_detected=True, confidence=0.95, face_count=1, presence_state="PRESENT")

        person = TrackedObject(
            tracking_id=1, object_type=DetectedObjectType.PERSON,
            bbox=BoundingBox(x=100, y=100, width=200, height=300), confidence=0.92,
            current_state="TRACKED"
        )
        obj_info = context.object_info
        obj_info.tracked_objects = [person]
        context.object_info = obj_info

        orchestrator._run_step('ObservationFusion', context)
        orchestrator._run_step('RuleEngine', context)

        triggered = [e.rule_id for e in context.rule_results.evaluations if e.triggered]
        self.assertNotIn("COMM_EARPHONES", triggered)

    def test_09_weak_isolated_detection_no_immediate_violation(self):
        """Verify single weak/low-confidence earphone detection does not trigger immediate violation."""
        from ai_engine.environment.object_validation.validation_processor import ObjectValidationProcessor
        from ai_engine.environment.object_validation.models import ObjectValidationConfig

        cfg = ObjectValidationConfig()
        validator = ObjectValidationProcessor(cfg)
        validator.initialize()

        context = ExamContext()
        context.current_frame = Frame.from_bgr_image(self.blank_frame, frame_id=1)

        # Single weak earphone detection (low confidence 0.20 < threshold 0.30)
        weak_obj = DetectedObject(
            object_type=DetectedObjectType.COMM_EARPHONES,
            confidence=0.20,
            bbox=BoundingBox(x=200, y=100, width=30, height=30)
        )
        obj_info = context.object_info
        obj_info.tracked_objects = [weak_obj]
        context.object_info = obj_info

        validator.process(context)
        validated = context.object_info.validated_objects
        # Low confidence detection filtered out
        self.assertEqual(len(validated), 0)

    def test_10_persistent_detection_triggers_violation(self):
        """Verify persistent earphone detection across multiple frames triggers confirmed violation when rule enabled."""
        orchestrator = MonitoringPipelineOrchestrator()
        orchestrator.initialize()
        try:
            rule_proc = orchestrator._processors['RuleEngine'].processor
            rule_proc.config.enabled_rules["COMM_EARPHONES"] = True
            rule_proc.config.enabled_rules["COMM_HEADPHONES"] = True

            t0 = time.time()
            # ObjectValidator requires min 2 frames; ViolationManager requires min 3 confirming frames = 5 frames total
            for frame_id in range(1, 6):
                rule_proc._last_evaluation_time = 0.0
                context = ExamContext()
                context.current_frame = Frame.from_bgr_image(self.blank_frame, frame_id=frame_id, timestamp=t0 + (frame_id * 0.2))
                context.face_info = FaceInfo(face_detected=True, confidence=0.95, face_count=1, presence_state="PRESENT")

                earphone = TrackedObject(
                    tracking_id=5, object_type=DetectedObjectType.COMM_EARPHONES,
                    bbox=BoundingBox(x=200, y=100, width=50, height=50), confidence=0.92,
                    current_state="TRACKED", first_detection_timestamp=t0,
                    last_detection_timestamp=t0 + (frame_id * 0.2), visible_duration=0.5 * frame_id,
                    consecutive_frames=frame_id, lost_frames=0, motion_status="STATIONARY"
                )
                obj_info = context.object_info
                obj_info.tracked_objects = [earphone]
                context.object_info = obj_info

                orchestrator._run_step('ObjectValidator', context)
                orchestrator._run_step('ObservationFusion', context)
                orchestrator._run_step('RuleEngine', context)
                orchestrator._run_step('ViolationManager', context)

            events = getattr(context, "lifecycle_events", [])
            active_viols = [v for v in getattr(context, "violations", getattr(context, "observation", None)).timeline.violations if v.status in ("OPEN", "ACTIVE")]
            self.assertTrue(
                any(v.violation_type in ("COMM_EARPHONES", "EARPHONE_DEVICE") for v in active_viols) or
                any(e.violation_type in ("COMM_EARPHONES", "EARPHONE_DEVICE") for e in events),
                "Expected active EARPHONE_DEVICE / COMM_EARPHONES violation after persistent frames"
            )
        finally:
            orchestrator.stop()

    def test_11_register_flat_desk_disambiguation_from_laptop(self):
        """Verify flat desk registers are disambiguated away from LAPTOP to REGISTER/BOOK across frames."""
        from ai_engine.environment.object_validation.validation_processor import ObjectValidationProcessor
        from ai_engine.environment.object_validation.models import ObjectValidationConfig

        cfg = ObjectValidationConfig()
        validator = ObjectValidationProcessor(cfg)
        validator.initialize()

        flat_box = BoundingBox(x=100, y=250, width=200, height=100)

        # Process frame 1
        context1 = ExamContext()
        context1.current_frame = Frame.from_bgr_image(self.blank_frame, frame_id=1)
        obj1 = TrackedObject(tracking_id=1, object_type=DetectedObjectType.REGISTER, bbox=flat_box, confidence=0.85, current_state="TRACKED")
        info1 = context1.object_info
        info1.tracked_objects = [obj1]
        context1.object_info = info1
        validator.process(context1)

        # Process frame 2 to satisfy min_consecutive_frames = 2
        context2 = ExamContext()
        context2.current_frame = Frame.from_bgr_image(self.blank_frame, frame_id=2)
        obj2 = TrackedObject(tracking_id=1, object_type=DetectedObjectType.REGISTER, bbox=flat_box, confidence=0.85, current_state="TRACKED")
        info2 = context2.object_info
        info2.tracked_objects = [obj2]
        context2.object_info = info2
        validator.process(context2)

        validated = context2.object_info.validated_objects
        self.assertEqual(len(validated), 1)
        type_str = validated[0].object_type.name if hasattr(validated[0].object_type, "name") else str(validated[0].object_type)
        self.assertNotEqual(type_str, "LAPTOP", "Desk register must not be validated as LAPTOP")
        self.assertIn(type_str, ["REGISTER", "BOOK", "NOTEBOOK"])


if __name__ == "__main__":
    unittest.main()
