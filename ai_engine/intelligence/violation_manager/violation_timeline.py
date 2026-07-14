"""Temporal aggregation and state machine for violations."""
import time
import uuid
import logging
from typing import List, Optional

from ai_engine.intelligence.violation_manager.models import (
    Violation,
    ViolationTimeline,
    ViolationStatistics,
    ViolationManagerConfig
)
from ai_engine.intelligence.violation_manager.exceptions import (
    ViolationCreationError,
    ViolationMergeError
)

logger = logging.getLogger(__name__)

class ViolationTimelineManager:
    """
    Manages the lifecycle, merging, and closure of violations across time.
    """
    
    def __init__(self, config: ViolationManagerConfig):
        self._config = config
        self._timeline = ViolationTimeline()
        self._statistics = ViolationStatistics()
        
    @property
    def timeline(self) -> ViolationTimeline:
        return self._timeline
        
    @property
    def statistics(self) -> ViolationStatistics:
        return self._statistics

    def process_triggers(self, triggered_rules: List[dict], risk_score: float, risk_level: str, evidence_refs: List[str], current_time: float) -> None:
        """
        Takes raw triggers for the current frame, looks for existing violations within
        the merge window, and either creates or merges.
        """
        # Step 1: Auto-close expired violations
        self._auto_close_expired(current_time)
        
        if not triggered_rules:
            return
            
        # Step 2: Determine primary category and type for this frame's violation
        # (Usually based on the highest weight or most severe rule in the trigger list)
        primary_trigger = triggered_rules[0]
        category = primary_trigger.get("category", "UNKNOWN")
        v_type = primary_trigger.get("rule_id", "UNKNOWN_RULE")
        
        rule_ids = [r.get("rule_id") for r in triggered_rules]
        
        # Step 3: Check for active violations to merge with
        active_violations = [v for v in self._timeline.violations if v.status in ("OPEN", "ACTIVE")]
        
        merged = False
        for violation in active_violations:
            if current_time - violation.last_updated_timestamp <= self._config.merge_window_seconds:
                # Merge into this violation
                self._merge_into(violation, rule_ids, risk_score, risk_level, evidence_refs, current_time)
                merged = True
                break
                
        # Step 4: Create new if not merged
        if not merged:
            if len(active_violations) >= self._config.maximum_active_violations:
                if self._config.enable_logging:
                    logger.warning("Maximum active violations reached. Cannot create new violation.")
                return
                
            self._create_violation(v_type, category, risk_score, risk_level, rule_ids, evidence_refs, current_time)

    def _auto_close_expired(self, current_time: float) -> None:
        for violation in self._timeline.violations:
            if violation.status in ("OPEN", "ACTIVE"):
                if current_time - violation.last_updated_timestamp > self._config.auto_close_timeout_seconds:
                    violation.status = "RESOLVED"
                    violation.end_timestamp = current_time
                    self._statistics.currently_active -= 1
                    self._statistics.total_resolved += 1
                    if self._config.enable_logging:
                        logger.debug(f"Auto-closed violation {violation.violation_id}")

    def _merge_into(self, violation: Violation, rule_ids: List[str], risk_score: float, risk_level: str, evidence_refs: List[str], current_time: float) -> None:
        try:
            violation.status = "ACTIVE"
            violation.last_updated_timestamp = current_time
            
            # Use max severity
            if risk_score > violation.risk_score:
                violation.risk_score = risk_score
                violation.severity = risk_level
                
            # Append new rules and distinct evidence
            for rid in rule_ids:
                if rid not in violation.triggered_rules:
                    violation.triggered_rules.append(rid)
                    
            for ev in evidence_refs:
                if ev not in violation.supporting_evidence_references:
                    violation.supporting_evidence_references.append(ev)
                    
            violation.description = f"Aggregated violation involving {len(violation.triggered_rules)} distinct rules."
            self._statistics.total_merged += 1
            
        except Exception as e:
            raise ViolationMergeError(f"Failed to merge into violation {violation.violation_id}: {e}")

    def _create_violation(self, v_type: str, category: str, risk_score: float, risk_level: str, rule_ids: List[str], evidence_refs: List[str], current_time: float) -> None:
        try:
            v_id = f"V-{uuid.uuid4().hex[:8].upper()}"
            violation = Violation(
                violation_id=v_id,
                violation_type=v_type,
                violation_category=category,
                severity=risk_level,
                risk_score=risk_score,
                triggered_rules=list(set(rule_ids)),
                supporting_evidence_references=list(set(evidence_refs)),
                start_timestamp=current_time,
                last_updated_timestamp=current_time,
                status="OPEN",
                description=f"New violation for {category} ({v_type})"
            )
            
            self._timeline.violations.append(violation)
            self._statistics.total_violations_created += 1
            self._statistics.currently_active += 1
            
            if self._config.enable_logging:
                logger.info(f"Created new violation {v_id} ({v_type})")
                
        except Exception as e:
            raise ViolationCreationError(f"Failed to create new violation: {e}")

    def close_all(self, current_time: float) -> None:
        """Force close all active violations, typically called during cleanup."""
        for v in self._timeline.violations:
            if v.status in ("OPEN", "ACTIVE"):
                v.status = "RESOLVED"
                v.end_timestamp = current_time
                self._statistics.currently_active -= 1
                self._statistics.total_resolved += 1

    def reopen(self, violation_id: str, current_time: float) -> None:
        """Manually reopen a resolved violation."""
        for v in self._timeline.violations:
            if v.violation_id == violation_id:
                if v.status == "RESOLVED":
                    v.status = "ACTIVE"
                    v.last_updated_timestamp = current_time
                    v.end_timestamp = None
                    self._statistics.currently_active += 1
                    self._statistics.total_resolved -= 1
                    return
        # If not found or not resolved, do nothing (or raise, but keeping it safe here)
