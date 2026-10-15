"""
Focused verification tests for:
1. Laptop misclassification fix (ensuring horizontal desk laptops with transient material votes stay LAPTOP).
2. Genuine material classification preservation.
3. Camera 2 intermittent-miss streak tolerance.
4. Camera 2 camera disconnect clearing.
5. Camera 2 low-confidence track initiation.
"""
import time
import unittest
import numpy as np

from ai_engine.core.enums import DetectedObjectType
from ai_engine.core.exam_context import ExamContext, TrackedObject, BoundingBox, DetectedObject
from ai_engine.camera.frame import Frame
from ai_engine.environment.object_validation.validation_processor import ObjectValidationProcessor
from ai_engine.environment.object_validation.temporal_buffer import TemporalConfirmationBuffer
from ai_engine.environment.object_validation.models import ObjectValidationConfig
from ai_engine.environment.object_tracking.bytetrack_tracker import ByteTrackTracker
from ai_engine.environment.object_tracking.models import ObjectTrackingConfig
from ai_engine.intelligence.observation_fusion.fusion_processor import FusionProcessor
from ai_engine.intelligence.observation_fusion.models import ObservationFusionConfig
from ai_engine.intelligence.rule_engine.rule_engine import RuleEngineProcessor
from ai_engine.intelligence.rule_engine.models import RuleEngineConfig


class TestLaptopCamera2Fixes(unittest.TestCase):

    def setUp(self):
        self.blank_img = np.zeros((100, 100, 3), dtype=np.uint8)

    def test_01_laptop_not_reclassified_by_horizontal_bbox_and_transient_material_vote(self):
        """Verify wide/horizontal bbox on desk with a transient UNAUTHORIZED_MATERIAL vote stays LAPTOP."""
        cfg = ObjectValidationConfig(enable_logging=False)
        validator = ObjectValidationProcessor(cfg)
        validator.initialize()

        fusion = FusionProcessor(ObservationFusionConfig(enable_environment=True, enable_audio=False))
        fusion.initialize()

        rules = RuleEngineProcessor(RuleEngineConfig())
        rules.initialize()
        rules.config.enabled_rules["UNAUTH_LAPTOP"] = True
        rules.config.enabled_rules["UNAUTH_BOOK"] = True

        # Horizontal desk laptop bounding box: aspect ratio = 2.0 (>= 1.20), y = 250 (> 200)
        desk_laptop_box = BoundingBox(x=100.0, y=250.0, width=300.0, height=150.0)

        # 3 frames of LAPTOP with 1 transient UNAUTHORIZED_MATERIAL vote mixed in
        frame_types = [
            (DetectedObjectType.LAPTOP, 0.75),
            (DetectedObjectType.UNAUTHORIZED_MATERIAL, 0.65),  # Transient material glitch that passes confidence
            (DetectedObjectType.LAPTOP, 0.75),
            (DetectedObjectType.LAPTOP, 0.78),
        ]

        last_ctx = None
        for i, (obj_type, conf) in enumerate(frame_types, start=1):
            ctx = ExamContext()
            ctx.current_frame = Frame.from_bgr_image(self.blank_img, frame_id=i, timestamp=time.time())
            obj = TrackedObject(
                tracking_id=42,
                object_type=obj_type,
                bbox=desk_laptop_box,
                confidence=conf,
                current_state="TRACKED",
            )
            oi = ctx.object_info
            oi.tracked_objects = [obj]
            ctx.object_info = oi

            validator.process(ctx)
            fusion.process(ctx)
            rules.process(ctx)
            last_ctx = ctx

        # Object must remain LAPTOP
        validated = last_ctx.object_info.validated_objects
        self.assertEqual(len(validated), 1)
        self.assertEqual(validated[0].object_type, DetectedObjectType.LAPTOP)

        # Fusion must mark laptop_present = True
        self.assertTrue(last_ctx.observation.environment.laptop_present)

        # UNAUTH_LAPTOP rule must trigger
        triggered = [r.rule_id for r in last_ctx.rule_results.evaluations if r.triggered]
        self.assertIn("UNAUTH_LAPTOP", triggered)
        self.assertNotIn("UNAUTH_BOOK", triggered)

    def test_02_genuine_material_preserved_when_material_dominant(self):
        """Verify genuine reading/writing material with transient laptop glitch resolves to material."""
        cfg = ObjectValidationConfig(enable_logging=False)
        validator = ObjectValidationProcessor(cfg)
        validator.initialize()

        desk_box = BoundingBox(x=100.0, y=250.0, width=200.0, height=100.0)

        # 3 frames of UNAUTHORIZED_MATERIAL with 1 transient LAPTOP glitch
        frame_types = [
            (DetectedObjectType.UNAUTHORIZED_MATERIAL, 0.80),
            (DetectedObjectType.LAPTOP, 0.50),  # Transient glitch
            (DetectedObjectType.UNAUTHORIZED_MATERIAL, 0.80),
            (DetectedObjectType.UNAUTHORIZED_MATERIAL, 0.85),
        ]

        last_ctx = None
        for i, (obj_type, conf) in enumerate(frame_types, start=1):
            ctx = ExamContext()
            ctx.current_frame = Frame.from_bgr_image(self.blank_img, frame_id=i, timestamp=time.time())
            obj = TrackedObject(
                tracking_id=99,
                object_type=obj_type,
                bbox=desk_box,
                confidence=conf,
                current_state="TRACKED",
            )
            oi = ctx.object_info
            oi.tracked_objects = [obj]
            ctx.object_info = oi

            validator.process(ctx)
            last_ctx = ctx

        validated = last_ctx.object_info.validated_objects
        self.assertEqual(len(validated), 1)
        self.assertIn(validated[0].object_type, [
            DetectedObjectType.UNAUTHORIZED_MATERIAL,
            DetectedObjectType.BOOK,
            DetectedObjectType.REGISTER,
            DetectedObjectType.NOTEBOOK
        ])

    def test_03_camera2_intermittent_miss_streak_tolerance(self):
        """Verify Camera 2 unconfirmed track tolerates 1-2 missed frames without resetting consecutive streak."""
        cfg = ObjectValidationConfig(enable_logging=False)
        buf = TemporalConfirmationBuffer(cfg)

        ts = 1000.0
        # Frame 1: Camera 2 detection
        buf.update_and_evaluate(
            track_id=10,
            object_type="PHONE",
            confidence=0.60,
            current_ts=ts,
            camera_id="camera_2"
        )
        self.assertEqual(buf._tracks["camera_2_trk_10"].consecutive_frames, 1)

        # Frame 2: Missed detection for Camera 2 (age_missing_tracks called)
        buf.age_missing_tracks(active_keys_seen=set(), current_camera_id="camera_2")
        # Streak should NOT be reset to 0 after 1 missed frame on Camera 2!
        self.assertEqual(buf._tracks["camera_2_trk_10"].consecutive_frames, 1)
        self.assertEqual(buf._tracks["camera_2_trk_10"].missing_frames, 1)

        # Frame 3: Seen again!
        confirmed, frames, dur, reason = buf.update_and_evaluate(
            track_id=10,
            object_type="PHONE",
            confidence=0.60,
            current_ts=ts + 0.70,
            camera_id="camera_2"
        )
        # Streak accumulates to 2 and confirms!
        self.assertEqual(frames, 2)
        self.assertTrue(confirmed)

    def test_04_camera2_clear_camera_purges_stale_tracks(self):
        """Verify clear_camera purges camera_2 tracks without affecting camera_1 tracks."""
        # Test tracker
        trk = ByteTrackTracker(ObjectTrackingConfig(enable_logging=False))
        trk.initialize()
        trk._tracks_by_camera["camera_1"] = {1: TrackedObject(tracking_id=1, object_type=DetectedObjectType.PERSON, confidence=0.9, bbox=BoundingBox(0, 0, 10, 10))}
        trk._tracks_by_camera["camera_2"] = {2: TrackedObject(tracking_id=2, object_type=DetectedObjectType.CELL_PHONE, confidence=0.7, bbox=BoundingBox(0, 0, 10, 10))}
        trk._tracks = {1: trk._tracks_by_camera["camera_1"][1], 2: trk._tracks_by_camera["camera_2"][2]}

        trk.clear_camera("camera_2")
        self.assertNotIn(2, trk._tracks)
        self.assertIn(1, trk._tracks)

        # Test temporal buffer
        buf = TemporalConfirmationBuffer(ObjectValidationConfig(enable_logging=False))
        buf.update_and_evaluate(track_id=1, object_type="PERSON", confidence=0.9, current_ts=1.0, camera_id="camera_1")
        buf.update_and_evaluate(track_id=2, object_type="CELL_PHONE", confidence=0.7, current_ts=1.0, camera_id="camera_2")

        self.assertIn("camera_1_trk_1", buf._tracks)
        self.assertIn("camera_2_trk_2", buf._tracks)

        buf.clear_camera("camera_2")
        self.assertIn("camera_1_trk_1", buf._tracks)
        self.assertNotIn("camera_2_trk_2", buf._tracks)

    def test_05_camera2_tracking_confidence_accepts_low_distant_detections(self):
        """Verify ByteTrackTracker with camera_2 uses effective_tracking_conf (0.22) to spawn tracks."""
        cfg = ObjectTrackingConfig(tracking_confidence=0.35, cam2_tracking_confidence=0.22, enable_logging=False)
        tracker = ByteTrackTracker(cfg)
        tracker.initialize()

        ctx = ExamContext()
        ctx.current_frame = Frame.from_bgr_image(self.blank_img, frame_id=1, camera_id="camera_2")
        # Detection at 0.28 confidence (between 0.22 and 0.35)
        det = DetectedObject(
            object_type=DetectedObjectType.CELL_PHONE,
            confidence=0.28,
            bbox=BoundingBox(x=10, y=10, width=30, height=30)
        )
        oi = ctx.object_info
        oi.filtered_detections = [det]
        ctx.object_info = oi

        tracker.process(ctx)
        # Should spawn a new track because 0.28 >= 0.22 cam2_tracking_confidence
        self.assertEqual(len(ctx.object_info.tracked_objects), 1)
        self.assertEqual(ctx.object_info.tracked_objects[0].current_state, "NEW")


if __name__ == "__main__":
    unittest.main()

