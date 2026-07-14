"""
Unit tests for the Temporal Blink Detection Processor.
"""
import pytest
import time

from ai_engine.core.exam_context import ExamContext, EyeInfo
from ai_engine.features.blink_detection.models import BlinkDetectionConfig
from ai_engine.features.blink_detection.temporal_processor import TemporalBlinkProcessor
from ai_engine.features.blink_detection.result import BlinkState
from ai_engine.features.blink_detection.exceptions import BlinkDetectionError, InvalidEARDataError


@pytest.fixture
def config():
    return BlinkDetectionConfig(
        ear_threshold=0.20,
        min_consecutive_frames=2,
        min_blink_duration_ms=50.0,
        max_blink_duration_ms=500.0,
        frequency_window_seconds=60.0,
        enable_logging=False
    )

@pytest.fixture
def processor(config):
    proc = TemporalBlinkProcessor(config)
    proc.initialize()
    proc.start()
    return proc

@pytest.fixture
def exam_context():
    ctx = ExamContext()
    ctx.eye_info = EyeInfo(ear_confidence=1.0) # Set confidence to 1.0 to simulate detected face
    return ctx

def test_initialization_and_cleanup(config):
    proc = TemporalBlinkProcessor(config)
    assert not proc.is_initialized
    
    proc.initialize()
    assert proc.is_initialized
    
    proc.cleanup()
    assert not proc.is_initialized

def test_process_uninitialized(config, exam_context):
    proc = TemporalBlinkProcessor(config)
    with pytest.raises(BlinkDetectionError, match="Processor is not initialized"):
        proc.process(exam_context)

def test_no_face_no_blink(processor, exam_context):
    # confidence 0 and ear 0
    exam_context.eye_info = EyeInfo(average_ear=0.0, ear_confidence=0.0)
    processor.process(exam_context)
    
    eye_info = exam_context.eye_info
    assert not eye_info.blink_detected
    assert eye_info.blink_count == 0
    assert eye_info.consecutive_closed_frames == 0
    assert eye_info.eye_state == BlinkState.OPEN

def test_invalid_ear(processor, exam_context):
    exam_context.eye_info = EyeInfo(average_ear=-0.1)
    with pytest.raises(InvalidEARDataError, match="Invalid EAR value"):
        processor.process(exam_context)

def test_normal_blink(processor, exam_context):
    # Frame 1: Open
    exam_context.eye_info = EyeInfo(average_ear=0.30, processing_timestamp=100.0)
    processor.process(exam_context)
    assert exam_context.eye_info.eye_state == BlinkState.OPEN
    
    # Frame 2: Closed (below threshold 0.20)
    exam_context.eye_info = EyeInfo(average_ear=0.15, processing_timestamp=100.033)
    processor.process(exam_context)
    # min consecutive frames is 2, so still OPEN
    assert exam_context.eye_info.eye_state == BlinkState.OPEN
    
    # Frame 3: Closed
    exam_context.eye_info = EyeInfo(average_ear=0.10, processing_timestamp=100.066)
    processor.process(exam_context)
    # Now it should be CLOSED
    assert exam_context.eye_info.eye_state == BlinkState.CLOSED
    assert not exam_context.eye_info.blink_detected
    
    # Frame 4: Open (blink finishes) -> duration = 100.100 - 100.066 = 0.034s = 34ms (wait, threshold is 50ms)
    # Let's make duration longer to pass min_blink_duration_ms=50.0
    exam_context.eye_info = EyeInfo(average_ear=0.30, processing_timestamp=100.200) # 134ms diff
    processor.process(exam_context)
    
    eye_info = exam_context.eye_info
    assert eye_info.eye_state == BlinkState.OPEN
    assert eye_info.blink_detected
    assert eye_info.blink_count == 1
    assert eye_info.blink_duration > 0.0
    assert eye_info.blink_duration < processor.config.max_blink_duration_ms
    assert eye_info.consecutive_closed_frames == 0

def test_fast_blink_invalid(processor, exam_context):
    # Fast blink (duration < 50ms)
    exam_context.eye_info = EyeInfo(average_ear=0.15, processing_timestamp=100.0)
    processor.process(exam_context)
    exam_context.eye_info = EyeInfo(average_ear=0.10, processing_timestamp=100.010)
    processor.process(exam_context)
    # Eye is closed
    assert exam_context.eye_info.eye_state == BlinkState.CLOSED
    
    # Eye opens very quickly (10ms later)
    exam_context.eye_info = EyeInfo(average_ear=0.30, processing_timestamp=100.020)
    processor.process(exam_context)
    
    # Should not count as blink
    assert not exam_context.eye_info.blink_detected
    assert exam_context.eye_info.blink_count == 0

def test_continuous_closure_invalid(processor, exam_context):
    # Eye closed for a long time (duration > 500ms)
    exam_context.eye_info = EyeInfo(average_ear=0.15, processing_timestamp=100.0)
    processor.process(exam_context)
    exam_context.eye_info = EyeInfo(average_ear=0.10, processing_timestamp=100.033)
    processor.process(exam_context)
    
    assert exam_context.eye_info.eye_state == BlinkState.CLOSED
    
    # Eye opens 1 second later
    exam_context.eye_info = EyeInfo(average_ear=0.30, processing_timestamp=101.033)
    processor.process(exam_context)
    
    # Should not count as blink (it's a long closure)
    assert not exam_context.eye_info.blink_detected
    assert exam_context.eye_info.blink_count == 0

def test_temporal_buffer_reset(processor, exam_context):
    exam_context.eye_info = EyeInfo(average_ear=0.10, processing_timestamp=100.0)
    processor.process(exam_context)
    assert exam_context.eye_info.consecutive_closed_frames == 1
    
    processor.cleanup()
    processor.initialize()
    processor.start()
    
    exam_context.eye_info = EyeInfo(average_ear=0.30, processing_timestamp=101.0)
    processor.process(exam_context)
    assert exam_context.eye_info.consecutive_closed_frames == 0
    assert exam_context.eye_info.blink_count == 0
