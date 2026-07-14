import logging
import threading
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

from app.websocket.connection_manager import manager
from app.websocket.websocket_events import WSEvent, WSEventType

logger = logging.getLogger(__name__)

class AIEngineThread(threading.Thread):
    def __init__(self, exam_id: int, student_id: int, reference_embedding: list[float] = None):
        super().__init__(daemon=True)
        self.exam_id = exam_id
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
                sess_info.exam_id = str(self.exam_id)
                sess_info.student_id = str(self.student_id)
                sess_info.start_time = time.time()
                self.context.session_info = sess_info
            
            self.event_bus = EventBus(async_dispatch=config.event_bus.async_dispatch, queue_size=config.event_bus.queue_size)
            
            # Setup bridge to Websocket
            def ws_bridge_callback(event):
                ws_event = WSEvent(
                    event=event.event_type.name,
                    timestamp=datetime.fromtimestamp(event.timestamp),
                    exam_session_id=self.exam_id,
                    payload={
                        "severity": event.severity.name,
                        "source": event.source_module,
                        "confidence": event.confidence,
                        "description": event.payload.get("description", ""),
                        "data": {k: v for k, v in event.payload.items() if k != "description"}
                    }
                )
                try:
                    # Best-effort broadcast
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.run_coroutine_threadsafe(manager.broadcast(ws_event), loop)
                except Exception as e:
                    logger.error(f"Failed to bridge AI event to WS: {e}")
            
            self.event_bus.subscribe(None, ws_bridge_callback)
            self.event_bus.start()
            
            self.camera_manager = CameraManager(
                camera_id=config.camera.camera_id,
                width=config.camera.width,
                height=config.camera.height,
                fps=config.camera.fps,
                exam_context=self.context
            )
            self.camera_manager.initialize()
            self.camera_manager.start()
            
            # Try to load and initialize processors
            try:
                from ai_engine.detectors.face_detection.mediapipe_detector import MediaPipeFaceDetector
                from ai_engine.detectors.face_detection.models import FaceDetectionConfig
                fd = MediaPipeFaceDetector(FaceDetectionConfig())
                fd.initialize()
                fd.start()
                self.processors.append(fd)
            except Exception as e:
                logger.warning(f"Could not init FaceDetector: {e}")
                
            try:
                from ai_engine.features.face_identity.embedding_processor import EmbeddingIdentityProcessor
                from ai_engine.features.face_identity.models import FaceIdentityConfig
                id_proc = EmbeddingIdentityProcessor(FaceIdentityConfig())
                id_proc.initialize()
                id_proc.start()
                self.processors.append(id_proc)
            except Exception as e:
                logger.warning(f"Could not init IdentityProcessor: {e}")
                
            try:
                from ai_engine.environment.object_detection.yolo_detector import YOLODetector
                from ai_engine.environment.object_detection.models import ObjectDetectionConfig
                od = YOLODetector(ObjectDetectionConfig())
                od.initialize()
                od.start()
                self.processors.append(od)
            except Exception as e:
                logger.warning(f"Could not init ObjectDetector: {e}")

            # Main loop
            while self.running:
                self.camera_manager.process(self.context)
                frame = self.camera_manager.get_frame(timeout=0.1)
                
                if frame is not None:
                    # Process frame through all available processors
                    for p in self.processors:
                        try:
                            p.process(self.context)
                        except Exception as e:
                            logger.error(f"Processor error: {e}")
                
                time.sleep(0.01)
                
        except Exception as e:
            logger.error(f"AIEngineThread crashed: {e}", exc_info=True)
        finally:
            self.cleanup()
            
    def stop(self):
        self.running = False
        
    def cleanup(self):
        if self.camera_manager:
            self.camera_manager.stop()
            self.camera_manager.cleanup()
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
    def initialize_session(cls, exam_id: int, student_id: int, reference_embedding: list[float] = None):
        if exam_id in cls._active_threads:
            logger.warning(f"AI Session already initialized for exam {exam_id}")
            return
            
        logger.info(f"Initializing AI Session for exam {exam_id} (Student {student_id})")
        thread = AIEngineThread(exam_id=exam_id, student_id=student_id, reference_embedding=reference_embedding)
        cls._active_threads[exam_id] = thread

    @classmethod
    def start_session(cls, exam_id: int):
        if exam_id in cls._active_threads:
            logger.info(f"Starting AI Session thread for Exam {exam_id}")
            cls._active_threads[exam_id].start()
        else:
            logger.error(f"Cannot start unknown AI Session {exam_id}")
            # If not initialized, fallback to creating it with unknown student
            cls.initialize_session(exam_id, 0)
            cls.start_session(exam_id)
        
    @classmethod
    def pause_session(cls, exam_id: int):
        logger.info(f"AI Session paused for Exam {exam_id}")
        # Not fully supported by simple thread model yet
        
    @classmethod
    def resume_session(cls, exam_id: int):
        logger.info(f"AI Session resumed for Exam {exam_id}")
        
    @classmethod
    def stop_session(cls, exam_id: int):
        logger.info(f"Stopping AI Session for Exam {exam_id}")
        if exam_id in cls._active_threads:
            cls._active_threads[exam_id].stop()
            del cls._active_threads[exam_id]
