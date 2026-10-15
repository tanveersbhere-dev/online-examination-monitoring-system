/**
 * useWebSocket — Manages the WebSocket connection to the AI backend.
 *
 * Protocol:
 *   - Sends binary JPEG blobs (captured from canvas) to /ws/monitor
 *   - Receives one JSON FrameResult per frame
 *   - Reconnects automatically with exponential backoff
 *
 * Design:
 *   - All mutable state that should NOT trigger re-renders is in refs.
 *   - The useEffect has an EMPTY dependency array so it runs once on mount
 *     and once on unmount — React 18 StrictMode safe.
 *   - connectRef holds the latest connect function so closures are never stale.
 */
import { useRef, useEffect, useState } from 'react'
import { WS_URL } from '../config/api'

const CAPTURE_INTERVAL_MS = 100   // 10 fps to backend
const MAX_RECONNECT_DELAY_MS = 8000

export function useWebSocket(videoRef) {
  // ── Refs (no re-render on change) ─────────────────────────────────
  const wsRef              = useRef(null)
  const captureIntervalRef  = useRef(null)
  const canvasRef           = useRef(null)
  const reconnectDelayRef   = useRef(500)
  const mountedRef          = useRef(false)
  const reconnectTimerRef   = useRef(null)
  const inferFpsCounterRef  = useRef({ count: 0, last: Date.now() })
  const connectRef          = useRef(null)   // always points to latest connect fn

  // ── React state (triggers UI re-render) ───────────────────────────
  const [connected,    setConnected]    = useState(false)
  const [connecting,   setConnecting]   = useState(false)
  const [frameResult,  setFrameResult]  = useState(null)
  const [droppedCount, setDroppedCount] = useState(0)
  const [inferFps,     setInferFps]     = useState(0)

  const isSendingRef = useRef(false)

  // ── Single-mount effect — empty deps = runs once ──────────────────
  useEffect(() => {
    mountedRef.current = true

    // Lazy-create the offscreen canvas once
    if (!canvasRef.current) {
      canvasRef.current = document.createElement('canvas')
    }

    // ── captureAndSend (defined inside effect so refs are captured correctly)
    function captureAndSend() {
      const video = videoRef.current
      const ws    = wsRef.current
      if (!video || !ws || ws.readyState !== WebSocket.OPEN) return
      if (video.readyState < 2 || video.videoWidth === 0) return
      if (isSendingRef.current) return // Backpressure: do not over-send if in-flight

      isSendingRef.current = true

      const canvas = canvasRef.current
      if (canvas.width !== video.videoWidth)  canvas.width  = video.videoWidth
      if (canvas.height !== video.videoHeight) canvas.height = video.videoHeight

      const ctx = canvas.getContext('2d')
      ctx.drawImage(video, 0, 0)

      canvas.toBlob(
        (blob) => {
          if (!blob) { isSendingRef.current = false; return }
          const currentWs = wsRef.current
          if (!currentWs || currentWs.readyState !== WebSocket.OPEN) { isSendingRef.current = false; return }
          blob.arrayBuffer().then((buf) => {
            try { currentWs.send(buf) }
            catch (_) { isSendingRef.current = false; setDroppedCount((d) => d + 1) }
          })
        },
        'image/jpeg',
        0.85
      )
    }

    // ── connect (defined inside effect, stored in ref for onclose access)
    function connect() {
      if (!mountedRef.current) return

      // Single-connection guard
      if (wsRef.current && wsRef.current.readyState <= WebSocket.OPEN) return

      setConnecting(true)

      const ws = new WebSocket(WS_URL)
      ws.binaryType = 'arraybuffer'
      wsRef.current  = ws

      ws.onopen = () => {
        if (!mountedRef.current) { ws.close(); return }
        setConnected(true)
        setConnecting(false)
        isSendingRef.current = false
        reconnectDelayRef.current = 500
        clearInterval(captureIntervalRef.current)
        captureIntervalRef.current = setInterval(captureAndSend, CAPTURE_INTERVAL_MS)
      }

      ws.onmessage = (evt) => {
        isSendingRef.current = false
        if (!mountedRef.current) return
        try {
          const data = JSON.parse(evt.data)
          if (data.lifecycle_events?.length > 0 || data.violations?.length > 0 || (data.risk?.score > 0)) {
            console.log('[LIVE BROWSER WS RECV]', {
              frame: data.frame_number,
              lifecycle_events: data.lifecycle_events,
              violations: data.violations,
              risk: data.risk,
              evidence: data.evidence
            })
          }
          setFrameResult(data)
          // Infer FPS
          const now = Date.now()
          const ctr = inferFpsCounterRef.current
          ctr.count++
          if (now - ctr.last >= 1000) {
            setInferFps(Math.round(ctr.count * 1000 / (now - ctr.last)))
            ctr.count = 0
            ctr.last  = now
          }
        } catch (_) {}
      }

      ws.onerror = () => {
        isSendingRef.current = false
        if (!mountedRef.current) return
        setConnected(false)
      }

      ws.onclose = () => {
        clearInterval(captureIntervalRef.current)
        captureIntervalRef.current = null
        wsRef.current = null

        // Only reconnect if component is still mounted
        if (!mountedRef.current) return

        setConnected(false)
        setConnecting(false)

        const delay = reconnectDelayRef.current
        reconnectDelayRef.current = Math.min(delay * 2, MAX_RECONNECT_DELAY_MS)

        clearTimeout(reconnectTimerRef.current)
        // Use connectRef so the closure always calls the live function
        reconnectTimerRef.current = setTimeout(() => connectRef.current?.(), delay)
      }
    }

    connectRef.current = connect
    connect()

    // ── Cleanup: signal unmount BEFORE closing so onclose skips reconnect
    return () => {
      mountedRef.current = false
      connectRef.current  = null
      clearInterval(captureIntervalRef.current)
      clearTimeout(reconnectTimerRef.current)
      captureIntervalRef.current = null
      reconnectTimerRef.current  = null
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [])  // ← intentionally empty: this effect must run exactly once

  return { connected, connecting, frameResult, droppedCount, inferFps }
}
