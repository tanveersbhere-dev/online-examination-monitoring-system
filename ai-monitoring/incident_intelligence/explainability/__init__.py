"""
Incident Intelligence Platform (IIP)
Package 10.6: Explainability Engine
"""
from incident_intelligence.explainability.reason_codes import ReasonCode, ReasonCodeEnum
from incident_intelligence.explainability.reason_code_generator import ReasonCodeGenerator
from incident_intelligence.explainability.technical_explanation import TechnicalExplanation, TechnicalExplanationDTO
from incident_intelligence.explainability.reviewer_summary import ReviewerSummary, ReviewerSummaryDTO
from incident_intelligence.explainability.machine_explanation import MachineExplanation, MachineExplanationDTO
from incident_intelligence.explainability.narrative_builder import NarrativeBuilder, IncidentExplanationPackage, IncidentExplanationPackageDTO
from incident_intelligence.explainability.explanation_repository import InMemoryExplanationRepository

__all__ = [
    "ReasonCode",
    "ReasonCodeEnum",
    "ReasonCodeGenerator",
    "TechnicalExplanation",
    "TechnicalExplanationDTO",
    "ReviewerSummary",
    "ReviewerSummaryDTO",
    "MachineExplanation",
    "MachineExplanationDTO",
    "NarrativeBuilder",
    "IncidentExplanationPackage",
    "IncidentExplanationPackageDTO",
    "InMemoryExplanationRepository"
]
