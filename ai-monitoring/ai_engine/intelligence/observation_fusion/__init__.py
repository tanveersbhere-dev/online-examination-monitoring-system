"""Observation Fusion Module."""
from ai_engine.intelligence.observation_fusion.models import (
    ObservationFusionConfig,
    UnifiedObservation,
    FaceObservation,
    EnvironmentObservation,
    AudioObservation,
    ObservationConfidenceSummary
)
from ai_engine.intelligence.observation_fusion.result import ObservationFusionResult
from ai_engine.intelligence.observation_fusion.processor import ObservationFusionProcessorInterface
from ai_engine.intelligence.observation_fusion.fusion_processor import FusionProcessor
from ai_engine.intelligence.observation_fusion.exceptions import (
    ObservationFusionError,
    MissingObservationError,
    InvalidObservationError
)

__all__ = [
    "ObservationFusionConfig",
    "UnifiedObservation",
    "FaceObservation",
    "EnvironmentObservation",
    "AudioObservation",
    "ObservationConfidenceSummary",
    "ObservationFusionResult",
    "ObservationFusionProcessorInterface",
    "FusionProcessor",
    "ObservationFusionError",
    "MissingObservationError",
    "InvalidObservationError"
]
