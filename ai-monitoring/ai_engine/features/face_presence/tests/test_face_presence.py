"""
Unit tests for the Temporal Face Presence Processor.
"""
import pytest
import time

from ai_engine.core.exam_context import ExamContext, FaceInfo
from ai_engine.features.face_presence.models import FacePresenceConfig
from ai_engine.features.face_presence.temporal_processor import TemporalFacePresenceProcessor
from ai_engine.features.face_presence.result import PresenceState
from ai_engine.features.face_presence.exceptions import FacePresenceError

@pytest.fixture
def config():
    return FacePresenceConfig(
        max_missing_frames=3,
        max_absence_duration_ms=500.0,
        min_face_confidence=0.5,
        presence_stability_window_frames=2,
        edge_margin=0.05,
        enable_logging=False
    )

@pytest.fixture
def processor(config):
    proc = TemporalFacePresenceProcessor(config)
    proc.initialize()
    proc.start()
    return proc

@pytest.fixture
def exam_context():
    ctx = ExamContext()
    ctx.face_info = FaceInfo(
        face_count=1,
        confidence=0.9,
        bbox=(0.2, 0.2, 0.5, 0.5),
        detection_timestamp=100.0
    )
    return ctx

def test_initialization_and_cleanup(config):
    proc = TemporalFacePresenceProcessor(config)
    assert not proc.is_initialized
    
    proc.initialize()
    assert proc.is_initialized
    
    proc.cleanup()
    assert not proc.is_initialized

def test_process_uninitialized(config, exam_context):
    proc = TemporalFacePresenceProcessor(config)
    with pytest.raises(FacePresenceError, match="Processor is not initialized"):
        proc.process(exam_context)

def test_face_continuously_present(processor, exam_context):
    # Frame 1
    processor.process(exam_context)
    assert exam_context.face_info.presence_state == PresenceState.PRESENT
    assert exam_context.face_info.consecutive_present_frames == 1
    assert not exam_context.face_info.partial_visibility_flag
    assert not exam_context.face_info.occlusion_flag
    
    # Frame 2
    exam_context.face_info.detection_timestamp = 100.1
    processor.process(exam_context)
    assert exam_context.face_info.presence_state == PresenceState.PRESENT
    assert exam_context.face_info.consecutive_present_frames == 2
    assert exam_context.face_info.present_duration > 0.0

def test_temporary_disappearance(processor, exam_context):
    # Frame 1: Present
    processor.process(exam_context)
    
    # Frame 2: Missing (but < max_missing_frames)
    exam_context.face_info.face_count = 0
    exam_context.face_info.confidence = 0.0
    exam_context.face_info.detection_timestamp = 100.1
    processor.process(exam_context)
    
    assert exam_context.face_info.consecutive_missing_frames == 1
    # Still state PRESENT (tolerating small gap)
    assert exam_context.face_info.presence_state == PresenceState.PRESENT
    
    # Frame 3: Present again
    exam_context.face_info.face_count = 1
    exam_context.face_info.confidence = 0.9
    exam_context.face_info.detection_timestamp = 100.2
    processor.process(exam_context)
    
    assert exam_context.face_info.presence_state == PresenceState.PRESENT
    assert exam_context.face_info.consecutive_missing_frames == 0

def test_long_absence(processor, exam_context):
    # Frame 1: Present
    processor.process(exam_context)
    
    # Missing for max_missing_frames
    exam_context.face_info.face_count = 0
    exam_context.face_info.confidence = 0.0
    for i in range(processor.config.max_missing_frames):
        exam_context.face_info.detection_timestamp = 100.1 + (i * 0.1)
        processor.process(exam_context)
        
    assert exam_context.face_info.presence_state == PresenceState.MISSING
    assert exam_context.face_info.absent_duration > 0.0
    assert exam_context.face_info.longest_absence > 0.0
    
    # Restore presence (requires presence_stability_window_frames)
    exam_context.face_info.face_count = 1
    exam_context.face_info.confidence = 0.9
    
    # 1st frame present (state still MISSING)
    exam_context.face_info.detection_timestamp += 0.1
    processor.process(exam_context)
    assert exam_context.face_info.presence_state == PresenceState.MISSING
    
    # 2nd frame present (stability window met)
    exam_context.face_info.detection_timestamp += 0.1
    processor.process(exam_context)
    assert exam_context.face_info.presence_state == PresenceState.PRESENT

def test_partial_face_visibility(processor, exam_context):
    # Move bbox to edge (x=0.01 < margin=0.05)
    exam_context.face_info.bbox = (0.01, 0.2, 0.5, 0.5)
    processor.process(exam_context)
    assert exam_context.face_info.partial_visibility_flag

def test_occluded_face(processor, exam_context):
    # Face detected but low confidence (e.g., 0.6 < 0.7)
    exam_context.face_info.confidence = 0.6
    processor.process(exam_context)
    assert exam_context.face_info.occlusion_flag

def test_low_confidence_detections(processor, exam_context):
    # Face count 1 but confidence < min_confidence (0.4 < 0.5)
    exam_context.face_info.confidence = 0.4
    processor.process(exam_context)
    
    # Treated as not present
    assert exam_context.face_info.consecutive_missing_frames == 1
    # Also flagged as occluded because it was detected but low conf
    assert exam_context.face_info.occlusion_flag

def test_missing_input_no_face_count(processor, exam_context):
    # Initialize with no faces
    exam_context.face_info = FaceInfo()
    processor.process(exam_context)
    
    assert exam_context.face_info.consecutive_missing_frames == 1
