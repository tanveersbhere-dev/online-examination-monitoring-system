import pytest
import time
from unittest.mock import patch, MagicMock

from ai_engine.core.exam_context import ExamContext, TrackedObject, BoundingBox
from ai_engine.core.enums import DetectedObjectType
from ai_engine.camera.frame import Frame
from ai_engine.environment.evidence.models import EvidenceConfig
from ai_engine.environment.evidence.snapshot_manager import EvidenceSnapshotManager
from ai_engine.environment.evidence.exceptions import EvidenceManagerError

@pytest.fixture
def config():
    return EvidenceConfig(
        snapshot_directory="test_snapshots",
        jpeg_quality=90,
        max_snapshots_per_object=3,
        enable_logging=False
    )

@pytest.fixture
def manager(config):
    mgr = EvidenceSnapshotManager(config)
    mgr.initialize()
    mgr.start()
    return mgr

@pytest.fixture
def context():
    ctx = ExamContext()
    ctx.object_info.frame_id = 1
    
    # Mock Frame
    mock_frame = MagicMock(spec=Frame)
    mock_frame.original_frame = MagicMock() # Mock numpy array
    mock_frame.original_frame.copy.return_value = MagicMock()
    ctx.current_frame = mock_frame
    
    return ctx

def test_manager_lifecycle(config):
    mgr = EvidenceSnapshotManager(config)
    assert not mgr.is_initialized
    mgr.initialize()
    assert mgr.is_initialized
    mgr.start()
    mgr.stop()
    mgr.cleanup()
    assert not mgr.is_initialized

@patch('ai_engine.environment.evidence.snapshot_manager.cv2', create=True)
def test_track_confirmed_snapshot(mock_cv2, manager, context):
    mock_cv2.imwrite.return_value = True
    
    # Simulating a new track that gets confirmed
    track = TrackedObject(
        tracking_id=1,
        object_type=DetectedObjectType.PERSON,
        bbox=BoundingBox(10, 10, 50, 50),
        confidence=0.8,
        current_state="TRACKED",
        first_detection_timestamp=time.time(),
        last_detection_timestamp=time.time(),
        visible_duration=0.5,
        consecutive_frames=5,
        lost_frames=0,
        motion_status="STATIONARY",
        frame_id=1
    )
    context.object_info.tracked_objects = [track]
    
    manager.process(context)
    
    evidence = getattr(context.object_info, "evidence", [])
    assert len(evidence) == 1
    assert evidence[0].snapshot_reason == "Track Confirmed"
    assert evidence[0].track_id == 1

@patch('ai_engine.environment.evidence.snapshot_manager.cv2', create=True)
def test_highest_confidence_snapshot(mock_cv2, manager, context):
    mock_cv2.imwrite.return_value = True
    
    # Frame 1: Confirmed with 0.7 conf
    t1 = TrackedObject(
        tracking_id=1, object_type=DetectedObjectType.PERSON,
        bbox=BoundingBox(10, 10, 50, 50), confidence=0.7,
        current_state="TRACKED", first_detection_timestamp=time.time(),
        last_detection_timestamp=time.time(), visible_duration=0.5,
        consecutive_frames=5, lost_frames=0, motion_status="STATIONARY", frame_id=1
    )
    context.object_info.tracked_objects = [t1]
    manager.process(context)
    
    # Should have 1 snapshot for Track Confirmed
    assert len(context.object_info.evidence) == 1
    
    # Frame 2: Higher conf (0.9)
    t2 = TrackedObject(
        tracking_id=1, object_type=DetectedObjectType.PERSON,
        bbox=BoundingBox(10, 10, 50, 50), confidence=0.9,
        current_state="TRACKED", first_detection_timestamp=time.time(),
        last_detection_timestamp=time.time(), visible_duration=1.0,
        consecutive_frames=6, lost_frames=0, motion_status="STATIONARY", frame_id=2
    )
    context.object_info.tracked_objects = [t2]
    
    # Clear previous frame's evidence list for clear testing
    context.object_info.evidence = []
    
    manager.process(context)
    
    assert len(context.object_info.evidence) == 1
    assert context.object_info.evidence[0].snapshot_reason == "Highest Confidence Observation"

@patch('ai_engine.environment.evidence.snapshot_manager.cv2', create=True)
def test_largest_area_snapshot(mock_cv2, manager, context):
    mock_cv2.imwrite.return_value = True
    
    # Frame 1: Confirmed with area 2500 (50x50)
    t1 = TrackedObject(
        tracking_id=2, object_type=DetectedObjectType.PERSON,
        bbox=BoundingBox(10, 10, 50, 50), confidence=0.8,
        current_state="TRACKED", first_detection_timestamp=time.time(),
        last_detection_timestamp=time.time(), visible_duration=0.5,
        consecutive_frames=5, lost_frames=0, motion_status="STATIONARY", frame_id=1
    )
    context.object_info.tracked_objects = [t1]
    manager.process(context)
    
    context.object_info.evidence = []
    
    # Frame 2: Same conf, but much larger area (100x100 = 10000)
    t2 = TrackedObject(
        tracking_id=2, object_type=DetectedObjectType.PERSON,
        bbox=BoundingBox(10, 10, 100, 100), confidence=0.8,
        current_state="TRACKED", first_detection_timestamp=time.time(),
        last_detection_timestamp=time.time(), visible_duration=1.0,
        consecutive_frames=6, lost_frames=0, motion_status="STATIONARY", frame_id=2
    )
    context.object_info.tracked_objects = [t2]
    
    manager.process(context)
    
    assert len(context.object_info.evidence) == 1
    assert context.object_info.evidence[0].snapshot_reason == "Largest Visible Bounding Box"

@patch('ai_engine.environment.evidence.snapshot_manager.cv2', create=True)
def test_track_removed_snapshot(mock_cv2, manager, context):
    mock_cv2.imwrite.return_value = True
    
    # Frame 1: Confirmed
    t1 = TrackedObject(
        tracking_id=3, object_type=DetectedObjectType.PERSON,
        bbox=BoundingBox(10, 10, 50, 50), confidence=0.8,
        current_state="TRACKED", first_detection_timestamp=time.time(),
        last_detection_timestamp=time.time(), visible_duration=0.5,
        consecutive_frames=5, lost_frames=0, motion_status="STATIONARY", frame_id=1
    )
    context.object_info.tracked_objects = [t1]
    manager.process(context)
    context.object_info.evidence = []
    
    # Frame 2: REMOVED
    t2 = TrackedObject(
        tracking_id=3, object_type=DetectedObjectType.PERSON,
        bbox=BoundingBox(10, 10, 50, 50), confidence=0.8,
        current_state="REMOVED", first_detection_timestamp=time.time(),
        last_detection_timestamp=time.time(), visible_duration=1.0,
        consecutive_frames=0, lost_frames=10, motion_status="STATIONARY", frame_id=2
    )
    context.object_info.tracked_objects = [t2]
    manager.process(context)
    
    assert len(context.object_info.evidence) == 1
    assert context.object_info.evidence[0].snapshot_reason == "Track Removed"
    
    # Frame 3: Disappeared (cleanup check)
    context.object_info.tracked_objects = []
    manager.process(context)
    assert 3 not in manager._track_states

@patch('ai_engine.environment.evidence.snapshot_manager.cv2', create=True)
def test_snapshot_limit(mock_cv2, manager, context):
    mock_cv2.imwrite.return_value = True
    # Max snapshots is set to 3 in fixture
    
    t = TrackedObject(
        tracking_id=4, object_type=DetectedObjectType.PERSON,
        bbox=BoundingBox(10, 10, 50, 50), confidence=0.7,
        current_state="TRACKED", first_detection_timestamp=time.time(),
        last_detection_timestamp=time.time(), visible_duration=0.5,
        consecutive_frames=5, lost_frames=0, motion_status="STATIONARY", frame_id=1
    )
    context.object_info.tracked_objects = [t]
    
    # 1st - Confirmed
    manager.process(context)
    
    # 2nd - Higher Conf
    t.confidence = 0.8
    manager.process(context)
    
    # 3rd - Even Higher Conf
    t.confidence = 0.9
    manager.process(context)
    
    assert len(context.object_info.evidence) == 3
    
    # 4th - Highest Conf, but max limit reached
    t.confidence = 0.99
    manager.process(context)
    
    # Should still be 3
    assert len(context.object_info.evidence) == 3
