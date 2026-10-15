"""
Unit tests for the Object Tracking Module.
"""
import pytest
import time

from ai_engine.core.exam_context import ExamContext, FilteredObject, BoundingBox
from ai_engine.core.enums import DetectedObjectType
from ai_engine.environment.object_tracking.models import ObjectTrackingConfig
from ai_engine.environment.object_tracking.bytetrack_tracker import ByteTrackTracker
from ai_engine.environment.object_tracking.exceptions import ObjectTrackingError

def set_filtered(ctx: ExamContext, detections: list, frame_id: int = None):
    oi = ctx.object_info
    oi.filtered_detections = detections
    if frame_id is not None:
        oi.frame_id = frame_id
    ctx.object_info = oi

@pytest.fixture
def config():
    return ObjectTrackingConfig(
        tracking_confidence=0.5,
        max_lost_frames=2,
        min_confirmed_frames=2,
        tracking_timeout=1.0,
        matching_threshold=0.5,
        enable_logging=False
    )

@pytest.fixture
def tracker(config):
    trk = ByteTrackTracker(config)
    trk.initialize()
    trk.start()
    return trk

@pytest.fixture
def exam_context():
    ctx = ExamContext()
    oi = ctx.object_info
    oi.frame_id = 1
    ctx.object_info = oi
    return ctx

def test_initialization_and_cleanup(config):
    trk = ByteTrackTracker(config)
    
    assert not trk.is_initialized
    trk.initialize()
    assert trk.is_initialized
    
    trk.cleanup()
    assert not trk.is_initialized
    assert len(trk._tracks) == 0

def test_track_creation(tracker, exam_context):
    set_filtered(exam_context, [
        FilteredObject(
            object_type=DetectedObjectType.PERSON,
            confidence=0.9,
            bbox=BoundingBox(10, 10, 50, 50),
            detection_timestamp=time.time(),
            frame_id=1
        )
    ])
    
    tracker.process(exam_context)
    
    tracked = exam_context.object_info.tracked_objects
    assert len(tracked) == 1
    assert tracked[0].current_state == 'NEW'
    assert tracked[0].tracking_id == 1
    assert tracked[0].consecutive_frames == 1
    assert tracked[0].lost_frames == 0
    
    stats = exam_context.object_info.tracking_statistics
    assert stats.new_tracks == 1
    assert stats.active_tracks == 1

def test_track_update(tracker, exam_context):
    # Frame 1: Creation
    set_filtered(exam_context, [
        FilteredObject(
            object_type=DetectedObjectType.PERSON,
            confidence=0.9,
            bbox=BoundingBox(10, 10, 50, 50),
            detection_timestamp=time.time(),
            frame_id=1
        )
    ], frame_id=1)
    tracker.process(exam_context)
    
    # Frame 2: Update (slight movement, high IoU)
    set_filtered(exam_context, [
        FilteredObject(
            object_type=DetectedObjectType.PERSON,
            confidence=0.95,
            bbox=BoundingBox(12, 12, 50, 50),
            detection_timestamp=time.time(),
            frame_id=2
        )
    ], frame_id=2)
    tracker.process(exam_context)
    
    tracked = exam_context.object_info.tracked_objects
    assert len(tracked) == 1
    assert tracked[0].current_state == 'TRACKED'
    assert tracked[0].tracking_id == 1
    assert tracked[0].consecutive_frames == 2
    assert tracked[0].confidence == 0.95

def test_track_loss_and_recovery(tracker, exam_context):
    # Frame 1: Create
    set_filtered(exam_context, [
        FilteredObject(object_type=DetectedObjectType.PERSON, confidence=0.9, bbox=BoundingBox(10, 10, 50, 50), detection_timestamp=time.time())
    ])
    tracker.process(exam_context)
    
    # Frame 2: Lost (no detections)
    set_filtered(exam_context, [])
    tracker.process(exam_context)
    
    tracked = exam_context.object_info.tracked_objects
    assert len(tracked) == 1
    assert tracked[0].current_state == 'LOST'
    assert tracked[0].lost_frames == 1
    
    # Frame 3: Recovered (detection returns)
    set_filtered(exam_context, [
        FilteredObject(object_type=DetectedObjectType.PERSON, confidence=0.9, bbox=BoundingBox(10, 10, 50, 50), detection_timestamp=time.time())
    ])
    tracker.process(exam_context)
    
    tracked = exam_context.object_info.tracked_objects
    assert len(tracked) == 1
    assert tracked[0].current_state == 'TRACKED'
    assert tracked[0].lost_frames == 0
    assert exam_context.object_info.tracking_statistics.recovered_tracks == 1

def test_track_removal(config, tracker, exam_context):
    config.max_lost_frames = 1
    
    # Frame 1: Create
    set_filtered(exam_context, [
        FilteredObject(object_type=DetectedObjectType.PERSON, confidence=0.9, bbox=BoundingBox(10, 10, 50, 50), detection_timestamp=time.time())
    ])
    tracker.process(exam_context)
    
    # Frame 2: Lost (exceeds max_lost_frames since it becomes 1 and max is 1)
    set_filtered(exam_context, [])
    tracker.process(exam_context)
    
    tracked = exam_context.object_info.tracked_objects
    assert len(tracked) == 0 # REMOVED tracks are dropped from active output
    assert exam_context.object_info.tracking_statistics.removed_tracks == 1
    assert len(tracker._tracks) == 0 # internal cleanup happened

def test_multiple_objects(tracker, exam_context):
    set_filtered(exam_context, [
        FilteredObject(object_type=DetectedObjectType.PERSON, confidence=0.9, bbox=BoundingBox(10, 10, 50, 50), detection_timestamp=time.time()),
        FilteredObject(object_type=DetectedObjectType.CELL_PHONE, confidence=0.8, bbox=BoundingBox(100, 100, 20, 20), detection_timestamp=time.time())
    ])
    tracker.process(exam_context)
    
    tracked = exam_context.object_info.tracked_objects
    assert len(tracked) == 2
    assert exam_context.object_info.tracking_statistics.active_tracks == 2
    
    ids = [t.tracking_id for t in tracked]
    assert 1 in ids
    assert 2 in ids
