import time
import signal
import logging
from pathlib import Path

from ai_engine.config.config import load_config
from ai_engine.utils.logger import setup_logging
from ai_engine.core.exam_context import ExamContext
from ai_engine.core.enums import ExamStatus
from ai_engine.events.event_bus import EventBus
from ai_engine.camera.camera_manager import CameraManager
from ai_engine.events.event import Event

logger = logging.getLogger("ai_engine.system")

def handle_event(event: Event) -> None:
    """Logs dispatched event information to the events logger."""
    event_logger = logging.getLogger("ai_engine.events")
    event_logger.info(
        f"Event Dispatched: ID={event.event_id} | Type={event.event_type.name} | "
        f"Severity={event.severity.name} | Source={event.source_module} | "
        f"Confidence={event.confidence:.2f} | FrameID={event.frame_id}"
    )

def main() -> None:
    # 1. Load System Configuration
    config = load_config()

    # 2. Configure Rotating File and Stream Loggers
    setup_logging(
        log_dir=config.logging.log_dir,
        max_bytes=config.logging.max_bytes,
        backup_count=config.logging.backup_count,
        level=config.logging.level
    )

    logger.info("Initializing AI Engine Foundation Layer...")

    # 3. Create Shared Exam Session Context
    context = ExamContext()
    with context.lock():
        sys_state = context.system_state
        sys_state.status = ExamStatus.IN_PROGRESS
        sys_state.active_profile = config.exam.active_profile
        context.system_state = sys_state
        
        sess_info = context.session_info
        sess_info.exam_id = "exam_session_001"
        sess_info.student_id = "student_101"
        sess_info.start_time = time.time()
        context.session_info = sess_info

    # 4. Start Event Routing Bus
    event_bus = EventBus(
        async_dispatch=config.event_bus.async_dispatch,
        queue_size=config.event_bus.queue_size
    )
    event_bus.subscribe(None, handle_event)  # Wildcard subscription for logging
    event_bus.start()

    # 5. Start Camera Manager Subsystem
    camera_manager = CameraManager(
        camera_id=config.camera.camera_id,
        width=config.camera.width,
        height=config.camera.height,
        fps=config.camera.fps,
        buffer_size=config.camera.buffer_size,
        reconnect_interval=config.camera.reconnect_interval,
        max_reconnect_attempts=config.camera.max_reconnect_attempts,
        exam_context=context
    )
    camera_manager.initialize()
    camera_manager.start()

    # Signal Handling flags
    running = True

    def signal_handler(sig, frame):
        nonlocal running
        logger.info("Termination signal received. Shutting down system...")
        running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("AI Engine Foundation Layer started successfully. Press Ctrl+C to terminate.")

    # 6. Main Orchestration and Status Loop
    try:
        while running:
            # Periodically poll and transfer metrics to context
            camera_manager.process(context)
            
            # Retrieve frame from camera queue with a short block to avoid busy waiting
            frame = camera_manager.get_frame(timeout=0.1)
            
            if frame is not None:
                # Log system diagnostics every 100 frames (~3.3 seconds at 30 fps)
                if frame.frame_id % 100 == 0:
                    logger.info(
                        f"Active Diagnostics: Frame ID={frame.frame_id} | "
                        f"Resolution={frame.width}x{frame.height} | "
                        f"FPS={frame.fps:.2f} | "
                        f"Dropped Frames={camera_manager.dropped_count}"
                    )
            else:
                if not camera_manager.is_running:
                    logger.warning("Camera manager background thread is not running. Exiting loop.")
                    break
                    
    except Exception as e:
        logger.critical(f"System crash due to unhandled exception: {e}", exc_info=True)
    finally:
        logger.info("Initiating clean shutdown sequence...")
        
        # Stop Frame Acquisition
        camera_manager.stop()
        camera_manager.cleanup()
        
        # Stop Event Dispatching
        event_bus.stop()
        
        # Conclude ExamContext session info
        with context.lock():
            sys_state = context.system_state
            sys_state.status = ExamStatus.COMPLETED
            context.system_state = sys_state
            
            sess_info = context.session_info
            sess_info.end_time = time.time()
            context.session_info = sess_info

        logger.info("AI Engine Foundation Layer terminated cleanly.")

if __name__ == "__main__":
    main()
