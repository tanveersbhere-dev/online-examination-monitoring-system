import { useEffect, useRef, useState, useCallback } from 'react'
import { getCameraFeedWsUrl, API_BASE } from '../../config/api'
import './SecondaryCameraFeed.css'

export default function SecondaryCameraFeed({ sessionId, camera2Info }) {
  const [feedConnected, setFeedConnected] = useState(false)
  const [mobileStatus, setMobileStatus] = useState(null)
  const [copied, setCopied] = useState(false)
  const imgRef = useRef(null)
  const wsRef = useRef(null)
  const objectUrlRef = useRef(null)

  // Fetch LAN status to get pairing link
  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/camera/status?session_id=${sessionId || ''}`)
      if (res.ok) {
        const data = await res.json()
        setMobileStatus(data)
      }
    } catch (_) {}
  }, [sessionId])

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 4000)
    return () => clearInterval(interval)
  }, [fetchStatus])

  // Connect to frame relay WebSocket for camera_2
  useEffect(() => {
    const wsUrl = getCameraFeedWsUrl('camera_2', sessionId)
    let ws = null
    let reconnectTimeout = null

    function connect() {
      try {
        ws = new WebSocket(wsUrl)
        wsRef.current = ws
        ws.binaryType = 'arraybuffer'

        ws.onopen = () => {
          setFeedConnected(true)
        }

        ws.onmessage = (event) => {
          if (event.data instanceof ArrayBuffer) {
            // Revoke previous blob URL to prevent memory leaks
            if (objectUrlRef.current) {
              URL.revokeObjectURL(objectUrlRef.current)
            }
            const blob = new Blob([event.data], { type: 'image/jpeg' })
            const url = URL.createObjectURL(blob)
            objectUrlRef.current = url
            if (imgRef.current) {
              imgRef.current.src = url
            }
          } else {
            try {
              const msg = JSON.parse(event.data)
              if (msg.type === 'status' && msg.is_connected === false) {
                if (imgRef.current) imgRef.current.src = ''
              }
            } catch (_) {}
          }
        }

        ws.onclose = () => {
          setFeedConnected(false)
          reconnectTimeout = setTimeout(connect, 2000)
        }

        ws.onerror = () => {
          ws.close()
        }
      } catch (err) {
        reconnectTimeout = setTimeout(connect, 3000)
      }
    }

    connect()

    return () => {
      if (reconnectTimeout) clearTimeout(reconnectTimeout)
      if (ws) ws.close()
      if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current)
    }
  }, [sessionId])

  const isCamera2Connected = camera2Info?.is_connected ?? mobileStatus?.cameras?.camera_2?.is_connected ?? false
  const mobileUrl = mobileStatus?.mobile_url || `https://${window.location.hostname}:5173/mobile?session_id=${sessionId || 'active_session'}`

  const handleCopy = () => {
    navigator.clipboard?.writeText(mobileUrl)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="secondary-camera-feed">
      <div className="sec-feed__header">
        <div className="sec-feed__title">
          <span className="sec-feed__icon">📱</span>
          <span>Camera 2 — Secondary (Mobile)</span>
        </div>
        <div className={`sec-feed__badge ${isCamera2Connected ? 'connected' : 'waiting'}`}>
          <span className={`status-dot status-dot--${isCamera2Connected ? 'connected' : 'connecting'}`} />
          {isCamera2Connected ? 'CONNECTED' : 'WAITING FOR MOBILE'}
        </div>
      </div>

      <div className="sec-feed__body">
        <img
          ref={imgRef}
          className="sec-feed__img"
          alt="Camera 2 feed"
          style={{ display: isCamera2Connected ? 'block' : 'none' }}
        />

        {!isCamera2Connected && (
          <div className="sec-feed__placeholder">
            <div className="sec-feed__placeholder-icon">📷</div>
            <div className="sec-feed__placeholder-title">Secondary Camera Offline</div>
            <div className="sec-feed__placeholder-sub">
              Open this link on your phone (connected to same Wi-Fi) to stream side view:
            </div>
            <div className="sec-feed__url-box">
              <span className="sec-feed__url-text">{mobileUrl}</span>
              <button className="sec-feed__copy-btn" onClick={handleCopy}>
                {copied ? '✓ Copied' : 'Copy Link'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

