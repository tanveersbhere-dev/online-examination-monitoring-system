import logging
import threading
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

from app.websocket.connection_manager import manager
from app.websocket.websocket_events import WSEvent, WSEventType
from app.schemas.ai_event import AIEventDTO
from app.services.ai_event_processor import AIEventProcessor

logger = logging.getLogger(__name__)

class AIEngineThread(threading.Thread):
    def __init__(self, exam_session_id: int, student_id: int, reference_embedding: list[float] = None):
        super().__init__(daemon=True)
        self.exam_session_id = exam_session_id
        self.student_id = student_id
        self.reference_embedding = reference_embedding
        self.running = False
        
        # We will hold references to the ai_engine components
        self.camera_manager = None
        self.event_bus = None
        self.context = None
        self.processors = []

    def run(self):
        self.running = True
        try:
            # Import ai_engine modules dynamically to avoid crashing the backend if missing
            from ai_engine.config.config import load_config
            from ai_engine.core.exam_context import ExamContext
            from ai_engine.events.event_bus import EventBus
            from ai_engine.camera.camera_manager import CameraManager
            from ai_engine.core.enums import ExamStatus
            
            config = load_config()
            self.context = ExamContext()
            
            with self.context.lock():
                sys_state = self.context.system_state
                sys_state.status = ExamStatus.IN_PROGRESS
                self.context.system_state = sys_state
                
                sess_info = self.context.session_info
                sess_info.exam_id = str(self.exam_session_id)
                sess_info.student_id = str(self.student_id)
                sess_info.start_time = time.time()
                self.context.session_info = sess_info
            
            self.event_bus = EventBus(async_dispatch=config.event_bus.async_dispatch, queue_size=config.event_bus.queue_size)
            
            # Setup bridge to Websocket and Event Processor
            def ws_bridge_callback(event):
                # Evidence Dumping
                if event.severity.name in ["HIGH", "CRITICAL"] and getattr(self.context, "current_frame", None) is not None:
                    try:
                        import os
                        import cv2
                        import uuid
                        from app.core.config import settings
                        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
                        filename = f"evidence_{uuid.uuid4().hex}.jpg"
                        frame_path = os.path.join(settings.UPLOAD_DIR, filename)
                        cv2.imwrite(frame_path, self.context.current_frame.original_frame)
                        
                        # Ensure payload is a dictionary and inject frame_path
                        if not isinstance(event.payload, dict):
                            event.payload = {}
                        event.payload["frame_path"] = frame_path
                    except Exception as e:
                        logger.error(f"Failed to dump evidence: {e}")

                dto = AIEventDTO(
                    event_type=event.event_type.name,
                    timestamp=event.timestamp,
                    exam_session_id=self.exam_session_id,
                    severity=event.severity.name,
                    source_module=event.source_module,
                    confidence=event.confidence,
                    payload=event.payload
                )
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.run_coroutine_threadsafe(AIEventProcessor.process_event(dto), loop)
                except Exception as e:
                    logger.error(f"Failed to bridge AI event to Processor: {e}")
            
            self.event_bus.subscribe(None, ws_bridge_callback)
            self.event_bus.start()
            
            # CameraManager dependency has been removed. Frames are ingested via the /frame endpoint.
            
            # Try to load and initialize processors
            try:
                from ai_engine.detectors import MediaPipeFaceDetector, FaceDetectionConfig
                from ai_engine.detectors import MediaPipeLandmarkDetector, LandmarkDetectionConfig
                from ai_engine.estimators import SolvePnPHeadPoseEstimator, HeadPoseConfig
                from ai_engine.features import (
                    MediaPipeEyeGazeExtractor, EyeGazeConfig,
                    TemporalFacePresenceProcessor, FacePresenceConfig,
                    EmbeddingIdentityProcessor, FaceIdentityConfig,
                    MediaPipeEARProcessor, EARConfig,
                    MediaPipeMARProcessor, MARConfig,
                    TemporalBlinkProcessor, BlinkDetectionConfig
                )
                from ai_engine.environment.object_detection.yolo_detector import YOLODetector
                from ai_engine.environment.object_detection.models import ObjectDetectionConfig

                # 1. Face Detection
                fd = MediaPipeFaceDetector(FaceDetectionConfig())
                fd.initialize()
                fd.start()
                self.processors.append(fd)
                
                # 2. Landmark Detection
                ld = MediaPipeLandmarkDetector(LandmarkDetectionConfig())
                ld.initialize()
                ld.start()
                self.processors.append(ld)
                
                # 3. Head Pose
                hp = SolvePnPHeadPoseEstimator(HeadPoseConfig())
                hp.initialize()
                hp.start()
                self.processors.append(hp)
                
                # 4. EAR
                ear = MediaPipeEARProcessor(EARConfig())
                ear.initialize()
                ear.start()
                self.processors.append(ear)

                # 5. MAR
                mar = MediaPipeMARProcessor(MARConfig())
                mar.initialize()
                mar.start()
                self.processors.append(mar)

                # 6. Blink
                blink = TemporalBlinkProcessor(BlinkDetectionConfig())
                blink.initialize()
                blink.start()
                self.processors.append(blink)

                # 7. Eye Gaze
                gaze = MediaPipeEyeGazeExtractor(EyeGazeConfig())
                gaze.initialize()
                gaze.start()
                self.processors.append(gaze)

                # 8. Face Identity
                id_proc = EmbeddingIdentityProcessor(FaceIdentityConfig())
                if self.reference_embedding:
                    import numpy as np
                    id_proc.update_reference_embedding(np.array(self.reference_embedding))
                id_proc.initialize()
                id_proc.start()
                self.processors.append(id_proc)

                # 9. Face Presence
                fp = TemporalFacePresenceProcessor(FacePresenceConfig())
                fp.initialize()
                fp.start()
                self.processors.append(fp)

                # 10. Object Detection (YOLO)
                od = YOLODetector(ObjectDetectionConfig())
                od.initialize()
                od.start()
                self.processors.append(od)

            except Exception as e:
                logger.warning(f"Could not init some AI processors: {e}")

            # Main loop
            self.last_frame = None
            while self.running:
                frame = self.context.current_frame
                
                if frame is not None and frame is not self.last_frame:
                    # Process frame through all available processors
                    for p in self.processors:
                        try:
                            p.process(self.context)
                        except Exception as e:
                            logger.error(f"Processor error: {e}")
                    self.last_frame = frame
                
                time.sleep(0.01)
                
        except Exception as e:
            logger.error(f"AIEngineThread crashed: {e}", exc_info=True)
        finally:
            self.cleanup()
            
    def stop(self):
        self.running = False
        
    def cleanup(self):
        for p in self.processors:
            try:
                p.stop()
                p.cleanup()
            except Exception:
                pass
        if self.event_bus:
            self.event_bus.stop()


class AISessionManager:
    """
    Adapter for AI Session orchestration.
    Triggers processes in the AI Engine subsystem.
    """
    _active_threads: Dict[int, AIEngineThread] = {}

    @classmethod
    def initialize_session(cls, exam_session_id: int, student_id: int, reference_embedding: list[float] = None):
        if exam_session_id in cls._active_threads:
            logger.warning(f"AI Session already initialized for exam_session {exam_session_id}")
            return
            
        logger.info(f"Initializing AI Session for exam_session {exam_session_id} (Student {student_id})")
        thread = AIEngineThread(exam_session_id=exam_session_id, student_id=student_id, reference_embedding=reference_embedding)
        cls._active_threads[exam_session_id] = thread

    @classmethod
    def start_session(cls, exam_session_id: int):
        if exam_session_id in cls._active_threads:
            thread = cls._active_threads[exam_session_id]
            if not thread.is_alive() and getattr(thread, '_started', False) and not thread._started.is_set():
                logger.info(f"Starting AI Session thread for ExamSession {exam_session_id}")
                thread.start()
            elif not getattr(thread, '_started', False) or not thread._started.is_set():
                logger.info(f"Starting AI Session thread for ExamSession {exam_session_id}")
                thread.start()
            else:
                logger.info(f"AI Session thread for ExamSession {exam_session_id} is already running.")
        else:
            logger.error(f"Cannot start unknown AI Session {exam_session_id}")
            # If not initialized, fallback to creating it with unknown student
            cls.initialize_session(exam_session_id, 0)
            cls.start_session(exam_session_id)
        
    @classmethod
    def pause_session(cls, exam_session_id: int):
        logger.info(f"AI Session paused for ExamSession {exam_session_id}")
        # Not fully supported by simple thread model yet
        
    @classmethod
    def resume_session(cls, exam_session_id: int):
        logger.info(f"AI Session resumed for ExamSession {exam_session_id}")
        
    @classmethod
    def stop_session(cls, exam_session_id: int):
        logger.info(f"Stopping AI Session for ExamSession {exam_session_id}")
        if exam_session_id in cls._active_threads:
            cls._active_threads[exam_session_id].stop()
            del cls._active_threads[exam_session_id]
