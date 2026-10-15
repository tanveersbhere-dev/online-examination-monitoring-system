"""
Review Decision Enum for Review Intelligence Engine.
"""
from enum import Enum

class ReviewDecisionEnum(str, Enum):
    CONFIRMED = "CONFIRMED"
    DISMISSED = "DISMISSED"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    NEEDS_ESCALATION = "NEEDS_ESCALATION"
    NO_DECISION = "NO_DECISION"
