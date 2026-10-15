# AI Engine — Features Package
from ai_engine.features.eye_gaze import (
    EyeGazeExtractorInterface,
    MediaPipeEyeGazeExtractor,
    EyeCenter,
    IrisCenter,
    EyeGaze,
    EyeGazeResult,
    EyeGazeConfig,
    EyeGazeError,
    EyeTrackingError,
    InvalidIrisLandmarksError,
    EyeGazeStateError
)
from ai_engine.features.mouth_aspect_ratio import (
    MouthAspectRatioProcessor,
    MediaPipeMARProcessor,
    MouthGeometry,
    MARResult,
    MARConfig,
    MARProcessorError,
    InvalidMouthLandmarksError,
    MARProcessorStateError
)
from ai_engine.features.eye_aspect_ratio import (
    EARProcessorError,
    InvalidEyeLandmarksError,
    EARConfig,
    EARResult,
    EyeGeometry,
    EyeAspectRatio,
    EyeAspectRatioProcessor,
    MediaPipeEARProcessor
)
from ai_engine.features.blink_detection import (
    BlinkDetectionError,
    InvalidEARDataError,
    TemporalProcessingError,
    BlinkDetectionConfig,
    BlinkDetectionResult,
    BlinkState,
    BlinkStatistics,
    BlinkDetectionProcessor,
    TemporalBlinkProcessor
)
from ai_engine.features.face_identity import (
    FaceIdentityError,
    EmbeddingGenerationError,
    IdentityVerificationError,
    FaceIdentityConfig,
    FaceIdentityResult,
    FaceEmbedding,
    IdentityVerification,
    FaceIdentityProcessor,
    EmbeddingIdentityProcessor
)
from ai_engine.features.face_presence import (
    FacePresenceError,
    InvalidFaceStateError,
    PresenceMonitoringError,
    FacePresenceConfig,
    FacePresenceResult,
    PresenceState,
    PresenceStatistics,
    FacePresenceProcessor,
    TemporalFacePresenceProcessor
)

__all__ = [
    # Eye Gaze (Stage 4)
    "EyeGazeExtractorInterface",
    "MediaPipeEyeGazeExtractor",
    "EyeCenter",
    "IrisCenter",
    "EyeGaze",
    "EyeGazeResult",
    "EyeGazeConfig",
    "EyeGazeError",
    "EyeTrackingError",
    "InvalidIrisLandmarksError",
    "EyeGazeStateError",
    
    # Mouth Aspect Ratio (Stage 5)
    "MouthAspectRatioProcessor",
    "MediaPipeMARProcessor",
    "MouthGeometry",
    "MARResult",
    "MARConfig",
    "MARProcessorError",
    "InvalidMouthLandmarksError",
    "MARProcessorStateError",
    
    # Eye Aspect Ratio
    "EARProcessorError",
    "InvalidEyeLandmarksError",
    "EARConfig",
    "EARResult",
    "EyeGeometry",
    "EyeAspectRatio",
    "EyeAspectRatioProcessor",
    "MediaPipeEARProcessor",

    # Blink Detection
    "BlinkDetectionError",
    "InvalidEARDataError",
    "TemporalProcessingError",
    "BlinkDetectionConfig",
    "BlinkDetectionResult",
    "BlinkState",
    "BlinkStatistics",
    "BlinkDetectionProcessor",
    "TemporalBlinkProcessor",

    # Face Identity
    "FaceIdentityError",
    "EmbeddingGenerationError",
    "IdentityVerificationError",
    "FaceIdentityConfig",
    "FaceIdentityResult",
    "FaceEmbedding",
    "IdentityVerification",
    "FaceIdentityProcessor",
    "EmbeddingIdentityProcessor",

    # Face Presence
    "FacePresenceError",
    "InvalidFaceStateError",
    "PresenceMonitoringError",
    "FacePresenceConfig",
    "FacePresenceResult",
    "PresenceState",
    "PresenceStatistics",
    "FacePresenceProcessor",
    "TemporalFacePresenceProcessor"
]
