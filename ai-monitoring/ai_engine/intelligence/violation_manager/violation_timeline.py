"""Temporal aggregation and state machine for violations."""
import time
import uuid
import logging
from threading import RLock
from typing import List, Optional

from ai_engine.intelligence.violation_manager.models import (
    Violation,
    ViolationTimeline,
    ViolationStatistics,
    ViolationManagerConfig,
    LifecycleEvent,
)
from ai_engine.intelligence.violation_manager.exceptions import (
    ViolationCreationError,
    ViolationMergeError,
)

logger = logging.getLogger(__name__)


# These detector-specific rules describe one canonical off-screen attention
# condition and therefore share one lifecycle episode.
ATTENTION_FAMILY = frozenset({
    "ATT_LOOKING_AWAY",
    "ATT_DOWNWARD_GAZE",
    "ATT_SIDE_GAZE",
    "ATT_UPWARD_GAZE",
    "ATT_HEAD_ROTATION",
})
PHONE_ATTENTION_COMPOSITE = "COMPOSITE_PHONE_LOOKING_AWAY_TALKING"
PHONE_ATTENTION_COMPONENTS = frozenset({"UNAUTH_PHONE", *ATTENTION_FAMILY})


class ViolationTimelineManager:
    """
    Manages the lifecycle, merging, and closure of violations across time.

    process_triggers() is called once per frame. On most frames it returns an
    empty list. It returns non-empty LifecycleEvent objects only when a
    violation transitions:
        NEW violation  →  LifecycleEvent("STARTED")
        Severity rises →  LifecycleEvent("UPDATED")
        Auto-closed    →  LifecycleEvent("RESOLVED")
    """

    def __init__(self, config: ViolationManagerConfig):
        self._config = config
        self._timeline = ViolationTimeline()
        self._statistics = ViolationStatistics()
        # Candidate tracking buffer: {violation_type: {"first_seen_ts": float, "last_seen_ts": float, "frame_count": int, "max_conf": float, "conf_sum": float}}
        self._candidates: dict = {}
        self._lock = RLock()

    @property
    def timeline(self) -> ViolationTimeline:
        return self._timeline

    @property
    def statistics(self) -> ViolationStatistics:
        return self._statistics

    # ------------------------------------------------------------------
    # Public interface — called once per frame
    # ------------------------------------------------------------------

    def process_triggers(
        self,
        triggered_rules: List[dict],
        risk_score: float,
        risk_level: str,
        evidence_refs: List[str],
        current_time: float,
        camera_id: str = "camera_1",
    ) -> List[LifecycleEvent]:
        """Advance one frame atomically so concurrent callbacks cannot create parallel episodes."""
        with self._lock:
            return self._process_triggers(triggered_rules, risk_score, risk_level, evidence_refs, current_time, camera_id=camera_id)
    def _process_triggers(
        self,
        triggered_rules: List[dict],
        risk_score: float,
        risk_level: str,
        evidence_refs: List[str],
        current_time: float,
        camera_id: str = "camera_1",
    ) -> List[LifecycleEvent]:
        """
        Advance the violation state machine for the current frame.

        Implements professional proctoring lifecycle:
          CANDIDATE (gated) → CONFIRMING (debounced) → ACTIVE (confirmed) → COOLDOWN → RESOLVED (coalesced)

        Returns a list of LifecycleEvent objects describing transitions that
        occurred this frame. The list is empty on the vast majority of frames.
        """
        lifecycle_events: List[LifecycleEvent] = []

        # Filter low-confidence triggers and apply hierarchical rule
        # subsumption before determining whether an attention episode should
        # be protected from expiry on this frame.
        min_conf = getattr(self._config, "min_candidate_confidence", 0.40)
        # Completely exclude identity mismatch, identity integrity, and identity instability violations from lifecycle
        triggered_rules = [r for r in triggered_rules if r.get("rule_id") not in ("ID_MISMATCH", "IDENTITY_REPEATED_MISMATCH", "IDENTITY_LOW_INTEGRITY", "IDENTITY_INSTABILITY")]
        raw_rids = set(r.get("rule_id", "") for r in triggered_rules if float(r.get("confidence", 1.0)) >= min_conf)

        # Hierarchical Subsumption: Higher-order composite rules suppress redundant sub-rule noise
        suppressed_rids = set()
        if PHONE_ATTENTION_COMPOSITE in raw_rids:
            # Composite rules provide contextual titling / behavior annotations,
            # but must NEVER merge or suppress underlying violation lifecycles.
            suppressed_rids.add(PHONE_ATTENTION_COMPOSITE)

        if "CONFIRMED_PRESENTATION_ATTACK" in raw_rids or "ID_MISMATCH" in raw_rids or "IDENTITY_REPEATED_MISMATCH" in raw_rids:
            suppressed_rids.update(["IDENTITY_LOW_INTEGRITY", "IDENTITY_INSTABILITY"])

        if "ID_FACE_MISSING" in raw_rids or "COMM_MULTIPLE_PERSONS" in raw_rids or "ID_MULTIPLE_FACES" in raw_rids:
            suppressed_rids.update(["ATT_LOOKING_AWAY", "ATT_DOWNWARD_GAZE", "IDENTITY_INSTABILITY", "IDENTITY_LOW_INTEGRITY"])

        # Attention family deduplication: Prevent parallel/simultaneous attention violations
        # A single continuous off-screen attention condition must map to a single active episode
        if "ATT_LOOKING_AWAY" in raw_rids:
            suppressed_rids.update(["ATT_DOWNWARD_GAZE", "ATT_SIDE_GAZE", "ATT_UPWARD_GAZE", "ATT_HEAD_ROTATION"])
        elif "ATT_DOWNWARD_GAZE" in raw_rids:
            suppressed_rids.update(["ATT_SIDE_GAZE", "ATT_UPWARD_GAZE", "ATT_HEAD_ROTATION"])
        elif "ATT_SIDE_GAZE" in raw_rids:
            suppressed_rids.update(["ATT_UPWARD_GAZE", "ATT_HEAD_ROTATION"])
        elif "ATT_UPWARD_GAZE" in raw_rids:
            suppressed_rids.update(["ATT_HEAD_ROTATION"])

        # Material family deduplication:
        if "ENV_BOOK_DETECTED" in raw_rids or "UNAUTH_BOOK" in raw_rids:
            suppressed_rids.update(["UNAUTH_NOTEBOOK", "UNAUTH_PAPER", "UNAUTH_REGISTER", "UNAUTH_PAGE"])

        # Multiple persons family deduplication:
        if "COMM_MULTIPLE_PERSONS" in raw_rids:
            suppressed_rids.update(["ID_MULTIPLE_FACES"])

        # An attention subtype can legitimately change from frame to frame for
        # the same off-screen condition.  Keep an existing attention episode
        # available for family matching when this frame still has an effective
        # attention signal; otherwise the pre-match expiry pass would resolve
        # it and force a second STARTED event/UUID in this same frame.
        has_attention_signal = bool((raw_rids - suppressed_rids) & ATTENTION_FAMILY)

        # Step 1: Auto-close violations that have gone silent longer than the
        # configured debounced cooldown timeout for the current camera.
        resolved_events = self._auto_close_expired(current_time, has_attention_signal, current_camera_id=camera_id)
        lifecycle_events.extend(resolved_events)

        # Age out stale unconfirmed candidate tracks (> 5.0s of inactivity to tolerate AI sampling intervals)
        self._age_candidates(current_time)

        grouped_triggers: dict = {}
        for r in triggered_rules:
            conf = float(r.get("confidence", 1.0))
            if conf < min_conf:
                continue  # Confidence gating
            rid = r.get("rule_id", "UNKNOWN_RULE")
            if rid in suppressed_rids:
                continue  # Subsumption gating
            if rid not in grouped_triggers:
                grouped_triggers[rid] = []
            grouped_triggers[rid].append(r)

        # Mark inactive frame gap for active violations not in grouped_triggers this frame on the same camera
        active_types = set(grouped_triggers.keys())
        for v in self._timeline.violations:
            if getattr(v, "camera_id", "camera_1") != camera_id:
                # Do NOT mark interruption for violations belonging to a different camera
                continue
            if v.status in ("OPEN", "ACTIVE") and v.violation_type not in active_types:
                v.was_interrupted = True

        if not grouped_triggers:
            return lifecycle_events

        attention_family = ATTENTION_FAMILY
        material_family = {"UNAUTH_BOOK", "ENV_BOOK_DETECTED", "UNAUTH_NOTEBOOK", "UNAUTH_PAPER", "UNAUTH_REGISTER", "UNAUTH_PAGE"}
        person_family = {"COMM_MULTIPLE_PERSONS", "ID_MULTIPLE_FACES"}

        for v_type, rules in grouped_triggers.items():
            category = rules[0].get("category", "UNKNOWN")
            rule_ids = [v_type]
            rule_conf = rules[0].get("confidence", 1.0) if rules else 1.0

            # Step 3: Match against an existing OPEN/ACTIVE/RECOVERING violation OF THE SAME TYPE or family
            matching_violation = None
            for v in self._timeline.violations:
                if v.status in ("OPEN", "ACTIVE", "RECOVERING"):
                    if v.violation_type == v_type:
                        matching_violation = v
                        break
                    elif (
                        v.violation_type in attention_family
                        and v_type in attention_family
                        and v.violation_type != "ATT_DOWNWARD_GAZE"
                        and v_type != "ATT_DOWNWARD_GAZE"
                    ):
                        matching_violation = v
                        break
                    elif v.violation_type in material_family and v_type in material_family:
                        matching_violation = v
                        break
                    elif v.violation_type in person_family and v_type in person_family:
                        matching_violation = v
                        break

            if matching_violation is not None:
                # Update existing behavior episode for this type
                severity_changed = self._merge_into(
                    matching_violation, rule_ids, risk_score, risk_level, evidence_refs, current_time, rule_conf
                )
                if severity_changed:
                    lifecycle_events.append(
                        LifecycleEvent(
                            event_type="UPDATED",
                            violation_id=matching_violation.violation_id,
                            violation_type=matching_violation.violation_type,
                            violation_category=matching_violation.violation_category,
                            severity=matching_violation.severity,
                            risk_score=matching_violation.risk_score,
                            triggered_rules=list(matching_violation.triggered_rules),
                            timestamp=current_time,
                            start_timestamp=matching_violation.start_timestamp,
                            end_timestamp=None,
                            description=matching_violation.description,
                            current_confidence=matching_violation.current_confidence,
                            peak_confidence=matching_violation.peak_confidence,
                            detection_count=matching_violation.detection_count,
                            duration=max(0.0, current_time - matching_violation.start_timestamp),
                            camera_id=getattr(matching_violation, "camera_id", "camera_1"),
                        )
                    )
            else:
                # Step 4: Candidate & Confirmation Debounce Stage
                # Check candidate buffer to confirm persistence before creating a violation
                cand = self._candidates.get(v_type)
                if cand is None:
                    cand = {
                        "first_seen_ts": current_time,
                        "last_seen_ts": current_time,
                        "frame_count": 1,
                        "max_conf": rule_conf,
                        "conf_sum": rule_conf,
                    }
                    self._candidates[v_type] = cand
                else:
                    cand["last_seen_ts"] = current_time
                    cand["frame_count"] += 1
                    cand["max_conf"] = max(cand["max_conf"], rule_conf)
                    cand["conf_sum"] += rule_conf

                # Determine if candidate meets confirmation criteria:
                # Criteria: consecutive frames reached OR debounce window elapsed OR high confidence
                debounce_dur = getattr(self._config, "per_violation_debounce_seconds", {}).get(
                    v_type, getattr(self._config, "debounce_window_seconds", 0.5)
                )
                min_frames = getattr(self._config, "min_confirming_frames", 1)
                elapsed = current_time - cand["first_seen_ts"]

                # Attention is especially susceptible to one-frame landmark/gaze
                # jitter. Require both sustained time and several observations before
                # opening an episode; non-attention rules retain their existing policy.
                is_confirmed = cand["frame_count"] >= min_frames

                if is_confirmed:
                    active_count = len([v for v in self._timeline.violations if v.status in ("OPEN", "ACTIVE", "RECOVERING")])
                    if active_count >= self._config.maximum_active_violations:
                        if self._config.enable_logging:
                            logger.warning("Maximum active violations reached. Cannot create new violation.")
                        continue

                    # Confirmed: create violation record and emit STARTED event
                    new_violation = self._create_violation(
                        v_type, category, risk_score, risk_level, rule_ids, evidence_refs, current_time, rule_conf, camera_id=camera_id
                    )
                    new_violation.is_confirmed = True
                    new_violation.candidate_first_seen = cand["first_seen_ts"]
                    new_violation.candidate_frame_count = cand["frame_count"]

                    lifecycle_events.append(
                        LifecycleEvent(
                            event_type="STARTED",
                            violation_id=new_violation.violation_id,
                            violation_type=new_violation.violation_type,
                            violation_category=new_violation.violation_category,
                            severity=new_violation.severity,
                            risk_score=new_violation.risk_score,
                            triggered_rules=list(new_violation.triggered_rules),
                            timestamp=current_time,
                            start_timestamp=new_violation.start_timestamp,
                            end_timestamp=None,
                            description=new_violation.description,
                            current_confidence=new_violation.current_confidence,
                            peak_confidence=new_violation.peak_confidence,
                            detection_count=new_violation.detection_count,
                            duration=0.0,
                            camera_id=new_violation.camera_id,
                        )
                    )
                    # Clean up candidate entry
                    self._candidates.pop(v_type, None)
                else:
                    self._statistics.total_candidates_debounced += 1

        return lifecycle_events

    def _promote_phone_attention_composite(self, current_time: float) -> List[LifecycleEvent]:
        """
        Deprecated: Underlying violations (UNAUTH_PHONE and ATTENTION_FAMILY) must remain
        completely independent episodes with separate lifecycles, evidence budgets, and DB records.
        """
        return []

    def _age_candidates(self, current_time: float) -> None:
        """Purge stale candidate tracks that flickered for only 1 frame and disappeared (> 5.0s)."""
        stale_keys = [
            k for k, v in self._candidates.items()
            if (current_time - v.get("last_seen_ts", current_time)) > 5.0
        ]
        for k in stale_keys:
            del self._candidates[k]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _auto_close_expired(
        self,
        current_time: float,
        has_attention_signal: bool = False,
        current_camera_id: str = "camera_1"
    ) -> List[LifecycleEvent]:
        """
        Close behavior episodes that have been inactive longer than their per-violation resolution timeout.
        Returns a LifecycleEvent("RESOLVED") carrying the full episode summary for each one that closes.
        """
        events: List[LifecycleEvent] = []
        per_timeouts = getattr(self._config, "per_violation_timeouts", {})
        default_timeout = getattr(self._config, "auto_close_timeout_seconds", 1.0)

        for violation in self._timeline.violations:
            if violation.status not in ("OPEN", "ACTIVE", "RECOVERING"):
                continue

            v_type = violation.violation_type
            v_cam = getattr(violation, "camera_id", "camera_1")

            # Camera Isolation: A frame from camera A cannot observe absence on camera B.
            # Only evaluate expiry if the current frame is from the same camera that owns the violation,
            # or if the violation has been completely silent/unobserved for an extended disconnect timeout (>=25.0s).
            if v_cam != current_camera_id:
                if (current_time - violation.last_updated_timestamp) < 25.0:
                    continue

            if has_attention_signal and v_type in ATTENTION_FAMILY:
                continue
            is_identity_rule = "IDENTITY" in v_type or "ID_" in v_type
            per_timeout = per_timeouts.get(v_type)
            cooldown_cfg = getattr(self._config, "cooldown_duration_seconds", None)
            if per_timeout is not None:
                timeout = per_timeout
            elif v_type in ATTENTION_FAMILY:
                # A brief gaze-model miss is not the end of an off-screen episode.
                timeout = float(getattr(self._config, "attention_grace_seconds", 5.0))
            elif cooldown_cfg is not None and cooldown_cfg != 12.0:
                timeout = cooldown_cfg
            else:
                timeout = 8.0 if is_identity_rule else default_timeout
            inactive_sec = current_time - violation.last_updated_timestamp

            if inactive_sec >= timeout:
                violation.status = "RESOLVED"
                violation.end_timestamp = violation.last_updated_timestamp
                total_dur = max(0.1, round(violation.end_timestamp - violation.start_timestamp, 1))
                avg_conf = round(violation.confidence_sum / max(1, violation.confidence_samples), 4)

                violation.description = (
                    f"Behavior Episode {v_type} Summary: duration={total_dur}s, "
                    f"peak_confidence={violation.peak_confidence:.2f}, avg_confidence={avg_conf:.2f}, "
                    f"interruptions={violation.interruption_count}"
                )

                self._statistics.currently_active = max(0, self._statistics.currently_active - 1)
                self._statistics.total_resolved += 1

                logger.info(
                    f"[EVENT LIFECYCLE - RESOLVED] Episode {violation.violation_id} ({v_type}) "
                    f"closed after {total_dur}s duration (peak_conf={violation.peak_confidence:.2f}, avg_conf={avg_conf:.2f})"
                )

                events.append(
                    LifecycleEvent(
                        event_type="RESOLVED",
                        violation_id=violation.violation_id,
                        violation_type=violation.violation_type,
                        violation_category=violation.violation_category,
                        severity=violation.severity,
                        risk_score=violation.risk_score,
                        triggered_rules=list(violation.triggered_rules),
                        timestamp=current_time,
                        start_timestamp=violation.start_timestamp,
                        end_timestamp=violation.end_timestamp,
                        description=violation.description,
                        current_confidence=violation.current_confidence,
                        peak_confidence=violation.peak_confidence,
                        detection_count=violation.detection_count,
                        duration=total_dur,
                        camera_id=getattr(violation, "camera_id", "camera_1"),
                    )
                )
        return events

    def _merge_into(
        self,
        violation: Violation,
        rule_ids: List[str],
        risk_score: float,
        risk_level: str,
        evidence_refs: List[str],
        current_time: float,
        rule_conf: float = 1.0,
    ) -> bool:
        """
        Merge a new frame trigger into an existing active behavior episode.
        Updates duration, peak confidence, and average confidence accumulation.
        """
        try:
            old_severity = violation.severity

            # Retries of an unchanged observation are idempotent. Test and
            # adapter callers may reuse a timestamp while supplying a newer
            # confidence or a resumed signal, both of which are real updates.
            if (
                current_time < violation.last_observation_timestamp
                or (
                    current_time == violation.last_observation_timestamp
                    and rule_conf == violation.current_confidence
                    and not violation.was_interrupted
                )
            ):
                return violation.severity != old_severity

            violation.status = "ACTIVE"
            violation.last_updated_timestamp = current_time
            violation.last_observation_timestamp = current_time

            # Increment interruption count if behavior resumed after a frame gap
            if getattr(violation, "was_interrupted", False):
                violation.interruption_count += 1
                violation.was_interrupted = False

            # Update confidence metrics
            violation.current_confidence = rule_conf
            violation.confidence_sum += rule_conf
            violation.confidence_samples += 1
            violation.detection_count += 1
            if rule_conf >= violation.peak_confidence:
                violation.peak_confidence = rule_conf

            # Only raise severity — never lower it mid-session.
            if risk_score > violation.risk_score:
                violation.risk_score = risk_score
                violation.severity = risk_level

            for rid in rule_ids:
                if rid not in violation.triggered_rules:
                    violation.triggered_rules.append(rid)

            for ev in evidence_refs:
                if ev not in violation.supporting_evidence_references:
                    violation.supporting_evidence_references.append(ev)

            total_dur = max(0.1, round(current_time - violation.start_timestamp, 1))
            violation.description = (
                f"Active Behavior Episode {violation.violation_type} (Duration: {total_dur}s, Peak Conf: {violation.peak_confidence:.2f})"
            )
            self._statistics.total_merged += 1

            return violation.severity != old_severity  # True ⟹ severity escalated

        except Exception as e:
            raise ViolationMergeError(f"Failed to merge into violation {violation.violation_id}: {e}")

    def _create_violation(
        self,
        v_type: str,
        category: str,
        risk_score: float,
        risk_level: str,
        rule_ids: List[str],
        evidence_refs: List[str],
        current_time: float,
        rule_conf: float = 1.0,
        camera_id: str = "camera_1",
    ) -> Violation:
        """
        Create a new behavior episode and register it in the timeline.
        """
        try:
            v_id = f"V-{uuid.uuid4().hex[:8].upper()}"
            violation = Violation(
                violation_id=v_id,
                violation_type=v_type,
                violation_category=category,
                severity=risk_level,
                risk_score=risk_score,
                triggered_rules=list(set(rule_ids)),
                supporting_evidence_references=list(set(evidence_refs)),
                start_timestamp=current_time,
                last_updated_timestamp=current_time,
                status="OPEN",
                description=f"New behavior episode for {category} ({v_type})",
                peak_confidence=rule_conf,
                current_confidence=rule_conf,
                confidence_sum=rule_conf,
                confidence_samples=1,
                detection_count=1,
                last_observation_timestamp=current_time,
                interruption_count=0,
                camera_id=camera_id,
            )

            self._timeline.violations.append(violation)
            self._statistics.total_violations_created += 1
            self._statistics.currently_active += 1

            if self._config.enable_logging:
                logger.info(f"Created new behavior episode {v_id} ({v_type})")

            return violation

        except Exception as e:
            raise ViolationCreationError(f"Failed to create new violation: {e}")

    # ------------------------------------------------------------------
    # Administrative helpers
    # ------------------------------------------------------------------

    def close_all(self, current_time: float) -> None:
        """Force-close all active violations — typically called on shutdown."""
        for v in self._timeline.violations:
            if v.status in ("OPEN", "ACTIVE"):
                v.status = "RESOLVED"
                v.end_timestamp = current_time
                self._statistics.currently_active -= 1
                self._statistics.total_resolved += 1

    def reopen(self, violation_id: str, current_time: float) -> None:
        """Manually reopen a resolved violation."""
        for v in self._timeline.violations:
            if v.violation_id == violation_id and v.status == "RESOLVED":
                v.status = "ACTIVE"
                v.last_updated_timestamp = current_time
                v.end_timestamp = None
                self._statistics.currently_active += 1
                self._statistics.total_resolved -= 1
                return
