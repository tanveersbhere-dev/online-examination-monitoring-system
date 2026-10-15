"""
Unit and integration test verifying:
1. Simultaneous cell phone + book detection without mutual suppression.
2. Suppression of ghost material box over cell phone when IoU > 0.40.
3. Proper distinct incident titling for both violations.
4. Distant Camera 2 candidate validation (conf >= 0.22).
"""
import unittest
import numpy as np

from ai_engine.core.enums import DetectedObjectType
from ai_engine.core.exam_context import ExamContext, DetectedObject, BoundingBox, TrackedObject
from ai_engine.camera.frame import Frame
from ai_engine.environment.object_filtering.filtering_processor import FilteringProcessor
from ai_engine.environment.object_filtering.models import ObjectFilteringConfig
from ai_engine.environment.object_validation.validation_processor import ObjectValidationProcessor
from ai_engine.environment.object_validation.models import ObjectValidationConfig
from ai_engine.intelligence.behavior_engine.composite_behavior import format_composite_incident_title

class TestSimultaneousDetectionAndCamera2(unittest.TestCase):
    def test_01_ghost_material_suppressed_over_phone(self):
        """Ghost material box right on top of a phone should be suppressed by higher-conf phone."""
        filter_proc = FilteringProcessor(ObjectFilteringConfig(enable_logging=False))
        filter_proc.initialize()

        ctx = ExamContext()
        ctx.current_frame = Frame.from_bgr_image(np.zeros((100, 100, 3), dtype=np.uint8), frame_id=1)

        # Phone at bottom
        phone = DetectedObject(
            object_type=DetectedObjectType.CELL_PHONE,
            confidence=0.72,
            bbox=BoundingBox(x=100, y=300, width=80, height=120)
        )
        # Ghost material right on top of the phone
        ghost_mat = DetectedObject(
            object_type=DetectedObjectType.UNAUTHORIZED_MATERIAL,
            confidence=0.30,
            bbox=BoundingBox(x=102, y=298, width=78, height=122)
        )
        # Genuine book at top
        book = DetectedObject(
            object_type=DetectedObjectType.UNAUTHORIZED_MATERIAL,
            confidence=0.62,
            bbox=BoundingBox(x=100, y=50, width=150, height=200)
        )
        obj_info = ctx.object_info
        obj_info.current_detections = [phone, ghost_mat, book]
        ctx.object_info = obj_info

        filter_proc.process(ctx)

        filtered = ctx.object_info.filtered_detections
        self.assertEqual(len(filtered), 2, "Expected exactly 2 objects: phone and book")
        types = [f.object_type for f in filtered]
        self.assertIn(DetectedObjectType.CELL_PHONE, types)
        self.assertIn(DetectedObjectType.UNAUTHORIZED_MATERIAL, types)

    def test_02_incident_titling_distinct(self):
        """Titling a book violation must never be overridden to Unauthorized Cell Phone."""
        objs = [{'type': 'CELL_PHONE'}, {'type': 'UNAUTHORIZED_MATERIAL'}]
        book_title = format_composite_incident_title('UNAUTH_BOOK', ['UNAUTH_BOOK'], objs)
        phone_title = format_composite_incident_title('UNAUTH_PHONE', ['UNAUTH_PHONE'], objs)

        self.assertEqual(book_title, "Unauthorized Material (Book)")
        self.assertEqual(phone_title, "Unauthorized Cell Phone")

    def test_03_camera2_distant_candidate_accepted(self):
        """Camera 2 distant objects with conf 0.23 should pass validation Step B."""
        validator = ObjectValidationProcessor(ObjectValidationConfig(enable_logging=False))
        validator.initialize()

        ctx = ExamContext()
        ctx.current_frame = Frame.from_bgr_image(np.zeros((10, 10, 3), dtype=np.uint8), frame_id=1, camera_id="camera_2")

        distant_phone = TrackedObject(
            tracking_id=1,
            object_type=DetectedObjectType.CELL_PHONE,
            bbox=BoundingBox(x=50, y=50, width=30, height=40),
            confidence=0.23,
            current_state="TRACKED"
        )
        obj_info = ctx.object_info
        obj_info.tracked_objects = [distant_phone]
        ctx.object_info = obj_info

        validator.process(ctx)

        val_res = getattr(ctx, "validation_results", {})
        rejected_low = val_res.get("statistics", {}).get("rejected_low_confidence", 0)
        self.assertEqual(rejected_low, 0, "Distant camera_2 detection should not be rejected for low confidence")

if __name__ == '__main__':
    unittest.main()

