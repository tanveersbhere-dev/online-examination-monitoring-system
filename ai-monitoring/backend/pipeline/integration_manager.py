"""
Incident Integration Bridge Manager
====================================
Production-grade integration bridge connecting Step 18 ViolationManager
lifecycle events to the Incident Intelligence Platform (Packages 10.1 - 10.9).

Design Principles:
- Single Point of Downstream Orchestration.
- Pure Event-Driven execution (non-blocking for high-frequency streams).
- Thread-safe repository container.
"""
import time
import logging
from typing import Dict, Any, List, Optional

# Package 10.1 Domain Core
from incident_intelligence.domain import (
    Incident,
    IncidentDTO,
    EvidenceReference,
    EvidenceReferenceDTO
)
from incident_intelligence.domain.enums import IncidentState

# Package 10.2 Incident Orchestration Engine
from incident_intelligence.orchestration import (
    IncidentFactory,
    InMemoryIncidentRepository,
    IncidentLifecycleManager,
    IncidentMatchingEngine,
    IncidentEventRouter,
    IncidentOrchestrator
)

# Package 10.3 Evidence Intelligence
from incident_intelligence.evidence import (
    EvidenceCandidate,
    EvidencePolicy,
    EvidenceRanker,
    EvidenceDeduplicator,
    EvidenceClusterer,
    EvidenceTimeline,
    EvidenceSelector
)

# Package 10.4 Incident Timeline Engine
from incident_intelligence.timeline import (
    TimelineEvent,
    TimelineEventDTO,
    TimelineBuilder,
    InMemoryTimelineRepository,
    TimelineQueryService,
    TimelineProjectionService,
    HumanTimelineProjection
)

# Package 10.5 Incident Intelligence Analytics Engine
from incident_intelligence.analytics import (
    AnalyticsEngine,
    InMemoryAnalyticsRepository,
    IncidentAnalyticsSnapshot,
    IncidentAnalyticsSnapshotDTO
)

# Package 10.6 Explainability Engine
from incident_intelligence.explainability import (
    ReasonCodeGenerator,
    NarrativeBuilder,
    IncidentExplanationPackage,
    IncidentExplanationPackageDTO,
    InMemoryExplanationRepository
)

# Package 10.7 Review Intelligence Engine
from incident_intelligence.review import (
    ReviewBuilder,
    ReviewPackage,
    ReviewPackageDTO,
    ReviewStatusEnum,
    ReviewDecisionEnum,
    ReviewNote,
    InMemoryReviewRepository
)

# Package 10.8 Replay Intelligence Engine
from incident_intelligence.replay import (
    ReplaySession,
    ReplaySessionDTO,
    FrameIndexEntry,
    FrameIndex,
    TimelineNavigator,
    EvidenceNavigator,
    ReplayBookmark,
    ReplayOverlayGenerator,
    InMemoryReplayRepository
)

# Package 10.9 Export & Reporting Engine
from incident_intelligence.export import (
    IntegrityHash,
    ExportManifest,
    CasePackage,
    JSONExporter,
    PDFExporter,
    ZIPExporter,
    InMemoryExportRepository
)

logger = logging.getLogger("playground.integration_manager")

class IncidentIntegrationManager:
    """
    Integration Container owning all Incident Intelligence Platform components.
    Listens to ViolationManager lifecycle events and updates domain aggregates,
    timelines, analytics snapshots, reason codes, review packages, and replay sessions.
    """

    def __init__(self):
        # Repositories (Session Lifetime)
        self.incident_repository = InMemoryIncidentRepository()
        self.timeline_repository = InMemoryTimelineRepository()
        self.analytics_repository = InMemoryAnalyticsRepository()
        self.explanation_repository = InMemoryExplanationRepository()
        self.review_repository = InMemoryReviewRepository()
        self.replay_repository = InMemoryReplayRepository()
        self.export_repository = InMemoryExportRepository()

        # Engine Components (Package 10.2 Orchestration)
        self.orchestrator = IncidentOrchestrator(
            repository=self.incident_repository
        )
        self.lifecycle_manager = self.orchestrator.lifecycle_manager

        # Evidence Selector (Package 10.3)
        self.evidence_selector = EvidenceSelector()

        # Timeline Services (Package 10.4)
        self.timeline_builder = TimelineBuilder(repository=self.timeline_repository)
        self.timeline_query = TimelineQueryService(repository=self.timeline_repository)
        self.timeline_projection = TimelineProjectionService(query_service=self.timeline_query)

        # Analytics Engine (Package 10.5)
        self.analytics_engine = AnalyticsEngine(repository=self.analytics_repository)

        # Explainability Services (Package 10.6)
        self.reason_code_generator = ReasonCodeGenerator()
        self.narrative_builder = NarrativeBuilder()

        # Review Services (Package 10.7)
        self.review_builder = ReviewBuilder()

        # Replay Services (Package 10.8)
        self.timeline_navigator = TimelineNavigator()
        self.evidence_navigator = EvidenceNavigator()
        self.overlay_generator = ReplayOverlayGenerator()

        # Export Services (Package 10.9)
        self.json_exporter = JSONExporter()
        self.pdf_exporter = PDFExporter()
        self.zip_exporter = ZIPExporter()

        self._active_replay_sessions: Dict[str, ReplaySession] = {}

    # ──────────────────────────────────────────────────────────────────────────
    # Event Handlers (Attached to ViolationManager Lifecycle Events)
    # ──────────────────────────────────────────────────────────────────────────

    def handle_frame_lifecycle_events(self, context) -> None:
        """
        Process frame context, index frame, and consume any ViolationLifecycleEvents.
        Executed once per frame. All exceptions caught to ensure pipeline resilience.
        """
        try:
            frame_num = getattr(getattr(context, "current_frame", None), "frame_id", 0)

            # 1. Capture lifecycle events emitted by ViolationManager
            events = getattr(context, "lifecycle_events", None) or []
            for e in events:
                self._process_single_lifecycle_event(e, frame_num)

            # Keep aggregate display metrics current without manufacturing an
            # append-only timeline event for every detector frame.
            self._synchronize_active_violation_state(context, frame_num)

            # 2. Synchronize active incident evidence keyframes from evidence store if available
            ev_list = getattr(context, "evidence_store", None) or []
            if ev_list:
                self._synchronize_evidence_store(ev_list)

        except Exception as err:
            logger.error(f"Error in IncidentIntegrationManager: {err}", exc_info=True)

    def _process_single_lifecycle_event(self, event_obj, frame_num: int) -> None:
        """Map a canonical violation transition to exactly one IIP aggregate update."""
        ts = float(getattr(event_obj, "timestamp", time.time()))
        event_type = getattr(event_obj, "event_type", "UPDATED")
        violation_id = getattr(event_obj, "violation_id", f"V-{int(ts)}")
        v_type = getattr(event_obj, "violation_type", "GENERAL_ANOMALY")
        category = getattr(event_obj, "violation_category", "Security")
        rules = getattr(event_obj, "triggered_rules", []) or [v_type]
        risk_score = float(getattr(event_obj, "risk_score", 50.0))
        description = getattr(event_obj, "description", "Behavior anomaly observed.")
        title = getattr(event_obj, "incident_title", v_type)

        event_dict = {
            "event_type": event_type,
            "violation_id": violation_id,
            "episode_id": violation_id,
            "incident_type": v_type,
            "timestamp": ts,
            "start_timestamp": float(getattr(event_obj, "start_timestamp", ts)),
            "end_timestamp": getattr(event_obj, "end_timestamp", None),
            "category": category,
            "title": title,
            "description": description,
            "triggered_rules": rules,
            "confidence": float(getattr(event_obj, "current_confidence", 0.0)),
            "peak_confidence": float(getattr(event_obj, "peak_confidence", 0.0)),
            "detection_count": int(getattr(event_obj, "detection_count", 0)),
            "duration": float(getattr(event_obj, "duration", 0.0)),
            "risk_score": risk_score,
            "frame_number": frame_num
        }

        # 1. Route through Incident Orchestrator (Package 10.2)
        incident = self.orchestrator.process_lifecycle_event(event_dict)
        if not incident:
            return

        # 2. Append to Canonical Timeline Engine (Package 10.4)
        if event_type == "STARTED":
            self.timeline_builder.record_incident_created(incident, ts)
        elif event_type == "RESOLVED":
            self.timeline_builder.record_resolved(incident.incident_id, ts, reason=description)
        else:
            self.timeline_builder.record_risk_updated(incident.incident_id, risk_score, ts, frame_number=frame_num)

        # 3. Derive Analytics Snapshot (Package 10.5)
        analytics_snap = self.analytics_engine.analyze_incident(incident, query_service=self.timeline_query)

        # 4. Generate Explainability Package (Package 10.6)
        timeline_events = self.timeline_query.get_complete_timeline(incident.incident_id)
        exp_pkg = self.narrative_builder.build_explanation_package(incident, timeline_events, analytics_snap)
        self.explanation_repository.save(exp_pkg)

        # 5. Build/Update ReviewPackage (Package 10.7)
        human_proj = self.timeline_projection.generate_human_projection(incident.incident_id, title)
        review_pkg = self.review_repository.get_by_incident_id(incident.incident_id)
        if not review_pkg:
            review_pkg = self.review_builder.build_review_package(
                incident=incident,
                human_timeline_projection=human_proj.to_dict(),
                analytics_snapshot=analytics_snap,
                explanation_package=exp_pkg
            )
            self.review_repository.save(review_pkg)

    def _synchronize_active_violation_state(self, context, frame_num: int) -> None:
        """Project active canonical violations into their existing incident aggregates."""
        violations_result = getattr(context, "violations", None)
        timeline = getattr(violations_result, "timeline", violations_result)
        violations = getattr(timeline, "violations", []) if timeline is not None else []
        for violation in violations:
            if getattr(violation, "status", "") not in ("OPEN", "ACTIVE", "RECOVERING"):
                continue
            incident = self.incident_repository.get_by_episode_id(violation.violation_id)
            if incident is None:
                continue
            timestamp = float(violation.last_updated_timestamp)
            incident.current_confidence = float(getattr(violation, "current_confidence", 0.0))
            incident.peak_confidence = max(incident.peak_confidence, float(getattr(violation, "peak_confidence", 0.0)))
            incident.current_risk = float(violation.risk_score)
            incident.last_updated = timestamp
            incident.duration = round(max(0.0, timestamp - incident.start_time), 2)
            if str(getattr(incident.status, "value", incident.status)) != "ACTIVE":
                self.lifecycle_manager.transition_state(incident, timestamp, IncidentState.ACTIVE, "Violation episode active")
            self.incident_repository.save(incident)

    def _synchronize_evidence_store(self, evidence_store: List[Dict[str, Any]]) -> None:
        """Attach evidence store image references to open incidents."""
        active_incidents = self.incident_repository.list_active()
        if not active_incidents or not evidence_store:
            return

        records_by_episode = {
            str(record.get("violation_id") or record.get("episode_id")): record
            for record in evidence_store
            if record.get("violation_id") or record.get("episode_id")
        }
        for inc in active_incidents:
            # Evidence belongs only to the incident with the same canonical episode ID;
            # never copy the latest gallery item to every active incident.
            record = records_by_episode.get(str(inc.episode_id))
            if not record:
                continue
            ev_id = str(record.get("id", f"EV-{inc.episode_id}"))
            existing_ids = {ref.evidence_id for ref in inc.evidence_references}
            if ev_id in existing_ids:
                continue
            uri = str(record.get("filepath") or record.get("uri") or record.get("path") or "")
            ts = float(record.get("timestamp", time.time()))
            ref = EvidenceReference(
                evidence_id=ev_id,
                frame_number=int(record.get("frame_id", record.get("frame_number", 1))),
                timestamp=ts,
                uri=uri,
                importance=float(record.get("peak_confidence", record.get("confidence", 0.85))),
                crop_type="FULL_FRAME"
            )
            inc.add_evidence_reference(ref)
            self.timeline_builder.record_evidence_added(inc.incident_id, ref, ts)

    # ──────────────────────────────────────────────────────────────────────────
    # Serializer & Query APIs (O(1) DTO Reads)
    # ──────────────────────────────────────────────────────────────────────────

    def get_platform_serializer_payload(self) -> Dict[str, Any]:
        """
        Fast DTO payload builder for ResultSerializer.

        Returns the last 20 incidents (any status: ACTIVE, RESOLVED, REVIEWED)
        so the frontend can display a complete session history with correct status
        badges, not just active incidents that disappear on resolution.
        """
        all_incidents = self.incident_repository.list_all()
        active_incidents = self.incident_repository.list_active()

        # Last 20 incidents, newest first, all statuses included
        recent_all = all_incidents[-20:]
        all_dtos = [inc.to_dto().to_dict() for inc in recent_all]

        return {
            "all_incidents": all_dtos,
            "active_incident_count": len(active_incidents),
            "total_incident_count": len(all_incidents),
        }

    def clear(self) -> None:
        """Reset all repositories (Session Teardown)."""
        self.incident_repository.clear()
        self.timeline_repository.clear()
        self.analytics_repository.clear()
        self.explanation_repository.clear()
        self.review_repository.clear()
        self.replay_repository.clear()
        self.export_repository.clear()
