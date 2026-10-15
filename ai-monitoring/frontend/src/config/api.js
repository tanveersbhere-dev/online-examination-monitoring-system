/**
 * API Configuration — Single source of truth for all backend URLs.
 *
 * Dynamically resolves to window.location.hostname so both laptop (localhost)
 * and mobile phone (LAN IP: 192.168.x.x) connect to the host machine seamlessly.
 */
const getHost = () => {
  if (typeof window !== 'undefined' && window.location?.hostname) {
    return window.location.hostname
  }
  return 'localhost'
}

export const API_BASE = `http://${getHost()}:8000`
export const WS_URL   = `ws://${getHost()}:8000/ws/monitor`

export const getCameraWsUrl = (cameraId, sessionId) => {
  const host = getHost()
  const sid = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : ''
  return `ws://${host}:8000/ws/camera/${cameraId}${sid}`
}

export const getCameraFeedWsUrl = (cameraId, sessionId) => {
  const host = getHost()
  const sid = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : ''
  return `ws://${host}:8000/ws/camera/feed/${cameraId}${sid}`
}

export const getAudioWsUrl = (cameraId = 'camera_1', sessionId) => {
  const host = getHost()
  const sid = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : ''
  return `ws://${host}:8000/ws/audio/${cameraId}${sid}`
}

