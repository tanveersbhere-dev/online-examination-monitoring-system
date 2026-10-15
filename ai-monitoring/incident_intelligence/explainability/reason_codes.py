"""
Reason Codes and Definitions for Explainability Engine.
Defines stable, auditable reason code constants and ReasonCode model.
"""
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, Any

class ReasonCodeEnum(str, Enum):
    PHONE_VISIBLE = "PHONE_VISIBLE"
    PHONE_NEAR_FACE = "PHONE_NEAR_FACE"
    PHONE_LONG_DURATION = "PHONE_LONG_DURATION"
    MULTIPLE_PERSON = "MULTIPLE_PERSON"
    LOOKING_AWAY = "LOOKING_AWAY"
    DOWNWARD_GAZE = "DOWNWARD_GAZE"
    IDENTITY_INSTABILITY = "IDENTITY_INSTABILITY"
    IDENTITY_LOW_INTEGRITY = "IDENTITY_LOW_INTEGRITY"
    PRESENTATION_ATTACK = "PRESENTATION_ATTACK"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    COMPOSITE_BEHAVIOR = "COMPOSITE_BEHAVIOR"
    RECOVERY_COMPLETED = "RECOVERY_COMPLETED"
    ESCALATION_OCCURRED = "ESCALATION_OCCURRED"
    UNAUTHORIZED_MATERIAL = "UNAUTHORIZED_MATERIAL"
    CAMERA_OCCLUSION = "CAMERA_OCCLUSION"
    FACE_MISSING = "FACE_MISSING"

@dataclass(frozen=True)
class ReasonCode:
    """Immutable reason code metadata container."""
    code: str
    category: str
    description: str
    severity_weight: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

REASON_CODE_REGISTRY: Dict[str, ReasonCode] = {
    ReasonCodeEnum.PHONE_VISIBLE.value: ReasonCode(
        code=ReasonCodeEnum.PHONE_VISIBLE.value,
        category="Security",
        description="Cell phone detected in video frame",
        severity_weight=0.85
    ),
    ReasonCodeEnum.PHONE_NEAR_FACE.value: ReasonCode(
        code=ReasonCodeEnum.PHONE_NEAR_FACE.value,
        category="Security",
        description="Cell phone held near face or ear region",
        severity_weight=0.90
    ),
    ReasonCodeEnum.PHONE_LONG_DURATION.value: ReasonCode(
        code=ReasonCodeEnum.PHONE_LONG_DURATION.value,
        category="Security",
        description="Cell phone usage detected for sustained duration (>5.0s)",
        severity_weight=0.95
    ),
    ReasonCodeEnum.MULTIPLE_PERSON.value: ReasonCode(
        code=ReasonCodeEnum.MULTIPLE_PERSON.value,
        category="Security",
        description="Multiple human faces detected in candidate camera view",
        severity_weight=0.85
    ),
    ReasonCodeEnum.LOOKING_AWAY.value: ReasonCode(
        code=ReasonCodeEnum.LOOKING_AWAY.value,
        category="Attention",
        description="Candidate gaze or head pose turned away from primary monitor",
        severity_weight=0.60
    ),
    ReasonCodeEnum.DOWNWARD_GAZE.value: ReasonCode(
        code=ReasonCodeEnum.DOWNWARD_GAZE.value,
        category="Attention",
        description="Candidate pitch angle directed downward off-screen",
        severity_weight=0.65
    ),
    ReasonCodeEnum.IDENTITY_INSTABILITY.value: ReasonCode(
        code=ReasonCodeEnum.IDENTITY_INSTABILITY.value,
        category="Identity",
        description="Candidate face embedding confidence fluctuates below stability threshold",
        severity_weight=0.75
    ),
    ReasonCodeEnum.IDENTITY_LOW_INTEGRITY.value: ReasonCode(
        code=ReasonCodeEnum.IDENTITY_LOW_INTEGRITY.value,
        category="Identity",
        description="Composite identity integrity score fell below baseline threshold",
        severity_weight=0.80
    ),
    ReasonCodeEnum.PRESENTATION_ATTACK.value: ReasonCode(
        code=ReasonCodeEnum.PRESENTATION_ATTACK.value,
        category="Identity",
        description="Non-live presentation spoof attempt detected (printed photo or screen replay)",
        severity_weight=1.00
    ),
    ReasonCodeEnum.IDENTITY_MISMATCH.value: ReasonCode(
        code=ReasonCodeEnum.IDENTITY_MISMATCH.value,
        category="Identity",
        description="Face embedding does not match candidate reference baseline",
        severity_weight=1.00
    ),
    ReasonCodeEnum.COMPOSITE_BEHAVIOR.value: ReasonCode(
        code=ReasonCodeEnum.COMPOSITE_BEHAVIOR.value,
        category="Security",
        description="Multiple concurrent behavioral anomalies detected in single episode",
        severity_weight=0.90
    ),
    ReasonCodeEnum.RECOVERY_COMPLETED.value: ReasonCode(
        code=ReasonCodeEnum.RECOVERY_COMPLETED.value,
        category="System",
        description="Behavior anomaly sustained recovery period and resolved cleanly",
        severity_weight=0.00
    ),
    ReasonCodeEnum.ESCALATION_OCCURRED.value: ReasonCode(
        code=ReasonCodeEnum.ESCALATION_OCCURRED.value,
        category="System",
        description="Incident severity escalated due to persistent anomaly duration",
        severity_weight=0.75
    ),
    ReasonCodeEnum.UNAUTHORIZED_MATERIAL.value: ReasonCode(
        code=ReasonCodeEnum.UNAUTHORIZED_MATERIAL.value,
        category="Security",
        description="Unauthorized physical material (book, notebook, loose paper) detected",
        severity_weight=0.70
    ),
    ReasonCodeEnum.CAMERA_OCCLUSION.value: ReasonCode(
        code=ReasonCodeEnum.CAMERA_OCCLUSION.value,
        category="Environment",
        description="Camera lens occluded or covered",
        severity_weight=0.85
    ),
    ReasonCodeEnum.FACE_MISSING.value: ReasonCode(
        code=ReasonCodeEnum.FACE_MISSING.value,
        category="Attention",
        description="Candidate face absent from camera field of view",
        severity_weight=0.70
    )
}
