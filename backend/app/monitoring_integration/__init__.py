"""
Monitoring Integration Layer
============================
Bridge between the Main FYP Examination System and the AI Monitoring Subsystem.
"""
from app.monitoring_integration.monitoring_contracts import (
    MonitoringSeverity,
    MonitoringStatus,
    NormalizedMonitoringEvent,
    EVENT_TYPE_MAPPING,
    SEVERITY_MAPPING,
)
from app.monitoring_integration.face_embedding_service import (
    FaceEmbeddingService,
    FaceEmbeddingError,
)
from app.monitoring_integration.monitoring_event_normalizer import (
    MonitoringEventNormalizer,
)
from app.monitoring_integration.monitoring_session_adapter import (
    MonitoringSessionAdapter,
    MonitoringSubsystemThread,
)
from app.monitoring_integration.monitoring_summary_adapter import (
    MonitoringSummaryAdapter,
)

__all__ = [
    "MonitoringSeverity",
    "MonitoringStatus",
    "NormalizedMonitoringEvent",
    "EVENT_TYPE_MAPPING",
    "SEVERITY_MAPPING",
    "FaceEmbeddingService",
    "FaceEmbeddingError",
    "MonitoringEventNormalizer",
    "MonitoringSessionAdapter",
    "MonitoringSubsystemThread",
    "MonitoringSummaryAdapter",
]
