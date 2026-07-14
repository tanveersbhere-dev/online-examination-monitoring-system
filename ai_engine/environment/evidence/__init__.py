"""
Evidence Snapshot Manager Module.
"""
from ai_engine.environment.evidence.models import EvidenceConfig, EvidenceSnapshot, SnapshotMetadata
from ai_engine.environment.evidence.result import EvidenceResult
from ai_engine.environment.evidence.manager import EvidenceSnapshotManagerInterface
from ai_engine.environment.evidence.snapshot_manager import EvidenceSnapshotManager
from ai_engine.environment.evidence.exceptions import (
    EvidenceManagerError,
    SnapshotCreationError,
    SnapshotStorageError,
    ImageProcessingError
)

__all__ = [
    "EvidenceConfig",
    "EvidenceSnapshot",
    "SnapshotMetadata",
    "EvidenceResult",
    "EvidenceSnapshotManagerInterface",
    "EvidenceSnapshotManager",
    "EvidenceManagerError",
    "SnapshotCreationError",
    "SnapshotStorageError",
    "ImageProcessingError"
]
