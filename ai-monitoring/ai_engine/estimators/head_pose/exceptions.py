"""
Custom exceptions for the Head Pose Estimation module.

These are fully isolated from both the core engine exceptions and other modules,
ensuring the head pose subsystem can be replaced or removed independently.
"""


class HeadPoseEstimatorError(Exception):
    """Base exception for all Head Pose Estimation errors."""
    pass


class PoseEstimationError(HeadPoseEstimatorError):
    """
    Raised when head pose estimation fails on a specific frame.
    
    Typical causes:
    • OpenCV solvePnP crash
    • Invalid camera matrix or distortion coefficients
    """
    pass


class InvalidLandmarkError(HeadPoseEstimatorError):
    """
    Raised when the required facial landmarks are missing, invalid, or 
    insufficient for pose estimation.
    """
    pass


class HeadPoseEstimatorStateError(HeadPoseEstimatorError):
    """
    Raised when a lifecycle method is called in an invalid order.
    """
    pass
