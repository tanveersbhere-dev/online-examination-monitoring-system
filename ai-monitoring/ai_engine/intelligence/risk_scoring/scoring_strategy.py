"""Strategy pattern definitions for Risk Scoring."""
from abc import ABC, abstractmethod
from typing import List, Tuple
import time

from ai_engine.intelligence.risk_scoring.models import (
    RiskScoringConfig,
    RiskContribution,
    RiskAssessment
)
from ai_engine.intelligence.rule_engine.models import RuleEvaluation
from ai_engine.intelligence.risk_scoring.exceptions import ScoreCalculationError

class ScoringStrategyInterface(ABC):
    """Abstract interface for scoring strategies."""
    
    @abstractmethod
    def calculate_score(self, evaluations: List[RuleEvaluation], config: RiskScoringConfig) -> RiskAssessment:
        """
        Calculates the final risk assessment based on triggered rule evaluations.
        """
        pass

class DefaultScoringStrategy(ScoringStrategyInterface):
    """
    Default strategy:
    - Sums raw configured weights of all triggered rules.
    - Capped at max_score (e.g. 100).
    - Maps the final score to categorical thresholds.
    """
    
    def calculate_score(self, evaluations: List[RuleEvaluation], config: RiskScoringConfig) -> RiskAssessment:
        start_time = time.perf_counter()
        
        contributions: List[RiskContribution] = []
        raw_total = 0.0
        triggered_count = 0
        highest_priority_id = "NONE"
        highest_weight = -1.0
        breakdown = {}
        
        for eval_obj in evaluations:
            if eval_obj.triggered:
                # Look up weight, defaulting to 10.0 if not configured to prevent crashes but allow fallback
                weight = config.rule_weights.get(eval_obj.rule_id, 10.0)
                
                raw_total += weight
                triggered_count += 1
                
                contributions.append(RiskContribution(
                    rule_id=eval_obj.rule_id,
                    rule_name=eval_obj.rule_name,
                    weight=weight,
                    contribution=weight # Before normalization
                ))
                
                breakdown[eval_obj.rule_id] = weight
                
                if weight > highest_weight:
                    highest_weight = weight
                    highest_priority_id = eval_obj.rule_id
                    
        # Normalize score
        final_score = min(raw_total, config.max_score)
        
        # Determine risk level
        risk_level = self._determine_risk_level(final_score, config)
        
        duration = (time.perf_counter() - start_time) * 1000
        
        return RiskAssessment(
            overall_score=final_score,
            risk_level=risk_level,
            contributions=contributions,
            triggered_rule_count=triggered_count,
            highest_priority_rule_id=highest_priority_id,
            weighted_score_breakdown=breakdown,
            processing_timestamp=time.time(),
            processing_duration=duration
        )

    def _determine_risk_level(self, score: float, config: RiskScoringConfig) -> str:
        # Sort thresholds by min value to iterate correctly
        for level, (min_val, max_val) in config.risk_thresholds.items():
            if min_val <= score <= max_val:
                return level
                
        # Fallback if score exceeds highest bound
        if score > config.max_score:
            return "CRITICAL"
            
        return "NORMAL"


class DynamicScoringStrategy(ScoringStrategyInterface):
    """
    Dynamic Risk Scoring Strategy:
    - Maintains running risk state across continuous frames.
    - Scales weight contributions by rule evaluation confidence.
    - Applies a gradual decay factor when candidate behavior is compliant.
    - Clamps score strictly in range [0.0, 100.0].
    """
    
    def __init__(self, decay_factor: float = 0.98, recovery_floor: float = 0.0) -> None:
        self._current_score: float = 0.0
        self._decay_factor: float = decay_factor
        self._recovery_floor: float = recovery_floor

    def calculate_score(self, evaluations: List[RuleEvaluation], config: RiskScoringConfig) -> RiskAssessment:
        start_time = time.perf_counter()
        
        contributions: List[RiskContribution] = []
        triggered_count = 0
        highest_priority_id = "NONE"
        highest_weight = -1.0
        breakdown = {}
        frame_added_risk = 0.0
        
        for eval_obj in evaluations:
            if eval_obj.triggered:
                weight = config.rule_weights.get(eval_obj.rule_id, 10.0)
                conf_scaled_weight = weight * max(0.5, eval_obj.confidence)
                
                frame_added_risk += conf_scaled_weight
                triggered_count += 1
                
                contributions.append(RiskContribution(
                    rule_id=eval_obj.rule_id,
                    rule_name=eval_obj.rule_name,
                    weight=weight,
                    contribution=round(conf_scaled_weight, 2)
                ))
                
                breakdown[eval_obj.rule_id] = round(conf_scaled_weight, 2)
                
                if weight > highest_weight:
                    highest_weight = weight
                    highest_priority_id = eval_obj.rule_id

        if triggered_count > 0:
            # Increase running score
            self._current_score = min(config.max_score, self._current_score + frame_added_risk)
        else:
            # Decay score during compliant frames
            self._current_score = max(self._recovery_floor, self._current_score * self._decay_factor)

        final_score = round(self._current_score, 2)
        
        # Determine risk level
        for level, (min_val, max_val) in config.risk_thresholds.items():
            if min_val <= final_score <= max_val:
                risk_level = level
                break
        else:
            risk_level = "CRITICAL" if final_score > config.max_score * 0.75 else "NORMAL"
            
        duration = (time.perf_counter() - start_time) * 1000
        
        return RiskAssessment(
            overall_score=final_score,
            risk_level=risk_level,
            contributions=contributions,
            triggered_rule_count=triggered_count,
            highest_priority_rule_id=highest_priority_id,
            weighted_score_breakdown=breakdown,
            processing_timestamp=time.time(),
            processing_duration=duration
        )

