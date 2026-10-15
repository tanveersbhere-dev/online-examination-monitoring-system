import pytest
import time
from unittest.mock import MagicMock

from ai_engine.core.exam_context import ExamContext, TrackedObject, BoundingBox
from ai_engine.core.enums import DetectedObjectType
from ai_engine.environment.history.models import HistoryConfig
from ai_engine.environment.history.temporal_history import TemporalHistoryEngine
from ai_engine.environment.history.exceptions import EnvironmentHistoryError, HistoryOverflowError
from ai_engine.environment.history.rolling_window import RollingWindowTimeSeries

@pytest.fixture
def config():
    return HistoryConfig(
        history_window_sizes=[1, 5],
        max_history_size=10,
        cleanup_interval_seconds=0.1,
        summary_interval_seconds=0.0,
        history_expiration_seconds=0.1,
        enable_logging=False
    )

@pytest.fixture
def engine(config):
    eng = TemporalHistoryEngine(config)
    eng.initialize()
    eng.start()
    return eng

@pytest.fixture
def context():
    ctx = ExamContext()
    ctx.object_info.tracked_objects = []
    # Mock evidence
    setattr(ctx.object_info, "evidence", [])
    return ctx

def test_engine_lifecycle(config):
    eng = TemporalHistoryEngine(config)
    assert not eng.is_initialized
    eng.initialize()
    assert eng.is_initialized
    eng.start()
    eng.stop()
    eng.cleanup()
    assert not eng.is_initialized

def test_history_creation_and_update(engine, context):
    # Frame 1
    t1 = TrackedObject(
        tracking_id=1, object_type=DetectedObjectType.PERSON,
        bbox=BoundingBox(10, 10, 50, 50), confidence=0.8,
        current_state="NEW", first_detection_timestamp=time.time(),
        last_detection_timestamp=time.time(), visible_duration=0.0,
        consecutive_frames=1, lost_frames=0, motion_status="STATIONARY", frame_id=1
    )
    context.object_info.tracked_objects = [t1]
    
    engine.process(context)
    history = context.environment_history
    
    assert len(history.object_histories) == 1
    obj_hist = history.object_histories[1]
    assert obj_hist.appearance_count == 1
    assert obj_hist.consecutive_visible_frames == 1
    assert obj_hist.average_detection_confidence == 0.8
    assert obj_hist.max_detection_confidence == 0.8
    assert obj_hist.min_detection_confidence == 0.8
    assert history.statistics.active_object_count == 1
    assert history.statistics.person_count_history[1] == 1

    # Frame 2
    t1.current_state = "TRACKED"
    t1.confidence = 0.9
    
    engine.process(context)
    history = context.environment_history
    
    obj_hist = history.object_histories[1]
    assert obj_hist.appearance_count == 2
    assert obj_hist.consecutive_visible_frames == 2
    assert obj_hist.average_detection_confidence == 0.85
    assert obj_hist.max_detection_confidence == 0.9
    
def test_history_cleanup(engine, context):
    t1 = TrackedObject(
        tracking_id=1, object_type=DetectedObjectType.PERSON,
        bbox=BoundingBox(), confidence=0.8,
        current_state="REMOVED", first_detection_timestamp=time.time(),
        last_detection_timestamp=time.time(), visible_duration=0.0,
        consecutive_frames=0, lost_frames=10, motion_status="STATIONARY", frame_id=1
    )
    context.object_info.tracked_objects = [t1]
    engine.process(context)
    
    assert 1 in context.environment_history.object_histories
    
    time.sleep(0.15) # Wait for expiration
    context.object_info.tracked_objects = []
    
    engine.process(context)
    
    # Should be cleaned up
    assert 1 not in context.environment_history.object_histories

def test_history_overflow(engine, context):
    engine._config.max_history_size = 2
    
    t1 = TrackedObject(tracking_id=1, object_type=DetectedObjectType.PERSON, bbox=BoundingBox(), confidence=0.8, current_state="NEW", first_detection_timestamp=time.time(), last_detection_timestamp=time.time(), visible_duration=0.0, consecutive_frames=1, lost_frames=0, motion_status="STATIONARY")
    t2 = TrackedObject(tracking_id=2, object_type=DetectedObjectType.PERSON, bbox=BoundingBox(), confidence=0.8, current_state="NEW", first_detection_timestamp=time.time(), last_detection_timestamp=time.time(), visible_duration=0.0, consecutive_frames=1, lost_frames=0, motion_status="STATIONARY")
    t3 = TrackedObject(tracking_id=3, object_type=DetectedObjectType.PERSON, bbox=BoundingBox(), confidence=0.8, current_state="NEW", first_detection_timestamp=time.time(), last_detection_timestamp=time.time(), visible_duration=0.0, consecutive_frames=1, lost_frames=0, motion_status="STATIONARY")
    
    context.object_info.tracked_objects = [t1, t2, t3]
    
    with pytest.raises(HistoryOverflowError):
        engine.process(context)

def test_rolling_window():
    rw = RollingWindowTimeSeries(max_duration_seconds=1.0)
    
    rw.add(100.0, 5)
    rw.add(100.2, 10)
    rw.add(100.8, 2)
    
    assert rw.get_max_in_window(101.0, 1.0) == 10  # Window 100.0 -> 101.0
    
    # Push time forward, dropping older entries
    rw.add(101.5, 3)
    
    # At 101.5, looking back 1 second (100.5), the value at 100.0 is dropped.
    assert rw.get_max_in_window(101.5, 1.0) == 10
    
    rw.add(102.5, 1)
    # Looking back 1.0s from 102.5 (101.5), 100.2 and 100.8 are dropped
    assert rw.get_max_in_window(102.5, 1.0) == 3
