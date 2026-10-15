import { useEffect, useRef, useState, useCallback } from 'react'
import { getCameraWsUrl } from '../../config/api'
import './MobileCameraView.css'

export default function MobileCameraView() {
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const wsRef = useRef(null)

  const [status, setStatus] = useState('DISCONNECTED') // CONNECTING | CONNECTED | DISCONNECTED | ERROR
  const [fps, setFps] = useState(0)
  const [frameCount, setFrameCount] = useState(0)
  const [cameraStatus, setCameraStatus] = useState('INITIALIZING') // INITIALIZING | ACTIVE | ERROR
  const [errorMsg, setErrorMsg] = useState(null)
  const [streaming, setStreaming] = useState(true)

  // Parse session_id from URL query string
  const urlParams = new URLSearchParams(window.location.search)
  const sessionId = urlParams.get('session_id') || 'active_session'

  // Initialize camera stream
  useEffect(() => {
    let stream = null

    async function initCamera() {
      // Check for Secure Context / mediaDevices support
      if (typeof window !== 'undefined' && !window.isSecureContext) {
        setErrorMsg('Security Error: Browser blocked camera access because page is not served over HTTPS. Please load via https://.')
        setCameraStatus('ERROR')
        return
      }

      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        setErrorMsg('Media Devices Error: navigator.mediaDevices.getUserMedia is not supported or blocked by browser security policy.')
        setCameraStatus('ERROR')
        return
      }

      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: 'environment', // Rear camera preferred
            width: { ideal: 1280, min: 640 },
            height: { ideal: 720, min: 480 },
          },
          audio: false,
        })

        if (videoRef.current) {
          videoRef.current.srcObject = stream
          await videoRef.current.play()
          setCameraStatus('ACTIVE')
          setErrorMsg(null)
        }
      } catch (err) {
        console.error('Camera access error:', err)
        let detailedMsg = `Camera Error (${err.name || 'Unknown'}): ${err.message || 'Unable to access camera.'}`
        if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
          detailedMsg = 'Permission Denied: Camera access was blocked. Please tap the lock/tune icon in your address bar and allow Camera permission.'
        } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
          detailedMsg = 'Camera Not Found: No rear camera was detected on this device.'
        } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
          detailedMsg = 'Camera Busy: Another application or browser tab is currently using the camera.'
        } else if (err.name === 'SecurityError') {
          detailedMsg = 'Security Error: Camera access restricted. Ensure page is loaded via HTTPS.'
        }
        setErrorMsg(detailedMsg)
        setCameraStatus('ERROR')
      }
    }

    initCamera()

    return () => {
      if (stream) {
        stream.getTracks().forEach((track) => track.stop())
      }
    }
  }, [])

  // Establish WebSocket connection to backend
  useEffect(() => {
    if (!streaming) {
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      setStatus('DISCONNECTED')
      return
    }

    const wsUrl = getCameraWsUrl('camera_2', sessionId)
    setStatus('CONNECTING')
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      setStatus('CONNECTED')
      setErrorMsg(null)
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'connection_ack') {
          setStatus('CONNECTED')
        }
      } catch (_) {}
    }

    ws.onclose = () => {
      setStatus('DISCONNECTED')
    }

    ws.onerror = (err) => {
      console.error('WebSocket error:', err)
      setStatus('ERROR')
    }

    return () => {
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close()
      }
    }
  }, [sessionId, streaming])

  const [droppedFrames, setDroppedFrames] = useState(0)

  // High-performance, backpressure-aware frame streaming loop (~18 FPS, 55ms throttle)
  useEffect(() => {
    if (!streaming || status !== 'CONNECTED') return

    let animId = null
    let lastCaptureTime = 0
    let isEncoding = false
    let framesSent = 0
    let droppedCount = 0
    let lastFpsCalcTime = performance.now()
    const TARGET_INTERVAL_MS = 55 // ~18 FPS (bounded between 15-20 FPS)
    const MAX_BUFFERED_AMOUNT = 65536 // 64KB threshold for WebSocket congestion backpressure

    function streamLoop(now) {
      if (!streaming) return

      animId = requestAnimationFrame(streamLoop)

      // Throttle capture to target ~18 FPS (55ms interval)
      if (now - lastCaptureTime < TARGET_INTERVAL_MS) {
        return
      }

      const video = videoRef.current
      const canvas = canvasRef.current
      const ws = wsRef.current

      if (!video || !canvas || !ws || ws.readyState !== WebSocket.OPEN) return
      if (video.videoWidth === 0 || video.videoHeight === 0) return

      // WebSocket backpressure check:
      // If socket is still sending previous frames or previous encode is in-flight,
      // drop this frame to keep stream real-time and prevent buffer bloat.
      if (isEncoding || (ws.bufferedAmount && ws.bufferedAmount > MAX_BUFFERED_AMOUNT)) {
        droppedCount++
        return
      }

      lastCaptureTime = now
      isEncoding = true

      // Maintain 960x720 high-definition resolution while strictly preserving camera aspect ratio
      const TARGET_WIDTH = 960
      const TARGET_HEIGHT = 720
      if (canvas.width !== TARGET_WIDTH || canvas.height !== TARGET_HEIGHT) {
        canvas.width = TARGET_WIDTH
        canvas.height = TARGET_HEIGHT
      }
      const ctx = canvas.getContext('2d')

      // Aspect-ratio preserving scaling (fit within 640x480 without distortion)
      const vWidth = video.videoWidth || TARGET_WIDTH
      const vHeight = video.videoHeight || TARGET_HEIGHT
      const scale = Math.min(TARGET_WIDTH / vWidth, TARGET_HEIGHT / vHeight)
      const renderWidth = Math.round(vWidth * scale)
      const renderHeight = Math.round(vHeight * scale)
      const offsetX = Math.round((TARGET_WIDTH - renderWidth) / 2)
      const offsetY = Math.round((TARGET_HEIGHT - renderHeight) / 2)

      ctx.fillStyle = '#000000'
      ctx.fillRect(0, 0, TARGET_WIDTH, TARGET_HEIGHT)
      ctx.drawImage(video, 0, 0, vWidth, vHeight, offsetX, offsetY, renderWidth, renderHeight)

      // Encode as higher quality JPEG (quality 0.85)
      canvas.toBlob(
        (blob) => {
          isEncoding = false
          if (!blob || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return

          blob.arrayBuffer().then((buffer) => {
            const currentWs = wsRef.current
            if (currentWs && currentWs.readyState === WebSocket.OPEN) {
              currentWs.send(buffer)
              framesSent++
              setFrameCount((c) => c + 1)

              const currTime = performance.now()
              if (currTime - lastFpsCalcTime >= 1000) {
                const elapsed = (currTime - lastFpsCalcTime) / 1000
                setFps(Math.round(framesSent / elapsed))
                setDroppedFrames((d) => d + droppedCount)
                framesSent = 0
                droppedCount = 0
                lastFpsCalcTime = currTime
              }
            }
          }).catch(() => {
            isEncoding = false
          })
        },
        'image/jpeg',
        0.85
      )
    }

    animId = requestAnimationFrame(streamLoop)

    return () => {
      if (animId) cancelAnimationFrame(animId)
      isEncoding = false
    }
  }, [streaming, status])

  return (
    <div className="mobile-camera-view">
      <div className="mobile-camera-header">
        <div className="mobile-camera-title">
          <h1>Exam Side-Camera (Camera 2)</h1>
          <div style={{ display: 'flex', gap: '6px' }}>
            <span className={`mobile-camera-status-badge ${status.toLowerCase()}`}>
              Backend: {status}
            </span>
            <span className={`mobile-camera-status-badge ${cameraStatus === 'ACTIVE' ? 'connected' : cameraStatus === 'INITIALIZING' ? 'connecting' : 'error'}`}>
              Camera: {cameraStatus}
            </span>
          </div>
        </div>
        <div className="mobile-camera-meta">
          <span>Session: {sessionId.slice(0, 12)}...</span>
          <span>FPS: {fps}</span>
          <span>Frames: #{frameCount}</span>
          {droppedFrames > 0 && <span style={{ color: '#f59e0b' }}>Dropped: {droppedFrames}</span>}
        </div>
      </div>

      <div className="mobile-camera-feed-container">
        <video ref={videoRef} className="mobile-camera-video" playsInline muted autoPlay />
        <canvas ref={canvasRef} style={{ display: 'none' }} />
        <div className="mobile-camera-overlay">Live Stream</div>
        {errorMsg && <div className="mobile-camera-error">{errorMsg}</div>}
      </div>

      <div className="mobile-camera-controls">
        <button
          className={`mobile-btn ${streaming ? 'mobile-btn-danger' : 'mobile-btn-primary'}`}
          onClick={() => setStreaming(!streaming)}
        >
          {streaming ? '⏹ Stop Streaming' : '▶ Start Streaming'}
        </button>

        <div className="mobile-instructions">
          <h3>Positioning Guide:</h3>
          <ol>
            <li>Prop your phone upright on your desk at a 45° angle.</li>
            <li>Ensure the camera captures your side profile, keyboard, and hands.</li>
            <li>Keep this browser tab open and do not lock your phone.</li>
          </ol>
        </div>
      </div>
    </div>
  )
}

