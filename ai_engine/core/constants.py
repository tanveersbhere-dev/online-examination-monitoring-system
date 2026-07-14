from pathlib import Path

# Default Paths
DEFAULT_CONFIG_DIR = Path("ai_engine/config")
DEFAULT_LOG_DIR = Path("logs")
DEFAULT_EVIDENCE_DIR = Path("evidence")

# Queue Sizes
DEFAULT_FRAME_QUEUE_SIZE = 10
DEFAULT_EVENT_QUEUE_SIZE = 100

# Default Resolutions
DEFAULT_FRAME_WIDTH = 640
DEFAULT_FRAME_HEIGHT = 480

# Supported Object Names (YOLO / COCO standard subset + custom)
SUPPORTED_OBJECT_NAMES = [
    "person", "cell phone", "mobile phone", "book", "laptop", "keyboard", "mouse",
    "monitor", "remote", "tablet", "document", "calculator"
]

# Supported Event Names
SUPPORTED_EVENT_NAMES = [
    "face_absent",
    "multiple_faces",
    "eye_gaze_deviation",
    "talking_detected",
    "unknown_person",
    "device_tampering",
    "system_info",
    "exam_state_change"
]

# Supported Violation Names
SUPPORTED_VIOLATION_NAMES = [
    "VIOLATION_FACE_ABSENT",
    "VIOLATION_MULTIPLE_FACES",
    "VIOLATION_EYE_GAZE_DEVIATION",
    "VIOLATION_TALKING_DETECTED",
    "VIOLATION_UNAUTHORIZED_OBJECT",
    "VIOLATION_DEVICE_TAMPERING",
]

# Model Identifiers
MODEL_FACE_DETECTOR = "mediapipe_face_detector"
MODEL_FACE_MESH = "mediapipe_face_mesh"
MODEL_HEAD_POSE = "head_pose_estimator"
MODEL_EYE_GAZE = "eye_gaze_tracker"
MODEL_OBJECT_DETECTOR = "yolov8_detector"
MODEL_AUDIO_VAD = "silero_vad_detector"
