"""
Pipeline Processor for Identity Protection Subsystem.
"""
import time
import logging
from typing import Optional, Dict, Any

from ai_engine.core.exam_context import ExamContext
from ai_engine.identity_protection.interfaces.liveness_engine import LivenessEngineInterface, LivenessResult
from ai_engine.identity_protection.aggregator.identity_protection_aggregator import IdentityProtectionAggregator
from ai_engine.identity_protection.observations.identity_observation import IdentityProtectionObservation
from ai_engine.identity_protection.engines.minifas_liveness_engine import MiniFASNetLivenessEngine
from ai_engine.identity_protection.analyzers.mesh_geometry_analyzer import MeshGeometryAnalyzer, MeshGeometryResult
from ai_engine.identity_protection.analyzers.reflection_screen_analyzer import ReflectionScreenAnalyzer, ReflectionAnalysisResult
from ai_engine.identity_protection.analyzers.temporal_consistency_analyzer import TemporalConsistencyAnalyzer, TemporalConsistencyResult
from ai_engine.identity_protection.integrity.integrity_engine import IdentityIntegrityEngine

logger = logging.getLogger("ai_engine.identity_protection.processor")

class IdentityProtectionProcessor:
    """
    Processor executing inside AIEngineThread. Orchestrates Liveness Engine, Visual Analyzers,
    Aggregator, and Identity Integrity Engine, publishing IdentityProtectionObservation to ExamContext.
    """
    
    def __init__(
        self,
        enabled: bool = True,
        spoof_threshold: float = 0.5,
        integrity_threshold: float = 0.6,
        engine: Optional[LivenessEngineInterface] = None
    ) -> None:
        self.enabled = enabled
        self.spoof_threshold = spoof_threshold
        self.integrity_threshold = integrity_threshold
        self._engine = engine if engine is not None else MiniFASNetLivenessEngine()
        self._mesh_analyzer = MeshGeometryAnalyzer()
        self._reflection_analyzer = ReflectionScreenAnalyzer()
        self._temporal_analyzer = TemporalConsistencyAnalyzer()
        self._integrity_engine = IdentityIntegrityEngine()
        self._aggregator = IdentityProtectionAggregator(
            spoof_threshold=self.spoof_threshold,
            integrity_threshold=self.integrity_threshold
        )
        self._initialized = False
        self._processed_count = 0

    def initialize(self) -> None:
        """Initializes the processor and configured engine."""
        logger.info("Initializing Identity Protection Subsystem Framework & Visual Analyzers...")
        if self._engine is not None:
            try:
                self._engine.initialize()
            except Exception as e:
                logger.error(f"Failed to initialize Liveness Engine: {e}")
        self._initialized = True

    def shutdown(self) -> None:
        """Cleans up engine resources."""
        if self._engine is not None:
            try:
                self._engine.shutdown()
            except Exception as e:
                logger.error(f"Failed to shutdown Liveness Engine: {e}")
        self._initialized = False

    def process(self, context: ExamContext) -> Optional[IdentityProtectionObservation]:
        """
        Processes current frame and face information in ExamContext using MiniFASNet, visual analyzers, and Integrity Engine.
        """
        if not self.enabled or not self._initialized:
            return None

        start_time = time.perf_counter()
        
        # Retrieve current frame and face detection state
        frame = getattr(context, "current_frame", None)
        face_info = getattr(context, "face_info", None)
        face_mesh_info = getattr(context, "face_mesh_info", None)
        
        identity_confidence = getattr(face_info, "identity_confidence", 1.0) if face_info else 1.0
        face_bbox = getattr(face_info, "bbox", None) if face_info else None
        
        liveness_result: Optional[LivenessResult] = None
        mesh_result: Optional[MeshGeometryResult] = None
        reflection_result: Optional[ReflectionAnalysisResult] = None
        temporal_result: Optional[TemporalConsistencyResult] = None

        original_frame = getattr(frame, "original_frame", None) if frame is not None else None
        
        # 1. Execute Passive Liveness Engine (MiniFASNet)
        if self._engine is not None and original_frame is not None:
            try:
                liveness_result = self._engine.process(original_frame, face_bbox=face_bbox)
            except Exception as e:
                logger.error(f"Error executing Liveness Engine: {e}")
                liveness_result = LivenessResult(
                    is_live=True,
                    liveness_score=1.0,
                    presentation_attack_type="ERROR_FALLBACK",
                    confidence=0.5,
                    reason=f"Liveness engine execution error: {e}"
                )

        liveness_score = liveness_result.liveness_score if liveness_result else 1.0

        # 2. Execute 3D Mesh Geometry Analyzer (Reuses MediaPipe landmarks)
        try:
            mesh_result = self._mesh_analyzer.process(face_mesh_info)
        except Exception as e:
            logger.error(f"Error executing MeshGeometryAnalyzer: {e}")

        # 3. Execute Reflection & Screen Analyzer (2D FFT Moiré pattern & specular glare)
        if original_frame is not None:
            try:
                reflection_result = self._reflection_analyzer.process(original_frame, face_bbox=face_bbox)
            except Exception as e:
                logger.error(f"Error executing ReflectionScreenAnalyzer: {e}")

        # 4. Execute Temporal Consistency Analyzer (Rolling 10-frame window metrics)
        try:
            temporal_result = self._temporal_analyzer.process(liveness_score=liveness_score, face_bbox=face_bbox)
        except Exception as e:
            logger.error(f"Error executing TemporalConsistencyAnalyzer: {e}")

        # 5. Aggregate visual signals into IdentityProtectionObservation
        observation = self._aggregator.aggregate(
            liveness_result=liveness_result,
            mesh_result=mesh_result,
            reflection_result=reflection_result,
            temporal_result=temporal_result,
            identity_confidence=identity_confidence,
            metadata={"frame_id": getattr(frame, "frame_id", None)}
        )

        # 6. Perform Decision Systems Identity Integrity Assessment (Phase 4.4)
        try:
            assessment = self._integrity_engine.evaluate(observation)
            observation.assessment = assessment
        except Exception as e:
            logger.error(f"Error executing IdentityIntegrityEngine: {e}")

        latency = (time.perf_counter() - start_time) * 1000.0
        observation.inference_latency_ms = round(latency, 2)
        self._processed_count += 1

        # Publish observation to ExamContext cleanly
        setattr(context, "identity_protection_observation", observation)
        
        return observation

    def health(self) -> Dict[str, Any]:
        """Returns health diagnostic metrics for Identity Protection Subsystem."""
        engine_health = self._engine.health() if self._engine is not None else {"status": "NO_ENGINE_CONFIGURED"}
        integrity_health = self._integrity_engine.health()
        return {
            "subsystem": "IdentityProtection",
            "enabled": self.enabled,
            "initialized": self._initialized,
            "processed_count": self._processed_count,
            "spoof_threshold": self.spoof_threshold,
            "integrity_threshold": self.integrity_threshold,
            "analyzers": ["MeshGeometryAnalyzer", "ReflectionScreenAnalyzer", "TemporalConsistencyAnalyzer"],
            "integrity_engine": integrity_health,
            "engine": engine_health
        }
