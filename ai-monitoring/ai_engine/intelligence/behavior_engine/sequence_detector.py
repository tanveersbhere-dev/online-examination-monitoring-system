"""
Sequence Detector for Behavioral Intelligence Engine.
Detects ordered temporal event sequences within configurable windows (e.g. 5s, 10s, 30s).
"""
from typing import List, Optional, Tuple
from ai_engine.intelligence.behavior_engine.behavior_event import BehaviorMemoryEntry

class SequenceDetector:
    """
    Detects ordered multi-step event sequences in recent memory.
    """
    @staticmethod
    def detect_sequence(
        entries: List[BehaviorMemoryEntry],
        target_rule_sequence: List[str],
        window_seconds: float = 10.0,
        current_timestamp: float = 0.0
    ) -> Tuple[bool, List[BehaviorMemoryEntry]]:
        """
        Checks if events matching target_rule_sequence occurred in order within window_seconds.
        Example: ["UNAUTH_PHONE", "ATT_LOOKING_AWAY", "MAR"] -> Phone -> Looking Away -> Talking.
        """
        cutoff = current_timestamp - window_seconds
        recent = [e for e in entries if e.timestamp >= cutoff]

        if not recent or len(target_rule_sequence) == 0:
            return False, []

        matched_entries: List[BehaviorMemoryEntry] = []
        seq_idx = 0

        for e in recent:
            target_rule = target_rule_sequence[seq_idx]
            # Match rule name or partial string
            if target_rule in e.rule_name or target_rule == e.object_type:
                matched_entries.append(e)
                seq_idx += 1
                if seq_idx >= len(target_rule_sequence):
                    return True, matched_entries

        return False, []

    @staticmethod
    def detect_repeated_alternation(
        entries: List[BehaviorMemoryEntry],
        rule_name: str,
        min_cycles: int = 2,
        window_seconds: float = 30.0,
        current_timestamp: float = 0.0
    ) -> Tuple[bool, int]:
        """
        Detects repeating cycle of appearance and resolution/disappearance (e.g. Camera Evasion).
        """
        cutoff = current_timestamp - window_seconds
        recent = [e for e in entries if e.timestamp >= cutoff and (rule_name in e.rule_name or rule_name == e.object_type)]

        cycles = len(recent)
        return cycles >= min_cycles, cycles
