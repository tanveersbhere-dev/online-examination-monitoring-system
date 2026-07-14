"""Concrete rule implementations for the Rule Engine."""
from abc import ABC, abstractmethod
from typing import Tuple

from ai_engine.intelligence.observation_fusion.models import UnifiedObservation
from ai_engine.intelligence.rule_engine.models import RuleEngineConfig

class RuleInterface(ABC):
    """Abstract base class for all rules."""
    
    @property
    @abstractmethod
    def rule_id(self) -> str:
        pass
        
    @property
    @abstractmethod
    def rule_name(self) -> str:
        pass
        
    @property
    @abstractmethod
    def category(self) -> str:
        pass

    @abstractmethod
    def evaluate(self, observation: UnifiedObservation, config: RuleEngineConfig) -> Tuple[bool, float, str]:
        """
        Evaluates the rule against the unified observation.
        Returns: (triggered, confidence, supporting_observations_string)
        """
        pass

# ============================================================================
# Attention Rules
# ============================================================================

class LookingAwayTooLongRule(RuleInterface):
    rule_id = "ATT_LOOKING_AWAY"
    rule_name = "Looking Away Too Long"
    category = "Attention"
    
    def evaluate(self, obs: UnifiedObservation, config: RuleEngineConfig) -> Tuple[bool, float, str]:
        if not obs.face or not obs.face.face_present:
            return False, 0.0, "No face present"
            
        gaze = obs.face.gaze_state
        head = obs.face.head_pose_state
        
        # Simple heuristic since we don't have historical duration natively here unless it's in behavioral_summary
        # The prompt mentioned we only get UnifiedObservation. We'll evaluate instant state,
        # or use behavioral summary if available. For now, evaluate instant severe gaze away.
        is_away = (gaze in ["LEFT", "RIGHT", "UP"]) or (head in ["LEFT", "RIGHT", "UP"])
        if is_away:
            return True, obs.face.face_confidence, f"Gaze: {gaze}, Head: {head}"
        return False, 0.0, "Attention normal"

class RepeatedDownwardGazeRule(RuleInterface):
    rule_id = "ATT_DOWNWARD_GAZE"
    rule_name = "Repeated Downward Gaze"
    category = "Attention"
    
    def evaluate(self, obs: UnifiedObservation, config: RuleEngineConfig) -> Tuple[bool, float, str]:
        if not obs.face or not obs.face.face_present:
            return False, 0.0, "No face present"
            
        is_down = (obs.face.gaze_state == "DOWN") or (obs.face.head_pose_state == "DOWN")
        if is_down:
            return True, obs.face.face_confidence, "Looking downwards detected"
        return False, 0.0, "Attention normal"


# ============================================================================
# Identity Rules
# ============================================================================

class IdentityMismatchRule(RuleInterface):
    rule_id = "ID_MISMATCH"
    rule_name = "Identity Mismatch"
    category = "Identity"
    
    def evaluate(self, obs: UnifiedObservation, config: RuleEngineConfig) -> Tuple[bool, float, str]:
        if obs.face and obs.face.face_present:
            if not obs.face.identity_consistent:
                return True, obs.face.identity_confidence, "Identity does not match registered profile"
        return False, 0.0, "Identity OK"

class FaceMissingRule(RuleInterface):
    rule_id = "ID_FACE_MISSING"
    rule_name = "Face Missing"
    category = "Identity"
    
    def evaluate(self, obs: UnifiedObservation, config: RuleEngineConfig) -> Tuple[bool, float, str]:
        # If face is specifically not present
        if obs.face and not obs.face.face_present:
            return True, 1.0, "No face detected in frame"
        return False, 0.0, "Face is present"

class MultipleFacesRule(RuleInterface):
    rule_id = "ID_MULTIPLE_FACES"
    rule_name = "Multiple Faces"
    category = "Identity"
    
    def evaluate(self, obs: UnifiedObservation, config: RuleEngineConfig) -> Tuple[bool, float, str]:
        # Fallback to env observation if face module only tracks one
        if obs.environment and obs.environment.total_persons > 1:
            return True, 1.0, f"Detected {obs.environment.total_persons} persons"
        return False, 0.0, "Single person detected"


# ============================================================================
# Unauthorized Material Rules
# ============================================================================

class MobilePhoneVisibleRule(RuleInterface):
    rule_id = "UNAUTH_PHONE"
    rule_name = "Mobile Phone Visible"
    category = "Unauthorized Material"
    
    def evaluate(self, obs: UnifiedObservation, config: RuleEngineConfig) -> Tuple[bool, float, str]:
        if obs.environment and obs.environment.phone_present:
            return True, 0.9, "Mobile phone detected"
        return False, 0.0, "No phone detected"

class BookVisibleRule(RuleInterface):
    rule_id = "UNAUTH_BOOK"
    rule_name = "Book Visible"
    category = "Unauthorized Material"
    
    def evaluate(self, obs: UnifiedObservation, config: RuleEngineConfig) -> Tuple[bool, float, str]:
        if obs.environment and obs.environment.book_present:
            return True, 0.9, "Book detected"
        return False, 0.0, "No book detected"

class NotebookVisibleRule(RuleInterface):
    rule_id = "UNAUTH_NOTEBOOK"
    rule_name = "Notebook Visible"
    category = "Unauthorized Material"
    
    def evaluate(self, obs: UnifiedObservation, config: RuleEngineConfig) -> Tuple[bool, float, str]:
        if obs.environment:
            for t in obs.environment.tracked_entities_summary:
                if t.get("type", "").upper() == "NOTEBOOK":
                    return True, t.get("conf", 0.9), "Notebook detected in tracked entities"
        return False, 0.0, "No notebook detected"

class PaperVisibleRule(RuleInterface):
    rule_id = "UNAUTH_PAPER"
    rule_name = "Paper Visible"
    category = "Unauthorized Material"
    
    def evaluate(self, obs: UnifiedObservation, config: RuleEngineConfig) -> Tuple[bool, float, str]:
        if obs.environment:
            for t in obs.environment.tracked_entities_summary:
                if t.get("type", "").upper() == "PAPER":
                    return True, t.get("conf", 0.9), "Paper detected in tracked entities"
        return False, 0.0, "No paper detected"


# ============================================================================
# Communication Rules
# ============================================================================

class EarphonesDetectedRule(RuleInterface):
    rule_id = "COMM_EARPHONES"
    rule_name = "Earphones Detected"
    category = "Communication"
    
    def evaluate(self, obs: UnifiedObservation, config: RuleEngineConfig) -> Tuple[bool, float, str]:
        if obs.environment and obs.environment.earphone_present:
            return True, 0.9, "Earphones detected"
        return False, 0.0, "No earphones detected"

class HeadphonesDetectedRule(RuleInterface):
    rule_id = "COMM_HEADPHONES"
    rule_name = "Headphones Detected"
    category = "Communication"
    
    def evaluate(self, obs: UnifiedObservation, config: RuleEngineConfig) -> Tuple[bool, float, str]:
        if obs.environment:
            for t in obs.environment.tracked_entities_summary:
                if t.get("type", "").upper() == "HEADPHONE":
                    return True, t.get("conf", 0.9), "Headphones detected in tracked entities"
        return False, 0.0, "No headphones detected"

class MultiplePersonsPresentRule(RuleInterface):
    rule_id = "COMM_MULTIPLE_PERSONS"
    rule_name = "Multiple Persons Present"
    category = "Communication"
    
    def evaluate(self, obs: UnifiedObservation, config: RuleEngineConfig) -> Tuple[bool, float, str]:
        if obs.environment and obs.environment.total_persons > 1:
            return True, 1.0, f"{obs.environment.total_persons} persons present"
        return False, 0.0, "Only 1 person present"


# ============================================================================
# Environment Rules
# ============================================================================

class CameraOccludedRule(RuleInterface):
    rule_id = "ENV_CAM_OCCLUDED"
    rule_name = "Camera Occluded"
    category = "Environment"
    
    def evaluate(self, obs: UnifiedObservation, config: RuleEngineConfig) -> Tuple[bool, float, str]:
        # Typically detected by very low face conf and 0 active objects over time, but for now
        # check if environment actively flagged it or behavioral summary.
        # Since it's not natively in Observation yet, we return False by default.
        return False, 0.0, "No occlusion detected"

class CameraCoveredRule(RuleInterface):
    rule_id = "ENV_CAM_COVERED"
    rule_name = "Camera Covered"
    category = "Environment"
    
    def evaluate(self, obs: UnifiedObservation, config: RuleEngineConfig) -> Tuple[bool, float, str]:
        # Placeholder logic for camera covered (usually total black screen check upstream)
        return False, 0.0, "Camera not covered"

# List of all available rule classes for the engine to discover
AVAILABLE_RULES = [
    LookingAwayTooLongRule,
    RepeatedDownwardGazeRule,
    IdentityMismatchRule,
    FaceMissingRule,
    MultipleFacesRule,
    MobilePhoneVisibleRule,
    BookVisibleRule,
    NotebookVisibleRule,
    PaperVisibleRule,
    EarphonesDetectedRule,
    HeadphonesDetectedRule,
    MultiplePersonsPresentRule,
    CameraOccludedRule,
    CameraCoveredRule
]
