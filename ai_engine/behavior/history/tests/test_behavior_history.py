"""
Unit tests for the Behavior History Engine.
"""
import pytest
import time

from ai_engine.core.exam_context import ExamContext, HeadPoseInfo, EyeInfo, MouthInfo, FaceInfo
from ai_engine.behavior.history.models import BehaviorHistoryConfig
from ai_engine.behavior.history.rolling_window import RollingWindow
from ai_engine.behavior.history.temporal_history import TemporalHistoryProcessor
from ai_engine.behavior.history.exceptions import BehaviorHistoryError, HistoryOverflowError

@pytest.fixture
def config():
    return BehaviorHistoryConfig(
        window_sizes_seconds=[1, 5],
        max_history_capacity=100,
        enable_logging=False
    )

@pytest.fixture
def processor(config):
    proc = TemporalHistoryProcessor(config)
    proc.initialize()
    proc.start()
    return proc

@pytest.fixture
def exam_context():
    ctx = ExamContext()
    
    ctx.head_pose_info = HeadPoseInfo(pitch=10.0, yaw=5.0, roll=0.0)
    
    eye = EyeInfo()
    eye.horizontal_ratio = 0.5
    eye.vertical_ratio = 0.5
    eye.ear = 0.3
    eye.blink_detected = False
    ctx.eye_info = eye
    
    mouth = MouthInfo()
    mouth.mar = 0.1
    ctx.mouth_info = mouth
    
    face = FaceInfo()
    face.presence_state = "PRESENT"
    face.identity_consistent = True
    ctx.face_info = face
    
    return ctx

def test_rolling_window_appends_and_prunes():
    window = RollingWindow(window_size_seconds=1.0, max_capacity=10)
    current_time = 100.0
    
    # Add values over 2 seconds
    window.append(current_time, 1.0)
    window.append(current_time + 0.5, 2.0)
    window.append(current_time + 1.5, 3.0) # Should prune first value
    
    values = window.get_values()
    assert len(values) == 2
    assert values == [2.0, 3.0]

def test_rolling_window_statistics():
    window = RollingWindow(window_size_seconds=5.0, max_capacity=10)
    current_time = 100.0
    
    window.append(current_time, 2.0)
    window.append(current_time + 1.0, 4.0)
    window.append(current_time + 2.0, 6.0)
    
    summary = window.calculate_statistics(current_time + 2.0)
    assert summary.minimum == 2.0
    assert summary.maximum == 6.0
    assert summary.mean == 4.0
    assert summary.median == 4.0
    assert summary.std_dev == 2.0
    assert summary.recent_trend > 0.0

def test_rolling_window_overflow():
    window = RollingWindow(window_size_seconds=10.0, max_capacity=3)
    current_time = 100.0
    
    window.append(current_time, 1.0)
    window.append(current_time + 0.1, 2.0)
    window.append(current_time + 0.2, 3.0)
    
    with pytest.raises(HistoryOverflowError):
         window.append(current_time + 0.3, 4.0)

def test_temporal_history_processor_initialization_and_cleanup(config):
    proc = TemporalHistoryProcessor(config)
    assert not proc.is_initialized
    
    proc.initialize()
    assert proc.is_initialized
    assert len(proc._windows) > 0
    
    proc.cleanup()
    assert not proc.is_initialized
    assert len(proc._windows) == 0

def test_temporal_history_process(processor, exam_context):
    processor.process(exam_context)
    
    history = exam_context.behavior_history
    assert len(history.summaries) > 0
    assert "head_pose_pitch" in history.summaries
    
    # Check 1 second window for pitch
    pitch_summary_1s = history.summaries["head_pose_pitch"][1]
    assert pitch_summary_1s.mean == 10.0
    
    # Process another frame with updated values
    exam_context.head_pose_info = HeadPoseInfo(pitch=20.0, yaw=5.0, roll=0.0)
    processor.process(exam_context)
    
    history = exam_context.behavior_history
    pitch_summary_1s = history.summaries["head_pose_pitch"][1]
    assert pitch_summary_1s.mean == 15.0 # (10 + 20) / 2

def test_empty_history(processor, exam_context):
    # First frame, history will only have 1 item
    processor.process(exam_context)
    
    summary = exam_context.behavior_history.summaries["head_pose_pitch"][1]
    assert summary.std_dev == 0.0 # Only 1 element, no stdev

def test_boolean_statistics(processor, exam_context):
    exam_context.eye_info.blink_detected = True
    processor.process(exam_context)
    
    history = exam_context.behavior_history
    blink_summary = history.summaries["blink_detected"][1]
    assert blink_summary.event_frequency == 1
    
    exam_context.eye_info.blink_detected = False
    processor.process(exam_context)
    
    history = exam_context.behavior_history
    blink_summary = history.summaries["blink_detected"][1]
    assert blink_summary.event_frequency == 1 # Still 1 true event in window

def test_processor_restart(config, processor, exam_context):
    processor.process(exam_context)
    assert len(processor._windows["head_pose_pitch"][1]._data) == 1
    
    processor.start() # Should clear windows
    assert len(processor._windows["head_pose_pitch"][1]._data) == 0
