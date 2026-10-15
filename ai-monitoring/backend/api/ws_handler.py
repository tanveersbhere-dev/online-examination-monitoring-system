"""
WebSocket Handler
=================
Single endpoint: /ws/monitor

Protocol:
  Client → Server : Binary JPEG frame bytes
  Server → Client : JSON-encoded FrameResult (one per frame)

No polling. No HTTP. Real-time only.
"""
import json
import logging
import time
import asyncio
from typing import Set, Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Response

from backend.camera.multi_camera_manager import multi_camera_manager

logger = logging.getLogger("playground.ws")

router = APIRouter()

# Injected at startup by main.py
_orchestrator = None
_context_builder = None
_serializer = None

# Dedicated bounded thread pool (1 worker) for Camera 1 AI processing.
# Offloads CPU-intensive inference off the asyncio event loop to ensure
# Camera 2 preview relay and WebSocket ingress remain completely responsive.
_cam1_executor: Optional[ThreadPoolExecutor] = None


def get_cam1_executor() -> ThreadPoolExecutor:
    global _cam1_executor
    if _cam1_executor is None:
        _cam1_executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="cam1_ai_worker",
        )
    return _cam1_executor


def shutdown_cam1_executor() -> None:
    global _cam1_executor
    if _cam1_executor is not None:
        _cam1_executor.shutdown(wait=False, cancel_futures=True)
        _cam1_executor = None


def _process_camera1_frame(data: bytes, session_id: Optional[str] = None):
    """
    Synchronous blocking Camera 1 AI pipeline processor executed in worker thread.
    Keeps FastAPI's asyncio event loop 100% unblocked.
    """
    frame = _context_builder.decode_and_inject(data, camera_id="camera_1")
    if frame is None:
        return None, 0.0

    context = _context_builder.get_context(camera_id="camera_1")
    pipeline_ms = _orchestrator.process(context)

    from backend.adapters.monitoring_persistence_adapter import monitoring_persistence_adapter
    effective_sid = session_id or monitoring_persistence_adapter.active_session_id
    monitoring_persistence_adapter.handle_frame_lifecycle(context, session_id=effective_sid)

    frame_result = _serializer.to_dict(
        context=context,
        processor_health=_orchestrator.processor_health(),
        frame_counter=_context_builder.frame_counter,
        pipeline_ms=pipeline_ms,
        evidence_store=_orchestrator.evidence_store,
        integration_manager=getattr(_orchestrator, "integration_manager", None),
    )
    return frame_result, pipeline_ms


def inject_dependencies(orchestrator, context_builder, serializer):
    global _orchestrator, _context_builder, _serializer
    _orchestrator = orchestrator
    _context_builder = context_builder
    _serializer = serializer


# Track active connections (for future multi-client support)
_active_connections: Set[WebSocket] = set()


@router.websocket("/ws/monitor")
async def ws_monitor(websocket: WebSocket):
    await websocket.accept()
    _active_connections.add(websocket)
    client = websocket.client
    logger.info(f"WebSocket connected: {client}")

    import asyncio

    latest_frame_queue: asyncio.Queue = asyncio.Queue(maxsize=1)
    dropped_frames: int = 0

    async def frame_receiver():
        nonlocal dropped_frames
        try:
            while True:
                data = await websocket.receive_bytes()
                if not data:
                    continue
                recv_time = time.perf_counter()
                
                # Push frame non-blockingly to dedicated audio detection worker
                try:
                    from ai_engine.audio_detection.audio_worker import audio_detection_worker
                    audio_detection_worker.push_frame(
                        camera_id="camera_1",
                        jpeg_bytes=data,
                        timestamp=time.time(),
                    )
                except Exception:
                    pass

                if latest_frame_queue.full():
                    try:
                        latest_frame_queue.get_nowait()
                        dropped_frames += 1
                    except asyncio.QueueEmpty:
                        pass
                await latest_frame_queue.put((data, recv_time))
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass

    receiver_task = asyncio.create_task(frame_receiver())

    try:
        while True:
            item = await latest_frame_queue.get()
            if item is None:
                break
            data, recv_time = item
            queue_wait_ms = (time.perf_counter() - recv_time) * 1000.0

            # Offload synchronous blocking Camera 1 AI pipeline off the asyncio event loop
            loop = asyncio.get_running_loop()
            from backend.adapters.monitoring_persistence_adapter import monitoring_persistence_adapter
            current_sid = monitoring_persistence_adapter.active_session_id

            executor = get_cam1_executor()
            frame_result, pipeline_ms = await loop.run_in_executor(
                executor,
                _process_camera1_frame,
                data,
                current_sid,
            )

            if frame_result is None:
                await websocket.send_text(json.dumps({
                    "error": "Frame decode failed",
                    "frame_number": _context_builder.frame_counter,
                    "timestamp": time.time(),
                }))
                continue

            # Attach session ID and queue metrics
            frame_result["active_session_id"] = monitoring_persistence_adapter.active_session_id
            frame_result["queue_wait_ms"] = round(queue_wait_ms, 2)
            frame_result["dropped_frames"] = dropped_frames

            # Register camera 1 as active & record frame in MultiCameraManager
            multi_camera_manager.register_connection("camera_1", monitoring_persistence_adapter.active_session_id)
            cam2_info = multi_camera_manager.get_camera_info("camera_2")
            frame_result["camera_2"] = {
                "is_connected": cam2_info.is_connected if cam2_info else False,
                "fps": round(cam2_info.fps, 1) if cam2_info else 0.0,
                "frame_count": cam2_info.frame_count if cam2_info else 0,
            }

            # Per-frame diagnostic (every 30 frames)
            fc = _context_builder.frame_counter
            if fc % 30 == 0:
                face = frame_result.get('face', {})
                objs = frame_result.get('objects', [])
                ev   = frame_result.get('evidence', [])
                hp   = frame_result.get('head_pose', {})
                logger.info(
                    f"[FRAME {fc}] face_detected={face.get('detected')} "
                    f"conf={face.get('confidence', 0):.3f} "
                    f"bbox={[round(x,1) for x in face.get('bbox', [])[:4]]} "
                    f"objects={len(objs)} "
                    f"head_yaw={hp.get('yaw',0):.1f} "
                    f"evidence={len(ev)} "
                    f"pipeline={pipeline_ms:.0f}ms queue_wait={queue_wait_ms:.1f}ms dropped={dropped_frames}"
                )

            # Send JSON response
            await websocket.send_text(json.dumps(frame_result, default=str))

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {client}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        receiver_task.cancel()
        _active_connections.discard(websocket)
        multi_camera_manager.register_disconnection("camera_1")


@router.websocket("/ws/camera/{camera_id}")
async def ws_camera_ingress(
    websocket: WebSocket,
    camera_id: str,
    session_id: Optional[str] = Query(None),
):
    """
    Ingress endpoint for Camera 2 (Mobile phone camera).
    Protocol:
      Client (Phone) -> Server : Binary JPEG frame bytes (3–5 FPS)
      Server -> Client : JSON ack / status updates
    Guarantees:
      - Independent connection; disconnects do not affect Camera 1 or the active session.
      - Zero AI processing in Phase 1 (transport & relay only).
    """
    from backend.adapters.monitoring_persistence_adapter import monitoring_persistence_adapter
    effective_sid = session_id or monitoring_persistence_adapter.active_session_id or "local_session"

    await websocket.accept()
    client = websocket.client
    logger.info(f"[CameraIngress] '{camera_id}' connected from {client} for session '{effective_sid}'")
    multi_camera_manager.register_connection(camera_id, effective_sid)
    multi_camera_manager.start_background_workers()

    try:
        # Acknowledge connection to mobile client
        await websocket.send_text(json.dumps({
            "type": "connection_ack",
            "camera_id": camera_id,
            "session_id": effective_sid,
            "status": "CONNECTED",
            "timestamp": time.time(),
        }))

        while True:
            data = await websocket.receive_bytes()
            if not data:
                continue
            recv_time = time.time()
            # Push frame to multi-camera manager for storage & dashboard relay
            multi_camera_manager.push_frame(
                camera_id=camera_id,
                jpeg_bytes=data,
                session_id=effective_sid,
                timestamp=recv_time,
            )
    except WebSocketDisconnect:
        logger.info(f"[CameraIngress] '{camera_id}' disconnected from {client}")
    except Exception as e:
        logger.warning(f"[CameraIngress] Error on '{camera_id}': {e}")
    finally:
        multi_camera_manager.register_disconnection(camera_id)


@router.websocket("/ws/camera/feed/{camera_id}")
async def ws_camera_feed(
    websocket: WebSocket,
    camera_id: str,
):
    """
    Relay endpoint for the laptop monitoring UI.
    Streams raw JPEG frames from Camera 2 directly to the laptop browser viewer.
    """
    await websocket.accept()
    feed_queue = multi_camera_manager.subscribe_feed(camera_id)
    c_info = multi_camera_manager.get_camera_info(camera_id)

    # If camera currently has a frame, send initial frame immediately
    if c_info and c_info.latest_jpeg_bytes:
        try:
            await websocket.send_bytes(c_info.latest_jpeg_bytes)
        except Exception:
            pass

    try:
        while True:
            item = await feed_queue.get()
            if isinstance(item, bytes):
                await websocket.send_bytes(item)
            elif isinstance(item, dict):
                await websocket.send_text(json.dumps(item))
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    except Exception as e:
        logger.debug(f"[CameraFeed] Stream closed for '{camera_id}': {e}")
    finally:
        multi_camera_manager.unsubscribe_feed(camera_id, feed_queue)


@router.get("/api/camera/status")
async def get_multi_camera_status(session_id: Optional[str] = Query(None)):
    """Return multi-camera system status, LAN pairing URL, and active stream metrics."""
    from backend.adapters.monitoring_persistence_adapter import monitoring_persistence_adapter
    effective_sid = session_id or monitoring_persistence_adapter.active_session_id
    return multi_camera_manager.get_status(effective_sid)


@router.get("/api/camera/{camera_id}/frame")
async def get_camera_snapshot(camera_id: str):
    """Return latest captured frame from a camera stream as JPEG image."""
    c_info = multi_camera_manager.get_camera_info(camera_id)
    if not c_info or not c_info.latest_jpeg_bytes:
        return Response(status_code=404, content=b"No frame available")
    return Response(content=c_info.latest_jpeg_bytes, media_type="image/jpeg")


@router.websocket("/ws/audio/camera_1")
async def ws_audio_camera_1(
    websocket: WebSocket,
    session_id: Optional[str] = Query(None),
):
    """
    Dedicated microphone audio ingress for Camera 1 (Student PC/Laptop).
    Protocol:
      Client -> Server : Binary 16kHz 16-bit mono PCM chunks
      Server -> Client : JSON audio monitoring status ack
    """
    await websocket.accept()
    client = websocket.client
    logger.info(f"[AudioIngress] Camera 1 microphone connected from {client} (session={session_id})")

    try:
        from ai_engine.audio_detection.voice_vad_worker import voice_vad_worker
        if not voice_vad_worker._running:
            voice_vad_worker.start()

        await websocket.send_text(json.dumps({
            "type": "audio_connection_ack",
            "camera_id": "camera_1",
            "status": "LISTENING",
            "sample_rate": 16000,
            "channels": 1,
            "timestamp": time.time(),
        }))

        while True:
            data = await websocket.receive_bytes()
            if not data:
                continue
            voice_vad_worker.push_pcm_bytes(data)

    except (WebSocketDisconnect, asyncio.CancelledError):
        logger.info(f"[AudioIngress] Camera 1 microphone disconnected: {client}")
    except Exception as e:
        logger.debug(f"[AudioIngress] Camera 1 audio error: {e}")


