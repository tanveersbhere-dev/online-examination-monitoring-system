import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Union, Dict, Any

from ai_engine.core.exceptions import ConfigurationError

@dataclass
class CameraConfig:
    camera_id: Union[int, str] = 0
    width: int = 640
    height: int = 480
    fps: int = 30
    buffer_size: int = 10
    reconnect_interval: float = 2.0
    max_reconnect_attempts: int = 5

@dataclass
class LoggingConfig:
    log_dir: str = "logs"
    max_bytes: int = 10485760
    backup_count: int = 5
    level: str = "INFO"

@dataclass
class EventBusConfig:
    queue_size: int = 100
    async_dispatch: bool = True

@dataclass
class ExamConfig:
    active_profile: str = "normal"

@dataclass
class FaceThresholds:
    min_confidence: float = 0.5
    max_faces: int = 1
    face_absent_timeout: float = 3.0

@dataclass
class GazeThresholds:
    deviation_threshold: float = 0.25
    look_away_timeout: float = 2.0

@dataclass
class HeadPoseThresholds:
    yaw_limit: float = 30.0
    pitch_limit: float = 20.0
    roll_limit: float = 20.0

@dataclass
class MouthThresholds:
    open_threshold: float = 0.15
    talking_timeout: float = 1.5

@dataclass
class ObjectThresholds:
    confidence_threshold: float = 0.4
    disallowed_objects: List[str] = field(default_factory=list)

@dataclass
class AudioThresholds:
    voice_activity_threshold: float = 0.5
    decibel_threshold: float = -30.0

@dataclass
class RiskThresholds:
    low_threshold: float = 0.3
    medium_threshold: float = 0.6
    high_threshold: float = 0.8

@dataclass
class SystemConfig:
    camera: CameraConfig
    logging: LoggingConfig
    event_bus: EventBusConfig
    exam: ExamConfig
    face: FaceThresholds
    gaze: GazeThresholds
    head_pose: HeadPoseThresholds
    mouth: MouthThresholds
    objects: ObjectThresholds
    audio: AudioThresholds
    risk: RiskThresholds


def load_yaml(file_path: Path) -> Dict[str, Any]:
    if not file_path.exists():
        raise ConfigurationError(f"Configuration file not found: {file_path}")
    try:
        with open(file_path, "r") as f:
            data = yaml.safe_load(f)
            return data or {}
    except Exception as e:
        raise ConfigurationError(f"Failed to parse YAML file {file_path}: {e}") from e


def deep_merge(target: Dict[str, Any], source: Dict[str, Any]) -> None:
    for key, value in source.items():
        if isinstance(value, dict) and key in target and isinstance(target[key], dict):
            deep_merge(target[key], value)
        else:
            target[key] = value


def load_config(config_dir: Union[Path, str, None] = None) -> SystemConfig:
    if config_dir is None:
        config_dir = Path(__file__).parent
    else:
        config_dir = Path(config_dir)

    config_path = config_dir / "config.yaml"
    thresholds_path = config_dir / "thresholds.yaml"

    base_config = load_yaml(config_path)
    thresholds_config = load_yaml(thresholds_path)

    # Combine configurations
    merged: Dict[str, Any] = {}
    deep_merge(merged, base_config)
    deep_merge(merged, thresholds_config)

    # Load active profile overrides
    active_profile = merged.get("exam", {}).get("active_profile", "normal")
    profile_path = config_dir / "profiles" / f"{active_profile}.yaml"

    if profile_path.exists():
        profile_config = load_yaml(profile_path)
        deep_merge(merged, profile_config)
    
    try:
        camera_data = merged.get("camera", {})
        logging_data = merged.get("logging", {})
        event_bus_data = merged.get("event_bus", {})
        exam_data = merged.get("exam", {})

        face_data = merged.get("face", {})
        gaze_data = merged.get("gaze", {})
        hp_data = merged.get("head_pose", {})
        mouth_data = merged.get("mouth", {})
        obj_data = merged.get("objects", {})
        audio_data = merged.get("audio", {})
        risk_data = merged.get("risk", {})

        config = SystemConfig(
            camera=CameraConfig(**camera_data),
            logging=LoggingConfig(**logging_data),
            event_bus=EventBusConfig(**event_bus_data),
            exam=ExamConfig(**exam_data),
            face=FaceThresholds(**face_data),
            gaze=GazeThresholds(**gaze_data),
            head_pose=HeadPoseThresholds(**hp_data),
            mouth=MouthThresholds(**mouth_data),
            objects=ObjectThresholds(**obj_data),
            audio=AudioThresholds(**audio_data),
            risk=RiskThresholds(**risk_data),
        )
        validate_config(config)
        return config
    except TypeError as e:
        raise ConfigurationError(f"Invalid configuration fields: {e}") from e

def validate_config(config: SystemConfig) -> None:
    """Validates parameters in the loaded configuration."""
    if not isinstance(config.camera.width, int) or config.camera.width <= 0:
        raise ConfigurationError(f"Invalid camera width: {config.camera.width}. Must be a positive integer.")
    if not isinstance(config.camera.height, int) or config.camera.height <= 0:
        raise ConfigurationError(f"Invalid camera height: {config.camera.height}. Must be a positive integer.")
    if not isinstance(config.camera.fps, (int, float)) or config.camera.fps <= 0:
        raise ConfigurationError(f"Invalid camera fps: {config.camera.fps}. Must be a positive number.")
    if not isinstance(config.camera.buffer_size, int) or config.camera.buffer_size <= 0:
        raise ConfigurationError(f"Invalid camera buffer size: {config.camera.buffer_size}. Must be a positive integer.")
    if not isinstance(config.event_bus.queue_size, int) or config.event_bus.queue_size <= 0:
        raise ConfigurationError(f"Invalid event bus queue size: {config.event_bus.queue_size}. Must be a positive integer.")
    
    valid_levels = {"DEBUG", "INFO", "WARNING", "WARN", "ERROR", "CRITICAL", "FATAL"}
    if not isinstance(config.logging.level, str) or config.logging.level.upper() not in valid_levels:
        raise ConfigurationError(f"Invalid log level: {config.logging.level}. Must be one of {valid_levels}.")
