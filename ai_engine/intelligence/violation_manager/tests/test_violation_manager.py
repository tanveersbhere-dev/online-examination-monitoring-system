import pytest
import time
from unittest.mock import MagicMock

from ai_engine.core.exam_context import ExamContext
from ai_engine.intelligence.rule_engine.models import RuleEvaluation
from ai_engine.intelligence.rule_engine.result import RuleEngineResult, RuleStatistics
from ai_engine.intelligence.risk_scoring.models import RiskAssessment
from ai_engine.intelligence.violation_manager.models import ViolationManagerConfig
from ai_engine.intelligence.violation_manager.violation_manager import ViolationManagerProcessor

@pytest.fixture
def config():
    return ViolationManagerConfig(
        merge_window_seconds=10.0,
        auto_close_timeout_seconds=30.0,
        maximum_active_violations=5,
        enable_logging=False
    )

@pytest.fixture
def processor(config):
    proc = ViolationManagerProcessor(config)
    proc.initialize()
    proc.start()
    return proc

def test_processor_lifecycle(config):
    proc = ViolationManagerProcessor(config)
    assert not proc.is_initialized
    proc.initialize()
    assert proc.is_initialized
    proc.start()
    proc.stop()
    proc.cleanup()
    assert not proc.is_initialized

def test_violation_creation(processor):
    ctx = ExamContext()
    
    # Mock rule results
    evals = [RuleEvaluation("UNAUTH_PHONE", "Phone", "Material", True, 0.9, "", time.time(), 1.0)]
    setattr(ctx, "rule_results", RuleEngineResult(evaluations=evals, statistics=RuleStatistics()))
    
    # Mock risk score
    assessment = RiskAssessment(50.0, "MEDIUM", [], 1, "UNAUTH_PHONE", {}, time.time(), 1.0)
    setattr(ctx, "risk_assessment", assessment)
    
    processor.process(ctx)
    result = ctx.violations
    
    assert len(result.timeline.violations) == 1
    v = result.timeline.violations[0]
    assert v.status == "OPEN"
    assert v.violation_type == "UNAUTH_PHONE"
    assert v.risk_score == 50.0
    assert "UNAUTH_PHONE" in v.triggered_rules

def test_violation_merging(processor):
    ctx = ExamContext()
    
    # Frame 1: Phone visible
    evals = [RuleEvaluation("UNAUTH_PHONE", "Phone", "Material", True, 0.9, "", time.time(), 1.0)]
    setattr(ctx, "rule_results", RuleEngineResult(evaluations=evals, statistics=RuleStatistics()))
    setattr(ctx, "risk_assessment", RiskAssessment(30.0, "LOW", [], 1, "UNAUTH_PHONE", {}, time.time(), 1.0))
    processor.process(ctx)
    
    # Frame 2: Look away (should merge into same violation)
    evals2 = [RuleEvaluation("ATT_LOOKING_AWAY", "Look Away", "Attention", True, 0.9, "", time.time(), 1.0)]
    setattr(ctx, "rule_results", RuleEngineResult(evaluations=evals2, statistics=RuleStatistics()))
    # Score goes up
    setattr(ctx, "risk_assessment", RiskAssessment(50.0, "MEDIUM", [], 1, "ATT_LOOKING_AWAY", {}, time.time(), 1.0))
    processor.process(ctx)
    
    result = ctx.violations
    assert len(result.timeline.violations) == 1
    v = result.timeline.violations[0]
    
    assert v.status == "ACTIVE"
    assert v.risk_score == 50.0
    assert v.severity == "MEDIUM"
    assert "UNAUTH_PHONE" in v.triggered_rules
    assert "ATT_LOOKING_AWAY" in v.triggered_rules
    assert result.statistics.total_merged == 1

def test_auto_close_timeout(processor):
    ctx = ExamContext()
    
    evals = [RuleEvaluation("UNAUTH_PHONE", "Phone", "Material", True, 0.9, "", time.time(), 1.0)]
    setattr(ctx, "rule_results", RuleEngineResult(evaluations=evals, statistics=RuleStatistics()))
    setattr(ctx, "risk_assessment", RiskAssessment(30.0, "LOW", [], 1, "UNAUTH_PHONE", {}, time.time(), 1.0))
    processor.process(ctx)
    
    # Mock time jump > 30 seconds
    timeline_mgr = processor._timeline_manager
    timeline_mgr.timeline.violations[0].last_updated_timestamp -= 40.0
    
    # Process frame with NO triggers
    setattr(ctx, "rule_results", RuleEngineResult(evaluations=[], statistics=RuleStatistics()))
    setattr(ctx, "risk_assessment", RiskAssessment(0.0, "NORMAL", [], 0, "NONE", {}, time.time(), 1.0))
    processor.process(ctx)
    
    v = ctx.violations.timeline.violations[0]
    assert v.status == "RESOLVED"
    assert v.end_timestamp is not None
    assert ctx.violations.statistics.total_resolved == 1

def test_maximum_active_violations(config):
    # Set max to 1
    config.maximum_active_violations = 1
    proc = ViolationManagerProcessor(config)
    proc.initialize()
    
    ctx = ExamContext()
    
    # Trigger 1
    evals = [RuleEvaluation("RULE_1", "R1", "C1", True, 1.0, "", time.time(), 1.0)]
    setattr(ctx, "rule_results", RuleEngineResult(evaluations=evals, statistics=RuleStatistics()))
    setattr(ctx, "risk_assessment", RiskAssessment(10.0, "LOW", [], 1, "R1", {}, time.time(), 1.0))
    proc.process(ctx)
    
    # Force time jump to bypass merge window (so it tries to create a new one)
    proc._timeline_manager.timeline.violations[0].last_updated_timestamp -= 20.0
    
    # Trigger 2
    evals2 = [RuleEvaluation("RULE_2", "R2", "C2", True, 1.0, "", time.time(), 1.0)]
    setattr(ctx, "rule_results", RuleEngineResult(evaluations=evals2, statistics=RuleStatistics()))
    setattr(ctx, "risk_assessment", RiskAssessment(10.0, "LOW", [], 1, "R2", {}, time.time(), 1.0))
    proc.process(ctx)
    
    # Should still only be 1 violation because maximum is 1
    assert len(ctx.violations.timeline.violations) == 1
    assert ctx.violations.timeline.violations[0].violation_type == "RULE_1"
