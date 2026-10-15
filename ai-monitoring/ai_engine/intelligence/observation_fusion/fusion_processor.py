"""Observation Fusion Processor implementation."""
import time
import logging
from typing import Optional, List, Any

from ai_engine.core.exam_context import ExamContext
from ai_engine.core.enums import DetectedObjectType
from ai_engine.intelligence.observation_fusion.processor import ObservationFusionProcessorInterface
from ai_engine.intelligence.observation_fusion.models import (
    ObservationFusionConfig,
    UnifiedObservation,
    FaceObservation,
    EnvironmentObservation,
    AudioObservation,
    ObservationConfidenceSummary
)
from ai_engine.intelligence.observation_fusion.exceptions import (
    ObservationFusionError,
    MissingObservationError,
    InvalidObservationError
)

logger = logging.getLogger(__name__)

class FusionProcessor(ObservationFusionProcessorInterface):
    """
    Collects outputs from completed AI subsystems and normalizes them into a common structure.
    """
    
    def __init__(self, config: ObservationFusionConfig) -> None:
        super().__init__(config)
        self._initialized = False

    def initialize(self) -> None:
        if self._config.enable_logging:
            logger.debug("Initializing FusionProcessor...")
        self._initialized = True

    def start(self) -> None:
        if not self._initialized:
            raise ObservationFusionError("Cannot start uninitialized FusionProcessor.")
        if self._config.enable_logging:
            logger.debug("FusionProcessor started.")

    def stop(self) -> None:
        if self._config.enable_logging:
            logger.debug("FusionProcessor stopped.")

    def cleanup(self) -> None:
        if self._config.enable_logging:
            logger.debug("Cleaning up FusionProcessor...")
        self._initialized = False

    def process(self, context: ExamContext) -> None:
        if not self._initialized:
            raise ObservationFusionError("FusionProcessor is not initialized.")
            
        start_time = time.perf_counter()
        
        face_obs = None
        env_obs = None
        audio_obs = None
        
        face_conf = 0.0
        env_conf = 0.0
        audio_conf = 0.0
        
        try:
            # 1. Process Face Subsystem
            if self._config.enable_face:
                if not hasattr(context, "face_info") or context.face_info is None:
                    raise MissingObservationError("face_info is missing from ExamContext but enable_face is True.")
                    
                face_obs = self._extract_face_observation(context)
                face_conf = face_obs.face_confidence if face_obs else 0.0
                
            # 2. Process Environment Subsystem
            if self._config.enable_environment:
                if not hasattr(context, "object_info") or context.object_info is None:
                    raise MissingObservationError("object_info is missing from ExamContext but enable_environment is True.")
                    
                env_obs, env_conf = self._extract_environment_observation(context)
                
            # 3. Process Audio Subsystem (Optional)
            if self._config.enable_audio:
                if hasattr(context, "audio_info") and context.audio_info is not None:
                    audio_obs = self._extract_audio_observation(context)
                    audio_conf = 1.0
                else:
                    if self._config.enable_logging:
                        logger.warning("audio_info is missing but enable_audio is True. Proceeding without audio.")
                        
            # Aggregate Confidence
            conf_summary = self._calculate_confidence_summary(face_conf, env_conf, audio_conf)
            
            # Construct Unified Observation
            unified_obs = UnifiedObservation(
                timestamp=time.time(),
                face=face_obs,
                environment=env_obs,
                audio=audio_obs,
                confidence_summary=conf_summary,
                identity_protection=getattr(context, "identity_protection_observation", None),
                calibration=getattr(context, "calibration_info", None)
            )
            
            # Dynamically attach to context without breaking frozen schema
            setattr(context, "observation", unified_obs)
            
            if self._config.enable_logging:
                proc_time = (time.perf_counter() - start_time) * 1000
                logger.debug(f"Fusion completed in {proc_time:.2f}ms. Overall Confidence: {conf_summary.overall_confidence:.2f}")
                
        except Exception as e:
            if isinstance(e, ObservationFusionError):
                raise
            raise InvalidObservationError(f"Failed to process observation fusion: {e}") from e

    def _extract_face_observation(self, context: ExamContext) -> FaceObservation:
        try:
            curr_frame = getattr(context, "current_frame", None)
            cam_id = str(getattr(curr_frame, "camera_id", "camera_1") or "camera_1")
            if cam_id == "camera_2":
                # Camera 2 is a side/rear view without face processing. Return neutral observation.
                return FaceObservation(
                    face_present=True,
                    face_count=1,
                    presence_state="PRESENT",
                    face_confidence=1.0,
                    identity_consistent=True,
                    identity_confidence=1.0,
                    gaze_state="ON_SCREEN",
                    gaze_confidence=1.0,
                    head_pose_state="FORWARD",
                    is_talking=False,
                    blink_state="UNKNOWN",
                    behavioral_summary={}
                )

            f_info = context.face_info
            
            # Default values
            gaze_state = "UNKNOWN"
            gaze_conf = 0.0
            gx, gy = 0.0, 0.0
            if hasattr(context, "eye_info") and context.eye_info:
                gaze_conf = getattr(context.eye_info, "gaze_confidence", 0.0)
                if context.eye_info.blink_detected:
                    gaze_state = "BLINKING"
                elif gaze_conf < 0.40:
                    # Low landmark confidence: mark UNKNOWN rather than guessing off-screen
                    gaze_state = "UNKNOWN"
                else:
                    gaze_state = "ON_SCREEN"
                    # Check combined gaze vector (or fallback to gaze_left/gaze_right)
                    cg = getattr(context.eye_info, "combined_gaze", None)
                    if not cg or cg == (0.0, 0.0, 0.0):
                        cg = getattr(context.eye_info, "gaze_left", (0.0, 0.0, 0.0))
                    if isinstance(cg, (tuple, list)) and len(cg) >= 2:
                        gx, gy = cg[0], cg[1]
                        if gx < -0.40:
                            gaze_state = "LEFT"
                        elif gx > 0.40:
                            gaze_state = "RIGHT"
                        elif gy > 0.35:
                            gaze_state = "DOWN"
                    
            head_pose = "FORWARD"
            yaw, pitch, roll = 0.0, 0.0, 0.0
            hp_success = True
            if hasattr(context, "head_pose_info") and context.head_pose_info:
                hpi = context.head_pose_info
                hp_success = getattr(hpi, "success", True)
                raw_pose = getattr(hpi, "pose_class", None)
                if raw_pose and raw_pose != "FORWARD":
                    head_pose = raw_pose
                elif not hp_success:
                    head_pose = "UNKNOWN"
                else:
                    yaw = getattr(hpi, "yaw", 0.0)
                    pitch = getattr(hpi, "pitch", 0.0)
                    roll = getattr(hpi, "roll", 0.0)
                    if yaw > 20.0:
                        head_pose = "RIGHT"
                    elif yaw < -20.0:
                        head_pose = "LEFT"
                    elif pitch < -20.0:
                        head_pose = "DOWN"
                    else:
                        head_pose = "FORWARD"
                
            is_talking = False
            if hasattr(context, "mouth_info") and context.mouth_info:
                is_talking = context.mouth_info.is_talking
                
            behavior = {
                "head_yaw": yaw,
                "head_pitch": pitch,
                "head_roll": roll,
                "gaze_x": gx,
                "gaze_y": gy,
                "head_pose_success": hp_success,
            }
            if hasattr(context, "behavior_history") and context.behavior_history:
                behavior["last_updated"] = context.behavior_history.last_updated
                
            return FaceObservation(
                face_present=f_info.face_detected or f_info.face_count > 0,
                face_count=getattr(f_info, "face_count", 1),
                presence_state=getattr(f_info, "presence_state", "PRESENT"),
                face_confidence=f_info.confidence,
                identity_consistent=f_info.identity_consistent,
                identity_confidence=f_info.identity_confidence,
                gaze_state=gaze_state,
                gaze_confidence=gaze_conf,
                head_pose_state=head_pose,
                is_talking=is_talking,
                blink_state=getattr(context.eye_info, "eye_state", "UNKNOWN") if hasattr(context, "eye_info") else "UNKNOWN",
                behavioral_summary=behavior
            )
        except Exception as e:
            raise InvalidObservationError(f"Error parsing face observation: {e}") from e
            
    def _extract_environment_observation(self, context: ExamContext) -> tuple[EnvironmentObservation, float]:
        try:
            o_info = context.object_info
            
            total_persons = 0
            phone_present = False
            book_present = False
            register_present = False
            laptop_present = False
            earphone_present = False
            earbuds_present = False
            neckband_present = False
            smartwatch_present = False
            
            summary_list = []
            avg_conf = 0.0
            
            # Resolve detection sources in priority order:
            # 1. validated_objects, 2. tracked_objects, 3. filtered_detections, 4. detected_objects, 5. current_detections
            raw_validated = getattr(o_info, "validated_objects", None)
            raw_tracked = getattr(o_info, "tracked_objects", None)
            raw_filtered = getattr(o_info, "filtered_detections", None)
            raw_detected = getattr(o_info, "detected_objects", None)
            raw_current = getattr(o_info, "current_detections", None)

            source_name = "NONE"
            if isinstance(raw_validated, list) and len(raw_validated) > 0:
                items_to_process = raw_validated
                source_name = "validated_objects (non-empty)"
            elif isinstance(raw_tracked, list) and len(raw_tracked) > 0:
                items_to_process = raw_tracked
                source_name = "tracked_objects (non-empty)"
            elif hasattr(raw_tracked, "tracked_objects") and isinstance(raw_tracked.tracked_objects, list) and len(raw_tracked.tracked_objects) > 0:
                items_to_process = raw_tracked.tracked_objects
                source_name = "tracked_objects.tracked_objects (non-empty)"
            elif isinstance(raw_filtered, list) and len(raw_filtered) > 0:
                items_to_process = raw_filtered
                source_name = "filtered_detections (non-empty)"
            elif isinstance(raw_detected, list) and len(raw_detected) > 0:
                items_to_process = raw_detected
                source_name = "detected_objects (non-empty)"
            elif isinstance(raw_current, list) and len(raw_current) > 0:
                items_to_process = raw_current
                source_name = "current_detections (non-empty)"
            elif isinstance(raw_tracked, list):
                items_to_process = raw_tracked
                source_name = "tracked_objects (empty list)"
            elif isinstance(raw_filtered, list):
                items_to_process = raw_filtered
                source_name = "filtered_detections (empty list)"
            elif isinstance(raw_detected, list):
                items_to_process = raw_detected
                source_name = "detected_objects (empty list)"
            elif isinstance(raw_current, list):
                items_to_process = raw_current
                source_name = "current_detections (empty list)"
            else:
                items_to_process = []
                source_name = "NONE (empty fallback)"

            # TEMPORARY DEBUG TRACE - STAGE 3
            logger.info(f"[STAGE 3 - FUSION] Selected source='{source_name}' count={len(items_to_process)}")
            for idx, item in enumerate(items_to_process):
                st = getattr(item, "current_state", "TRACKED")
                ot = getattr(item, "object_type", None)
                ot_name = getattr(ot, "name", str(ot))
                logger.info(f"  [FUSION IN] idx={idx} type_class={type(item)} obj_type={ot} enum_name={ot_name} state={st}")

            person_items = []
            for idx, item in enumerate(items_to_process):
                # Handles both TrackedObject and DetectedObject
                state = getattr(item, "current_state", "TRACKED")
                if state in ["NEW", "TRACKED", "DETECTED"]:
                    obj_type = item.object_type
                    ot_str = getattr(obj_type, "name", str(obj_type)).upper()
                    if obj_type == DetectedObjectType.PERSON or ot_str == "PERSON":
                        person_items.append(item)
                    elif obj_type == DetectedObjectType.CELL_PHONE or ot_str in ("CELL_PHONE", "PHONE"):
                        phone_present = True
                    elif obj_type in [DetectedObjectType.BOOK, DetectedObjectType.NOTEBOOK, DetectedObjectType.PAPER, DetectedObjectType.REGISTER, DetectedObjectType.UNAUTHORIZED_MATERIAL] or any(
                        m in ot_str for m in ("BOOK", "NOTEBOOK", "REGISTER", "PAPER", "PAGE", "DIARY", "JOURNAL", "TEXTBOOK", "PAD", "UNAUTHORIZED_MATERIAL", "MATERIAL")
                    ):
                        book_present = True
                        if obj_type == DetectedObjectType.REGISTER or "REGISTER" in ot_str:
                            register_present = True
                    elif obj_type in [DetectedObjectType.COMM_EARPHONES, DetectedObjectType.EARBUDS, DetectedObjectType.HEADPHONES, DetectedObjectType.HEADSET, DetectedObjectType.NECKBAND] or any(
                        e in ot_str for e in ("EARPHONE", "EARBUDS", "HEADPHONE", "NECKBAND")
                    ):
                        earphone_present = True
                        earbuds_present = True
                        neckband_present = True
                    elif obj_type == DetectedObjectType.SMARTWATCH or "SMARTWATCH" in ot_str:
                        smartwatch_present = True
                    elif obj_type == DetectedObjectType.LAPTOP or ot_str == "LAPTOP":
                        laptop_present = True
                        
                    summary_list.append({
                        "id": getattr(item, "tracking_id", idx + 1),
                        "type": obj_type.name if hasattr(obj_type, 'name') else str(obj_type),
                        "conf": item.confidence,
                        "state": state
                    })
                    avg_conf += item.confidence

            # Compute physical person count with deduplication and arm-sliver suppression
            total_persons = self._count_physical_persons(person_items, context)
            # Check dedicated audio device branch
            audio_dev = getattr(context, "audio_device_info", None)
            if audio_dev and getattr(audio_dev, "detected", False):
                earphone_present = True
                earbuds_present = True
                neckband_present = True
                dev_conf = float(getattr(audio_dev, "confidence", 0.90))
                dev_side = getattr(audio_dev, "side", "NONE")
                summary_list.append({
                    "id": 999,
                    "type": "COMM_EARPHONES",
                    "conf": dev_conf,
                    "state": "TRACKED",
                    "side": dev_side,
                })
                avg_conf += dev_conf

            # TEMPORARY DEBUG TRACE - STAGE 4 & 5
            logger.info(f"[STAGE 4 & 5 - ENV OBS] phone_present={phone_present} book_present={book_present} register_present={register_present} laptop_present={laptop_present} earbuds_present={earbuds_present} neckband_present={neckband_present} total_persons={total_persons} summary_list_len={len(summary_list)}")
                    
            active_objects = len(summary_list)
            if active_objects > 0:
                avg_conf /= active_objects
                
            if hasattr(context, "environment_history"):
                hist = context.environment_history
                total_persons = hist.statistics.person_count_history.get(1, total_persons)
                
            obs = EnvironmentObservation(
                active_objects=active_objects,
                total_persons=total_persons,
                phone_present=phone_present,
                book_present=book_present,
                earphone_present=earphone_present,
                earbuds_present=earbuds_present,
                neckband_present=neckband_present,
                register_present=register_present,
                laptop_present=laptop_present,
                smartwatch_present=smartwatch_present,
                tracked_entities_summary=summary_list
            )
            return obs, avg_conf
            
        except Exception as e:
            raise InvalidObservationError(f"Error parsing environment observation: {e}") from e

    def _extract_audio_observation(self, context: ExamContext) -> AudioObservation:
        try:
            a_info = context.audio_info
            return AudioObservation(
                is_speaking=a_info.is_speaking,
                decibel_level=a_info.db_level,
                noise_level=a_info.noise_level
            )
        except Exception as e:
            raise InvalidObservationError(f"Error parsing audio observation: {e}") from e

    def _calculate_confidence_summary(self, face: float, env: float, audio: float) -> ObservationConfidenceSummary:
        # Simple weighted average for overall confidence. 
        # Modalities that are disabled or absent will provide 0.0 which will lower the overall score.
        # However, to be fair, we should only average over enabled modalities.
        active_modalities = 0
        total = 0.0
        
        if self._config.enable_face:
            active_modalities += 1
            total += face
            
        if self._config.enable_environment:
            active_modalities += 1
            total += env
            
        if self._config.enable_audio:
            active_modalities += 1
            total += audio
            
        overall = total / active_modalities if active_modalities > 0 else 0.0
        
        return ObservationConfidenceSummary(
            face_confidence=face,
            environment_confidence=env,
            audio_confidence=audio,
            overall_confidence=overall
        )

    def _count_physical_persons(self, person_items: List[Any], context: ExamContext) -> int:
        """
        Determines the count of physically distinct persons among candidate detections,
        suppressing nested multi-scale duplicates and subordinate arm/hand slivers.
        """
        if not person_items:
            return 0
        if len(person_items) == 1:
            return 1

        # Retrieve face bounding boxes from context if available
        face_info = getattr(context, "face_info", None)
        face_bboxes = []
        if face_info:
            all_b = getattr(face_info, "all_bboxes", None)
            if all_b and isinstance(all_b, list):
                face_bboxes.extend(all_b)
            elif getattr(face_info, "bbox", None):
                face_bboxes.append(face_info.bbox)

        def _get_bbox(item):
            bb = getattr(item, "bbox", None)
            if bb is None:
                return None
            if hasattr(bb, "x"):
                return (float(bb.x), float(bb.y), float(bb.width), float(bb.height))
            elif isinstance(bb, (list, tuple)) and len(bb) >= 4:
                return (float(bb[0]), float(bb[1]), float(bb[2]), float(bb[3]))
            return None

        def _has_face(p_box):
            if not p_box or not face_bboxes:
                return False
            px, py, pw, ph = p_box
            for fb in face_bboxes:
                if isinstance(fb, (list, tuple)) and len(fb) >= 4:
                    fx, fy, fw, fh = fb[0], fb[1], fb[2], fb[3]
                elif hasattr(fb, "x"):
                    fx, fy, fw, fh = fb.x, fb.y, fb.width, fb.height
                else:
                    continue
                fcx, fcy = fx + fw / 2.0, fy + fh / 2.0
                if (px <= fcx <= px + pw) and (py <= fcy <= py + ph):
                    return True
            return False

        def _ios(boxA, boxB):
            xA = max(boxA[0], boxB[0])
            yA = max(boxA[1], boxB[1])
            xB = min(boxA[0] + boxA[2], boxB[0] + boxB[2])
            yB = min(boxA[1] + boxA[3], boxB[1] + boxB[3])
            inter = max(0.0, xB - xA) * max(0.0, yB - yA)
            if inter == 0.0:
                return 0.0
            areaA = boxA[2] * boxA[3]
            areaB = boxB[2] * boxB[3]
            min_area = min(areaA, areaB)
            return (inter / min_area) if min_area > 0 else 0.0

        # Sort candidate items by box area descending (so primary body is considered first)
        boxes_with_items = []
        for it in person_items:
            b = _get_bbox(it)
            area = (b[2] * b[3]) if b else 0.0
            boxes_with_items.append((area, b, it))
        boxes_with_items.sort(key=lambda x: x[0], reverse=True)

        accepted_boxes = []
        for area, b, it in boxes_with_items:
            if not b or area <= 0.0:
                accepted_boxes.append((area, b, it))
                continue

            # Check 1: Nested / Subsumed duplicate check against already accepted persons
            is_subsumed = False
            for acc_area, acc_b, acc_it in accepted_boxes:
                if acc_b and _ios(b, acc_b) > 0.50:
                    is_subsumed = True
                    break
            if is_subsumed:
                logger.debug(f"[ObservationFusion] Suppressed subsumed duplicate person box {b}")
                continue

            # Check 2: Subordinate arm/hand sliver check
            # If an established primary student body is already accepted (large torso):
            if accepted_boxes:
                primary_area, primary_b, _ = accepted_boxes[0]
                if primary_b and primary_area >= 40000.0:
                    area_ratio = area / primary_area
                    has_associated_face = _has_face(b)
                    # Arm/extremity: small relative area (< 20%), no face, and narrow sliver or desk-height
                    if not has_associated_face and area_ratio < 0.20 and (b[2] < 220.0 or b[3] < 320.0):
                        logger.debug(
                            f"[ObservationFusion] Suppressed subordinate arm/extremity detection {b} "
                            f"(area_ratio={area_ratio:.2f}, no face)"
                        )
                        continue

            accepted_boxes.append((area, b, it))

        return len(accepted_boxes)

