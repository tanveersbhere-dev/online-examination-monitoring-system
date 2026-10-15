"""
Temporal Analyzer for Behavioral Intelligence Engine.
Analyzes event occurrences over time windows to classify temporal patterns.
"""
from typing import List, Dict, Any
from ai_engine.intelligence.behavior_engine.behavior_memory import BehaviorMemory, BehaviorMemoryEntry

class TemporalAnalyzer:
    """
    Analyzes temporal patterns over recent memory window.
    """
    @staticmethod
    def is_persistent(entries: List[BehaviorMemoryEntry], min_duration_sec: float = 5.0) -> bool:
        if not entries:
            return False
        first_ts = min(e.timestamp for e in entries)
        last_ts = max(e.timestamp for e in entries)
        return (last_ts - first_ts) >= min_duration_sec

    @staticmethod
    def count_repetitions(entries: List[BehaviorMemoryEntry], window_sec: float = 30.0, current_ts: float = 0.0) -> int:
        cutoff = current_ts - window_sec
        recent = [e for e in entries if e.timestamp >= cutoff]
        return len(recent)

    @staticmethod
    def is_escalating(entries: List[BehaviorMemoryEntry]) -> bool:
        if len(entries) < 2:
            return False
        # Check if severity or risk score is increasing
        recent_scores = [e.risk_score for e in entries[-5:]]
        return recent_scores[-1] > recent_scores[0]

    @staticmethod
    def is_recovered(entries: List[BehaviorMemoryEntry], quiet_window_sec: float = 5.0, current_ts: float = 0.0) -> bool:
        if not entries:
            return True
        last_event_ts = max(e.timestamp for e in entries)
        return (current_ts - last_event_ts) >= quiet_window_sec
