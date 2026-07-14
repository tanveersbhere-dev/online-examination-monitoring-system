import copy
import threading
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Union, TYPE_CHECKING
from contextlib import contextmanager

from ai_engine.core.enums import ExamStatus, DetectedObjectType

if TYPE_CHECKING:
    from ai_engine.camera.frame import Frame

@dataclass
class SessionInfo:
    exam_id: str = ""
    student_id: str = ""
    start_time: float = 0.0
    end_time: float = 0.0

@dataclass
class CameraState:
    is_connected: bool = False
    fps: float = 0.0
    width: int = 0
    height: int = 0
    frame_count: int = 0
    dropped_frames: int = 0
    status: str = "OFFLINE"

@dataclass
class FaceInfo:
    # Primary face (highest confidence) — preserved for backward compatibility
    face_detected: bool = False
    confidence: float = 0.0
    bbox: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)  # x, y, w, h (pixels)
    landmarks: List[Dict[str, float]] = field(default_factory=list)
    # Multi-face support
    face_count: int = 0
    all_bboxes: List[Tuple[float, float, float, float]] = field(default_factory=list)
    all_confidences: List[float] = field(default_factory=list)
    # Timing and traceability
    detection_timestamp: float = 0.0
    frame_id: Optional[int] = None
    
    # Face Presence temporal metrics
    presence_state: str = "PRESENT"  # PRESENT, MISSING
    presence_confidence: float = 0.0
    present_duration: float = 0.0
    absent_duration: float = 0.0
    longest_absence: float = 0.0
    consecutive_missing_frames: int = 0
    consecutive_present_frames: int = 0
    partial_visibility_flag: bool = False
    occlusion_flag: bool = False
    
    # Feature Processing Metadata
    processing_timestamp: float = 0.0
    processing_time_ms: float = 0.0
    
    # Face Identity Consistency metrics
    reference_embedding: Optional[List[float]] = None
    current_embedding: Optional[List[float]] = None
    similarity_score: float = 0.0
    identity_consistent: bool = True
    identity_confidence: float = 0.0
    verification_timestamp: float = 0.0
    identity_processing_time_ms: float = 0.0


@dataclass
class FaceMeshInfo:
    # Backward-compatible primary-face flat list (x, y, z) — normalised [0,1]
    mesh_points: List[Tuple[float, float, float]] = field(default_factory=list)
    # Per-face structured landmark data (index == face index)
    # Each entry is a list of 468 landmarks as (x, y, z) normalised triples
    all_face_landmarks: List[List[Tuple[float, float, float]]] = field(default_factory=list)
    # Visibility scores per face per landmark (may be empty if model does not provide)
    all_face_visibility: List[List[Optional[float]]] = field(default_factory=list)
    # Presence scores per face per landmark (may be empty if model does not provide)
    all_face_presence: List[List[Optional[float]]] = field(default_factory=list)
    # Number of faces for which landmarks were extracted
    face_count: int = 0
    # Processing metadata
    processing_timestamp: float = 0.0
    processing_time_ms: float = 0.0
    frame_id: Optional[int] = None

@dataclass
class HeadPoseInfo:
    yaw: float = 0.0
    pitch: float = 0.0
    roll: float = 0.0
    pose_class: str = "FORWARD"  # Preserved for backward compatibility
    
    # solvePnP metrics
    rotation_vector: Optional[Tuple[float, float, float]] = None
    translation_vector: Optional[Tuple[float, float, float]] = None
    camera_matrix: Optional[List[List[float]]] = None
    distortion_coefficients: Optional[List[float]] = None
    success: bool = False
    
    # Metadata
    processing_timestamp: float = 0.0
    processing_time_ms: float = 0.0
    frame_id: Optional[int] = None

@dataclass
class EyeInfo:
    gaze_left: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    gaze_right: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    combined_gaze: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    
    # 2D centers in normalized coordinates (x, y)
    left_iris_center: Optional[Tuple[float, float]] = None
    right_iris_center: Optional[Tuple[float, float]] = None
    left_eye_center: Optional[Tuple[float, float]] = None
    right_eye_center: Optional[Tuple[float, float]] = None
    
    # EAR Feature metrics
    left_ear: float = 0.0
    right_ear: float = 0.0
    average_ear: float = 0.0
    left_eye_width: float = 0.0
    left_eye_height: float = 0.0
    right_eye_width: float = 0.0
    right_eye_height: float = 0.0
    ear_confidence: float = 0.0
    
    gaze_confidence: float = 0.0
    
    # Blink Detection temporal metrics
    blink_detected: bool = False
    blink_start_timestamp: float = 0.0
    blink_end_timestamp: float = 0.0
    blink_duration: float = 0.0
    blink_frequency: float = 0.0
    consecutive_closed_frames: int = 0
    eye_state: str = "OPEN"
    
    # Backward compatibility
    blink_count: int = 0
    look_away_seconds: float = 0.0
    
    # Metadata
    processing_timestamp: float = 0.0
    processing_time_ms: float = 0.0
    frame_id: Optional[int] = None

@dataclass
class MouthInfo:
    mar: float = 0.0
    mouth_width: float = 0.0
    mouth_height: float = 0.0
    
    # 2D centers and points in normalized coordinates (x, y)
    mouth_center: Optional[Tuple[float, float]] = None
    upper_lip_points: List[Tuple[float, float]] = field(default_factory=list)
    lower_lip_points: List[Tuple[float, float]] = field(default_factory=list)
    
    confidence: float = 0.0
    
    # Backward compatibility
    aperture_ratio: float = 0.0
    is_talking: bool = False
    talking_seconds: float = 0.0
    
    # Metadata
    processing_timestamp: float = 0.0
    processing_time_ms: float = 0.0
    frame_id: Optional[int] = None

@dataclass
class BoundingBox:
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0

@dataclass
class DetectedObject:
    object_type: DetectedObjectType
    confidence: float
    bbox: BoundingBox

@dataclass
class FilteredObject:
    object_type: DetectedObjectType
    confidence: float
    bbox: BoundingBox
    detection_timestamp: float
    frame_id: Optional[int] = None

@dataclass
class FilteringStatistics:
    total_received: int = 0
    total_accepted: int = 0
    total_rejected: int = 0
    duplicates_removed: int = 0
    low_confidence_removed: int = 0
    invalid_box_removed: int = 0
    unsupported_class_removed: int = 0

@dataclass
class TrackedObject:
    tracking_id: int
    object_type: DetectedObjectType
    bbox: BoundingBox
    confidence: float
    current_state: str  # e.g., 'NEW', 'TRACKED', 'LOST', 'REMOVED'
    first_detection_timestamp: float
    last_detection_timestamp: float
    visible_duration: float
    consecutive_frames: int
    lost_frames: int
    motion_status: str
    frame_id: Optional[int] = None

@dataclass
class TrackingStatistics:
    active_tracks: int = 0
    new_tracks: int = 0
    lost_tracks: int = 0
    recovered_tracks: int = 0
    removed_tracks: int = 0

@dataclass
class DetectedObjects:
    items: List[DetectedObject] = field(default_factory=list)

@dataclass
class AudioInfo:
    is_speaking: bool = False
    db_level: float = -100.0
    noise_level: float = 0.0

@dataclass
class FeatureValues:
    metrics: Dict[str, float] = field(default_factory=dict)

@dataclass
class TemporalState:
    history: Dict[str, List[Any]] = field(default_factory=dict)

@dataclass
class BehaviorHistory:
    """Stores temporal summaries of behavioral features across multiple rolling windows."""
    summaries: Dict[str, Dict[int, Any]] = field(default_factory=dict)
    # summaries[feature_name][window_size_seconds] = BehaviorSummary
    last_updated: float = 0.0

@dataclass
class ViolationInfo:
    violation_id: str
    name: str
    timestamp: float
    severity: str
    description: str

@dataclass
class Violations:
    list_violations: List[ViolationInfo] = field(default_factory=list)

@dataclass
class EvidenceInfo:
    evidence_id: str
    timestamp: float
    file_path: str
    description: str
    violation_id: str

@dataclass
class Evidence:
    list_evidence: List[EvidenceInfo] = field(default_factory=list)

@dataclass
class RiskScore:
    current_score: float = 0.0
    history: List[Tuple[float, float]] = field(default_factory=list)

@dataclass
class SystemState:
    status: ExamStatus = ExamStatus.NOT_STARTED
    active_profile: str = "normal"
    errors: List[str] = field(default_factory=list)

@dataclass
class ObjectInfo:
    current_detections: List[DetectedObject] = field(default_factory=list)
    filtered_detections: List[FilteredObject] = field(default_factory=list)
    tracked_objects: List[TrackedObject] = field(default_factory=list)
    filtering_statistics: FilteringStatistics = field(default_factory=FilteringStatistics)
    tracking_statistics: TrackingStatistics = field(default_factory=TrackingStatistics)
    total_object_count: int = 0
    timestamp: float = 0.0
    frame_id: Optional[int] = None
    processing_time_ms: float = 0.0
    filtering_processing_time_ms: float = 0.0
    tracking_processing_time_ms: float = 0.0

@dataclass
class DetectionState:
    pass

@dataclass
class FeatureState:
    metrics: Dict[str, float] = field(default_factory=dict)

@dataclass
class ViolationState:
    list_violations: List[ViolationInfo] = field(default_factory=list)

@dataclass
class EvidenceState:
    list_evidence: List[EvidenceInfo] = field(default_factory=list)

@dataclass
class Metadata:
    data: Dict[str, Any] = field(default_factory=dict)


class ExamContext:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        
        # State Fields
        self._session_info = SessionInfo()
        self._camera_state = CameraState()
        self._current_frame: Optional["Frame"] = None
        self._face_info = FaceInfo()
        self._face_mesh_info = FaceMeshInfo()
        self._head_pose_info = HeadPoseInfo()
        self._eye_info = EyeInfo()
        self._mouth_info = MouthInfo()
        self._detected_objects = DetectedObjects()
        self._object_info = ObjectInfo()
        self._audio_info = AudioInfo()
        self._detection_state = DetectionState()
        self._feature_values = FeatureValues()
        self._feature_state = FeatureState()
        self._temporal_state = TemporalState()
        self._behavior_history = BehaviorHistory()
        self._violations = Violations()
        self._violation_state = ViolationState()
        self._evidence = Evidence()
        self._evidence_state = EvidenceState()
        self._risk_score = RiskScore()
        self._metadata = Metadata()
        self._system_state = SystemState()

    @contextmanager
    def lock(self):
        """Context manager to lock the context for atomic operations."""
        with self._lock:
            yield

    @property
    def session_info(self) -> SessionInfo:
        with self._lock:
            return copy.deepcopy(self._session_info)

    @session_info.setter
    def session_info(self, value: SessionInfo) -> None:
        with self._lock:
            self._session_info = copy.deepcopy(value)

    @property
    def camera_state(self) -> CameraState:
        with self._lock:
            return copy.deepcopy(self._camera_state)

    @camera_state.setter
    def camera_state(self, value: CameraState) -> None:
        with self._lock:
            self._camera_state = copy.deepcopy(value)

    @property
    def current_frame(self) -> Optional["Frame"]:
        with self._lock:
            # We don't perform deepcopy on Frame because original_frame (numpy array)
            # would be expensive, but Frame is a structured dataclass.
            # We can return a shallow copy or direct reference as it's modified out-of-loop.
            return self._current_frame

    @current_frame.setter
    def current_frame(self, value: Optional["Frame"]) -> None:
        with self._lock:
            self._current_frame = value

    @property
    def face_info(self) -> FaceInfo:
        with self._lock:
            return copy.deepcopy(self._face_info)

    @face_info.setter
    def face_info(self, value: FaceInfo) -> None:
        with self._lock:
            self._face_info = copy.deepcopy(value)

    @property
    def face_mesh_info(self) -> FaceMeshInfo:
        with self._lock:
            return copy.deepcopy(self._face_mesh_info)

    @face_mesh_info.setter
    def face_mesh_info(self, value: FaceMeshInfo) -> None:
        with self._lock:
            self._face_mesh_info = copy.deepcopy(value)

    @property
    def head_pose_info(self) -> HeadPoseInfo:
        with self._lock:
            return copy.deepcopy(self._head_pose_info)

    @head_pose_info.setter
    def head_pose_info(self, value: HeadPoseInfo) -> None:
        with self._lock:
            self._head_pose_info = copy.deepcopy(value)

    @property
    def eye_info(self) -> EyeInfo:
        with self._lock:
            return copy.deepcopy(self._eye_info)

    @eye_info.setter
    def eye_info(self, value: EyeInfo) -> None:
        with self._lock:
            self._eye_info = copy.deepcopy(value)

    @property
    def mouth_info(self) -> MouthInfo:
        with self._lock:
            return copy.deepcopy(self._mouth_info)

    @mouth_info.setter
    def mouth_info(self, value: MouthInfo) -> None:
        with self._lock:
            self._mouth_info = copy.deepcopy(value)

    @property
    def detected_objects(self) -> DetectedObjects:
        with self._lock:
            return copy.deepcopy(self._detected_objects)

    @detected_objects.setter
    def detected_objects(self, value: DetectedObjects) -> None:
        with self._lock:
            self._detected_objects = copy.deepcopy(value)

    @property
    def audio_info(self) -> AudioInfo:
        with self._lock:
            return copy.deepcopy(self._audio_info)

    @audio_info.setter
    def audio_info(self, value: AudioInfo) -> None:
        with self._lock:
            self._audio_info = copy.deepcopy(value)

    @property
    def feature_values(self) -> FeatureValues:
        with self._lock:
            return copy.deepcopy(self._feature_values)

    @feature_values.setter
    def feature_values(self, value: FeatureValues) -> None:
        with self._lock:
            self._feature_values = copy.deepcopy(value)

    @property
    def temporal_state(self) -> TemporalState:
        with self._lock:
            return copy.deepcopy(self._temporal_state)

    @temporal_state.setter
    def temporal_state(self, value: TemporalState) -> None:
        with self._lock:
            self._temporal_state = copy.deepcopy(value)

    @property
    def behavior_history(self) -> BehaviorHistory:
        with self._lock:
            return copy.deepcopy(self._behavior_history)

    @behavior_history.setter
    def behavior_history(self, value: BehaviorHistory) -> None:
        with self._lock:
            self._behavior_history = copy.deepcopy(value)

    @property
    def violations(self) -> Violations:
        with self._lock:
            return copy.deepcopy(self._violations)

    @violations.setter
    def violations(self, value: Violations) -> None:
        with self._lock:
            self._violations = copy.deepcopy(value)

    @property
    def evidence(self) -> Evidence:
        with self._lock:
            return copy.deepcopy(self._evidence)

    @evidence.setter
    def evidence(self, value: Evidence) -> None:
        with self._lock:
            self._evidence = copy.deepcopy(value)

    @property
    def risk_score(self) -> RiskScore:
        with self._lock:
            return copy.deepcopy(self._risk_score)

    @risk_score.setter
    def risk_score(self, value: RiskScore) -> None:
        with self._lock:
            self._risk_score = copy.deepcopy(value)

    @property
    def object_info(self) -> ObjectInfo:
        with self._lock:
            return copy.deepcopy(self._object_info)

    @object_info.setter
    def object_info(self, value: ObjectInfo) -> None:
        with self._lock:
            self._object_info = copy.deepcopy(value)

    @property
    def detection_state(self) -> DetectionState:
        with self._lock:
            return copy.deepcopy(self._detection_state)

    @detection_state.setter
    def detection_state(self, value: DetectionState) -> None:
        with self._lock:
            self._detection_state = copy.deepcopy(value)

    @property
    def feature_state(self) -> FeatureState:
        with self._lock:
            return copy.deepcopy(self._feature_state)

    @feature_state.setter
    def feature_state(self, value: FeatureState) -> None:
        with self._lock:
            self._feature_state = copy.deepcopy(value)

    @property
    def violation_state(self) -> ViolationState:
        with self._lock:
            return copy.deepcopy(self._violation_state)

    @violation_state.setter
    def violation_state(self, value: ViolationState) -> None:
        with self._lock:
            self._violation_state = copy.deepcopy(value)

    @property
    def evidence_state(self) -> EvidenceState:
        with self._lock:
            return copy.deepcopy(self._evidence_state)

    @evidence_state.setter
    def evidence_state(self, value: EvidenceState) -> None:
        with self._lock:
            self._evidence_state = copy.deepcopy(value)

    @property
    def metadata(self) -> Metadata:
        with self._lock:
            return copy.deepcopy(self._metadata)

    @metadata.setter
    def metadata(self, value: Union[Metadata, Dict[str, Any]]) -> None:
        with self._lock:
            if isinstance(value, dict):
                self._metadata = Metadata(data=copy.deepcopy(value))
            else:
                self._metadata = copy.deepcopy(value)

    @property
    def system_state(self) -> SystemState:
        with self._lock:
            return copy.deepcopy(self._system_state)

    @system_state.setter
    def system_state(self, value: SystemState) -> None:
        with self._lock:
            self._system_state = copy.deepcopy(value)
