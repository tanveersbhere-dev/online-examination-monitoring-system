"""
Automated Test Suite for Object Validation & Reliability Layer.
"""
import unittest
import time
import numpy as np

from ai_engine.core.exam_context import ExamContext, TrackedObject, BoundingBox
from ai_engine.core.enums import DetectedObjectType
from ai_engine.camera.frame import Frame
from ai_engine.environment.object_validation.models import (
    ObjectValidationConfig, ClassValidationConfig, ValidationReason
)
from ai_engine.environment.object_validation.temporal_buffer import TemporalConfirmationBuffer
from ai_engine.environment.object_validation.validation_processor import ObjectValidationProcessor
from backend.pipeline.orchestrator import MonitoringPipelineOrchestrator

class TestObjectValidation(unittest.TestCase):

    def setUp(self):
        self.config = ObjectValidationConfig()
        self.processor = ObjectValidationProcessor(self.config)
        self.processor.initialize()
        self.orchestrator = MonitoringPipelineOrchestrator()
        self.orchestrator.initialize()
        self.blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    def test_01_whitelisting_rejection(self):
        """Verify non-whitelisted object classes (e.g. chair, tie, cup) are rejected."""
        context = ExamContext()
        obj_unsupported = TrackedObject(
            tracking_id=1,
            object_type="CHAIR",
            confidence=0.95,
            bbox=BoundingBox(10, 10, 100, 100)
        )
        obj_info = context.object_info
        obj_info.tracked_objects = [obj_unsupported]
        context.object_info = obj_info

        self.processor.process(context)

        val_payload = getattr(context, "object_validation", {})
        stats = val_payload.get("statistics", {})
        self.assertEqual(stats.get("rejected_unsupported_class"), 1)
        self.assertEqual(stats.get("accepted_count"), 0)

    def test_02_per_class_confidence_thresholds(self):
        """Verify objects below per-class confidence thresholds are rejected."""
        context = ExamContext()
        obj_low_conf = TrackedObject(
            tracking_id=2,
            object_type=DetectedObjectType.CELL_PHONE,
            confidence=0.20,
            bbox=BoundingBox(10, 10, 100, 100)
        )
        obj_info = context.object_info
        obj_info.tracked_objects = [obj_low_conf]
        context.object_info = obj_info

        self.processor.process(context)

        val_payload = getattr(context, "object_validation", {})
        stats = val_payload.get("statistics", {})
        self.assertEqual(stats.get("rejected_low_confidence"), 1)
        self.assertEqual(stats.get("accepted_count"), 0)

    def test_03_phone_2_frame_temporal_confirmation(self):
        """Verify cell phone requires 2 consecutive frames before being emitted."""
        context = ExamContext()
        phone_obj = TrackedObject(
            tracking_id=10,
            object_type=DetectedObjectType.CELL_PHONE,
            confidence=0.85,
            bbox=BoundingBox(50, 50, 80, 80)
        )

        # Frame 1: Pending confirmation
        obj_info = context.object_info
        obj_info.tracked_objects = [phone_obj]
        context.object_info = obj_info
        self.processor.process(context)
        val1 = getattr(context.object_info, "validated_objects", [])
        self.assertEqual(len(val1), 0)

        # Frame 2: Confirmed and emitted
        obj_info = context.object_info
        obj_info.tracked_objects = [phone_obj]
        context.object_info = obj_info
        self.processor.process(context)
        val2 = getattr(context.object_info, "validated_objects", [])
        self.assertEqual(len(val2), 1)

    def test_04_second_person_temporal_tracking_confirmation(self):
        """Verify second person requires sustained tracking before confirmation."""
        context = ExamContext()
        person_obj = TrackedObject(
            tracking_id=20,
            object_type=DetectedObjectType.PERSON,
            confidence=0.75,
            bbox=BoundingBox(200, 100, 150, 300)
        )

        # Frames 1..7: Pending confirmation
        for i in range(1, 8):
            obj_info = context.object_info
            obj_info.tracked_objects = [person_obj]
            context.object_info = obj_info
            self.processor.process(context)
            val = getattr(context.object_info, "validated_objects", [])
            self.assertEqual(len(val), 0)

        # Frame 8: Confirmed and emitted
        obj_info = context.object_info
        obj_info.tracked_objects = [person_obj]
        context.object_info = obj_info
        self.processor.process(context)
        val_final = getattr(context.object_info, "validated_objects", [])
        self.assertEqual(len(val_final), 1)

    def test_05_transient_flicker_suppression(self):
        """Verify single-frame transient noise glitches are suppressed and expire cleanly."""
        context = ExamContext()
        glitch_obj = TrackedObject(
            tracking_id=99,
            object_type=DetectedObjectType.CELL_PHONE,
            confidence=0.90,
            bbox=BoundingBox(300, 300, 50, 50)
        )

        # Frame 1: Glitch appears
        obj_info = context.object_info
        obj_info.tracked_objects = [glitch_obj]
        context.object_info = obj_info
        self.processor.process(context)
        self.assertEqual(len(getattr(context.object_info, "validated_objects", [])), 0)

        # Frames 2..10: Glitch disappears
        for _ in range(9):
            obj_info = context.object_info
            obj_info.tracked_objects = []
            context.object_info = obj_info
            self.processor.process(context)
            self.assertEqual(len(getattr(context.object_info, "validated_objects", [])), 0)

        # Track should be expired from buffer
        self.assertEqual(self.processor.temporal_buffer.active_track_count, 0)

    def test_06_orchestrator_step13_integration(self):
        """Verify MonitoringPipelineOrchestrator executes ObjectValidator as Step 13."""
        context = ExamContext()
        context.current_frame = Frame.from_bgr_image(self.blank_frame, frame_id=1)

        pipeline_ms = self.orchestrator.process(context)
        self.assertGreater(pipeline_ms, 0.0)

        val_payload = getattr(context, "object_validation", None)
        self.assertIsNotNone(val_payload)
        self.assertIn("statistics", val_payload)

if __name__ == "__main__":
    unittest.main()
