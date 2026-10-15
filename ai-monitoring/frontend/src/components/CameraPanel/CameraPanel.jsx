import { useEffect, useRef, useState } from 'react'
import SecondaryCameraFeed from './SecondaryCameraFeed'
import { getAudioWsUrl } from '../../config/api'
import './CameraPanel.css'

const RISK_BORDER = {
  NORMAL: '#4caf50',
  LOW: '#8bc34a',
  MEDIUM: '#ff9800',
  HIGH: '#ff5722',
  CRITICAL: '#ff1744',
}

export default function CameraPanel({ videoRef, frameResult, connected, connectionStatus, sessionId, camera2Info }) {
  const overlayCanvasRef = useRef(null)
  const [micStatus, setMicStatus] = useState('OFF')
  const audioWsRef = useRef(null)

  // Start webcam on mount
  useEffect(() => {
    let stream = null
    async function startCam() {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
          audio: false,
        })
        if (videoRef.current) {
          videoRef.current.srcObject = stream
          videoRef.current.play().catch(() => {})
        }
      } catch (e) {
        console.error('Camera access denied:', e)
      }
    }
    startCam()
    return () => {
      if (stream) stream.getTracks().forEach((t) => t.stop())
    }
  }, [videoRef])

  // Dedicated Camera 1 Microphone Streaming
  useEffect(() => {
    let micStream = null
    let audioCtx = null
    let processor = null
    let source = null
    let muteGain = null
    let ws = null

    if (!connected) {
      setMicStatus('OFF')
      return
    }

    // Downsample input float buffer to 16,000 Hz if hardware operates at 44.1k or 48k
    function downsampleTo16k(inputBuffer, sampleRate) {
      if (sampleRate === 16000) return inputBuffer
      const ratio = sampleRate / 16000
      const newLength = Math.round(inputBuffer.length / ratio)
      const result = new Float32Array(newLength)
      let offsetResult = 0
      let offsetBuffer = 0
      while (offsetResult < result.length) {
        const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio)
        let accum = 0
        let count = 0
        for (let i = offsetBuffer; i < nextOffsetBuffer && i < inputBuffer.length; i++) {
          accum += inputBuffer[i]
          count++
        }
        result[offsetResult] = count > 0 ? accum / count : inputBuffer[offsetBuffer]
        offsetResult++
        offsetBuffer = nextOffsetBuffer
      }
      return result
    }

    async function startMic() {
      try {
        setMicStatus('CONNECTING')
        micStream = await navigator.mediaDevices.getUserMedia({
          audio: {
            channelCount: 1,
            sampleRate: 16000,
            echoCancellation: false,
            noiseSuppression: false,
            autoGainControl: false,
          },
        })

        const url = getAudioWsUrl('camera_1', sessionId)
        ws = new WebSocket(url)
        audioWsRef.current = ws

        ws.onopen = async () => {
          setMicStatus('ACTIVE')
          try {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 })
            if (audioCtx.state === 'suspended') {
              await audioCtx.resume()
            }
            console.log('[CameraPanel Mic] AudioContext started. Native rate:', audioCtx.sampleRate, 'State:', audioCtx.state)

            source = audioCtx.createMediaStreamSource(micStream)
            processor = audioCtx.createScriptProcessor(2048, 1, 1)

            processor.onaudioprocess = (e) => {
              if (ws && ws.readyState === WebSocket.OPEN) {
                const rawFloat = e.inputBuffer.getChannelData(0)
                const floatData = downsampleTo16k(rawFloat, audioCtx.sampleRate)
                const pcm16 = new Int16Array(floatData.length)
                for (let i = 0; i < floatData.length; i++) {
                  let s = Math.max(-1, Math.min(1, floatData[i]))
                  pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff
                }
                ws.send(pcm16.buffer)
              }
            }

            // Route through 0-gain node to destination so script processor is pulled without acoustic feedback
            muteGain = audioCtx.createGain()
            muteGain.gain.value = 0.0

            source.connect(processor)
            processor.connect(muteGain)
            muteGain.connect(audioCtx.destination)
          } catch (err) {
            console.error('Audio processing error:', err)
            setMicStatus('ERROR')
          }
        }

        ws.onerror = () => {
          setMicStatus('ERROR')
        }

        ws.onclose = () => {
          setMicStatus('OFF')
        }
      } catch (err) {
        console.warn('Microphone access denied or unavailable:', err)
        setMicStatus('DENIED')
      }
    }

    startMic()

    return () => {
      if (processor) {
        processor.disconnect()
        processor.onaudioprocess = null
      }
      if (muteGain) {
        muteGain.disconnect()
      }
      if (source) source.disconnect()
      if (audioCtx && audioCtx.state !== 'closed') audioCtx.close()
      if (micStream) micStream.getTracks().forEach((t) => t.stop())
      if (ws) {
        ws.close()
        audioWsRef.current = null
      }
      setMicStatus('OFF')
    }
  }, [connected, sessionId])

  // Draw bounding boxes and face landmarks overlay (violation-aware z-order & glow)
  useEffect(() => {
    const canvas = overlayCanvasRef.current
    const video = videoRef.current
    if (!canvas || !video || !frameResult) return

    canvas.width = video.videoWidth || canvas.clientWidth
    canvas.height = video.videoHeight || canvas.clientHeight
    const ctx = canvas.getContext('2d')
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    // Build active violation object types set
    const activeViolations = frameResult.violations || []
    const ruleResults = frameResult.rule_results || []
    const activeRules = ruleResults.filter(r => r.triggered).map(r => r.rule_id)

    const violatingObjectTypes = new Set()
    if (activeRules.includes('UNAUTH_PHONE') || activeRules.includes('COMPOSITE_PHONE_LOOKING_AWAY_TALKING')) violatingObjectTypes.add('CELL_PHONE')
    if (activeRules.includes('UNAUTH_BOOK') || activeRules.includes('ENV_BOOK_DETECTED')) {
      violatingObjectTypes.add('BOOK')
      violatingObjectTypes.add('UNAUTHORIZED_MATERIAL')
    }
    if (activeRules.includes('UNAUTH_NOTEBOOK')) {
      violatingObjectTypes.add('NOTEBOOK')
      violatingObjectTypes.add('UNAUTHORIZED_MATERIAL')
    }
    if (activeRules.includes('UNAUTH_REGISTER')) {
      violatingObjectTypes.add('REGISTER')
      violatingObjectTypes.add('UNAUTHORIZED_MATERIAL')
    }
    if (activeRules.includes('UNAUTH_PAPER')) {
      violatingObjectTypes.add('PAPER')
      violatingObjectTypes.add('UNAUTHORIZED_MATERIAL')
    }
    if (activeRules.includes('UNAUTH_LAPTOP')) violatingObjectTypes.add('LAPTOP')
    if (activeRules.includes('COMM_EARPHONES') || activeRules.includes('COMM_EARBUDS') || activeRules.includes('COMM_NECKBAND') || activeRules.includes('EARPHONE_DEVICE')) {
      violatingObjectTypes.add('COMM_EARPHONES')
      violatingObjectTypes.add('EARBUDS')
      violatingObjectTypes.add('HEADPHONES')
      violatingObjectTypes.add('HEADSET')
      violatingObjectTypes.add('NECKBAND')
    }
    if (activeRules.includes('COMM_EARBUDS')) violatingObjectTypes.add('EARBUDS')
    if (activeRules.includes('COMM_NECKBAND')) violatingObjectTypes.add('NECKBAND')
    if (activeRules.includes('COMM_HEADPHONES')) violatingObjectTypes.add('HEADPHONES')
    if (activeRules.includes('COMM_MULTIPLE_PERSONS') || activeRules.includes('ID_MULTIPLE_FACES')) violatingObjectTypes.add('PERSON')

    const objects = frameResult.objects || []
    const nonViolatingObjs = objects.filter(o => !violatingObjectTypes.has(o.type))
    const violatingObjs = objects.filter(o => violatingObjectTypes.has(o.type))

    // 1. Draw non-violating objects first
    nonViolatingObjs.forEach((obj) => {
      if (!obj.bbox || obj.bbox.length < 4) return
      const [x, y, w, h] = obj.bbox
      const colour = obj.type === 'PERSON' ? '#ff9800' : '#00e676'
      ctx.strokeStyle = colour
      ctx.lineWidth = 2
      ctx.shadowColor = colour
      ctx.shadowBlur = 6
      ctx.strokeRect(x, y, w, h)

      ctx.shadowBlur = 0
      ctx.fillStyle = colour + 'cc'
      const objTitle = (obj.type === 'COMM_EARPHONES' || obj.type === 'EARBUDS' || obj.type === 'HEADPHONES' || obj.type === 'NECKBAND')
        ? 'UNAUTHORIZED AUDIO DEVICE'
        : (obj.type === 'UNAUTHORIZED_MATERIAL' ? 'UNAUTHORIZED MATERIAL' : obj.type)
      const label = `${objTitle} ${(obj.confidence * 100).toFixed(0)}%`
      const tw = ctx.measureText(label).width
      ctx.fillRect(x, y - 18, tw + 10, 18)
      ctx.fillStyle = '#07080e'
      ctx.font = 'bold 11px Inter'
      ctx.fillText(label, x + 5, y - 5)
    })

    // 2. Draw face bounding box
    const face = frameResult.face
    if (face?.detected && face.bbox?.length === 4) {
      const [x, y, w, h] = face.bbox
      ctx.strokeStyle = '#00c9ff'
      ctx.lineWidth = 2
      ctx.shadowColor = '#00c9ff'
      ctx.shadowBlur = 8
      ctx.strokeRect(x, y, w, h)

      // Face label
      ctx.shadowBlur = 0
      ctx.fillStyle = 'rgba(0,201,255,0.85)'
      ctx.fillRect(x, y - 20, 140, 20)
      ctx.fillStyle = '#07080e'
      ctx.font = '11px Inter'
      ctx.fillText(`Face  ${(face.confidence * 100).toFixed(0)}%`, x + 6, y - 6)
    }

    // 3. Draw VIOLATING objects ON TOP (higher z-order, prominent stroke & glow)
    violatingObjs.forEach((obj) => {
      if (!obj.bbox || obj.bbox.length < 4) return
      const [x, y, w, h] = obj.bbox
      const colour = '#ff1744'

      // Outer glow pulse
      ctx.strokeStyle = colour
      ctx.lineWidth = 5
      ctx.shadowColor = '#ff1744'
      ctx.shadowBlur = 20
      ctx.strokeRect(x, y, w, h)

      // Inner stroke accent
      ctx.strokeStyle = '#ffffff'
      ctx.lineWidth = 1.5
      ctx.shadowBlur = 0
      ctx.strokeRect(x + 2, y + 2, Math.max(0, w - 4), Math.max(0, h - 4))

      // Violation badge label
      ctx.fillStyle = '#ff1744'
      const objTitle = (obj.type === 'COMM_EARPHONES' || obj.type === 'EARBUDS' || obj.type === 'HEADPHONES' || obj.type === 'NECKBAND')
        ? 'UNAUTHORIZED AUDIO DEVICE'
        : (obj.type === 'UNAUTHORIZED_MATERIAL' ? 'UNAUTHORIZED MATERIAL' : obj.type)
      const label = `🚨 [VIOLATION] ${objTitle} ${(obj.confidence * 100).toFixed(0)}%`
      ctx.font = 'bold 12px Inter'
      const tw = ctx.measureText(label).width
      ctx.fillRect(x, y - 22, tw + 12, 22)
      ctx.fillStyle = '#ffffff'
      ctx.fillText(label, x + 6, y - 6)
    })
  }, [frameResult, videoRef])

  const riskLevel = frameResult?.risk?.level || 'NORMAL'
  const riskScore = frameResult?.risk?.score ?? 0
  const fps = frameResult?.fps ?? 0
  const latency = frameResult?.latency_ms ?? 0
  const frameNum = frameResult?.frame_number ?? 0

  return (
    <div className="camera-panel">
      {/* Video container */}
      <div
        className="camera-feed"
        style={{ '--risk-border-color': RISK_BORDER[riskLevel] || RISK_BORDER.NORMAL }}
      >
        <video ref={videoRef} className="camera-video" autoPlay playsInline muted />
        <canvas ref={overlayCanvasRef} className="camera-overlay" />

        {/* Live badge */}
        <div className="camera-live-badge">
          <span className={`status-dot status-dot--${connectionStatus} pulse`} />
          Camera 1 — Laptop
        </div>

        {/* Microphone status badge */}
        <div style={{
          position: 'absolute',
          bottom: 10,
          left: 10,
          background: 'rgba(15, 23, 42, 0.85)',
          backdropFilter: 'blur(4px)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          color: micStatus === 'ACTIVE' ? '#00e676' : (micStatus === 'DENIED' ? '#ff1744' : '#ff9800'),
          padding: '3px 8px',
          borderRadius: 4,
          fontSize: 10,
          fontWeight: 600,
          display: 'flex',
          alignItems: 'center',
          gap: 5,
          zIndex: 4,
        }}>
          <span style={{
            display: 'inline-block',
            width: 7,
            height: 7,
            borderRadius: '50%',
            background: micStatus === 'ACTIVE' ? '#00e676' : (micStatus === 'DENIED' ? '#ff1744' : '#ff9800'),
          }} />
          🎤 Mic: {micStatus}
        </div>

        {/* Active human voice violation alert banner */}
        {(frameResult?.rule_results || []).some(r => r.triggered && r.rule_id === 'UNAUTH_VOICE') && (
          <div style={{
            position: 'absolute',
            top: 10,
            left: '50%',
            transform: 'translateX(-50%)',
            background: 'rgba(255, 23, 68, 0.95)',
            color: '#fff',
            padding: '5px 12px',
            borderRadius: 6,
            fontWeight: 'bold',
            fontSize: 12,
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            boxShadow: '0 4px 12px rgba(255, 23, 68, 0.5)',
            zIndex: 10,
            letterSpacing: '0.5px',
          }}>
            <span>🎤</span>
            <span>HUMAN VOICE DETECTED</span>
          </div>
        )}

        {/* Risk badge */}
        <div className={`camera-risk-badge bg-risk--${riskLevel}`}>
          <span className={`risk--${riskLevel}`}>{riskLevel}</span>
          <span className={`camera-risk-score risk--${riskLevel} mono`}>{riskScore.toFixed(0)}</span>
        </div>

        {/* No connection overlay */}
        {!connected && (
          <div className="camera-overlay-msg">
            <div className="camera-overlay-icon">◈</div>
            <div>Waiting for backend connection…</div>
          </div>
        )}
      </div>

      {/* Camera stats bar */}
      <div className="camera-stats">
        <StatItem label="FPS" value={fps.toFixed(1)} color="var(--accent-cyan)" />
        <StatItem label="Latency" value={`${latency.toFixed(0)} ms`} color={latency > 200 ? 'var(--accent-red)' : 'var(--accent-green)'} />
        <StatItem label="Frame" value={`#${frameNum.toLocaleString()}`} color="var(--text-secondary)" />
        <StatItem label="Face" value={frameResult?.face?.detected ? 'DETECTED' : 'NONE'} color={frameResult?.face?.detected ? 'var(--accent-green)' : 'var(--accent-red)'} />
        <StatItem label="Objects" value={`${(frameResult?.objects || []).length}`} color="var(--text-secondary)" />
        <StatItem label="Risk" value={`${riskScore.toFixed(0)}/100`} color={RISK_BORDER[riskLevel]} />
      </div>

      {/* Camera 2 — Secondary mobile camera feed */}
      <SecondaryCameraFeed
        sessionId={sessionId || frameResult?.active_session_id}
        camera2Info={camera2Info || frameResult?.camera_2}
      />
    </div>
  )
}

function StatItem({ label, value, color }) {
  return (
    <div className="camera-stat">
      <span className="camera-stat__label">{label}</span>
      <span className="camera-stat__value mono" style={{ color }}>{value}</span>
    </div>
  )
}
