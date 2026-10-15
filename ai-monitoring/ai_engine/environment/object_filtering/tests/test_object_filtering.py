"""
Unit tests for the Object Filtering Processor.
"""
import pytest

from ai_engine.core.exam_context import ExamContext, DetectedObject, BoundingBox
from ai_engine.core.enums import DetectedObjectType
from ai_engine.environment.object_filtering.models import ObjectFilteringConfig
from ai_engine.environment.object_filtering.filtering_processor import FilteringProcessor
from ai_engine.environment.object_filtering.exceptions import ObjectFilteringError

def set_detections(ctx: ExamContext, detections: list):
    oi = ctx.object_info
    oi.current_detections = detections
    ctx.object_info = oi

@pytest.fixture
def config():
    return ObjectFilteringConfig(
        min_confidence=0.5,
        supported_classes=[DetectedObjectType.PERSON, DetectedObjectType.CELL_PHONE],
        max_objects=5,
        iou_threshold=0.5,
        duplicate_filtering_enabled=True,
        enable_logging=False
    )

@pytest.fixture
def processor(config):
    proc = FilteringProcessor(config)
    proc.initialize()
    proc.start()
    return proc

@pytest.fixture
def exam_context():
    ctx = ExamContext()
    oi = ctx.object_info
    oi.frame_id = 1
    ctx.object_info = oi
    return ctx

def test_initialization_and_cleanup(config):
    proc = FilteringProcessor(config)
    
    assert not proc.is_initialized
    proc.initialize()
    assert proc.is_initialized
    
    proc.cleanup()
    assert not proc.is_initialized

def test_empty_detections(processor, exam_context):
    set_detections(exam_context, [])
    
    processor.process(exam_context)
    
    assert len(exam_context.object_info.filtered_detections) == 0
    stats = exam_context.object_info.filtering_statistics
    assert stats.total_received == 0
    assert stats.total_accepted == 0
    assert stats.total_rejected == 0

def test_single_valid_detection(processor, exam_context):
    set_detections(exam_context, [
        DetectedObject(
            object_type=DetectedObjectType.PERSON,
            confidence=0.9,
            bbox=BoundingBox(10, 10, 50, 50)
        )
    ])
    
    processor.process(exam_context)
    
    filtered = exam_context.object_info.filtered_detections
    assert len(filtered) == 1
    assert filtered[0].object_type == DetectedObjectType.PERSON
    assert filtered[0].confidence == 0.9
    assert filtered[0].frame_id == 1
    
    stats = exam_context.object_info.filtering_statistics
    assert stats.total_received == 1
    assert stats.total_accepted == 1
    assert stats.total_rejected == 0

def test_unsupported_classes_removed(processor, exam_context):
    set_detections(exam_context, [
        DetectedObject(
            object_type=DetectedObjectType.PERSON,
            confidence=0.9,
            bbox=BoundingBox(10, 10, 50, 50)
        ),
        DetectedObject(
            object_type=DetectedObjectType.LAPTOP, # Not in fixture supported classes
            confidence=0.9,
            bbox=BoundingBox(20, 20, 50, 50)
        )
    ])
    
    processor.process(exam_context)
    
    filtered = exam_context.object_info.filtered_detections
    assert len(filtered) == 1
    assert filtered[0].object_type == DetectedObjectType.PERSON
    
    stats = exam_context.object_info.filtering_statistics
    assert stats.total_received == 2
    assert stats.total_accepted == 1
    assert stats.total_rejected == 1
    assert stats.unsupported_class_removed == 1

def test_low_confidence_removed(processor, exam_context):
    set_detections(exam_context, [
        DetectedObject(
            object_type=DetectedObjectType.PERSON,
            confidence=0.9,
            bbox=BoundingBox(10, 10, 50, 50)
        ),
        DetectedObject(
            object_type=DetectedObjectType.CELL_PHONE,
            confidence=0.3, # Below 0.5 min_conf
            bbox=BoundingBox(20, 20, 50, 50)
        )
    ])
    
    processor.process(exam_context)
    
    filtered = exam_context.object_info.filtered_detections
    assert len(filtered) == 1
    assert filtered[0].object_type == DetectedObjectType.PERSON
    
    stats = exam_context.object_info.filtering_statistics
    assert stats.total_received == 2
    assert stats.total_accepted == 1
    assert stats.total_rejected == 1
    assert stats.low_confidence_removed == 1

def test_invalid_bounding_boxes(processor, exam_context):
    set_detections(exam_context, [
        DetectedObject(
            object_type=DetectedObjectType.PERSON,
            confidence=0.9,
            bbox=BoundingBox(10, 10, -50, 50) # Invalid width
        ),
        DetectedObject(
            object_type=DetectedObjectType.CELL_PHONE,
            confidence=0.9,
            bbox=BoundingBox(-10, 10, 50, 50) # Invalid x
        )
    ])
    
    processor.process(exam_context)
    
    filtered = exam_context.object_info.filtered_detections
    assert len(filtered) == 0
    
    stats = exam_context.object_info.filtering_statistics
    assert stats.invalid_box_removed == 2

def test_duplicate_filtering_nms(processor, exam_context):
    # Two identical boxes, one with lower confidence
    set_detections(exam_context, [
        DetectedObject(
            object_type=DetectedObjectType.PERSON,
            confidence=0.9,
            bbox=BoundingBox(10, 10, 50, 50)
        ),
        DetectedObject(
            object_type=DetectedObjectType.PERSON,
            confidence=0.7,
            bbox=BoundingBox(12, 12, 48, 48) # High IoU
        )
    ])
    
    processor.process(exam_context)
    
    filtered = exam_context.object_info.filtered_detections
    assert len(filtered) == 1
    assert filtered[0].confidence == 0.9
    
    stats = exam_context.object_info.filtering_statistics
    assert stats.duplicates_removed == 1

def test_max_objects_truncation(processor, exam_context):
    # Max objects is 5 in fixture
    detections = []
    for i in range(10):
        detections.append(
            DetectedObject(
                object_type=DetectedObjectType.PERSON,
                confidence=0.9 - (i * 0.01),
                bbox=BoundingBox(i*100, 10, 50, 50) # Separate boxes, no IoU overlap
            )
        )
    set_detections(exam_context, detections)
    
    processor.process(exam_context)
    
    filtered = exam_context.object_info.filtered_detections
    assert len(filtered) == 5
    
    # Should keep the highest confidence ones (first 5)
    assert filtered[0].confidence == 0.9
    
    stats = exam_context.object_info.filtering_statistics
    assert stats.total_rejected == 5
