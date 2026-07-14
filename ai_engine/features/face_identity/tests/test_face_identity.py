"""
Unit tests for the Face Identity Consistency Verification Processor.
"""
import pytest
import numpy as np

from ai_engine.core.exam_context import ExamContext, FaceInfo
from ai_engine.camera.frame import Frame
from ai_engine.features.face_identity.models import FaceIdentityConfig
from ai_engine.features.face_identity.embedding_processor import EmbeddingIdentityProcessor
from ai_engine.features.face_identity.exceptions import FaceIdentityError, EmbeddingGenerationError

@pytest.fixture
def config():
    return FaceIdentityConfig(
        similarity_threshold=0.60,
        embedding_model_name="test_model",
        verification_interval_frames=2,
        min_face_confidence=0.5,
        enable_logging=False
    )

@pytest.fixture
def processor(config, monkeypatch):
    proc = EmbeddingIdentityProcessor(config)
    proc.initialize()
    proc.start()
    
    # Mock the embedding extraction so it doesn't require insightface
    def mock_extract(image, bbox):
        # Return a dummy vector based on the first pixel value to allow different vectors
        val = float(image[0, 0, 0]) / 255.0
        return [val, val, 1.0, 0.0, 0.5]
    
    monkeypatch.setattr(proc, "_extract_embedding", mock_extract)
    return proc

@pytest.fixture
def exam_context():
    ctx = ExamContext()
    ctx.face_info = FaceInfo(
        face_count=1,
        confidence=0.9,
        bbox=(0, 0, 100, 100)
    )
    
    # Create a dummy image
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[0, 0, 0] = 100  # set a value
    ctx.current_frame = Frame(
        frame_id=1,
        original_frame=img,
        timestamp=0.0
    )
    return ctx

def test_initialization_and_cleanup(config):
    proc = EmbeddingIdentityProcessor(config)
    assert not proc.is_initialized
    proc.initialize()
    assert proc.is_initialized
    proc.cleanup()
    assert not proc.is_initialized

def test_process_uninitialized(config, exam_context):
    proc = EmbeddingIdentityProcessor(config)
    with pytest.raises(FaceIdentityError, match="Processor is not initialized"):
        proc.process(exam_context)

def test_reference_embedding_generation(processor, exam_context):
    processor.process(exam_context)
    
    # Check that reference embedding was captured
    face_info = exam_context.face_info
    assert face_info.reference_embedding is not None
    assert face_info.current_embedding is not None
    # No comparison done on the first frame since ref was just captured (wait, it actually compares it to itself)
    assert face_info.identity_consistent

def test_matching_identity(processor, exam_context):
    # Frame 1: capture reference
    processor.process(exam_context)
    
    # Frame 2: verification interval is 2, so this frame should be skipped
    exam_context.current_frame.frame_id = 2
    processor.process(exam_context)
    
    # Frame 3: extraction happens again
    exam_context.current_frame.frame_id = 3
    processor.process(exam_context)
    
    face_info = exam_context.face_info
    assert face_info.similarity_score > 0.99  # Should be exactly 1.0 since same image
    assert face_info.identity_consistent
    assert face_info.verification_timestamp > 0.0

def test_identity_mismatch(processor, exam_context):
    # Frame 1: capture reference
    processor.process(exam_context)
    
    # Frame 3: verification interval met, change image significantly
    exam_context.current_frame.frame_id = 3
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[0, 0, 0] = 250  # very different value, changes the mock vector
    exam_context.current_frame.original_frame = img
    
    # Wait, our mock vector uses [val, val, 1.0, 0.0, 0.5]
    # val1 = 100/255 = 0.39, val2 = 250/255 = 0.98
    # Cosine similarity won't be 0, but it will be slightly different.
    # Let's adjust the mock dynamically for this test.
    
    processor._extract_embedding = lambda i, b: [-1.0, -1.0, -1.0, 0.0, -0.5]
    
    processor.process(exam_context)
    
    face_info = exam_context.face_info
    # Since vectors are essentially opposite, cosine sim is < 0.6
    assert face_info.similarity_score < processor.config.similarity_threshold
    assert not face_info.identity_consistent

def test_low_quality_face(processor, exam_context):
    # Confidence below min_face_confidence
    exam_context.face_info.confidence = 0.4
    processor.process(exam_context)
    
    assert exam_context.face_info.reference_embedding is None

def test_missing_face(processor, exam_context):
    exam_context.face_info.face_count = 0
    processor.process(exam_context)
    
    assert exam_context.face_info.reference_embedding is None

def test_embedding_failure(config, exam_context):
    proc = EmbeddingIdentityProcessor(config)
    proc.initialize()
    proc.start()
    # Let it use the unmocked _extract_embedding with no insightface
    with pytest.raises(EmbeddingGenerationError):
        proc.process(exam_context)

def test_cosine_similarity(processor):
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert processor._cosine_similarity(v1, v2) == 1.0
    
    v3 = [0.0, 1.0, 0.0]
    assert processor._cosine_similarity(v1, v3) == 0.0
    
    v4 = [-1.0, 0.0, 0.0]
    assert processor._cosine_similarity(v1, v4) == -1.0
