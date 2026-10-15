"""
ReviewBuilder for Review Intelligence Engine.
Assembles read-only Incident, Evidence, Timeline, Analytics, and Explanation references into a ReviewPackage.
"""
from typing import Optional, List, Dict, Any
import time
import uuid

from incident_intelligence.domain.incident import Incident
from incident_intelligence.domain.evidence_reference import EvidenceReference
from incident_intelligence.analytics.analytics_repository import IncidentAnalyticsSnapshot
from incident_intelligence.explainability.narrative_builder import IncidentExplanationPackage
from incident_intelligence.review.review_status import ReviewStatusEnum
from incident_intelligence.review.review_decision import ReviewDecisionEnum
from incident_intelligence.review.review_audit import ReviewAuditEntry
from incident_intelligence.review.review_package import ReviewPackage

class ReviewBuilder:
    """Builder assembling read-only incident references into an immutable ReviewPackage."""

    def build_review_package(
        self,
        incident: Incident,
        evidence_references: Optional[List[EvidenceReference]] = None,
        human_timeline_projection: Optional[Dict[str, Any]] = None,
        analytics_snapshot: Optional[IncidentAnalyticsSnapshot] = None,
        explanation_package: Optional[IncidentExplanationPackage] = None
    ) -> ReviewPackage:
        """
        Construct a new ReviewPackage containing read-only DTO snapshots and metadata.
        """
        ts_now = time.time()
        pkg_id = f"REV-{uuid.uuid4().hex[:8].upper()}"

        ev_dtos = [ref.to_dto() for ref in (evidence_references or incident.evidence_references)]

        rc_strings = []
        if explanation_package:
            rc_strings = [rc.code for rc in explanation_package.reason_codes]

        init_audit = ReviewAuditEntry(
            entry_id="AUD-1",
            timestamp=ts_now,
            action="REVIEW_STARTED",
            details="ReviewPackage instantiated for reviewer evaluation"
        )

        return ReviewPackage(
            package_id=pkg_id,
            incident_id=incident.incident_id,
            created_timestamp=ts_now,
            last_updated_timestamp=ts_now,
            incident_dto=incident.to_dto(),
            evidence_references=ev_dtos,
            human_timeline_projection=human_timeline_projection,
            analytics_snapshot_id=analytics_snapshot.snapshot_id if analytics_snapshot else None,
            explanation_package_id=explanation_package.incident_id if explanation_package else None,
            reason_codes=rc_strings,
            review_status=ReviewStatusEnum.UNREVIEWED,
            review_decision=ReviewDecisionEnum.NO_DECISION,
            notes=[],
            audit_trail=[init_audit]
        )
