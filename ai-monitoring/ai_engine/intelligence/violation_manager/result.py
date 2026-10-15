"""Result models for Violation Manager."""
from dataclasses import dataclass
from ai_engine.intelligence.violation_manager.models import ViolationTimeline, ViolationStatistics

@dataclass
class ViolationManagerResult:
    """Wrapper for the final violation processing results."""
    timeline: ViolationTimeline
    statistics: ViolationStatistics
