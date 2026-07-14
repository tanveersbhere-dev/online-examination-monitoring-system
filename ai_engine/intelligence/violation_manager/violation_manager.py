"""Violation Manager implementation."""
import time
import logging

from ai_engine.core.exam_context import ExamContext
from ai_engine.intelligence.violation_manager.processor import ViolationManagerProcessorInterface
from ai_engine.intelligence.violation_manager.models import (
    ViolationManagerConfig
)
from ai_engine.intelligence.violation_manager.result import ViolationManagerResult
from ai_engine.intelligence.violation_manager.violation_timeline import ViolationTimelineManager
from ai_engine.intelligence.violation_manager.exceptions import ViolationManagerError

logger = logging.getLogger(__name__)

class ViolationManagerProcessor(ViolationManagerProcessorInterface):
    """
    Manages lifecycle of examination violations across time based on Rule Engine and Risk Engine outputs.
    """
    
    def __init__(self, config: ViolationManagerConfig) -> None:
        super().__init__(config)
        self._timeline_manager = ViolationTimelineManager(config)
        self._initialized = False

    def initialize(self) -> None:
        if self._config.enable_logging:
            logger.debug("Initializing ViolationManagerProcessor...")
        self._timeline_manager = ViolationTimelineManager(self._config)
        self._initialized = True
        if self._config.enable_logging:
            logger.debug("ViolationManagerProcessor initialized.")

    def start(self) -> None:
        if not self._initialized:
            raise ViolationManagerError("Cannot start uninitialized ViolationManagerProcessor.")
        if self._config.enable_logging:
            logger.debug("ViolationManagerProcessor started.")

    def stop(self) -> None:
        if self._config.enable_logging:
            logger.debug("ViolationManagerProcessor stopped.")
        # Optionally force close all on stop
        self._timeline_manager.close_all(time.time())

    def cleanup(self) -> None:
        if self._config.enable_logging:
            logger.debug("Cleaning up ViolationManagerProcessor...")
        self._timeline_manager.close_all(time.time())
        self._initialized = False

    def process(self, context: ExamContext) -> None:
        if not self._initialized:
            raise ViolationManagerError("ViolationManagerProcessor is not initialized.")
            
        current_time = time.time()
        
        # Pull triggered rules
        triggered_rules = []
        if hasattr(context, "rule_results") and context.rule_results is not None:
            for ev in context.rule_results.evaluations:
                if ev.triggered:
                    triggered_rules.append({
                        "rule_id": ev.rule_id,
                        "category": ev.category
                    })
                    
        # Pull risk score
        risk_score = 0.0
        risk_level = "NORMAL"
        if hasattr(context, "risk_assessment") and context.risk_assessment is not None:
            risk_score = context.risk_assessment.overall_score
            risk_level = context.risk_assessment.risk_level
            
        # Pull evidence
        evidence_refs = []
        if hasattr(context, "object_info") and context.object_info is not None:
            if hasattr(context.object_info, "evidence") and context.object_info.evidence is not None:
                for ev in context.object_info.evidence:
                    # Collect snapshot IDs if available
                    if hasattr(ev, "snapshot_id"):
                        evidence_refs.append(ev.snapshot_id)
                        
        # Only invoke triggers if risk score is > 0 or if rules triggered
        if triggered_rules or risk_score > 0:
            self._timeline_manager.process_triggers(
                triggered_rules=triggered_rules,
                risk_score=risk_score,
                risk_level=risk_level,
                evidence_refs=evidence_refs,
                current_time=current_time
            )
        else:
            # Still call process to handle auto-closing
            self._timeline_manager.process_triggers([], 0.0, "NORMAL", [], current_time)
            
        result = ViolationManagerResult(
            timeline=self._timeline_manager.timeline,
            statistics=self._timeline_manager.statistics
        )
        
        setattr(context, "violations", result)
