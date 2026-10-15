"""
Observation model for Identity Protection & Anti-Spoofing.
"""
import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass
class IdentityProtectionObservation:
    """
    Observation schema emitted by the Identity Protection Subsystem.
    """
    liveness_state: str = "LIVE"  # LIVE, SPOOF_SUSPECTED, SPOOF_CONFIRMED
    liveness_score: float = 1.0   # [0.0 - 1.0] continuous probability
    presentation_attack_type: str = "NONE"  # NONE, PRINTED_PHOTO, SCREEN_REPLAY, VIRTUAL_FEED, MASK
    identity_integrity_score: float = 1.0  # Composite Liveness * Cosine Identity Similarity
    spoof_confidence: float = 0.0
    reason: str = "Candidate identity and liveness verified"
    inference_timestamp: float = field(default_factory=time.time)
    model_version: str = "1.0.0-framework-foundation"
    inference_latency_ms: float = 0.0
    
    # Phase 4.3 Supporting Visual Analyzer Metrics
    mesh_confidence: float = 1.0
    reflection_score: float = 0.0
    temporal_consistency: float = 1.0
    supporting_signals: Dict[str, Any] = field(default_factory=dict)
    
    # Phase 4.4 Decision Systems Integrity Assessment
    assessment: Optional[Any] = None
    
    raw_metrics: Dict[str, Any] = field(default_factory=dict)
