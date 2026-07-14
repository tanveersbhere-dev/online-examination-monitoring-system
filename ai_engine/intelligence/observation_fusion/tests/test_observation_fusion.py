import pytest
from unittest.mock import MagicMock

from ai_engine.core.exam_context import ExamContext, TrackedObject, BoundingBox
from ai_engine.core.enums import DetectedObjectType
from ai_engine.intelligence.observation_fusion.models import ObservationFusionConfig
from ai_engine.intelligence.observation_fusion.fusion_processor import FusionProcessor
from ai_engine.intelligence.observation_fusion.exceptions import ObservationFusionError, MissingObservationError, InvalidObservationError

@pytest.fixture
def config_all():
    return ObservationFusionConfig(
        enable_face=True,
        enable_environment=True,
        enable_audio=True,
        enable_logging=False
    )

@pytest.fixture
def config_partial():
    return ObservationFusionConfig(
        enable_face=True,
        enable_environment=False,
        enable_audio=False,
        enable_logging=False
    )

@pytest.fixture
def context_complete():
    ctx = ExamContext()
    ctx.face_info.face_detected = True
    ctx.face_info.confidence = 0.95
    ctx.eye_info.gaze_confidence = 0.8
    ctx.eye_info.blink_detected = False
    ctx.head_pose_info.pose_class = "FORWARD"
    
    t = TrackedObject(
        tracking_id=1, object_type=DetectedObjectType.CELL_PHONE,
        bbox=BoundingBox(), confidence=0.9,
        current_state="TRACKED", first_detection_timestamp=1.0,
        last_detection_timestamp=1.0, visible_duration=0.0,
        consecutive_frames=1, lost_frames=0, motion_status="STATIONARY"
    )
    ctx.object_info.tracked_objects = [t]
    
    ctx.audio_info.is_speaking = True
    ctx.audio_info.db_level = -20.0
    return ctx

def test_processor_lifecycle(config_all):
    processor = FusionProcessor(config_all)
    assert not processor.is_initialized
    processor.initialize()
    assert processor.is_initialized
    processor.start()
    processor.stop()
    processor.cleanup()
    assert not processor.is_initialized

def test_fusion_all_enabled(config_all, context_complete):
    processor = FusionProcessor(config_all)
    processor.initialize()
    processor.start()
    
    processor.process(context_complete)
    
    obs = context_complete.observation
    assert obs is not None
    assert obs.face.face_present is True
    assert obs.face.face_confidence == 0.95
    assert obs.environment.phone_present is True
    assert obs.audio.is_speaking is True
    
    # Check overall confidence logic
    assert obs.confidence_summary.overall_confidence > 0.0

def test_fusion_missing_observation_error(config_all):
    processor = FusionProcessor(config_all)
    processor.initialize()
    
    ctx = ExamContext()
    # Explicitly remove face_info which shouldn't happen natively, but testing bounds
    delattr(ctx, "face_info")
    
    with pytest.raises(MissingObservationError):
        processor.process(ctx)

def test_fusion_partial_config(config_partial, context_complete):
    processor = FusionProcessor(config_partial)
    processor.initialize()
    
    processor.process(context_complete)
    
    obs = context_complete.observation
    assert obs.face is not None
    assert obs.environment is None
    assert obs.audio is None

def test_fusion_missing_optional_audio(config_all, context_complete):
    processor = FusionProcessor(config_all)
    processor.initialize()
    
    # Audio is marked enable_audio=True in config_all, but if missing it should still process since audio is explicitly optional 
    # Wait, in the implementation we warn but continue if enable_audio is True and it's missing?
    # No, audio_info is ALWAYS on context by default. If we delattr it:
    delattr(context_complete, "audio_info")
    
    processor.process(context_complete)
    obs = context_complete.observation
    assert obs.audio is None
    # Ensure it doesn't crash
