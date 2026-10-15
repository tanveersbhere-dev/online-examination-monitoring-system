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

def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _calibrated_attention_decision(obs: UnifiedObservation, config: RuleEngineConfig, mode: str) -> Tuple[str, float, str]:
    """Classify calibrated attention as ON_SCREEN, UNCERTAIN or OFF_SCREEN.

    Iris displacement is the primary signal. Head-pose deviation supports
    and reinforces meaningful iris deviation. Head pose alone cannot create
    OFF_SCREEN when eyes remain on screen. Low quality or missing iris yields
    UNCERTAIN (never OFF_SCREEN).
    """
    calibration = obs.calibration if isinstance(getattr(obs, "calibration", None), dict) else {}
    debug = {
        "state": "UNCERTAIN",
        "confidence": 0.0,
        "reason": "CALIBRATION_REQUIRED",
        "combined_score": 0.0,
        "eye_h_score": 0.0,
        "eye_v_score": 0.0,
        "head_support": 0.0,
    }

    def finish(state: str, confidence: float, reason: str, **details) -> Tuple[str, float, str]:
        debug.update({"state": state, "confidence": round(confidence, 4), "reason": reason, **details})
        if calibration is not None and "gaze_decision" not in calibration:
            calibration["gaze_decision"] = debug
        return state, confidence, reason

    # 1. Face Presence Verification
    if not obs.face or not obs.face.face_present:
        return finish("UNCERTAIN", 0.0, "FACE_NOT_PRESENT")

    # 2. Calibration Verification
    behavior = getattr(obs.face, "behavioral_summary", {}) or {}
    has_explicit_calib = bool(calibration and isinstance(calibration, dict))
    calib_status = calibration.get("status", "CALIBRATED" if (calibration.get("has_baseline") or not has_explicit_calib) else "NOT_STARTED")
    calib_stage = calibration.get("stage", "READY" if calib_status in ("CALIBRATED", "READY") else "CALIBRATING")
    if bool(getattr(config, "require_calibrated_attention", False)) and has_explicit_calib and not calibration.get("has_baseline") and calib_status not in ("CALIBRATED", "READY"):
        return finish("UNCERTAIN", 0.0, f"GAZE_{calib_stage}")

    # 2.5 Consume Authoritative CameraCenteredAttention Decision
    gaze_decision = calibration.get("gaze_decision") if isinstance(calibration, dict) else None
    if gaze_decision and isinstance(gaze_decision, dict) and "state" in gaze_decision:
        dec_state = gaze_decision.get("state")
        dec_dir = gaze_decision.get("direction", "CENTER")
        dec_conf = float(gaze_decision.get("confidence", 0.0))
        dec_reason = gaze_decision.get("reason", "")

        if mode == "DOWN":
            if (dec_dir == "DOWN" or dec_state == "DOWN") and dec_state in ("OFF_SCREEN", "DOWN"):
                return finish("OFF_SCREEN", dec_conf, dec_reason)
            elif dec_state == "UNCERTAIN" and dec_dir == "DOWN":
                return finish("UNCERTAIN", 0.0, dec_reason)
            elif dec_state in ("LEFT", "RIGHT") or dec_dir in ("LEFT", "RIGHT"):
                return finish("ON_SCREEN", 0.0, dec_reason)
        else:  # mode == "SIDE_OR_UP"
            # NOTE: Temporarily disabled UPWARD gaze violation - only horizontal/side gaze triggers
            if (dec_dir in ("LEFT", "RIGHT") or dec_state in ("LEFT", "RIGHT")) and dec_state in ("OFF_SCREEN", "LEFT", "RIGHT"):
                return finish("OFF_SCREEN", dec_conf, dec_reason)
            elif dec_state == "UNCERTAIN" and dec_dir in ("LEFT", "RIGHT"):
                return finish("UNCERTAIN", 0.0, dec_reason)
            else:
                return finish("ON_SCREEN", 0.0, dec_reason)

    # 3. Extract Calibrated Deviations
    gaze_delta = calibration.get("gaze_deviation", {}) if isinstance(calibration, dict) else {}
    pose_delta = calibration.get("head_pose_deviation", {}) if isinstance(calibration, dict) else {}
    dx = float(gaze_delta.get("delta_gaze_x", behavior.get("gaze_x", 0.0)))
    dy = float(gaze_delta.get("delta_gaze_y", behavior.get("gaze_y", 0.0)))
    yaw_delta = float(pose_delta.get("delta_yaw", behavior.get("head_yaw", 0.0)))
    pitch_delta = float(pose_delta.get("delta_pitch", behavior.get("head_pitch", 0.0)))

    tolerance = getattr(config, "attention_tolerance", None)
    min_quality = float(getattr(tolerance, "min_landmark_confidence", 0.35))
    face_quality = float(getattr(obs.face, "face_confidence", 0.0))
    gaze_quality = float(getattr(obs.face, "gaze_confidence", 0.0))
    measurement = calibration.get("gaze_measurement", {}) if isinstance(calibration, dict) else {}
    landmark_quality = min(face_quality, gaze_quality) if (face_quality > 0 and gaze_quality > 0) else max(face_quality, gaze_quality)

    # In extreme head turns (yaw >= 35° or extreme downward pitch), iris is physically occluded - evaluate before iris check
    # NOTE: Extreme upward pitch is temporarily disabled as an off-screen violation
    if abs(yaw_delta) >= 35.0 or (pitch_delta <= -28.0 and mode == "DOWN"):
        head_support = _clamp01((max(abs(yaw_delta), abs(pitch_delta)) - 18.0) / 15.0)
        confidence = max(0.60, face_quality) * (0.60 + 0.40 * head_support)
        reason_str = "CALIBRATED_HEAD_POSE_OFF_SCREEN"
        return finish("OFF_SCREEN", confidence, reason_str,
                      mode=mode, delta_head_yaw=round(yaw_delta, 2), delta_head_pitch=round(pitch_delta, 2),
                      delta_gaze_x=round(dx, 4), delta_gaze_y=round(dy, 4),
                      head_support=round(head_support, 4), eye_score=0.0, combined_score=round(head_support, 4),
                      landmark_quality=round(face_quality, 4))

    # 4. Landmark & Measurement Quality Verification
    if (face_quality < min_quality or gaze_quality < min_quality
            or not measurement.get("valid", True)
            or not behavior.get("head_pose_success", True)):
        return finish("UNCERTAIN", 0.0, "LOW_QUALITY_OR_MISSING_IRIS",
                      landmark_quality=round(landmark_quality, 4),
                      eye_quality=round(gaze_quality, 4))


    # Dynamic Screen Tolerances (influenced by baseline dispersion if available)
    dyn_tol = calibration.get("dynamic_tolerances", {})
    tol_h_left = float(dyn_tol.get("horizontal_gaze_tolerance", getattr(tolerance, "horizontal_gaze_tolerance", 0.180)))
    tol_h_right = float(dyn_tol.get("horizontal_gaze_tolerance_right", getattr(tolerance, "horizontal_gaze_tolerance_right", 0.210)))  # Right-side allowance (0.210)
    tol_up = float(dyn_tol.get("vertical_gaze_tolerance_up", 0.080))                         # Upward gaze threshold (0.080 covers upper monitor)
    tol_down = float(dyn_tol.get("vertical_gaze_tolerance_down", getattr(tolerance, "vertical_gaze_tolerance_down", 0.160)))
    head_tol_yaw_left = float(dyn_tol.get("head_yaw_support_deg", getattr(tolerance, "head_yaw_support_deg", 18.0)))
    head_tol_yaw_right = float(dyn_tol.get("head_yaw_support_deg_right", getattr(tolerance, "head_yaw_support_deg_right", 20.0)))
    head_tol_pitch = float(dyn_tol.get("head_pitch_support_deg", getattr(tolerance, "head_pitch_support_deg", 14.0)))

    head_range = 15.0  # Degrees beyond tolerance that reaches 100% head evidence

    if mode == "DOWN":
        # Downward gaze evaluation: architecturally separated from horizontal/upward logic
        # In normalized coordinates, dy > 0 is looking down (in 3D coordinates, dy < 0 is down)
        dy_down = max(dy, -dy if pitch_delta < -8.0 else 0.0)
        eye_range_down = 0.10  # Balanced downward dynamic range for reading allowance
        down_excess = max(0.0, dy_down - tol_down)
        eye_v_score = _clamp01(down_excess / eye_range_down)
        eye_h_score = 0.0
        eye_score = eye_v_score

        # Downward pitch: pitch < 0 is downward tilt
        head_tol_pitch_down = float(dyn_tol.get("head_pitch_down_support_deg", 14.0))
        pitch_down_excess = max(0.0, -pitch_delta - head_tol_pitch_down) if pitch_delta < 0 else 0.0
        head_support = _clamp01(pitch_down_excess / 10.0)

        # Multi-modal downward fusion:
        # Iris displacement is primary. Head pitch reinforces downward iris deviation.
        if eye_score >= 0.25:
            combined_score = max(eye_score * 1.10, 0.65 * eye_score + 0.35 * head_support + 0.15 * min(eye_score, head_support))
        elif eye_score >= 0.12 and head_support >= 0.12:
            combined_score = 0.60 * eye_score + 0.40 * head_support + 0.20 * min(eye_score, head_support)
        elif eye_score == 0.0:
            # Eyes on screen; head pitch alone cannot create downward violation
            combined_score = 0.0
        else:
            combined_score = 0.70 * eye_score + 0.30 * head_support
    else:
        # Side gaze calculations (LEFT / RIGHT): camera is centered above screen
        eye_range_h = 0.12    # Side gaze response curve

        # Horizontal gaze excess with asymmetric right-side expansion
        if dx >= 0.0:
            h_excess = max(0.0, dx - tol_h_right)
        else:
            h_excess = max(0.0, -dx - tol_h_left)

        eye_h_score = _clamp01(h_excess / eye_range_h)
        eye_v_score = 0.0
        eye_score = eye_h_score

        # Head yaw excess with asymmetric right-side expansion
        if yaw_delta >= 0.0:
            yaw_excess = max(0.0, yaw_delta - head_tol_yaw_right)
        else:
            yaw_excess = max(0.0, -yaw_delta - head_tol_yaw_left)

        head_yaw_support = _clamp01(yaw_excess / 14.0)
        head_support = head_yaw_support

        # Multi-modal side gaze fusion: iris is primary signal. Head yaw reinforces genuine iris deviation.
        if eye_h_score > 0.0:
            if eye_score >= 0.25:
                combined_score = max(eye_score * 1.10, 0.65 * eye_score + 0.35 * head_yaw_support + 0.20 * min(eye_score, head_yaw_support))
            elif eye_score >= 0.12 and head_yaw_support >= 0.12:
                combined_score = 0.60 * eye_score + 0.40 * head_yaw_support + 0.20 * min(eye_score, head_yaw_support)
            else:
                combined_score = 0.70 * eye_score + 0.30 * head_yaw_support
        else:
            # Eyes remain within horizontal screen region: eyes on screen
            combined_score = 0.0

    off_screen_min = float(getattr(tolerance, "min_combined_off_screen_confidence", 0.35))

    details = {
        "mode": mode,
        "delta_gaze_x": round(dx, 4),
        "delta_gaze_y": round(dy, 4),
        "delta_head_yaw": round(yaw_delta, 2),
        "delta_head_pitch": round(pitch_delta, 2),
        "eye_score": round(eye_score, 4),
        "eye_h_score": round(eye_h_score, 4),
        "eye_v_score": round(eye_v_score, 4),
        "head_support": round(head_support, 4),
        "combined_score": round(combined_score, 4),
        "landmark_quality": round(landmark_quality, 4),
        "required_threshold": round(off_screen_min, 4),
    }

    # 5. Determine State
    if combined_score >= off_screen_min or eye_score >= 0.35:
        confidence = landmark_quality * (0.60 + 0.40 * combined_score)
        if mode == "DOWN":
            reason_str = "CALIBRATED_DOWNWARD_GAZE_OFF_SCREEN"
        else:
            reason_str = "CALIBRATED_EYE_GAZE_OFF_SCREEN"
            confidence *= 0.90  # 10% more relaxed confidence for horizontal (left/right) gaze
        return finish("OFF_SCREEN", confidence, reason_str, **details)

    if eye_score <= 0.12 and combined_score <= 0.28:
        return finish("ON_SCREEN", landmark_quality, "WITHIN_CALIBRATED_SCREEN_REGION", **details)

    return finish("UNCERTAIN", 0.0, "INSUFFICIENT_COMBINED_EVIDENCE", **details)


class LookingAwayTooLongRule(RuleInterface):
    rule_id = "ATT_LOOKING_AWAY"
    rule_name = "Off-Screen Attention"
    category = "Attention"

    def evaluate(self, obs: UnifiedObservation, config: RuleEngineConfig) -> Tuple[bool, float, str]:
        state, confidence, reason = _calibrated_attention_decision(obs, config, "SIDE")
        return state == "OFF_SCREEN", confidence if state == "OFF_SCREEN" else 0.0, f"Calibrated attention: {state} ({reason})"


class RepeatedDownwardGazeRule(RuleInterface):
    rule_id = "ATT_DOWNWARD_GAZE"
    rule_name = "Off-Screen Downward Gaze"
    category = "Attention"

    def evaluate(self, obs: UnifiedObservation, config: RuleEngineConfig) -> Tuple[bool, float, str]:
        state, confidence, reason = _calibrated_attention_decision(obs, config, "DOWN")
        return state == "OFF_SCREEN", confidence if state == "OFF_SCREEN" else 0.0, f"Calibrated downward attention: {state} ({reason})"


# ============================================================================
# Identity Rules
# ============================================================================

class IdentityMismatchRule(RuleInterface):
    rule_id = "ID_MISMATCH"
    rule_name = "Identity Mismatch"
    category = "Identity"
    
    def evaluate(self, obs: UnifiedObservation, config: RuleEngineConfig) -> Tuple[bool, float, str]:
        # Identity mismatch violation completely removed from project
        return False, 0.0, "Identity Mismatch violation removed"

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
        if obs.face and (getattr(obs.face, "face_count", 0) > 1 or getattr(obs.face, "presence_state", "") == "MULTIPLE"):
            return True, 1.0, "Multiple faces detected in scene"
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
            for t in obs.environment.tracked_entities_summary:
                if t.get("type", "").upper() in ("BOOK", "NOTEBOOK", "REGISTER", "PAPER", "PAGE", "UNAUTHORIZED_MATERIAL", "MATERIAL"):
                    return True, t.get("conf", 0.6), "Unauthorized reading/writing material (book/notebook/page) detected"
            return True, 0.6, "Unauthorized reading/writing material (book/notebook/page) detected"
        return False, 0.0, "No book detected"

class EnvBookDetectedRule(RuleInterface):
    rule_id = "ENV_BOOK_DETECTED"
    rule_name = "Book Detected"
    category = "Unauthorized Material"
    
    def evaluate(self, obs: UnifiedObservation, config: RuleEngineConfig) -> Tuple[bool, float, str]:
        if obs.environment and obs.environment.book_present:
            for t in obs.environment.tracked_entities_summary:
                if t.get("type", "").upper() in ("BOOK", "NOTEBOOK", "REGISTER", "PAPER", "PAGE", "UNAUTHORIZED_MATERIAL", "MATERIAL"):
                    return True, t.get("conf", 0.6), "Unauthorized reading/writing material (book/notebook/page) detected"
            return True, 0.6, "Unauthorized reading/writing material (book/notebook/page) detected"
        return False, 0.0, "No book detected"

class NotebookVisibleRule(RuleInterface):
    rule_id = "UNAUTH_NOTEBOOK"
    rule_name = "Notebook Visible"
    category = "Unauthorized Material"
    
    def evaluate(self, obs: UnifiedObservation, config: RuleEngineConfig) -> Tuple[bool, float, str]:
        if obs.environment:
            if obs.environment.book_present:
                for t in obs.environment.tracked_entities_summary:
                    if t.get("type", "").upper() in ("NOTEBOOK", "EXERCISE_BOOK", "EXAM_NOTEBOOK", "WRITING_PAD", "BOOK", "REGISTER", "PAPER", "PAGE", "UNAUTHORIZED_MATERIAL"):
                        return True, t.get("conf", 0.9), "Notebook / unauthorized material detected in tracked entities"
                return True, 0.9, "Notebook detected"
        return False, 0.0, "No notebook detected"

class PaperVisibleRule(RuleInterface):
    rule_id = "UNAUTH_PAPER"
    rule_name = "Paper Visible"
    category = "Unauthorized Material"
    
    def evaluate(self, obs: UnifiedObservation, config: RuleEngineConfig) -> Tuple[bool, float, str]:
        if obs.environment:
            if obs.environment.book_present:
                for t in obs.environment.tracked_entities_summary:
                    if t.get("type", "").upper() in ("PAPER", "PAGE", "PRINTED_PAGE", "BOOK", "NOTEBOOK", "UNAUTHORIZED_MATERIAL"):
                        return True, t.get("conf", 0.9), "Paper / page detected in tracked entities"
                return True, 0.9, "Paper detected"
        return False, 0.0, "No paper detected"

class RegisterVisibleRule(RuleInterface):
    rule_id = "UNAUTH_REGISTER"
    rule_name = "Register Visible"
    category = "Unauthorized Material"
    
    def evaluate(self, obs: UnifiedObservation, config: RuleEngineConfig) -> Tuple[bool, float, str]:
        if obs.environment:
            if getattr(obs.environment, "register_present", False):
                return True, 0.9, "Register detected in environment"
            for t in obs.environment.tracked_entities_summary:
                if t.get("type", "").upper() in ("REGISTER", "NOTEBOOK", "BOOK", "PAPER", "PAGE", "UNAUTHORIZED_MATERIAL"):
                    return True, t.get("conf", 0.9), f"Unauthorized Material ({t.get('type')}) detected"
            if obs.environment.book_present:
                return True, 0.9, "Register / unauthorized material detected"
        return False, 0.0, "No register detected"

class LaptopVisibleRule(RuleInterface):
    rule_id = "UNAUTH_LAPTOP"
    rule_name = "Laptop Visible"
    category = "Electronic Device"
    
    def evaluate(self, obs: UnifiedObservation, config: RuleEngineConfig) -> Tuple[bool, float, str]:
        if obs.environment:
            if getattr(obs.environment, "laptop_present", False):
                for t in obs.environment.tracked_entities_summary:
                    if t.get("type", "").upper() == "LAPTOP":
                        return True, t.get("conf", 0.9), "Unauthorized laptop detected"
                return True, 0.9, "Unauthorized laptop detected"
            for t in obs.environment.tracked_entities_summary:
                if t.get("type", "").upper() == "LAPTOP":
                    return True, t.get("conf", 0.9), "Unauthorized laptop detected"
        return False, 0.0, "No laptop detected"


# ============================================================================
# Communication Rules
# ============================================================================

class EarphonesDetectedRule(RuleInterface):
    rule_id = "COMM_EARPHONES"
    rule_name = "Unauthorized Audio Device"
    category = "Communication"
    
    def evaluate(self, obs: UnifiedObservation, config: RuleEngineConfig) -> Tuple[bool, float, str]:
        if obs.environment:
            if obs.environment.earphone_present or obs.environment.earbuds_present or obs.environment.neckband_present:
                return True, 0.90, "Unauthorized audio device detected"
            for t in obs.environment.tracked_entities_summary:
                if t.get("type", "").upper() in ("COMM_EARPHONES", "EARBUDS", "EARPODS", "NECKBAND", "HEADPHONES", "HEADSET", "EARPHONE"):
                    return True, t.get("conf", 0.90), "Unauthorized audio device detected"
        return False, 0.0, "No audio device detected"

class EarbudsDetectedRule(EarphonesDetectedRule):
    rule_name = "Unauthorized Audio Device"

class NeckbandDetectedRule(EarphonesDetectedRule):
    rule_name = "Unauthorized Audio Device"

class HeadphonesDetectedRule(EarphonesDetectedRule):
    rule_name = "Unauthorized Audio Device"

class HumanVoiceDetectedRule(RuleInterface):
    rule_id = "UNAUTH_VOICE"
    rule_name = "Human Voice Detected"
    category = "Communication"

    def evaluate(self, obs: UnifiedObservation, config: RuleEngineConfig) -> Tuple[bool, float, str]:
        audio_obs = getattr(obs, "audio", None)
        if audio_obs and getattr(audio_obs, "is_speaking", False):
            db = getattr(audio_obs, "decibel_level", -50.0)
            return True, 0.90, f"Unauthorized human voice activity detected ({db:.1f} dB)"
        return False, 0.0, "No human voice detected"

class MultiplePersonsPresentRule(RuleInterface):
    rule_id = "COMM_MULTIPLE_PERSONS"
    rule_name = "Multiple Persons Present"
    category = "Communication"
    
    def evaluate(self, obs: UnifiedObservation, config: RuleEngineConfig) -> Tuple[bool, float, str]:
        if obs.face and (getattr(obs.face, "face_count", 0) > 1 or getattr(obs.face, "presence_state", "") == "MULTIPLE"):
            return True, 1.0, "Multiple persons detected from facial presence"
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
        return False, 0.0, "Camera not covered"


# ============================================================================
# Composite Contextual & Behavioral Pattern Rules
# ============================================================================

class CompositePhoneLookingAwayTalkingRule(RuleInterface):
    rule_id = "COMPOSITE_PHONE_LOOKING_AWAY_TALKING"
    rule_name = "Composite Phone, Looking Away & Talking"
    category = "Composite Malpractice"
    
    def evaluate(self, obs: UnifiedObservation, config: RuleEngineConfig) -> Tuple[bool, float, str]:
        phone = bool(obs.environment and obs.environment.phone_present)
        # Raw head orientation must not manufacture a phone composite when the
        # eyes remain on the calibrated screen region.
        side_state, _, _ = _calibrated_attention_decision(obs, config, "SIDE_OR_UP")
        down_state, _, _ = _calibrated_attention_decision(obs, config, "DOWN")
        is_away = side_state == "OFF_SCREEN" or down_state == "OFF_SCREEN"        
        # Talking / speech check
        is_talking = False
        if hasattr(obs, "mouth") and obs.mouth:
            is_talking = getattr(obs.mouth, "is_talking", False)
            
        if phone and is_away and is_talking:
            return True, 0.98, "CRITICAL: Mobile Phone visible + Candidate Looking Away + Talking co-occurrence detected."
        elif phone and is_away:
            return True, 0.90, "HIGH: Mobile Phone visible + Candidate Looking Away co-occurrence detected."
        # Phone by itself is handled by UNAUTH_PHONE. This composite rule is
        # intentionally reserved for multi-signal phone-plus-attention behavior.
        return False, 0.0, "No composite phone-and-attention violation detected"


class CompositeFaceMissingUnknownRule(RuleInterface):
    rule_id = "COMPOSITE_FACE_MISSING_UNKNOWN"
    rule_name = "Composite Face Missing or Identity Mismatch"
    category = "Identity"
    
    def evaluate(self, obs: UnifiedObservation, config: RuleEngineConfig) -> Tuple[bool, float, str]:
        face_absent = bool(obs.face and not obs.face.face_present)
        mismatch = bool(obs.face and obs.face.face_present and not obs.face.identity_consistent)
        
        # A face cannot be absent and simultaneously provide a current-frame
        # identity mismatch. The concrete ID_FACE_MISSING and ID_MISMATCH rules
        # own those independent lifecycles; this legacy pseudo-composite must
        # not manufacture a duplicate incident for either one.
        return False, 0.0, "Composite identity condition not applicable"


class RepeatedBehaviorPatternRule(RuleInterface):
    rule_id = "BEHAVIOR_REPEATED_PATTERN"
    rule_name = "Repeated Behavioral Anomaly Pattern"
    category = "Behavioral Pattern"
    
    def evaluate(self, obs: UnifiedObservation, config: RuleEngineConfig) -> Tuple[bool, float, str]:
        summary = obs.face.behavioral_summary if (obs.face and hasattr(obs.face, "behavioral_summary")) else None
        if summary:
            looking_away_duration = summary.get("looking_away_total_seconds", 0.0)
            phone_count = summary.get("phone_detections_count", 0)
            
            if phone_count >= 2:
                return True, 0.95, f"Repeated Phone Usage Pattern: {phone_count} occurrences detected."
            if looking_away_duration >= 15.0:
                return True, 0.85, f"Repeated Looking Away Pattern: {looking_away_duration:.1f}s total duration."
                
        return False, 0.0, "No repeated behavioral anomaly pattern detected"


# ============================================================================
# Phase 4.5 Identity Protection & Anti-Spoofing Rules
# ============================================================================

class LowIdentityIntegrityRule(RuleInterface):
    rule_id = "IDENTITY_LOW_INTEGRITY"
    rule_name = "Low Identity Integrity"
    category = "Identity Protection"
    
    def evaluate(self, obs: UnifiedObservation, config: RuleEngineConfig) -> Tuple[bool, float, str]:
        # Identity integrity violation completely removed from project
        return False, 0.0, "Identity Integrity violation removed"

class RepeatedIdentityMismatchRule(RuleInterface):
    rule_id = "IDENTITY_REPEATED_MISMATCH"
    rule_name = "Repeated Identity Mismatch"
    category = "Identity Protection"
    
    def evaluate(self, obs: UnifiedObservation, config: RuleEngineConfig) -> Tuple[bool, float, str]:
        # Repeated Identity Mismatch violation completely removed from project
        return False, 0.0, "Identity Mismatch violation removed"

class ConfirmedPresentationAttackRule(RuleInterface):
    rule_id = "CONFIRMED_PRESENTATION_ATTACK"
    rule_name = "Confirmed Presentation Attack"
    category = "Identity Protection"
    
    def evaluate(self, obs: UnifiedObservation, config: RuleEngineConfig) -> Tuple[bool, float, str]:
        id_obs = getattr(obs, "identity_protection", None)
        if id_obs:
            liveness_state = getattr(id_obs, "liveness_state", "LIVE")
            spoof_conf = getattr(id_obs, "spoof_confidence", 0.0)
            refl_score = getattr(id_obs, "reflection_score", 0.0)

            # Only fire when the liveness engine explicitly classifies SPOOF_CONFIRMED
            # (liveness_score < 0.25), OR when both spoof confidence AND reflection
            # evidence are simultaneously very high.  Reflection alone is unreliable
            # because JPEG webcam compression produces high-frequency spectral energy
            # that mimics screen MoirÃƒÂ© patterns.
            temporal_score = getattr(id_obs, "temporal_consistency", 1.0)
            liveness_score = getattr(id_obs, "liveness_score", 1.0)
            mesh_score = getattr(id_obs, "mesh_confidence", 1.0)
            # Presentation attack is an exceptional, high-impact verdict. It
            # requires persistent very-low liveness plus independent evidence
            # of a flat presentation surface and screen/replay artifacts. A
            # webcam angle, glare, or one weak liveness model score is never
            # enough to keep a real candidate flagged for an entire session.
            confirmed_spoof = (
                liveness_state == "SPOOF_CONFIRMED"
                and liveness_score <= 0.12
                and spoof_conf >= 0.88
                and temporal_score <= 0.20
                and mesh_score <= 0.25
                and refl_score >= 0.85
            )

            if confirmed_spoof:
                reason = getattr(id_obs, "reason", "Presentation Attack Detected")
                return True, spoof_conf, f"CRITICAL: Presentation Attack Confirmed ({reason})"
        return False, 0.0, "No presentation attack detected"


class IdentityInstabilityRule(RuleInterface):
    rule_id = "IDENTITY_INSTABILITY"
    rule_name = "Identity Instability"
    category = "Identity Protection"
    
    def evaluate(self, obs: UnifiedObservation, config: RuleEngineConfig) -> Tuple[bool, float, str]:
        # Identity instability violation completely removed from project
        return False, 0.0, "Identity Instability violation removed"

class InsufficientIdentityEvidenceRule(RuleInterface):
    rule_id = "INSUFFICIENT_IDENTITY_EVIDENCE"
    rule_name = "Insufficient Identity Evidence"
    category = "Identity Protection"
    
    def evaluate(self, obs: UnifiedObservation, config: RuleEngineConfig) -> Tuple[bool, float, str]:
        id_obs = getattr(obs, "identity_protection", None)
        if id_obs:
            assessment = getattr(id_obs, "assessment", None)
            conf_level = getattr(assessment, "confidence_level", None) if assessment else None
            reason = getattr(assessment, "decision_reason", None) if assessment else None
            if conf_level == "UNKNOWN" or reason == "INSUFFICIENT_EVIDENCE":
                return True, 0.50, "Insufficient Identity Evidence available"
        return False, 0.0, "Identity evidence sufficient"


# List of all available rule classes for the engine to discover
AVAILABLE_RULES = [
    LookingAwayTooLongRule,
    RepeatedDownwardGazeRule,
    IdentityMismatchRule,
    FaceMissingRule,
    MultipleFacesRule,
    MobilePhoneVisibleRule,
    BookVisibleRule,
    EnvBookDetectedRule,
    NotebookVisibleRule,
    RegisterVisibleRule,
    PaperVisibleRule,
    LaptopVisibleRule,
    EarphonesDetectedRule,
    EarbudsDetectedRule,
    NeckbandDetectedRule,
    HeadphonesDetectedRule,
    HumanVoiceDetectedRule,
    MultiplePersonsPresentRule,
    CameraOccludedRule,
    CameraCoveredRule,
    CompositePhoneLookingAwayTalkingRule,
    CompositeFaceMissingUnknownRule,
    RepeatedBehaviorPatternRule,
    LowIdentityIntegrityRule,
    RepeatedIdentityMismatchRule,
    ConfirmedPresentationAttackRule,
    IdentityInstabilityRule,
    InsufficientIdentityEvidenceRule
]
