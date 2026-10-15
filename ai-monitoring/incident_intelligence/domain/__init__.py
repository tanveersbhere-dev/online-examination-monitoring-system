"""
Incident Intelligence Platform - Domain Package
Package 10.1: Incident Domain Core
"""
from incident_intelligence.domain.versions import (
    INCIDENT_SCHEMA_VERSION,
    EVIDENCE_SCHEMA_VERSION,
    IncidentSchemaVersion,
    EvidenceSchemaVersion
)

from incident_intelligence.domain.enums import (
    IncidentState,
    IncidentSeverity,
    IncidentPriority
)

from incident_intelligence.domain.evidence_reference import (
    EvidenceReference,
    EvidenceReferenceDTO
)

from incident_intelligence.domain.history import (
    ConfidenceHistoryEntry,
    RiskHistoryEntry,
    StateHistoryEntry,
    HistoryDTO
)

from incident_intelligence.domain.metadata import (
    IncidentMetadata,
    MetadataDTO
)

from incident_intelligence.domain.incident import (
    Incident,
    IncidentDTO
)

from incident_intelligence.domain.interfaces import (
    IncidentRepositoryInterface,
    IncidentFactoryInterface,
    IncidentBuilderInterface
)

__all__ = [
    "INCIDENT_SCHEMA_VERSION",
    "EVIDENCE_SCHEMA_VERSION",
    "IncidentSchemaVersion",
    "EvidenceSchemaVersion",
    "IncidentState",
    "IncidentSeverity",
    "IncidentPriority",
    "EvidenceReference",
    "EvidenceReferenceDTO",
    "ConfidenceHistoryEntry",
    "RiskHistoryEntry",
    "StateHistoryEntry",
    "HistoryDTO",
    "IncidentMetadata",
    "MetadataDTO",
    "Incident",
    "IncidentDTO",
    "IncidentRepositoryInterface",
    "IncidentFactoryInterface",
    "IncidentBuilderInterface"
]
