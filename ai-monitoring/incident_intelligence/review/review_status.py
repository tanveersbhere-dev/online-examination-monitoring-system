"""
Review Status Enum for Review Intelligence Engine.
"""
from enum import Enum

class ReviewStatusEnum(str, Enum):
    UNREVIEWED = "UNREVIEWED"
    UNDER_REVIEW = "UNDER_REVIEW"
    REVIEWED = "REVIEWED"
