"""Observation Fusion Processor implementation."""
import time
import logging
from typing import Optional

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
                if not hasattr(context, "face_info"):
                    raise MissingObservationError("face_info is missing from ExamContext but enable_face is True.")
                    
                face_obs = self._extract_face_observation(context)
                face_conf = face_obs.face_confidence if face_obs else 0.0
                
            # 2. Process Environment Subsystem
            if self._config.enable_environment:
                if not hasattr(context, "object_info"):
                    raise MissingObservationError("object_info is missing from ExamContext but enable_environment is True.")
                    
                env_obs, env_conf = self._extract_environment_observation(context)
                
            # 3. Process Audio Subsystem (Optional)
            if self._config.enable_audio:
                if hasattr(context, "audio_info"):
                    audio_obs = self._extract_audio_observation(context)
                    # For audio, confidence might be binary or based on noise floor, default to 1.0 if present
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
                confidence_summary=conf_summary
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
            f_info = context.face_info
            
            # Default values
            gaze_state = "UNKNOWN"
            gaze_conf = 0.0
            if hasattr(context, "eye_info") and context.eye_info:
                gaze_conf = context.eye_info.gaze_confidence
                # Simple heuristic since gaze_state might not be explicitly enum'd as a single string
                # We'll rely on the blink state or look away logic
                if context.eye_info.blink_detected:
                    gaze_state = "BLINKING"
                else:
                    gaze_state = "OPEN"
                    
            head_pose = "UNKNOWN"
            if hasattr(context, "head_pose_info") and context.head_pose_info:
                head_pose = context.head_pose_info.pose_class
                
            is_talking = False
            if hasattr(context, "mouth_info") and context.mouth_info:
                is_talking = context.mouth_info.is_talking
                
            behavior = {}
            if hasattr(context, "behavior_history") and context.behavior_history:
                # Basic dump of history keys if needed
                behavior = {"last_updated": context.behavior_history.last_updated}
                
            return FaceObservation(
                face_present=f_info.face_detected,
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
            earphone_present = False
            smartwatch_present = False
            
            summary_list = []
            avg_conf = 0.0
            
            for track in o_info.tracked_objects:
                if track.current_state in ["NEW", "TRACKED"]:
                    if track.object_type == DetectedObjectType.PERSON:
                        total_persons += 1
                    elif track.object_type == DetectedObjectType.CELL_PHONE:
                        phone_present = True
                    elif track.object_type == DetectedObjectType.BOOK:
                        book_present = True
                    elif track.object_type == DetectedObjectType.EARPHONE:
                        earphone_present = True
                    elif track.object_type == DetectedObjectType.SMARTWATCH:
                        smartwatch_present = True
                        
                    summary_list.append({
                        "id": track.tracking_id,
                        "type": track.object_type.name,
                        "conf": track.confidence,
                        "state": track.current_state
                    })
                    avg_conf += track.confidence
                    
            active_objects = len(summary_list)
            if active_objects > 0:
                avg_conf /= active_objects
                
            # If environment_history is available, pull from it
            if hasattr(context, "environment_history"):
                hist = context.environment_history
                total_persons = hist.statistics.person_count_history.get(1, total_persons)
                
            obs = EnvironmentObservation(
                active_objects=active_objects,
                total_persons=total_persons,
                phone_present=phone_present,
                book_present=book_present,
                earphone_present=earphone_present,
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
