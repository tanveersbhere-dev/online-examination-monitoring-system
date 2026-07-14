"""
Unit tests for the Object Detector.
"""
import pytest
import numpy as np

from ai_engine.core.exam_context import ExamContext
from ai_engine.core.enums import DetectedObjectType
from ai_engine.camera.frame import Frame
from ai_engine.environment.object_detection.models import ObjectDetectionConfig
from ai_engine.environment.object_detection.yolo_detector import YOLODetector
from ai_engine.environment.object_detection.exceptions import ObjectDetectionError, InvalidFrameError, InferenceError

class MockBoxes:
    def __init__(self, xyxy, conf, cls):
        self.xyxy = xyxy
        self.conf = conf
        self.cls = cls

class MockTensor:
    def __init__(self, data):
        self.data = data
    def cpu(self):
        return self
    def numpy(self):
        return self.data

class MockResult:
    def __init__(self, xyxy, conf, cls):
        self.boxes = MockBoxes(MockTensor(xyxy), MockTensor(conf), MockTensor(cls))

class MockYOLOModel:
    def __init__(self, mock_results=None):
        self.mock_results = mock_results or []
        self.called_device = None
        
    def to(self, device):
        self.called_device = device
        
    def predict(self, source, conf, iou, device, max_det, verbose):
        return self.mock_results

@pytest.fixture
def config():
    return ObjectDetectionConfig(
        confidence_threshold=0.5,
        iou_threshold=0.45,
        max_detections=10,
        enabled_classes=[
            DetectedObjectType.PERSON,
            DetectedObjectType.CELL_PHONE,
            DetectedObjectType.LAPTOP,
            DetectedObjectType.UNKNOWN
        ],
        model_path="mock_model.pt",
        device="cpu",
        enable_logging=False
    )

@pytest.fixture
def empty_frame_context():
    ctx = ExamContext()
    ctx.current_frame = Frame(
        frame_id=1,
        original_frame=None,
        timestamp=0.0
    )
    return ctx

@pytest.fixture
def valid_frame_context():
    ctx = ExamContext()
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    ctx.current_frame = Frame(
        frame_id=1,
        original_frame=img,
        timestamp=0.0
    )
    return ctx

def test_initialization_and_cleanup(config):
    detector = YOLODetector(config)
    
    # We won't patch ultralytics here, so it should catch ImportError and initialize to None
    detector.initialize()
    assert detector.is_initialized
    
    detector.cleanup()
    assert not detector.is_initialized

def test_invalid_frame(config, empty_frame_context, monkeypatch):
    detector = YOLODetector(config)
    detector.initialize()
    detector.start()
    
    with pytest.raises(InvalidFrameError):
        detector.process(empty_frame_context)

def test_inference_error_when_no_model(config, valid_frame_context):
    detector = YOLODetector(config)
    detector.initialize()
    detector.start()
    
    with pytest.raises(InferenceError, match="YOLO model is not loaded"):
        detector.process(valid_frame_context)

def test_no_objects_detected(config, valid_frame_context, monkeypatch):
    detector = YOLODetector(config)
    detector.initialize()
    detector._model = MockYOLOModel(mock_results=[])
    detector.start()
    
    detector.process(valid_frame_context)
    
    assert len(valid_frame_context.object_info.current_detections) == 0
    assert valid_frame_context.object_info.total_object_count == 0

def test_single_object_detection(config, valid_frame_context, monkeypatch):
    detector = YOLODetector(config)
    detector.initialize()
    
    # Mock result: 1 Person (ID 0)
    mock_xyxy = np.array([[10, 10, 50, 50]])
    mock_conf = np.array([0.9])
    mock_cls = np.array([0])
    detector._model = MockYOLOModel(mock_results=[MockResult(mock_xyxy, mock_conf, mock_cls)])
    
    detector.start()
    detector.process(valid_frame_context)
    
    objects = valid_frame_context.object_info.current_detections
    assert len(objects) == 1
    assert valid_frame_context.object_info.total_object_count == 1
    
    obj = objects[0]
    assert obj.object_type == DetectedObjectType.PERSON
    assert obj.confidence == 0.9
    assert obj.bbox.x == 10.0
    assert obj.bbox.width == 40.0

def test_multiple_objects_and_filtering(config, valid_frame_context, monkeypatch):
    # Enable Person and Cell Phone, but NOT Keyboard (ID 66)
    config.enabled_classes = [DetectedObjectType.PERSON, DetectedObjectType.CELL_PHONE]
    
    detector = YOLODetector(config)
    detector.initialize()
    
    # Mock result: Person(0), Cell Phone(67), Keyboard(66)
    mock_xyxy = np.array([
        [10, 10, 50, 50],
        [20, 20, 30, 30],
        [0, 0, 10, 10]
    ])
    mock_conf = np.array([0.9, 0.8, 0.7])
    mock_cls = np.array([0, 67, 66])
    detector._model = MockYOLOModel(mock_results=[MockResult(mock_xyxy, mock_conf, mock_cls)])
    
    detector.start()
    detector.process(valid_frame_context)
    
    objects = valid_frame_context.object_info.current_detections
    assert len(objects) == 2 # Keyboard should be filtered out
    assert objects[0].object_type == DetectedObjectType.PERSON
    assert objects[1].object_type == DetectedObjectType.CELL_PHONE

def test_unsupported_object_class_mapped_to_unknown(config, valid_frame_context, monkeypatch):
    config.enabled_classes = [DetectedObjectType.UNKNOWN]
    detector = YOLODetector(config)
    detector.initialize()
    
    # Mock result: Random class ID (e.g., 99)
    mock_xyxy = np.array([[10, 10, 50, 50]])
    mock_conf = np.array([0.9])
    mock_cls = np.array([99])
    detector._model = MockYOLOModel(mock_results=[MockResult(mock_xyxy, mock_conf, mock_cls)])
    
    detector.start()
    detector.process(valid_frame_context)
    
    objects = valid_frame_context.object_info.current_detections
    assert len(objects) == 1
    assert objects[0].object_type == DetectedObjectType.UNKNOWN

def test_exception_during_inference(config, valid_frame_context):
    detector = YOLODetector(config)
    detector.initialize()
    
    class FaultyModel:
        def predict(self, *args, **kwargs):
            raise ValueError("Simulated YOLO crash")
            
    detector._model = FaultyModel()
    detector.start()
    
    with pytest.raises(InferenceError, match="Simulated YOLO crash"):
        detector.process(valid_frame_context)
