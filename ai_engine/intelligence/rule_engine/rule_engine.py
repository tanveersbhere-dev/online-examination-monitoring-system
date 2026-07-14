"""Rule Engine Processor implementation."""
import time
import logging
from typing import List

from ai_engine.core.exam_context import ExamContext
from ai_engine.intelligence.rule_engine.processor import RuleEngineProcessorInterface
from ai_engine.intelligence.rule_engine.models import (
    RuleEngineConfig,
    RuleEvaluation,
    RuleStatistics
)
from ai_engine.intelligence.rule_engine.result import RuleEngineResult
from ai_engine.intelligence.rule_engine.rules import AVAILABLE_RULES, RuleInterface
from ai_engine.intelligence.rule_engine.exceptions import (
    RuleEngineError,
    RuleEvaluationError,
    InvalidRuleConfigurationError
)

logger = logging.getLogger(__name__)

class RuleEngineProcessor(RuleEngineProcessorInterface):
    """
    Evaluates enabled examination rules against the current UnifiedObservation.
    """
    
    def __init__(self, config: RuleEngineConfig) -> None:
        super().__init__(config)
        self._initialized = False
        self._active_rules: List[RuleInterface] = []
        self._last_evaluation_time = 0.0

    def initialize(self) -> None:
        if self._config.enable_logging:
            logger.debug("Initializing RuleEngineProcessor...")
            
        self._active_rules.clear()
        
        # Discover and initialize enabled rules
        for rule_class in AVAILABLE_RULES:
            rule_instance = rule_class()
            rule_id = rule_instance.rule_id
            
            # Check if enabled in config
            if self._config.enabled_rules.get(rule_id, False):
                self._active_rules.append(rule_instance)
                if self._config.enable_logging:
                    logger.debug(f"Rule enabled: {rule_id} ({rule_instance.rule_name})")
            else:
                if self._config.enable_logging:
                    logger.debug(f"Rule ignored/disabled: {rule_id}")
                    
        if not self._active_rules and self._config.enable_logging:
            logger.warning("No rules were enabled for the RuleEngineProcessor.")
            
        self._initialized = True
        if self._config.enable_logging:
            logger.debug(f"RuleEngineProcessor initialized with {len(self._active_rules)} active rules.")

    def start(self) -> None:
        if not self._initialized:
            raise RuleEngineError("Cannot start uninitialized RuleEngineProcessor.")
        if self._config.enable_logging:
            logger.debug("RuleEngineProcessor started.")

    def stop(self) -> None:
        if self._config.enable_logging:
            logger.debug("RuleEngineProcessor stopped.")

    def cleanup(self) -> None:
        if self._config.enable_logging:
            logger.debug("Cleaning up RuleEngineProcessor...")
        self._active_rules.clear()
        self._initialized = False

    def process(self, context: ExamContext) -> None:
        if not self._initialized:
            raise RuleEngineError("RuleEngineProcessor is not initialized.")
            
        current_time = time.time()
        
        # Check evaluation interval
        if self._config.evaluation_interval_seconds > 0:
            if current_time - self._last_evaluation_time < self._config.evaluation_interval_seconds:
                return
                
        start_perf = time.perf_counter()
        
        if not hasattr(context, "observation") or context.observation is None:
            if self._config.enable_logging:
                logger.warning("No observation found in context. Rule Engine skipping evaluation.")
            # We will still output empty results to fulfill the output contract
            empty_result = RuleEngineResult(evaluations=[], statistics=RuleStatistics())
            setattr(context, "rule_results", empty_result)
            return
            
        observation = context.observation
        evaluations: List[RuleEvaluation] = []
        stats = RuleStatistics()
        
        stats.total_rules_evaluated = len(self._active_rules)
        
        for rule in self._active_rules:
            rule_start = time.perf_counter()
            try:
                triggered, confidence, support = rule.evaluate(observation, self._config)
                
                rule_duration = (time.perf_counter() - rule_start) * 1000
                
                evaluation = RuleEvaluation(
                    rule_id=rule.rule_id,
                    rule_name=rule.rule_name,
                    category=rule.category,
                    triggered=triggered,
                    confidence=confidence,
                    supporting_observations=support,
                    evaluation_timestamp=current_time,
                    evaluation_duration=rule_duration
                )
                
                evaluations.append(evaluation)
                
                if triggered:
                    stats.total_rules_triggered += 1
                    stats.triggered_by_category[rule.category] = stats.triggered_by_category.get(rule.category, 0) + 1
                    
                    if self._config.enable_logging:
                        logger.info(f"Rule TRIGGERED: {rule.rule_id} - {support} (Conf: {confidence:.2f})")
                        
            except Exception as e:
                # Do not crash the entire engine if one rule fails, just log it.
                if self._config.enable_logging:
                    logger.error(f"RuleEvaluationError evaluating {rule.rule_id}: {e}")
                    
        stats.processing_time_ms = (time.perf_counter() - start_perf) * 1000
        
        result = RuleEngineResult(
            evaluations=evaluations,
            statistics=stats
        )
        
        setattr(context, "rule_results", result)
        self._last_evaluation_time = current_time
        
        if self._config.enable_logging:
            logger.debug(f"Evaluated {stats.total_rules_evaluated} rules in {stats.processing_time_ms:.2f}ms. Triggered: {stats.total_rules_triggered}.")
