"""
Enum Definitions for Incident Domain Core.
"""
from enum import Enum

class IncidentState(str, Enum):
    STARTED = "STARTED"
    ACTIVE = "ACTIVE"
    ESCALATED = "ESCALATED"
    RECOVERING = "RECOVERING"
    RESOLVED = "RESOLVED"

class IncidentSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class IncidentPriority(str, Enum):
    P4_LOW = "P4_LOW"
    P3_MEDIUM = "P3_MEDIUM"
    P2_HIGH = "P2_HIGH"
    P1_CRITICAL = "P1_CRITICAL"
