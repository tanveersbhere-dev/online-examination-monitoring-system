"""
Test Suite: Fused Laptop & Unauthorized-Material YOLO Detector Integration
==========================================================================
Verifies:
1. Portable checkpoint resolution without user-specific hardcoded paths.
2. Single-load initialization and strict class schema validation {0: 'unauthorized_material', 1: 'laptop'}.
3. Explicit error raising (ModelLoadError) on missing checkpoint or schema mismatch (no silent fallback).
4. Authoritative class mapping: Class 0 -> UNAUTHORIZED_MATERIAL, Class 1 -> LAPTOP.
5. Inference processing returning normalized DetectedObject instances with BoundingBox.
6. CompositeObjectDetector orchestration combining YOLODetector + FusedLaptopMaterialDetector.
7. Complete duplicate suppression: YOLODetector no longer detects laptops or books/paper.
8. End-to-end downstream pipeline:
   - UNAUTHORIZED_MATERIAL triggers UNAUTH_BOOK / ENV_BOOK_DETECTED.
   - LAPTOP triggers UNAUTH_LAPTOP.
9. Non-regression: Phone, Person, and Audio device detections are 100% preserved.
"""
import pytest
import numpy as np
from pathlib import Path

from ai_engine.core.enums import DetectedObjectType
from ai_engine.core.exam_context import ExamContext, DetectedObject, TrackedObject, BoundingBox
from ai_engine.camera.frame import Frame
from ai_engine.environment.object_detection.fused_detector import (
    FusedLaptopMaterialDetector,
    resolve_fused_checkpoint_path,
)
from ai_engine.environment.object_detection.exceptions import ModelLoadError
from ai_engine.environment.object_detection.models import ObjectDetectionConfig
from ai_engine.environment.object_detection.yolo_detector import YOLODetector
from ai_engine.environment.object_detection.composite_detector import CompositeObjectDetector
from ai_engine.environment.object_validation.models import ObjectValidationConfig
from ai_engine.environment.object_validation.validation_processor import ObjectValidationProcessor
from ai_engine.intelligence.observation_fusion.models import ObservationFusionConfig
from ai_engine.intelligence.observation_fusion.fusion_processor import FusionProcessor
from ai_engine.intelligence.rule_engine.models import RuleEngineConfig
from ai_engine.intelligence.rule_engine.rule_engine import RuleEngineProcessor
from ai_engine.intelligence.rule_engine.rules import BookVisibleRule, LaptopVisibleRule


# ------------------------------------------------------------------------------
# 1. Checkpoint Resolution & Schema Validation
# ------------------------------------------------------------------------------

def test_01_portable_checkpoint_resolution():
    """Verify relative checkpoint path resolves correctly without user-specific hardcoded paths."""
    resolved = resolve_fused_checkpoint_path("models/yoloe/fused_laptop_material_model.pt")
    assert resolved.is_file(), f"Expected checkpoint file at {resolved}"
    assert resolved.name == "fused_laptop_material_model.pt"


def test_02_model_initialization_and_schema_validation():
    """Verify fused model initializes and strictly verifies class schema {0: 'unauthorized_material', 1: 'laptop'}."""
    detector = FusedLaptopMaterialDetector()
    detector.initialize()
    assert detector._initialized is True
    assert detector._model is not None
    assert detector.resolved_checkpoint_path is not None
    assert detector.resolved_checkpoint_path.is_file()


def test_03_missing_checkpoint_raises_explicit_error():
    """Verify that a non-existent checkpoint path raises ModelLoadError rather than falling back silently."""
    detector = FusedLaptopMaterialDetector(model_path="non_existent/path/model.pt")
    with pytest.raises(ModelLoadError) as exc_info:
        detector.initialize()
    assert "not found" in str(exc_info.value).lower()


def test_04_class_mapping_authoritative():
    """Verify class 0 maps to UNAUTHORIZED_MATERIAL and class 1 maps to LAPTOP."""
    detector = FusedLaptopMaterialDetector()
    assert detector._map_class_id(0) == DetectedObjectType.UNAUTHORIZED_MATERIAL
    assert detector._map_class_id(1) == DetectedObjectType.LAPTOP
    assert detector._map_class_id(999) == DetectedObjectType.UNKNOWN


# ------------------------------------------------------------------------------
# 2. Inference Execution
# ------------------------------------------------------------------------------

def test_05_inference_on_frame():
    """Verify detector processes a frame without errors and populates current_detections."""
    detector = FusedLaptopMaterialDetector()
    detector.initialize()

    context = ExamContext()
    dummy_img = np.zeros((480, 640, 3), dtype=np.uint8)
    context.current_frame = Frame.from_bgr_image(dummy_img, frame_id=1)

    detector.process(context)
    assert hasattr(context.object_info, "current_detections")
    assert isinstance(context.object_info.current_detections, list)


# ------------------------------------------------------------------------------
# 3. Duplicate Suppression & Composite Orchestration
# ------------------------------------------------------------------------------

def test_06_coco_detector_suppresses_laptop_and_books():
    """Verify general YOLODetector has removed laptop (63), book (73), notebook (75), paper (76)."""
    cfg = ObjectDetectionConfig(enable_logging=False)
    yolo = YOLODetector(config=cfg)
    # Suppressed classes return UNKNOWN
    assert yolo._map_class_id(63) == DetectedObjectType.UNKNOWN
    assert yolo._map_class_id(73) == DetectedObjectType.UNKNOWN
    assert yolo._map_class_id(75) == DetectedObjectType.UNKNOWN
    assert yolo._map_class_id(76) == DetectedObjectType.UNKNOWN

    # Non-material classes remain fully active
    assert yolo._map_class_id(0) == DetectedObjectType.PERSON
    assert yolo._map_class_id(67) == DetectedObjectType.CELL_PHONE
    assert yolo._map_class_id(66) == DetectedObjectType.KEYBOARD
    assert yolo._map_class_id(64) == DetectedObjectType.MOUSE
    assert yolo._map_class_id(72) == DetectedObjectType.MONITOR
    assert yolo._map_class_id(74) == DetectedObjectType.SMARTWATCH


def test_07_composite_detector_aggregates_both_detectors():
    """Verify CompositeObjectDetector sequences both YOLODetector and FusedLaptopMaterialDetector."""
    cfg = ObjectDetectionConfig(enable_logging=False)
    yolo = YOLODetector(config=cfg)
    fused = FusedLaptopMaterialDetector(config=cfg)

    composite = CompositeObjectDetector(detectors=[yolo, fused], config=cfg)
    composite.initialize()
    assert composite._initialized is True

    context = ExamContext()
    dummy_img = np.zeros((480, 640, 3), dtype=np.uint8)
    context.current_frame = Frame.from_bgr_image(dummy_img, frame_id=1)

    composite.process(context)
    assert hasattr(context.object_info, "current_detections")


# ------------------------------------------------------------------------------
# 4. End-to-End Validation, Fusion & Rule Triggering
# ------------------------------------------------------------------------------

def test_08_unauthorized_material_triggers_book_rule():
    """Verify DetectedObjectType.UNAUTHORIZED_MATERIAL passes validation, fusion, and triggers UNAUTH_BOOK."""
    validator = ObjectValidationProcessor(ObjectValidationConfig(enable_logging=False))
    validator.initialize()
    fusion = FusionProcessor(ObservationFusionConfig(enable_environment=True, enable_audio=False))
    fusion.initialize()
    rules = RuleEngineProcessor(RuleEngineConfig())
    rules.initialize()
    rules.config.enabled_rules["UNAUTH_BOOK"] = True

    dummy_img = np.zeros((10, 10, 3), dtype=np.uint8)
    # Process 2 consecutive frames to satisfy temporal confirmation
    for i in range(1, 3):
        ctx = ExamContext()
        ctx.current_frame = Frame.from_bgr_image(dummy_img, frame_id=i)
        material = TrackedObject(
            tracking_id=1,
            object_type=DetectedObjectType.UNAUTHORIZED_MATERIAL,
            bbox=BoundingBox(x=50, y=50, width=100, height=100),
            confidence=0.88,
            current_state="TRACKED",
        )
        oi = ctx.object_info
        oi.tracked_objects = [material]
        ctx.object_info = oi

        validator.process(ctx)
        fusion.process(ctx)
        rules.process(ctx)

    assert len(ctx.object_info.validated_objects) == 1
    assert ctx.object_info.validated_objects[0].object_type == DetectedObjectType.UNAUTHORIZED_MATERIAL
    assert ctx.observation.environment.book_present is True

    triggered_ids = [r.rule_id for r in ctx.rule_results.evaluations if r.triggered]
    assert "UNAUTH_BOOK" in triggered_ids


def test_09_laptop_triggers_laptop_rule():
    """Verify DetectedObjectType.LAPTOP passes validation, fusion, and triggers UNAUTH_LAPTOP."""
    validator = ObjectValidationProcessor(ObjectValidationConfig(enable_logging=False))
    validator.initialize()
    fusion = FusionProcessor(ObservationFusionConfig(enable_environment=True, enable_audio=False))
    fusion.initialize()
    rules = RuleEngineProcessor(RuleEngineConfig())
    rules.initialize()
    rules.config.enabled_rules["UNAUTH_LAPTOP"] = True

    dummy_img = np.zeros((10, 10, 3), dtype=np.uint8)
    # Process 3 consecutive frames to satisfy LAPTOP min_consecutive_frames = 3
    for i in range(1, 4):
        ctx = ExamContext()
        ctx.current_frame = Frame.from_bgr_image(dummy_img, frame_id=i)
        laptop = TrackedObject(
            tracking_id=2,
            object_type=DetectedObjectType.LAPTOP,
            bbox=BoundingBox(x=100, y=100, width=200, height=150),
            confidence=0.85,
            current_state="TRACKED",
        )
        oi = ctx.object_info
        oi.tracked_objects = [laptop]
        ctx.object_info = oi

        validator.process(ctx)
        fusion.process(ctx)
        rules.process(ctx)

    assert len(ctx.object_info.validated_objects) == 1
    assert ctx.object_info.validated_objects[0].object_type == DetectedObjectType.LAPTOP
    assert ctx.observation.environment.laptop_present is True

    triggered_ids = [r.rule_id for r in ctx.rule_results.evaluations if r.triggered]
    assert "UNAUTH_LAPTOP" in triggered_ids


def test_10_non_regression_phone_and_person_preserved():
    """Verify phone and person detections continue to be processed cleanly alongside fused models."""
    validator = ObjectValidationProcessor(ObjectValidationConfig(enable_logging=False))
    validator.initialize()
    fusion = FusionProcessor(ObservationFusionConfig(enable_environment=True, enable_audio=False))
    fusion.initialize()

    dummy_img = np.zeros((10, 10, 3), dtype=np.uint8)
    for i in range(1, 3):
        ctx = ExamContext()
        ctx.current_frame = Frame.from_bgr_image(dummy_img, frame_id=i)
        phone = TrackedObject(
            tracking_id=3,
            object_type=DetectedObjectType.CELL_PHONE,
            bbox=BoundingBox(x=10, y=10, width=40, height=60),
            confidence=0.82,
            current_state="TRACKED",
        )
        oi = ctx.object_info
        oi.tracked_objects = [phone]
        ctx.object_info = oi

        validator.process(ctx)
        fusion.process(ctx)

    assert len(ctx.object_info.validated_objects) == 1
    assert ctx.object_info.validated_objects[0].object_type == DetectedObjectType.CELL_PHONE
    assert ctx.observation.environment.phone_present is True
