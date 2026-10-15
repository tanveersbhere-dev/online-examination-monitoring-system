"""
Temporal Confirmation Buffer for Object Validation & Reliability Layer.
Tracks object persistence, performs temporal majority voting across rolling frame history,
and disambiguates visually confusable object classes (e.g. Notebook/Book vs Laptop).
"""
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

from ai_engine.environment.object_validation.models import (
    ObjectValidationConfig, ClassValidationConfig, ValidationReason
)

logger = logging.getLogger("ai_engine.object_validation.temporal_buffer")


@dataclass
class TrackConfirmationState:
    track_key: str                      # String key (track_id or spatial key)
    object_type: str                    # Raw incoming object type
    first_seen_ts: float
    last_seen_ts: float
    consecutive_frames: int = 0
    missing_frames: int = 0
    max_confidence: float = 0.0
    is_confirmed: bool = False
    resolved_type: str = ""             # Majority-voted/smoothed class
    resolved_confidence: float = 0.0    # Smoothed confidence
    history: List[dict] = field(default_factory=list)  # Rolling history: [{"type": str, "conf": float, "ts": float, "bbox": Any}]
    camera_id: str = "camera_1"


class TemporalConfirmationBuffer:
    """
    Manages track state history, temporal confirmation criteria,
    and temporal majority voting to stabilize classifications.
    """
    def __init__(self, config: ObjectValidationConfig) -> None:
        self.config: ObjectValidationConfig = config
        self._tracks: Dict[str, TrackConfirmationState] = {}

    def update_and_evaluate(
        self,
        track_id: Optional[int],
        object_type: str,
        confidence: float,
        current_ts: float,
        bbox: Any = None,
        camera_id: str = "camera_1",
    ) -> Tuple[bool, int, float, ValidationReason]:
        """
        Updates tracking state with rolling history, applies temporal majority voting
        and geometric disambiguation, then evaluates confirmation criteria.

        Returns: (is_confirmed, consecutive_frames, tracking_seconds, reason)
        """
        # Key on track identity so cross-class predictions for the same physical object share history
        if track_id is not None and track_id >= 0:
            key = f"{camera_id}_trk_{track_id}"
        else:
            x_center = round(getattr(bbox, 'x', 0) / 50.0) if bbox else 0
            y_center = round(getattr(bbox, 'y', 0) / 50.0) if bbox else 0
            key = f"{camera_id}_sp_{x_center}_{y_center}"

        if key in self._tracks:
            state = self._tracks[key]
            state.consecutive_frames += 1
            state.missing_frames = 0
            state.last_seen_ts = current_ts
            state.max_confidence = max(state.max_confidence, confidence)
            state.object_type = object_type
        else:
            # Check if there is a recently confirmed track of the same or confusable type in buffer grace memory.
            # PERSON detections must strictly validate through their full temporal window (8 frames / 0.8s)
            # and never inherit instant confirmation from another person track or transient track.
            inherited_confirmed = False
            if object_type != "PERSON":
                for prev_key, prev_state in self._tracks.items():
                    if getattr(prev_state, "camera_id", "camera_1") == camera_id and (prev_state.object_type == object_type or prev_state.resolved_type == object_type) and prev_state.is_confirmed and prev_state.missing_frames > 0:
                        inherited_confirmed = True
                        break

            state = TrackConfirmationState(
                track_key=key,
                object_type=object_type,
                first_seen_ts=current_ts,
                last_seen_ts=current_ts,
                consecutive_frames=1,
                missing_frames=0,
                max_confidence=confidence,
                is_confirmed=inherited_confirmed,
                resolved_type=object_type,
                resolved_confidence=confidence,
                history=[],
                camera_id=camera_id,
            )
            self._tracks[key] = state

        # Append to rolling history window (e.g. last 10 frames)
        max_window = getattr(self.config, "majority_vote_window", 10)
        state.history.append({
            "type": object_type,
            "conf": confidence,
            "ts": current_ts,
            "bbox": bbox
        })
        if len(state.history) > max_window:
            state.history = state.history[-max_window:]

        # ── Temporal Majority Voting & Smoothing ───────────────────────
        smoothed_type, smoothed_conf = self._compute_majority_vote(state, bbox)
        state.resolved_type = smoothed_type
        state.resolved_confidence = smoothed_conf

        tracking_duration = current_ts - state.first_seen_ts
        class_cfg = self.config.class_configs.get(smoothed_type, self.config.default_config)

        # Check confirmation criteria: consecutive frames, tracking duration, or grace memory
        frames_ok = state.consecutive_frames >= class_cfg.min_consecutive_frames or state.is_confirmed
        duration_ok = (class_cfg.min_tracking_seconds > 0.0) and (tracking_duration >= class_cfg.min_tracking_seconds)

        if frames_ok or duration_ok:
            state.is_confirmed = True
            return True, state.consecutive_frames, tracking_duration, ValidationReason.ACCEPTED_CONFIRMED
        else:
            return False, state.consecutive_frames, tracking_duration, ValidationReason.REJECTED_TEMPORAL_UNCONFIRMED

    def _compute_majority_vote(self, state: TrackConfirmationState, bbox: Any) -> Tuple[str, float]:
        """
        Calculates confidence-weighted majority vote across rolling track history
        and applies geometric heuristics (aspect ratio, desk placement) to disambiguate
        notebooks/registers from upright laptops.
        """
        if not state.history:
            return state.object_type, state.max_confidence

        votes: Dict[str, int] = {}
        weighted_conf: Dict[str, float] = {}

        for entry in state.history:
            t = entry["type"]
            c = entry["conf"]
            votes[t] = votes.get(t, 0) + 1
            weighted_conf[t] = weighted_conf.get(t, 0.0) + c

        total_frames = len(state.history)
        avg_confs = {t: weighted_conf[t] / max(1, votes[t]) for t in votes}

        # ── Conservative Disambiguation: Book / Register / Notebook / Material vs Laptop ─────
        paper_types = ("BOOK", "NOTEBOOK", "REGISTER", "PAPER", "UNAUTHORIZED_MATERIAL")
        paper_vote_count = sum(votes.get(k, 0) for k in paper_types)
        laptop_votes = votes.get("LAPTOP", 0)
        has_paper_votes = paper_vote_count > 0

        laptop_conf = avg_confs.get("LAPTOP", 0.0)
        laptop_min_conf = self.config.class_configs.get("LAPTOP", ClassValidationConfig(min_confidence=0.45)).min_confidence
        paper_conf = max([avg_confs.get(k, 0.0) for k in paper_types] or [0.0])

        if laptop_votes > 0 and has_paper_votes:
            # Conservative, evidence-based disambiguation:
            # 1. If laptop has the majority of votes and meets minimum confidence, keep LAPTOP.
            #    A wide or horizontal bounding box, low vertical position, or transient material votes
            #    must not override a valid, dominant laptop prediction.
            if laptop_votes > paper_vote_count and laptop_conf >= laptop_min_conf:
                return "LAPTOP", laptop_conf

            # 2. If paper/material has the majority of votes, or laptop confidence is below minimum:
            #    resolve to the dominant material candidate based on weighted confidence.
            paper_dominant = (paper_vote_count > laptop_votes) or (laptop_conf < laptop_min_conf)

            # 3. In case of tied votes: if laptop confidence exceeds paper confidence, keep LAPTOP.
            if not paper_dominant:
                if laptop_conf >= laptop_min_conf and (laptop_conf - paper_conf) >= 0.05:
                    return "LAPTOP", laptop_conf
                paper_dominant = True

            if paper_dominant:
                material_candidates = [k for k in paper_types if k in votes]
                if material_candidates:
                    best_mat = max(material_candidates, key=lambda k: weighted_conf.get(k, 0.0))
                    return best_mat, avg_confs.get(best_mat, paper_conf)
                return "UNAUTHORIZED_MATERIAL", paper_conf

        # Standard weighted vote resolution
        best_type = max(weighted_conf.keys(), key=lambda k: weighted_conf[k])
        return best_type, avg_confs[best_type]

    def _find_track_state(self, track_key: str):
        if track_key in self._tracks:
            return self._tracks[track_key]
        for k, v in self._tracks.items():
            if k == track_key or k.endswith(f"_{track_key}"):
                return v
        return None

    def get_resolved_type(self, track_key: str, default: str) -> str:
        """Returns smoothed object type for a track."""
        state = self._find_track_state(track_key)
        if state and state.resolved_type:
            return state.resolved_type
        return default

    def get_resolved_confidence(self, track_key: str, default: float) -> float:
        """Returns smoothed confidence for a track."""
        state = self._find_track_state(track_key)
        if state and state.resolved_confidence > 0.0:
            return state.resolved_confidence
        return default

    def age_missing_tracks(self, active_keys_seen: set, current_camera_id: Optional[str] = None) -> None:
        """
        Increments missing frame counts for un-seen tracks and purges expired tracks.
        Unconfirmed transient noise glitches expire quickly (5 frames), while confirmed
        object tracks persist up to max_missing_frames_to_expire for smooth re-appearance.
        Only ages tracks belonging to current_camera_id so Camera 1 frames never expire
        Camera 2 tracks, and vice versa.
        """
        expired_keys = []
        for key, state in self._tracks.items():
            track_cam = getattr(state, "camera_id", None)
            if current_camera_id is not None and track_cam is not None and track_cam != current_camera_id:
                # Do not age tracks belonging to a different camera!
                continue
            if key not in active_keys_seen:
                state.missing_frames += 1
                # Tolerant temporal streak preservation for intermittent misses:
                # Camera 2 is throttled at ~2.8 FPS, allow up to 2 missed frames before streak reset.
                # Camera 1 (30 FPS) allows 1 missed frame tolerance.
                max_missed_streak_tolerance = 2 if (track_cam == "camera_2" or current_camera_id == "camera_2") else 1
                if not state.is_confirmed:
                    if state.missing_frames > max_missed_streak_tolerance:
                        state.consecutive_frames = 0
                    if state.missing_frames > 5:
                        expired_keys.append(key)
                else:
                    if state.missing_frames > self.config.max_missing_frames_to_expire:
                        expired_keys.append(key)

        for key in expired_keys:
            del self._tracks[key]

    def clear_camera(self, camera_id: str) -> None:
        """Purges all track confirmation states for a specific camera (e.g. on disconnect)."""
        expired_keys = [k for k, state in self._tracks.items() if getattr(state, "camera_id", None) == camera_id]
        for k in expired_keys:
            del self._tracks[k]

    def clear(self) -> None:
        self._tracks.clear()

    @property
    def active_track_count(self) -> int:
        return len(self._tracks)

