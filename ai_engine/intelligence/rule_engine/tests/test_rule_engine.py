import pytest

from ai_engine.core.exam_context import ExamContext
from ai_engine.intelligence.observation_fusion.models import (
    UnifiedObservation,
    FaceObservation,
    EnvironmentObservation
)
from ai_engine.intelligence.rule_engine.models import RuleEngineConfig
from ai_engine.intelligence.rule_engine.rule_engine import RuleEngineProcessor

@pytest.fixture
def config_all_enabled():
    config = RuleEngineConfig()
    # Explicitly enable everything for testing
    for k in config.enabled_rules.keys():
        config.enabled_rules[k] = True
    config.enable_logging = False
    return config

@pytest.fixture
def processor(config_all_enabled):
    proc = RuleEngineProcessor(config_all_enabled)
    proc.initialize()
    proc.start()
    return proc

def test_engine_lifecycle(config_all_enabled):
    proc = RuleEngineProcessor(config_all_enabled)
    assert not proc.is_initialized
    proc.initialize()
    assert proc.is_initialized
    assert len(proc._active_rules) > 0
    proc.start()
    proc.stop()
    proc.cleanup()
    assert not proc.is_initialized
    assert len(proc._active_rules) == 0

def test_no_rules_triggered(processor):
    ctx = ExamContext()
    ctx.observation = UnifiedObservation(
        face=FaceObservation(
            face_present=True,
            identity_consistent=True,
            gaze_state="CENTER",
            head_pose_state="FORWARD"
        ),
        environment=EnvironmentObservation(
            total_persons=1,
            phone_present=False,
            book_present=False,
            tracked_entities_summary=[]
        )
    )
    
    processor.process(ctx)
    result = ctx.rule_results
    
    assert result.statistics.total_rules_evaluated > 0
    assert result.statistics.total_rules_triggered == 0
    assert len([e for e in result.evaluations if e.triggered]) == 0

def test_single_rule_triggered(processor):
    ctx = ExamContext()
    ctx.observation = UnifiedObservation(
        face=FaceObservation(
            face_present=True,
            identity_consistent=True,
            gaze_state="CENTER",
            head_pose_state="FORWARD"
        ),
        environment=EnvironmentObservation(
            total_persons=1,
            phone_present=True, # Phone present!
            book_present=False,
            tracked_entities_summary=[]
        )
    )
    
    processor.process(ctx)
    result = ctx.rule_results
    
    triggered = [e for e in result.evaluations if e.triggered]
    assert len(triggered) == 1
    assert triggered[0].rule_id == "UNAUTH_PHONE"

def test_multiple_rules_triggered(processor):
    ctx = ExamContext()
    ctx.observation = UnifiedObservation(
        face=FaceObservation(
            face_present=True,
            identity_consistent=False, # Mismatch!
            gaze_state="DOWN", # Downward gaze!
            head_pose_state="FORWARD"
        ),
        environment=EnvironmentObservation(
            total_persons=1,
            phone_present=False,
            book_present=True, # Book present!
            tracked_entities_summary=[{"type": "NOTEBOOK", "conf": 0.9}] # Notebook present!
        )
    )
    
    processor.process(ctx)
    result = ctx.rule_results
    
    triggered = {e.rule_id for e in result.evaluations if e.triggered}
    
    expected = {"ATT_DOWNWARD_GAZE", "ID_MISMATCH", "UNAUTH_BOOK", "UNAUTH_NOTEBOOK"}
    assert expected.issubset(triggered)

def test_disabled_rules():
    config = RuleEngineConfig()
    config.enabled_rules["UNAUTH_PHONE"] = False
    
    proc = RuleEngineProcessor(config)
    proc.initialize()
    proc.start()
    
    ctx = ExamContext()
    ctx.observation = UnifiedObservation(
        face=FaceObservation(face_present=True, identity_consistent=True),
        environment=EnvironmentObservation(phone_present=True) # Phone present but rule is disabled
    )
    
    proc.process(ctx)
    result = ctx.rule_results
    
    triggered = [e.rule_id for e in result.evaluations if e.triggered]
    assert "UNAUTH_PHONE" not in triggered

def test_missing_observation(processor):
    ctx = ExamContext()
    # Missing observation entirely
    assert not hasattr(ctx, "observation")
    
    processor.process(ctx)
    
    # Engine should not crash, it should just output 0 evaluations
    assert hasattr(ctx, "rule_results")
    assert len(ctx.rule_results.evaluations) == 0
