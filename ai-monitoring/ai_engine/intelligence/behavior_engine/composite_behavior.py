"""
Composite Behavior Definitions and Evaluators for Behavioral Intelligence Engine.
"""
import time
from typing import List, Dict, Any, Optional
from ai_engine.intelligence.behavior_engine.behavior_event import (
    BehaviorMemoryEntry, CompositeBehaviorInstance
)
from ai_engine.intelligence.behavior_engine.sequence_detector import SequenceDetector
from ai_engine.intelligence.behavior_engine.temporal_analyzer import TemporalAnalyzer

def format_composite_incident_title(
    violation_type: str,
    contributing_rules: Optional[List[str]] = None,
    objects: Optional[List[Any]] = None
) -> str:
    """
    Generates a clear, descriptive incident title by combining primary behavior with supporting signals.
    Replaces generic 'Composite Behavior' labels with explicit human-readable titles like:
    - Phone + Looking Down
    - Book + Looking Away
    - Identity Mismatch + Phone
    - Multiple Person + Conversation
    - Phone + Earpods
    - Gaze + Phone
    - Gaze + Book
    """
    contributing = set(contributing_rules or [])
    obj_types = set()
    if objects:
        for obj in objects:
            t = getattr(obj, "object_type", None) or (obj.get("type") if isinstance(obj, dict) else str(obj))
            obj_types.add(str(t).upper())

    # Primary Physical Object & Security Signals
    # Safe token-aware matching so EARPHONE is never confused with PHONE
    has_phone = (
        "UNAUTH_PHONE" in contributing
        or "CELL_PHONE" in contributing
        or "CELL_PHONE" in obj_types
        or "PHONE" in obj_types
        or ("PHONE" in violation_type and "EARPHONE" not in violation_type and "HEADPHONE" not in violation_type)
    )
    has_laptop = (
        "UNAUTH_LAPTOP" in contributing
        or "LAPTOP" in contributing
        or "LAPTOP" in obj_types
        or "LAPTOP" in violation_type
    )
    has_register = "UNAUTH_REGISTER" in contributing or "REGISTER" in obj_types or "REGISTER" in violation_type
    has_book = (
        "UNAUTH_BOOK" in contributing
        or "ENV_BOOK_DETECTED" in contributing
        or "UNAUTH_NOTEBOOK" in contributing
        or "UNAUTH_PAPER" in contributing
        or has_register
        or "BOOK" in obj_types
        or "NOTEBOOK" in obj_types
        or "PAPER" in obj_types
        or "PAGE" in obj_types
        or "BOOK" in violation_type
        or "NOTES" in violation_type
    )
    has_id_mismatch = False  # Identity mismatch violation removed from project
    has_multi = "COMM_MULTIPLE_PERSONS" in contributing or "MULTIPLE" in violation_type or "MULTIPLE_FACES" in contributing
    has_neckband = "COMM_NECKBAND" in contributing or "NECKBAND" in obj_types or "NECKBAND" in violation_type
    has_earbuds = "COMM_EARBUDS" in contributing or "EARBUDS" in obj_types or "EARBUDS" in violation_type
    has_earphones = (
        "COMM_EARPHONES" in contributing
        or "COMM_HEADPHONES" in contributing
        or "EARPHONE_DEVICE" in contributing
        or "EARPHONES" in obj_types
        or "EARPHONE" in obj_types
        or "EARPHONE" in violation_type
        or "HEADPHONE" in violation_type
    )
    has_audio_device = (
        has_earbuds
        or has_neckband
        or has_earphones
        or any("EAR" in r or "HEADPHONE" in r for r in contributing)
        or any(t in ["EARBUDS", "HEADPHONES", "HEADSET", "NECKBAND", "COMM_EARPHONES"] for t in obj_types)
    )
    has_talk = "MAR" in contributing or "TALKING" in contributing or "COMMUNICATION" in violation_type

    # Supporting Gaze & Head Direction Signals
    has_gaze_down = "ATT_DOWNWARD_GAZE" in contributing or "DOWNWARD" in violation_type
    has_gaze_away = "ATT_LOOKING_AWAY" in contributing or "LOOKING_AWAY" in violation_type
    has_gaze_side = "ATT_SIDE_GAZE" in contributing or "SIDE_GAZE" in violation_type
    has_gaze_up = "ATT_UPWARD_GAZE" in contributing or "UPWARD_GAZE" in violation_type
    has_head_rot = "ATT_HEAD_ROTATION" in contributing or "HEAD_ROTATION" in violation_type

    has_off_screen = has_gaze_away or has_gaze_down or has_gaze_side or has_gaze_up or has_head_rot

    # Construct descriptive combined titles matching exact enterprise proctoring standards
    v_type_upper = str(violation_type).upper()
    is_vtype_material = any(m in v_type_upper for m in ("BOOK", "NOTEBOOK", "REGISTER", "PAPER", "PAGE", "MATERIAL"))
    is_vtype_phone = ("PHONE" in v_type_upper and "EARPHONE" not in v_type_upper and "HEADPHONE" not in v_type_upper)
    is_vtype_laptop = ("LAPTOP" in v_type_upper)
    is_vtype_audio = any(a in v_type_upper for a in ("EARPHONE", "EARBUDS", "HEADPHONE", "NECKBAND", "AUDIO"))

    # When titling a specific single-category violation, preserve its subject category
    if is_vtype_material and not is_vtype_phone:
        if has_id_mismatch:
            return "Identity Mismatch + Register/Book"
        if has_gaze_down or has_off_screen:
            return "Book + Off-Screen Attention"
        if "REGISTER" in v_type_upper or "UNAUTH_REGISTER" in contributing:
            return "Unauthorized Register / Notebook"
        return "Unauthorized Material (Book)"

    if is_vtype_laptop and not is_vtype_phone:
        if has_gaze_down or has_off_screen:
            return "Laptop + Off-Screen Attention"
        return "Unauthorized Laptop"

    if is_vtype_audio and not is_vtype_phone:
        return "Unauthorized Audio Device"

    if is_vtype_phone and not is_vtype_material:
        if has_id_mismatch:
            return "Identity Mismatch + Phone"
        if has_multi:
            return "Multiple Person + Phone"
        if has_audio_device:
            return "Phone + Unauthorized Audio Device"
        if has_gaze_down or has_off_screen:
            return "Phone + Off-Screen Attention"
        return "Unauthorized Cell Phone"

    # Multi-signal composite rules / combined incidents
    if has_id_mismatch and has_phone:
        return "Identity Mismatch + Phone"
    if has_id_mismatch and has_book:
        return "Identity Mismatch + Register/Book"
    if has_multi and (has_talk or "COMMUNICATION" in violation_type):
        return "Multiple Person + Conversation"
    if has_multi and has_phone:
        return "Multiple Person + Phone"
    if has_phone and has_book:
        return "Phone + Unauthorized Material"
    if has_phone and has_laptop:
        return "Phone + Unauthorized Laptop"
    if has_phone and has_audio_device:
        return "Phone + Unauthorized Audio Device"
    if has_audio_device:
        return "Unauthorized Audio Device"
    if has_phone and (has_gaze_down or has_off_screen):
        return "Phone + Off-Screen Attention"
    if has_laptop and (has_gaze_down or has_off_screen):
        return "Laptop + Off-Screen Attention"
    if has_register and (has_gaze_down or has_off_screen):
        return "Register + Off-Screen Attention"
    if has_book and (has_gaze_down or has_off_screen):
        return "Book + Off-Screen Attention"
    if has_phone:
        return "Phone + Off-Screen Attention" if has_off_screen else "Unauthorized Cell Phone"
    if has_laptop:
        return "Unauthorized Laptop"
    if has_register:
        return "Unauthorized Register / Notebook"
    if has_book:
        return "Book + Off-Screen Attention" if has_off_screen else "Unauthorized Material (Book)"

    # Pure Off-Screen Behavioral attention
    if has_off_screen:
        return "Off-Screen Attention"

    # Fallback readable title
    clean_title = violation_type.replace("_", " ").title().replace("Att ", "").replace("Unauth ", "").replace("Env ", "")
    return clean_title if "Composite" not in clean_title else "Multi-Signal Behavioral Flag"


class CompositeBehaviorEvaluator:
    """
    Evaluates higher-level composite behavior patterns over memory window entries.
    """

    @staticmethod
    def evaluate_phone_usage(entries: List[BehaviorMemoryEntry], current_ts: float) -> Optional[CompositeBehaviorInstance]:
        phone_entries = [e for e in entries if (("PHONE" in e.rule_name and "EARPHONE" not in e.rule_name) or e.object_type == "CELL_PHONE" or e.phone_present)]
        gaze_entries = [e for e in entries if "LOOKING_AWAY" in e.rule_name or "DOWNWARD_GAZE" in e.rule_name]

        # Active support requires a phone observation in the last 1.0s
        recent_phone = [e for e in phone_entries if current_ts - e.timestamp <= 1.0]
        if not recent_phone:
            return None

        supporting_rules = list(set([e.rule_name for e in phone_entries + gaze_entries]))
        supporting_vids = list(set([e.violation_id for e in phone_entries + gaze_entries if e.violation_id]))

        start_time = min(e.timestamp for e in phone_entries)
        duration = current_ts - start_time

        explain = [f"Cell phone detected in scene ({len(phone_entries)} occurrences)"]
        if gaze_entries:
            explain.append("Gaze deviation while phone visible")
        explain.append(f"Persistence: {duration:.1f}s")

        dynamic_title = format_composite_incident_title("PHONE_USAGE", supporting_rules)

        return CompositeBehaviorInstance(
            name="PHONE_USAGE",
            title=dynamic_title,
            confidence=0.0, # Computed by ConfidenceEngine
            supporting_events=supporting_rules,
            supporting_violations=supporting_vids,
            start_time=start_time,
            last_update=current_ts,
            duration_seconds=round(duration, 1),
            explainability=explain
        )

    @staticmethod
    def evaluate_communication(entries: List[BehaviorMemoryEntry], current_ts: float) -> Optional[CompositeBehaviorInstance]:
        talking_entries = [e for e in entries if e.talking or "MAR" in e.rule_name or "TALKING" in e.rule_name]
        multi_entries = [e for e in entries if e.multiple_faces or "MULTIPLE" in e.rule_name]

        recent_talk = [e for e in talking_entries if current_ts - e.timestamp <= 1.0]
        if not recent_talk:
            return None

        supporting_rules = list(set([e.rule_name for e in talking_entries + multi_entries]))
        supporting_vids = list(set([e.violation_id for e in talking_entries + multi_entries if e.violation_id]))

        start_time = min(e.timestamp for e in talking_entries)
        duration = current_ts - start_time

        explain = [f"Mouth movement / speech detected ({len(talking_entries)} occurrences)"]
        if multi_entries: explain.append("Multiple persons detected in scene during speech")
        explain.append(f"Duration: {duration:.1f}s")

        dynamic_title = format_composite_incident_title("COMMUNICATION", supporting_rules)

        return CompositeBehaviorInstance(
            name="COMMUNICATION",
            title=dynamic_title,
            confidence=0.0,
            supporting_events=supporting_rules,
            supporting_violations=supporting_vids,
            start_time=start_time,
            last_update=current_ts,
            duration_seconds=round(duration, 1),
            explainability=explain
        )

    @staticmethod
    def evaluate_outside_assistance(entries: List[BehaviorMemoryEntry], current_ts: float) -> Optional[CompositeBehaviorInstance]:
        multi_entries = [e for e in entries if e.multiple_faces or "MULTIPLE" in e.rule_name]
        gaze_entries = [e for e in entries if "LOOKING_AWAY" in e.rule_name or "SIDE_GAZE" in e.rule_name]

        recent_multi = [e for e in multi_entries if current_ts - e.timestamp <= 1.0]
        recent_gaze = [e for e in gaze_entries if current_ts - e.timestamp <= 1.0]
        if not recent_multi or not recent_gaze:
            return None

        supporting_rules = list(set([e.rule_name for e in multi_entries + gaze_entries]))
        supporting_vids = list(set([e.violation_id for e in multi_entries + gaze_entries if e.violation_id]))

        start_time = min(e.timestamp for e in multi_entries)
        duration = current_ts - start_time

        explain = [f"Second person present in scene ({len(multi_entries)} frames)", "Candidate gaze diverted toward second individual"]

        return CompositeBehaviorInstance(
            name="OUTSIDE_ASSISTANCE",
            title="Outside Assistance",
            confidence=0.0,
            supporting_events=supporting_rules,
            supporting_violations=supporting_vids,
            start_time=start_time,
            last_update=current_ts,
            duration_seconds=round(duration, 1),
            explainability=explain
        )

    @staticmethod
    def evaluate_camera_evasion(entries: List[BehaviorMemoryEntry], current_ts: float) -> Optional[CompositeBehaviorInstance]:
        absent_entries = [e for e in entries if "ABSENT" in e.rule_name or "MISSING" in e.rule_name]

        recent_absent = [e for e in absent_entries if current_ts - e.timestamp <= 1.0]
        if not recent_absent or len(absent_entries) < 2:
            return None

        supporting_rules = list(set([e.rule_name for e in absent_entries]))
        supporting_vids = list(set([e.violation_id for e in absent_entries if e.violation_id]))

        start_time = min(e.timestamp for e in absent_entries)
        duration = current_ts - start_time

        explain = [f"Repeated candidate camera absence ({len(absent_entries)} events)", f"Evasion window: {duration:.1f}s"]

        return CompositeBehaviorInstance(
            name="CAMERA_EVASION",
            title="Camera Evasion",
            confidence=0.0,
            supporting_events=supporting_rules,
            supporting_violations=supporting_vids,
            start_time=start_time,
            last_update=current_ts,
            duration_seconds=round(duration, 1),
            explainability=explain
        )

    @staticmethod
    def evaluate_looking_for_notes(entries: List[BehaviorMemoryEntry], current_ts: float) -> Optional[CompositeBehaviorInstance]:
        material_entries = [
            e for e in entries
            if e.object_type in ["BOOK", "NOTEBOOK", "PAPER", "REGISTER", "PAGE"]
            or "BOOK" in e.rule_name
            or "NOTEBOOK" in e.rule_name
            or "REGISTER" in e.rule_name
            or "PAPER" in e.rule_name
        ]
        gaze_entries = [e for e in entries if "DOWNWARD_GAZE" in e.rule_name or "LOOKING_AWAY" in e.rule_name]

        recent_mat = [e for e in material_entries if current_ts - e.timestamp <= 1.0]
        recent_gaze = [e for e in gaze_entries if current_ts - e.timestamp <= 1.0]

        # Multi-stage composite behavior strictly requires BOTH physical material present AND active gaze deviation
        if not recent_mat or not recent_gaze:
            return None

        supporting_rules = list(set([e.rule_name for e in material_entries + gaze_entries]))
        supporting_vids = list(set([e.violation_id for e in material_entries + gaze_entries if e.violation_id]))

        start_time = min(e.timestamp for e in material_entries)
        duration = current_ts - start_time

        explain = [f"Unauthorized notes/book material detected ({len(material_entries)} frames)"]
        if gaze_entries: explain.append("Downward gaze directed towards physical material")
        explain.append(f"Duration: {duration:.1f}s")

        dynamic_title = format_composite_incident_title("LOOKING_FOR_NOTES", supporting_rules)

        return CompositeBehaviorInstance(
            name="LOOKING_FOR_NOTES",
            title=dynamic_title,
            confidence=0.0,
            supporting_events=supporting_rules,
            supporting_violations=supporting_vids,
            start_time=start_time,
            last_update=current_ts,
            duration_seconds=round(duration, 1),
            explainability=explain
        )

    @staticmethod
    def evaluate_screen_reference(entries: List[BehaviorMemoryEntry], current_ts: float) -> Optional[CompositeBehaviorInstance]:
        screen_entries = [e for e in entries if e.object_type in ["LAPTOP", "TABLET", "MONITOR"]]
        gaze_entries = [e for e in entries if "LOOKING_AWAY" in e.rule_name]

        recent_screen = [e for e in screen_entries if current_ts - e.timestamp <= 1.0]
        recent_gaze = [e for e in gaze_entries if current_ts - e.timestamp <= 1.0]
        if not recent_screen or not recent_gaze:
            return None

        supporting_rules = list(set([e.rule_name for e in screen_entries + gaze_entries]))
        supporting_vids = list(set([e.violation_id for e in screen_entries + gaze_entries if e.violation_id]))

        start_time = min(e.timestamp for e in screen_entries)
        duration = current_ts - start_time

        explain = [f"Secondary screen/laptop present ({len(screen_entries)} occurrences)", "Gaze diverted to secondary monitor"]

        return CompositeBehaviorInstance(
            name="SCREEN_REFERENCE",
            title="Secondary Screen Reference",
            confidence=0.0,
            supporting_events=supporting_rules,
            supporting_violations=supporting_vids,
            start_time=start_time,
            last_update=current_ts,
            duration_seconds=round(duration, 1),
            explainability=explain
        )
