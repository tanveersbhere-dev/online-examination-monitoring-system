import pytest
import time

from ai_engine.core.exam_context import ExamContext
from ai_engine.intelligence.rule_engine.models import RuleEvaluation
from ai_engine.intelligence.rule_engine.result import RuleEngineResult, RuleStatistics
from ai_engine.intelligence.risk_scoring.models import RiskScoringConfig
from ai_engine.intelligence.risk_scoring.risk_engine import RiskScoringProcessor
from ai_engine.intelligence.risk_scoring.exceptions import RiskScoringError, ScoreCalculationError

@pytest.fixture
def config():
    return RiskScoringConfig(
        rule_weights={
            "RULE_LOW": 10.0,
            "RULE_MID": 30.0,
            "RULE_HIGH": 60.0
        },
        enable_logging=False
    )

@pytest.fixture
def processor(config):
    proc = RiskScoringProcessor(config)
    proc.initialize()
    proc.start()
    return proc

def test_processor_lifecycle(config):
    proc = RiskScoringProcessor(config)
    assert not proc.is_initialized
    proc.initialize()
    assert proc.is_initialized
    proc.start()
    proc.stop()
    proc.cleanup()
    assert not proc.is_initialized

def test_no_rules_triggered(processor):
    ctx = ExamContext()
    
    # Populate rule_results with no triggered rules
    evals = [
        RuleEvaluation("RULE_LOW", "Low Risk Rule", "TEST", False, 0.0, "", time.time(), 1.0)
    ]
    setattr(ctx, "rule_results", RuleEngineResult(evaluations=evals, statistics=RuleStatistics()))
    
    processor.process(ctx)
    assessment = ctx.risk_assessment
    
    assert assessment.overall_score == 0.0
    assert assessment.risk_level == "NORMAL"
    assert assessment.triggered_rule_count == 0

def test_single_rule_contribution(processor):
    ctx = ExamContext()
    
    evals = [
        RuleEvaluation("RULE_LOW", "Low Risk Rule", "TEST", True, 0.9, "", time.time(), 1.0)
    ]
    setattr(ctx, "rule_results", RuleEngineResult(evaluations=evals, statistics=RuleStatistics()))
    
    processor.process(ctx)
    assessment = ctx.risk_assessment
    
    assert assessment.overall_score == 10.0
    assert assessment.risk_level == "NORMAL"
    assert assessment.triggered_rule_count == 1
    assert assessment.highest_priority_rule_id == "RULE_LOW"

def test_multiple_rule_contributions_and_normalization(processor):
    ctx = ExamContext()
    
    evals = [
        RuleEvaluation("RULE_MID", "Mid Risk Rule", "TEST", True, 0.9, "", time.time(), 1.0), # 30
        RuleEvaluation("RULE_HIGH", "High Risk Rule", "TEST", True, 0.9, "", time.time(), 1.0), # 60
        RuleEvaluation("RULE_LOW", "Low Risk Rule", "TEST", True, 0.9, "", time.time(), 1.0), # 10
        RuleEvaluation("UNKNOWN_RULE", "Unknown", "TEST", True, 0.9, "", time.time(), 1.0) # Falls back to 10
    ]
    setattr(ctx, "rule_results", RuleEngineResult(evaluations=evals, statistics=RuleStatistics()))
    
    processor.process(ctx)
    assessment = ctx.risk_assessment
    
    # 30 + 60 + 10 + 10 = 110, capped at 100
    assert assessment.overall_score == 100.0
    assert assessment.risk_level == "CRITICAL"
    assert assessment.triggered_rule_count == 4
    assert assessment.highest_priority_rule_id == "RULE_HIGH"

def test_threshold_transitions(processor):
    ctx = ExamContext()
    
    # Exactly 20 should be NORMAL
    evals = [
        RuleEvaluation("RULE_LOW", "L", "T", True, 1.0, "", time.time(), 1.0),
        RuleEvaluation("RULE_LOW", "L", "T", True, 1.0, "", time.time(), 1.0) # Assume 2 rules triggering same ID or diff IDs with same weight
    ]
    setattr(ctx, "rule_results", RuleEngineResult(evaluations=evals, statistics=RuleStatistics()))
    processor.process(ctx)
    assert ctx.risk_assessment.overall_score == 20.0
    assert ctx.risk_assessment.risk_level == "NORMAL"

def test_missing_rule_results(processor):
    ctx = ExamContext()
    assert not hasattr(ctx, "rule_results")
    
    processor.process(ctx)
    
    # Should safely emit a 0.0 score
    assert hasattr(ctx, "risk_assessment")
    assert ctx.risk_assessment.overall_score == 0.0
    assert ctx.risk_assessment.risk_level == "NORMAL"

def test_invalid_configuration():
    config = RiskScoringConfig(rule_weights={}, risk_thresholds={})
    proc = RiskScoringProcessor(config)
    
    with pytest.raises(RiskScoringError):
        proc.initialize()
