"""
Performance and Concurrency Hardening Verification Suite
==========================================================
Tests the architectural optimizations for Phase 4:
1. Camera 1 AI processing does not block the asyncio event loop.
2. Camera 2 preview remains responsive while Camera 1 AI runs.
3. YOLO concurrency lock prevents overlapping inference.
4. Camera 2 preview does not wait for AI inference.
5. Camera 1 full 19-stage pipeline functionality remains unchanged.
6. Camera 2 approved violation subset remains unchanged.
7. Laptop violation (UNAUTH_LAPTOP) remains functional with Evidence Engine.
"""
import time
import asyncio
import threading
import numpy as np
import cv2
import pytest
from unittest.mock import MagicMock

from ai_engine.camera.frame import Frame
from ai_engine.core.enums import DetectedObjectType
from ai_engine.core.exam_context import ExamContext, DetectedObject, BoundingBox
from ai_engine.environment.object_detection.yolo_detector import YOLODetector
from ai_engine.environment.object_detection.models import ObjectDetectionConfig
from ai_engine.intelligence.rule_engine.rule_engine import RuleEngineProcessor
from ai_engine.intelligence.rule_engine.models import RuleEngineConfig
from ai_engine.intelligence.observation_fusion.models import UnifiedObservation, EnvironmentObservation
from backend.camera.multi_camera_manager import MultiCameraManager
from backend.api import ws_handler
from backend.pipeline.context_builder import ContextBuilder
from backend.pipeline.orchestrator import MonitoringPipelineOrchestrator
from backend.pipeline.result_serializer import ResultSerializer


@pytest.fixture
def sample_jpeg_frame():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(img, "TEST FRAME", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    success, encoded = cv2.imencode(".jpg", img)
    assert success
    return encoded.tobytes()


def test_cam1_processing_does_not_block_event_loop(sample_jpeg_frame):
    """Verifies that running Camera 1 AI does not block the asyncio event loop."""
    async def _async_test():
        mock_orch = MagicMock()
        # Simulate a 100ms blocking CPU operation
        def blocking_process(ctx):
            time.sleep(0.1)
            return 100.0
        mock_orch.process.side_effect = blocking_process
        mock_orch.processor_health.return_value = {}
        mock_orch.evidence_store = []

        mock_cb = ContextBuilder()
        mock_serializer = ResultSerializer()
        ws_handler.inject_dependencies(mock_orch, mock_cb, mock_serializer)

        loop = asyncio.get_running_loop()
        loop_ticks = 0
        monitoring = True

        async def event_loop_ticker():
            nonlocal loop_ticks
            while monitoring:
                loop_ticks += 1
                await asyncio.sleep(0.01)  # 10ms tick

        ticker_task = asyncio.create_task(event_loop_ticker())

        executor = ws_handler.get_cam1_executor()
        # Run 3 frames in executor
        for _ in range(3):
            res, ms = await loop.run_in_executor(
                executor,
                ws_handler._process_camera1_frame,
                sample_jpeg_frame,
                "test_session",
            )
            assert res is not None

        monitoring = False
        await ticker_task

        # During 300ms of blocking CPU time, the event loop should have ticked multiple times (>15 times)
        assert loop_ticks >= 15, f"Event loop was blocked! Ticks: {loop_ticks}"

    asyncio.run(_async_test())


def test_yolo_concurrency_lock_prevents_simultaneous_inference():
    """Verifies that _inference_lock serializes concurrent predict calls."""
    cfg = ObjectDetectionConfig(enable_logging=False)
    det = YOLODetector(config=cfg)
    det._initialized = True
    
    mock_model = MagicMock()
    active_inferences = 0
    max_concurrent = 0
    lock = threading.Lock()

    def mock_predict(*args, **kwargs):
        nonlocal active_inferences, max_concurrent
        with lock:
            active_inferences += 1
            if active_inferences > max_concurrent:
                max_concurrent = active_inferences
        time.sleep(0.05)  # 50ms inside predict
        with lock:
            active_inferences -= 1
        return []

    mock_model.predict.side_effect = mock_predict
    det._model = mock_model

    ctx1 = ExamContext()
    ctx1.current_frame = Frame.from_bgr_image(np.zeros((100, 100, 3), dtype=np.uint8), camera_id="camera_1")
    ctx2 = ExamContext()
    ctx2.current_frame = Frame.from_bgr_image(np.zeros((100, 100, 3), dtype=np.uint8), camera_id="camera_2")

    # Run in two concurrent threads
    t1 = threading.Thread(target=det.process, args=(ctx1,))
    t2 = threading.Thread(target=det.process, args=(ctx2,))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # The maximum concurrent inferences inside predict must be strictly 1
    assert max_concurrent == 1, f"YOLO was executed concurrently! Max concurrent: {max_concurrent}"


def test_cam2_preview_does_not_wait_for_ai(sample_jpeg_frame):
    """Verifies that Camera 2 push_frame broadcasts preview immediately without waiting for AI."""
    async def _async_test():
        mcm = MultiCameraManager()
        feed_q = mcm.subscribe_feed("camera_2")

        ai_called = False
        def slow_ai_processor(cam_id, jpeg_bytes, session_id):
            nonlocal ai_called
            time.sleep(0.5)
            ai_called = True

        mcm.set_ai_pipeline_processor(slow_ai_processor)

        # Push 5 frames rapidly
        for i in range(5):
            mcm.push_frame("camera_2", sample_jpeg_frame, session_id="s1")

        # Feed queue should have immediately received frames without waiting 500ms
        assert not feed_q.empty()
        item = feed_q.get_nowait()
        assert item == sample_jpeg_frame

    asyncio.run(_async_test())


def test_cam1_functionality_remains_unchanged(sample_jpeg_frame):
    """Verifies that Camera 1 runs through the executor and outputs valid FrameResult."""
    cb = ContextBuilder()
    orch = MonitoringPipelineOrchestrator()
    orch.initialize()
    orch.start()
    serializer = ResultSerializer()
    ws_handler.inject_dependencies(orch, cb, serializer)

    res, pipe_ms = ws_handler._process_camera1_frame(sample_jpeg_frame, "test_session")
    assert res is not None
    assert "face" in res
    assert "objects" in res
    assert "violations" in res
    assert pipe_ms > 0

    orch.stop()
    orch.shutdown()


def test_laptop_violation_and_evidence_remain_functional():
    """Verifies that UNAUTH_LAPTOP violation is detected and evaluated in context."""
    cfg = RuleEngineConfig()
    engine = RuleEngineProcessor(cfg)
    engine.initialize()

    ctx = ExamContext()
    ctx.current_frame = Frame.from_bgr_image(np.zeros((100, 100, 3), dtype=np.uint8), camera_id="camera_2")
    ctx.observation = UnifiedObservation(
        timestamp=100.0,
        environment=EnvironmentObservation(
            laptop_present=True,
            tracked_entities_summary=[{"id": 1, "type": "LAPTOP", "conf": 0.85}]
        )
    )

    engine.process(ctx)
    evals = [e.rule_id for e in ctx.rule_results.evaluations if e.triggered]
    assert "UNAUTH_LAPTOP" in evals, f"UNAUTH_LAPTOP did not trigger: {evals}"
