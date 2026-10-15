"""Result models for Observation Fusion."""
from dataclasses import dataclass
from ai_engine.intelligence.observation_fusion.models import UnifiedObservation

@dataclass
class ObservationFusionResult:
    """Wrapper for the final unified observation."""
    observation: UnifiedObservation
