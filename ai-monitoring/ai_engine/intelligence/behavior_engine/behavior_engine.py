"""
Behavior Engine Processor for AI Monitoring Engine (Step 18 in Orchestrator).
Consumes rule results, lifecycle events, and observation fields to perform temporal reasoning.
"""
import time
import logging
from typing import List, Dict, Any, Optional

from ai_engine.core.exam_context import ExamContext
from ai_engine.intelligence.behavior_engine.behavior_event import (
    BehaviorMemoryEntry, CompositeBehaviorInstance, CandidateBehaviorProfile, BehaviorSessionSummary
)
from ai_engine.intelligence.behavior_engine.behavior_memory import BehaviorMemory
from ai_engine.intelligence.behavior_engine.composite_behavior import CompositeBehaviorEvaluator
from ai_engine.intelligence.behavior_engine.confidence_engine import ConfidenceEngine
from ai_engine.intelligence.behavior_engine.behavior_profile import BehaviorProfileManager
from ai_engine.intelligence.behavior_engine.behavior_serializer import BehaviorSerializer

from ai_engine.intelligence.behavior_engine.temporal_state_machine import BehaviorStateMachineManager, BehaviorState

logger = logging.getLogger("ai_engine.behavior.engine")

class BehaviorEngineProcessor:
    """
    Step 18 in Monitoring Pipeline Orchestrator. Performs temporal state machine reasoning,
    composite behavior detection, confidence calculation, and candidate behavior profiling.
    """
    def __init__(self, memory_window_seconds: float = 60.0) -> None:
        self._initialized: bool = False
        self.memory: BehaviorMemory = BehaviorMemory(window_seconds=memory_window_seconds)
        self.confidence_engine: ConfidenceEngine = ConfidenceEngine(decay_rate_per_sec=45.0)
        self.state_machine_manager: BehaviorStateMachineManager = BehaviorStateMachineManager()
        self.profile_manager: BehaviorProfileManager = BehaviorProfileManager()
        self.last_proc_time_ms: float = 0.0
        self.active_behaviors: Dict[str, CompositeBehaviorInstance] = {}
        self.resolved_behaviors: List[CompositeBehaviorInstance] = []
        self.total_escalations_count: int = 0
        self.peak_confidence: float = 0.0

    def initialize(self) -> None:
        self.memory.clear()
        self.confidence_engine.reset()
        self.state_machine_manager = BehaviorStateMachineManager()
        self.profile_manager = BehaviorProfileManager()
        self.active_behaviors.clear()
        self.resolved_behaviors.clear()
        self.total_escalations_count = 0
        self.peak_confidence = 0.0
        self._initialized = True
        logger.info("BehaviorEngineProcessor initialized.")

    def start(self) -> None:
        self.initialize()

    def stop(self) -> None:
        pass

    def cleanup(self) -> None:
        self._initialized = False

    def process(self, context: ExamContext) -> None:
        if not self._initialized:
            return

        t0 = time.perf_counter()
        current_ts = time.time()
        calib_info = getattr(context, "calibration_info", None)

        # 0. Process Rule State Machine transitions for all rule evaluations
        rr = getattr(context, "rule_results", None)
        evaluations = getattr(rr, "evaluations", []) if rr else []
        state_telemetry: Dict[str, Dict[str, Any]] = {}

        for ev in evaluations:
            rule_id = getattr(ev, "rule_id", "UNKNOWN")
            raw_triggered = getattr(ev, "triggered", False)
            raw_conf = getattr(ev, "confidence", 1.0)

            state, state_conf, is_active = self.state_machine_manager.update_frame(
                rule_id=rule_id,
                observed=raw_triggered,
                raw_confidence=raw_conf,
                current_ts=current_ts,
                calibration_info=calib_info
            )

            state_telemetry[rule_id] = {
                "state": state,
                "confidence": state_conf,
                "is_active": is_active,
                "sustained_seconds": round(self.state_machine_manager.get_tracker(rule_id, current_ts).sustained_duration, 2)
            }

        # 1. Extract atomic frame observations & rule outputs to build BehaviorMemoryEntry
        self._ingest_frame_entry(context, current_ts)

        # 2. Evaluate all Composite Behaviors over rolling memory window
        memory_entries = self.memory.get_recent(within_seconds=60.0, current_timestamp=current_ts)

        candidates: List[Optional[CompositeBehaviorInstance]] = [
            CompositeBehaviorEvaluator.evaluate_phone_usage(memory_entries, current_ts),
            CompositeBehaviorEvaluator.evaluate_communication(memory_entries, current_ts),
            CompositeBehaviorEvaluator.evaluate_outside_assistance(memory_entries, current_ts),
            CompositeBehaviorEvaluator.evaluate_camera_evasion(memory_entries, current_ts),
            CompositeBehaviorEvaluator.evaluate_looking_for_notes(memory_entries, current_ts),
            CompositeBehaviorEvaluator.evaluate_screen_reference(memory_entries, current_ts),
        ]

        evaluated_active: List[CompositeBehaviorInstance] = []

        for inst in candidates:
            if inst is None:
                continue

            # Compute 0-100% confidence with buildup/decay
            conf = self.confidence_engine.calculate_confidence(
                instance=inst,
                current_ts=current_ts,
                is_actively_supported=True
            )
            inst.confidence = conf

            if conf > 20.0:
                evaluated_active.append(inst)
                self.active_behaviors[inst.name] = inst
                if conf > self.peak_confidence:
                    self.peak_confidence = conf

        # Handle decay for inactive behaviors
        all_names = {"PHONE_USAGE", "COMMUNICATION", "OUTSIDE_ASSISTANCE", "CAMERA_EVASION", "LOOKING_FOR_NOTES", "SCREEN_REFERENCE"}
        active_names = {b.name for b in evaluated_active}

        for name in all_names - active_names:
            if name in self.active_behaviors:
                inst = self.active_behaviors[name]
                decayed_conf = self.confidence_engine.calculate_confidence(
                    instance=inst,
                    current_ts=current_ts,
                    is_actively_supported=False
                )
                inst.confidence = decayed_conf
                if decayed_conf > 10.0:
                    evaluated_active.append(inst)
                else:
                    # Fully resolved
                    inst.resolved = True
                    self.resolved_behaviors.append(inst)
                    del self.active_behaviors[name]

        # 3. Update Candidate Behavior Profile
        profile = self.profile_manager.update_profile(evaluated_active, current_ts)

        if profile.trend == "ESCALATING":
            self.total_escalations_count += 1

        # 4. Generate Session Summary
        summary = self.generate_session_summary(current_ts)

        # 5. Measure Latency & Metrics
        self.last_proc_time_ms = (time.perf_counter() - t0) * 1000.0

        behavior_payload = {
            "profile": BehaviorSerializer.serialize_profile(profile),
            "timeline": BehaviorSerializer.serialize_timeline_events(self.profile_manager.timeline_events),
            "summary": BehaviorSerializer.serialize_summary(summary),
            "state_machine_states": state_telemetry,
            "metrics": {
                "proc_time_ms": round(self.last_proc_time_ms, 2),
                "memory_size": self.memory.size,
                "active_behaviors_count": len(evaluated_active),
                "resolved_behaviors_count": len(self.resolved_behaviors),
            }
        }

        # Dynamically attach to ExamContext
        setattr(context, "behavior_result", behavior_payload)

    def _ingest_frame_entry(self, context: ExamContext, current_ts: float) -> None:
        fi = getattr(context, "face_info", None)
        hp = getattr(context, "head_pose_info", None)
        ei = getattr(context, "eye_info", None)
        mi = getattr(context, "mouth_info", None)
        oi = getattr(context, "object_info", None)
        risk = getattr(context, "risk_score", None)

        face_detected = getattr(fi, "face_detected", False) if fi else False
        face_count = getattr(fi, "face_count", 0) if fi else 0

        talking = getattr(mi, "is_talking", False) if mi else False

        # Parse rule results if present
        rr = getattr(context, "rule_results", None)
        evaluations = getattr(rr, "evaluations", []) if rr else []

        phone_present = False
        tracked = getattr(oi, "tracked_objects", []) or getattr(oi, "filtered_detections", []) if oi else []
        for obj in tracked:
            otype = getattr(obj.object_type, "name", str(obj.object_type))
            if otype == "CELL_PHONE":
                phone_present = True

        r_score = getattr(risk, "current_score", 0.0) if risk else 0.0

        for ev in evaluations:
            if not getattr(ev, "triggered", False):
                continue

            entry = BehaviorMemoryEntry(
                timestamp=current_ts,
                rule_name=getattr(ev, "rule_id", "UNKNOWN"),
                violation_id=getattr(ev, "rule_name", "UNKNOWN"),
                severity=getattr(ev, "severity", "MEDIUM"),
                confidence=getattr(ev, "confidence", 1.0),
                duration=getattr(ev, "duration_seconds", 0.0),
                talking=talking,
                phone_present=phone_present,
                multiple_faces=(face_count > 1),
                risk_score=r_score
            )
            self.memory.add_entry(entry)

    def generate_session_summary(self, current_ts: float) -> BehaviorSessionSummary:
        detected_names = list(set([b.title for b in list(self.active_behaviors.values()) + self.resolved_behaviors]))

        all_confs = [b.confidence for b in list(self.active_behaviors.values()) + self.resolved_behaviors]
        avg_conf = float(sum(all_confs) / max(len(all_confs), 1)) if all_confs else 0.0

        overall_score = self.profile_manager.profile.behavior_score

        if overall_score < 30.0 and len(detected_names) == 0:
            assessment = "HIGH_INTEGRITY"
        elif overall_score < 65.0:
            assessment = "MODERATE_CONCERN"
        else:
            assessment = "COMPROMISED"

        return BehaviorSessionSummary(
            behavior_score=overall_score,
            highest_risk_state=self.profile_manager.profile.state,
            composite_behaviors_detected=detected_names,
            total_escalations=self.total_escalations_count,
            avg_confidence=round(avg_conf, 1),
            peak_confidence=round(self.peak_confidence, 1),
            longest_suspicious_period_sec=round(max([b.duration_seconds for b in list(self.active_behaviors.values()) + self.resolved_behaviors], default=0.0), 1),
            recovered_behaviors_count=len(self.resolved_behaviors),
            overall_integrity_assessment=assessment
        )
