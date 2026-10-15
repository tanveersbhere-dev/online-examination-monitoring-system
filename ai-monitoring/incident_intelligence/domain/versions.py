"""
Schema Versioning Definitions for Incident Intelligence Platform.
"""
from dataclasses import dataclass

INCIDENT_SCHEMA_VERSION = "1.0.0"
EVIDENCE_SCHEMA_VERSION = "1.0.0"

@dataclass(frozen=True)
class IncidentSchemaVersion:
    major: int = 1
    minor: int = 0
    patch: int = 0
    version_string: str = INCIDENT_SCHEMA_VERSION

@dataclass(frozen=True)
class EvidenceSchemaVersion:
    major: int = 1
    minor: int = 0
    patch: int = 0
    version_string: str = EVIDENCE_SCHEMA_VERSION
