"""
Result object for Evidence Snapshot Manager.
"""
from dataclasses import dataclass, field
from typing import List
from ai_engine.environment.evidence.models import EvidenceSnapshot

@dataclass
class EvidenceResult:
    """Wrapper for all newly captured evidence in the current frame processing cycle."""
    snapshots: List[EvidenceSnapshot] = field(default_factory=list)
