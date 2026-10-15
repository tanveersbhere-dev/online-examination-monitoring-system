"""
Unit tests for the Eye Aspect Ratio Processor.
"""
import pytest

from ai_engine.core.exam_context import ExamContext, FaceMeshInfo
from ai_engine.features.eye_aspect_ratio.models import EARConfig
from ai_engine.features.eye_aspect_ratio.mediapipe_processor import MediaPipeEARProcessor
from ai_engine.features.eye_aspect_ratio.exceptions import EARProcessorError, InvalidEyeLandmarksError


@pytest.fixture
def config():
    return EARConfig(enable_logging=False)

@pytest.fixture
def processor(config):
    proc = MediaPipeEARProcessor(config)
    proc.initialize()
    proc.start()
    return proc

@pytest.fixture
def exam_context():
    return ExamContext()

def create_mock_landmarks(face_count=1):
    """Helper to create dummy 468 landmarks."""
    landmarks = [[0.0, 0.0, 0.0] for _ in range(468)]
    
    # Left eye points
    # P1..P6 for left eye (362, 385, 387, 263, 373, 380)
    # Give them some spread so width and height are non-zero
    landmarks[362] = [0.60, 0.50, 0.0] # P1
    landmarks[385] = [0.62, 0.48, 0.0] # P2
    landmarks[387] = [0.65, 0.48, 0.0] # P3
    landmarks[263] = [0.70, 0.50, 0.0] # P4
    landmarks[373] = [0.65, 0.52, 0.0] # P5
    landmarks[380] = [0.62, 0.52, 0.0] # P6
    
    # Right eye points
    # P1..P6 for right eye (33, 160, 158, 133, 153, 144)
    landmarks[33]  = [0.30, 0.50, 0.0] # P1
    landmarks[160] = [0.35, 0.48, 0.0] # P2
    landmarks[158] = [0.38, 0.48, 0.0] # P3
    landmarks[133] = [0.40, 0.50, 0.0] # P4
    landmarks[153] = [0.38, 0.52, 0.0] # P5
    landmarks[144] = [0.35, 0.52, 0.0] # P6
    
    return [landmarks for _ in range(face_count)]


def test_initialization_and_cleanup(config):
    proc = MediaPipeEARProcessor(config)
    assert not proc.is_initialized
    
    proc.initialize()
    assert proc.is_initialized
    
    proc.cleanup()
    assert not proc.is_initialized

def test_process_uninitialized(config, exam_context):
    proc = MediaPipeEARProcessor(config)
    with pytest.raises(EARProcessorError, match="Processor is not initialized"):
        proc.process(exam_context)

def test_start_uninitialized(config):
    proc = MediaPipeEARProcessor(config)
    with pytest.raises(EARProcessorError, match="Cannot start uninitialized processor."):
        proc.start()

def test_no_face(processor, exam_context):
    exam_context.face_mesh_info = FaceMeshInfo(all_face_landmarks=[])
    
    processor.process(exam_context)
    
    eye_info = exam_context.eye_info
    assert eye_info.average_ear == 0.0
    assert eye_info.left_ear == 0.0
    assert eye_info.right_ear == 0.0

def test_missing_landmarks(processor, exam_context):
    # Only provide 100 landmarks, which is insufficient
    landmarks = [[0.0, 0.0, 0.0] for _ in range(100)]
    exam_context.face_mesh_info = FaceMeshInfo(all_face_landmarks=[landmarks])
    
    with pytest.raises(InvalidEyeLandmarksError, match="Insufficient landmarks"):
        processor.process(exam_context)

def test_invalid_eye_landmarks(processor, exam_context):
    # Missing coordinates (only x instead of x, y, z)
    landmarks = [[0.0] for _ in range(468)]
    exam_context.face_mesh_info = FaceMeshInfo(all_face_landmarks=[landmarks])
    
    with pytest.raises(InvalidEyeLandmarksError, match="Invalid landmark at index"):
        processor.process(exam_context)

def test_single_face_ear(processor, exam_context):
    exam_context.face_mesh_info = FaceMeshInfo(
        all_face_landmarks=create_mock_landmarks(face_count=1),
        frame_id=123
    )
    
    processor.process(exam_context)
    
    eye_info = exam_context.eye_info
    assert eye_info.frame_id == 123
    assert eye_info.left_ear > 0.0
    assert eye_info.right_ear > 0.0
    assert eye_info.average_ear > 0.0
    assert eye_info.left_eye_width > 0.0
    assert eye_info.right_eye_width > 0.0
    assert eye_info.ear_confidence == 1.0

def test_multiple_faces(processor, exam_context):
    exam_context.face_mesh_info = FaceMeshInfo(
        all_face_landmarks=create_mock_landmarks(face_count=3),
        frame_id=456
    )
    
    processor.process(exam_context)
    
    eye_info = exam_context.eye_info
    assert eye_info.frame_id == 456
    # It should set the eye_info to the primary face (index 0)
    assert eye_info.average_ear > 0.0

def test_failure_handling(processor, exam_context):
    # Pass bad type to trigger exception in math.sqrt or index error
    exam_context.face_mesh_info = FaceMeshInfo(
        all_face_landmarks=[[(float('nan'), float('nan'), 0.0) for _ in range(468)]]
    )
    
    with pytest.raises(InvalidEyeLandmarksError, match="NaN coordinate found"):
         processor.process(exam_context)

def test_horizontal_distance_zero(processor, exam_context):
    # Simulate a face where the eye corners are at the exact same location
    landmarks = create_mock_landmarks(1)
    # Set left eye horizontal to 0
    landmarks[0][362] = [0.5, 0.5, 0.0]
    landmarks[0][263] = [0.5, 0.5, 0.0]
    
    exam_context.face_mesh_info = FaceMeshInfo(all_face_landmarks=landmarks)
    
    processor.process(exam_context)
    assert exam_context.eye_info.left_ear == 0.0
    assert exam_context.eye_info.right_ear > 0.0
