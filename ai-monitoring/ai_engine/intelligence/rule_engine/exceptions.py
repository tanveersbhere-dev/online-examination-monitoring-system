"""Exceptions for Rule Engine."""
from ai_engine.core.exceptions import AIEngineError

class RuleEngineError(AIEngineError):
    """Base exception for rule engine errors."""
    pass

class RuleEvaluationError(RuleEngineError):
    """Raised when an individual rule fails to evaluate properly."""
    pass

class InvalidRuleConfigurationError(RuleEngineError):
    """Raised when the rule engine is improperly configured."""
    pass
