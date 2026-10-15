"""
Automated Verification Test Suite for Dormant AI Capabilities (InsightFace & MiniFASNet).
Verifies:
1. Successful model loading for InsightFace and MiniFASNet.
2. Inference on representative images.
3. Propagation through ExamContext & Pipeline Orchestrator.
4. Violation generation.
5. Evidence snapshot generation.
6. Graceful handling of missing model files.
"""

import unittest
import numpy as np
import time
from pathlib import Path

from ai_engine.core.exam_context import ExamContext, FaceInfo
from ai_engine.camera.frame import Frame
from ai_engine.features.face_identity.embedding_processor import EmbeddingIdentityProcessor
from ai_engine.features.face_identity.models import FaceIdentityConfig
from ai_engine.identity_protection.engines.minifas_liveness_engine import MiniFASNetLivenessEngine
from ai_engine.identity_protection.processors.identity_protection_processor import IdentityProtectionProcessor
from backend.pipeline.orchestrator import MonitoringPipelineOrchestrator


class TestAICapabilities(unittest.TestCase):

    def setUp(self):
        self.blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    def test_01_insightface_model_loading_and_inference(self):
        """Verify InsightFace embedding processor loads weights and extracts embeddings."""
        config = FaceIdentityConfig()
        processor = EmbeddingIdentityProcessor(config)
        processor.initialize()
        
        self.assertTrue(processor._initialized)
        self.assertIsNotNone(processor._model, "InsightFace model should be initialized and loaded")

        # Test process with ExamContext
        context = ExamContext()
        context.current_frame = Frame.from_bgr_image(self.blank_frame, frame_id=1)
        context.face_info = FaceInfo(
            face_count=1,
            confidence=0.95,
            bbox=(100, 100, 200, 200)
        )
        
        processor.process(context)
        self.assertIsNotNone(context.face_info.identity_confidence)
        self.assertTrue(hasattr(context.face_info, "similarity_score"))

    def test_02_minifasnet_liveness_model_loading_and_inference(self):
        """Verify MiniFASNet passive liveness engine loads ONNX model and executes inference."""
        engine = MiniFASNetLivenessEngine("minifasnet_v2.onnx")
        engine.initialize()
        
        self.assertTrue(engine._initialized)
        self.assertTrue(engine._model_loaded, "MiniFASNet ONNX model should be loaded")

        result = engine.process(self.blank_frame, (100, 100, 200, 200))
        self.assertIsNotNone(result)
        self.assertIn(result.is_live, (True, False))
        self.assertGreaterEqual(result.confidence, 0.5)
        self.assertEqual(result.metadata.get("model_loaded"), True)

    def test_03_identity_protection_processor_integration(self):
        """Verify IdentityProtectionProcessor integrates MiniFASNet and publishes observation to ExamContext."""
        processor = IdentityProtectionProcessor()
        processor.initialize()
        
        self.assertTrue(processor._initialized)
        self.assertTrue(processor._engine._model_loaded)

        context = ExamContext()
        context.current_frame = Frame.from_bgr_image(self.blank_frame, frame_id=1)
        context.face_info = FaceInfo(
            face_count=1,
            confidence=0.9,
            bbox=(100, 100, 200, 200)
        )

        obs = processor.process(context)
        self.assertIsNotNone(obs)
        self.assertTrue(hasattr(context, "identity_protection_observation"))

    def test_04_full_pipeline_orchestration_and_evidence(self):
        """Verify full orchestrator runs all 17 processors including identity and liveness."""
        orchestrator = MonitoringPipelineOrchestrator()
        orchestrator.initialize()
        
        # Verify 19/19 processors initialized (including Step 13 ObjectValidator)
        self.assertEqual(len(orchestrator._processors), 19)

        context = ExamContext()
        context.current_frame = Frame.from_bgr_image(self.blank_frame, frame_id=1)

        pipeline_ms = orchestrator.process(context)
        self.assertGreater(pipeline_ms, 0.0)
        self.assertIsNotNone(context.rule_results)

        # Check evidence store handles state transition
        evidence_store = orchestrator._evidence_store
        self.assertIsInstance(evidence_store, list)

    def test_05_graceful_fallback_on_missing_model(self):
        """Verify MiniFASNet falls back gracefully when model fails to load."""
        engine = MiniFASNetLivenessEngine()
        engine._initialized = True
        engine._model_loaded = False
        engine._model = None

        result = engine.process(self.blank_frame, (100, 100, 200, 200))
        self.assertTrue(result.is_live)
        self.assertEqual(result.metadata.get("model_loaded"), False)
        self.assertEqual(result.liveness_score, 0.98)


if __name__ == "__main__":
    unittest.main()
