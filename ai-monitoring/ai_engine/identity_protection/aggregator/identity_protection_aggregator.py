"""
Multi-signal Aggregator for Identity Protection Subsystem.
"""
import time
import logging
from typing import Optional, Dict, Any

from ai_engine.identity_protection.interfaces.liveness_engine import LivenessResult
from ai_engine.identity_protection.observations.identity_observation import IdentityProtectionObservation
from ai_engine.identity_protection.analyzers.mesh_geometry_analyzer import MeshGeometryResult
from ai_engine.identity_protection.analyzers.reflection_screen_analyzer import ReflectionAnalysisResult
from ai_engine.identity_protection.analyzers.temporal_consistency_analyzer import TemporalConsistencyResult

logger = logging.getLogger("ai_engine.identity_protection.aggregator")

class IdentityProtectionAggregator:
    """
    Fuses multiple liveness, 3D mesh geometry, reflection screen, and temporal consistency signals
    into a single unified IdentityProtectionObservation.
    """
    
    def __init__(self, spoof_threshold: float = 0.5, integrity_threshold: float = 0.6) -> None:
        self.spoof_threshold = spoof_threshold
        self.integrity_threshold = integrity_threshold

    def aggregate(
        self,
        liveness_result: Optional[LivenessResult] = None,
        mesh_result: Optional[MeshGeometryResult] = None,
        reflection_result: Optional[ReflectionAnalysisResult] = None,
        temporal_result: Optional[TemporalConsistencyResult] = None,
        identity_confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> IdentityProtectionObservation:
        """
        Aggregates liveness engine result, visual analyzers, and facial identity match confidence.
        
        Args:
            liveness_result: Result from active/passive liveness engine (MiniFASNet)
            mesh_result: Result from 3D Mesh Geometry Analyzer
            reflection_result: Result from Reflection & Screen Analyzer
            temporal_result: Result from Temporal Consistency Analyzer
            identity_confidence: Cosine similarity score from Face Recognition
            metadata: Optional dictionary of feature metrics
            
        Returns:
            IdentityProtectionObservation dataclass
        """
        if liveness_result is None:
            liveness_result = LivenessResult(
                is_live=True,
                liveness_score=1.0,
                presentation_attack_type="NONE",
                confidence=1.0,
                reason="Framework active - Liveness Engine placeholder",
                latency_ms=0.0
            )

        base_score = liveness_result.liveness_score
        
        # Extract supporting analyzer metrics
        mesh_conf = mesh_result.depth_variance_score if mesh_result else 1.0
        refl_score = reflection_result.moire_pattern_score if reflection_result else 0.0
        temp_score = temporal_result.liveness_trend_score if temporal_result else 1.0

        # Dynamically adjust liveness score based on supporting analyzer evidence
        adjusted_score = base_score
        
        # High Moiré grid energy (>0.7) reduces liveness score (suspected screen replay)
        if refl_score > 0.7:
            adjusted_score *= 0.85

        # Flat 2D depth variance (<0.2) reduces liveness score (suspected photo/screen print)
        if mesh_conf < 0.2:
            adjusted_score *= 0.90

        # High temporal continuity boosts overall liveness confidence
        if temp_score > 0.8:
            adjusted_score = min(1.0, adjusted_score * 1.02)

        liveness_score = float(max(0.0, min(1.0, adjusted_score)))

        # Composite identity integrity score: Liveness * Identity Match
        integrity_score = liveness_score * identity_confidence
        
        # Determine Liveness State.  A single low MiniFASNet score is a
        # suspicion, not a confirmed presentation attack.  The existing
        # temporal analyzer supplies a confirmed trend only after it has at
        # least two frames, and its rolling mean must remain below the same
        # score boundary used for SPOOF_CONFIRMED.
        temporal_metadata = temporal_result.metadata if temporal_result else {}
        history_length = temporal_metadata.get("window_size", temporal_metadata.get("history_length", 0))
        mean_liveness = temporal_metadata.get("mean_liveness")
        confirmed_threshold = self.spoof_threshold * 0.5
        persistent_low_liveness = (
            history_length >= 2
            and mean_liveness is not None
            and float(mean_liveness) < confirmed_threshold
        )

        if liveness_score >= self.spoof_threshold:
            state = "LIVE"
        elif liveness_score >= confirmed_threshold:
            state = "SPOOF_SUSPECTED"
        elif persistent_low_liveness:
            state = "SPOOF_CONFIRMED"
        else:
            state = "SPOOF_SUSPECTED"

        spoof_conf = 1.0 - liveness_score

        supporting_signals = {
            "mesh_geometry": mesh_result.metadata if mesh_result else {},
            "reflection_screen": reflection_result.metadata if reflection_result else {},
            "temporal_consistency": temporal_result.metadata if temporal_result else {}
        }

        return IdentityProtectionObservation(
            liveness_state=state,
            liveness_score=round(liveness_score, 4),
            presentation_attack_type=liveness_result.presentation_attack_type,
            identity_integrity_score=round(integrity_score, 4),
            spoof_confidence=round(spoof_conf, 4),
            reason=liveness_result.reason,
            inference_timestamp=time.time(),
            model_version="2.0.0-multi-signal-analyzers",
            inference_latency_ms=liveness_result.latency_ms,
            mesh_confidence=round(mesh_conf, 4),
            reflection_score=round(refl_score, 4),
            temporal_consistency=round(temp_score, 4),
            supporting_signals=supporting_signals,
            raw_metrics=metadata or {}
        )
