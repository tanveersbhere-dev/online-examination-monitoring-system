"""Result objects for Environment History Engine."""
from dataclasses import dataclass
from ai_engine.environment.history.models import EnvironmentHistory

@dataclass
class EnvironmentHistoryResult:
    """Wrapper for the final updated environment history object."""
    history: EnvironmentHistory
