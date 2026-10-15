"""
In-Memory Session Profile Container for the Adaptive Calibration Engine.
"""
from typing import Optional, Dict, Any
from ai_engine.calibration.baseline_profile import CandidateBaseline
from ai_engine.calibration.calibration_manager import CalibrationManager

class SessionProfile:
    """
    In-memory storage for active calibration profile within a monitoring session.
    """
    def __init__(self, session_id: str = "playground") -> None:
        self.session_id: str = session_id
        self.manager: CalibrationManager = CalibrationManager()

    @property
    def baseline(self) -> Optional[CandidateBaseline]:
        return self.manager.baseline

    @property
    def status(self) -> str:
        return self.manager.status
