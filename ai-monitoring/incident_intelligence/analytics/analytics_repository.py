"""
Analytics Repository and Snapshot Model for IIAE.
Stores immutable IncidentAnalyticsSnapshot objects.
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List
import time

from incident_intelligence.analytics.incident_metrics import IncidentMetrics, IncidentMetricsDTO
from incident_intelligence.analytics.confidence_analysis import ConfidenceAnalysis, ConfidenceAnalysisDTO
from incident_intelligence.analytics.risk_analysis import RiskAnalysis, RiskAnalysisDTO
from incident_intelligence.analytics.behavior_analysis import BehaviorAnalysis, BehaviorAnalysisDTO
from incident_intelligence.analytics.timeline_statistics import TimelineStatistics, TimelineStatisticsDTO

@dataclass(frozen=True)
class IncidentAnalyticsSnapshot:
    """Immutable analytics snapshot for an incident."""
    snapshot_id: str
    incident_id: str
    timestamp: float
    metrics: IncidentMetrics
    confidence_analysis: ConfidenceAnalysis
    risk_analysis: RiskAnalysis
    behavior_analysis: BehaviorAnalysis
    timeline_statistics: TimelineStatistics

    def to_dto(self) -> 'IncidentAnalyticsSnapshotDTO':
        return IncidentAnalyticsSnapshotDTO(
            snapshot_id=self.snapshot_id,
            incident_id=self.incident_id,
            timestamp=self.timestamp,
            metrics=self.metrics.to_dto(),
            confidence_analysis=self.confidence_analysis.to_dto(),
            risk_analysis=self.risk_analysis.to_dto(),
            behavior_analysis=self.behavior_analysis.to_dto(),
            timeline_statistics=self.timeline_statistics.to_dto()
        )

@dataclass(frozen=True)
class IncidentAnalyticsSnapshotDTO:
    """Data Transfer Object for IncidentAnalyticsSnapshot."""
    snapshot_id: str
    incident_id: str
    timestamp: float
    metrics: IncidentMetricsDTO
    confidence_analysis: ConfidenceAnalysisDTO
    risk_analysis: RiskAnalysisDTO
    behavior_analysis: BehaviorAnalysisDTO
    timeline_statistics: TimelineStatisticsDTO

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "incident_id": self.incident_id,
            "timestamp": self.timestamp,
            "metrics": self.metrics.to_dict(),
            "confidence_analysis": self.confidence_analysis.to_dict(),
            "risk_analysis": self.risk_analysis.to_dict(),
            "behavior_analysis": self.behavior_analysis.to_dict(),
            "timeline_statistics": self.timeline_statistics.to_dict()
        }

class InMemoryAnalyticsRepository:
    """In-memory repository for analytics snapshots."""

    def __init__(self):
        self._snapshots_by_incident: Dict[str, List[IncidentAnalyticsSnapshot]] = {}

    def save(self, snapshot: IncidentAnalyticsSnapshot) -> None:
        """Save an analytics snapshot."""
        inc_id = snapshot.incident_id
        if inc_id not in self._snapshots_by_incident:
            self._snapshots_by_incident[inc_id] = []
        self._snapshots_by_incident[inc_id].append(snapshot)

    def get_latest(self, incident_id: str) -> Optional[IncidentAnalyticsSnapshot]:
        """Fetch latest snapshot for an incident."""
        snapshots = self._snapshots_by_incident.get(incident_id, [])
        return snapshots[-1] if snapshots else None

    def get_all(self, incident_id: str) -> List[IncidentAnalyticsSnapshot]:
        """Fetch all historical snapshots for an incident."""
        return list(self._snapshots_by_incident.get(incident_id, []))

    def clear(self) -> None:
        """Clear repository."""
        self._snapshots_by_incident.clear()
