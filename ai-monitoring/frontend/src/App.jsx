import { useRef, useEffect, useState, useCallback } from 'react'
import { useWebSocket } from './hooks/useWebSocket'
import { useIncidentStore } from './store/useIncidentStore'
import CameraPanel from './components/CameraPanel/CameraPanel'
import MonitoringPanel from './components/MonitoringPanel/MonitoringPanel'
import PipelineDebug from './components/PipelineDebug/PipelineDebug'
import EventTimeline from './components/EventTimeline/EventTimeline'
import EvidenceGallery from './components/EvidenceGallery/EvidenceGallery'
import StatusBar from './components/StatusBar/StatusBar'
import CalibrationModal from './components/CalibrationModal/CalibrationModal'
import CalibrationDebugOverlay from './components/CalibrationDebugOverlay/CalibrationDebugOverlay'
import AudioDiagnosticOverlay from './components/AudioDiagnosticOverlay/AudioDiagnosticOverlay'
import BehaviorPanel from './components/BehaviorPanel/BehaviorPanel'
import BehaviorTimeline from './components/BehaviorTimeline/BehaviorTimeline'
import MonitoringReport from './components/MonitoringReport/MonitoringReport'

// Incident Intelligence Platform Components (Packages 10.1 - 10.9)
import IncidentDashboard from './components/IncidentDashboard/IncidentDashboard'
import ProctorReviewModal from './components/ProctorReviewModal/ProctorReviewModal'
import ReplayViewerModal from './components/ReplayViewerModal/ReplayViewerModal'
import ExportCaseDialog from './components/ExportCaseDialog/ExportCaseDialog'
import MobileCameraView from './components/MobileCamera/MobileCameraView'

import { API_BASE } from './config/api'
import './App.css'

export default function App() {
  // Mobile camera standalone page mode (accessed via pairing link)
  const isMobileView = typeof window !== 'undefined' && (
    window.location.pathname.startsWith('/mobile') ||
    new URLSearchParams(window.location.search).get('view') === 'mobile'
  )

  if (isMobileView) {
    return <MobileCameraView />
  }

  const videoRef = useRef(null)
  const [events, setEvents] = useState([])
  const [evidenceList, setEvidenceList] = useState([])
  const [systemHealth, setSystemHealth] = useState(null)
  const [showCalibModal, setShowCalibModal] = useState(false)
  const [viewMode, setViewMode] = useState('monitoring') // 'monitoring' | 'report'
  const [currentSessionId, setCurrentSessionId] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const { connected, connecting, frameResult, droppedCount, inferFps } = useWebSocket(videoRef)
  const { incidents, selectedIncidentId, activeModal, selectIncident, closeModal, submitReviewDecision } = useIncidentStore(frameResult)

  // Track active session ID from frame or backend
  useEffect(() => {
    if (frameResult?.active_session_id && !currentSessionId) {
      setCurrentSessionId(frameResult.active_session_id)
    }
  }, [frameResult?.active_session_id, currentSessionId])

  // Fetch initial session if needed
  useEffect(() => {
    fetch(`${API_BASE}/api/session`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data?.session_id) {
          setCurrentSessionId(data.session_id)
        }
      })
      .catch(() => {})
  }, [])

  const handleSubmitMonitoring = useCallback(async () => {
    const sid = currentSessionId || frameResult?.active_session_id || 'active_session'
    setSubmitting(true)
    try {
      const res = await fetch(`${API_BASE}/api/monitoring/sessions/${sid}/submit`, {
        method: 'POST',
      })
      if (res.ok) {
        setViewMode('report')
      } else {
        // Even if server returns 404/error, open report view for this session
        setViewMode('report')
      }
    } catch (err) {
      console.error('Error submitting monitoring session:', err)
      setViewMode('report')
    } finally {
      setSubmitting(false)
    }
  }, [currentSessionId, frameResult?.active_session_id])

  const handleStartNewSession = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/monitoring/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ student_id: 'local_student' }),
      })
      if (res.ok) {
        const data = await res.json()
        setCurrentSessionId(data.session_id)
      }
    } catch (err) {
      console.error('Error creating new session:', err)
    }
    setEvents([])
    setEvidenceList([])
    setViewMode('monitoring')
  }, [])

  // Accumulate & deduplicate evidence gallery state as a rolling FIFO buffer (max 50)
  // Strictly keyed by logical violation ID so one violation = one gallery card
  useEffect(() => {
    if (!frameResult?.evidence || !Array.isArray(frameResult.evidence)) return
    setEvidenceList((prev) => {
      const map = new Map()
      frameResult.evidence.forEach((item) => {
        if (!item || typeof item !== 'object') return
        const key = item.violation_id || item.episode_id || item.id
        if (key) map.set(key, item)
      })
      ;(Array.isArray(prev) ? prev : []).forEach((item) => {
        if (!item || typeof item !== 'object') return
        const key = item.violation_id || item.episode_id || item.id
        if (key && !map.has(key)) map.set(key, item)
      })

      const sorted = Array.from(map.values()).sort(
        (a, b) => (b.timestamp || b.frame_id || 0) - (a.timestamp || a.frame_id || 0)
      )
      return sorted.slice(0, 50)
    })
  }, [frameResult?.evidence])

  // Event Timeline
  useEffect(() => {
    if (!frameResult?.lifecycle_events || !Array.isArray(frameResult.lifecycle_events)) return

    setEvents((prev) => {
      const map = new Map((Array.isArray(prev) ? prev : []).map((ev) => [ev.id, ev]))

      for (const le of frameResult.lifecycle_events) {
        if (!le || typeof le !== 'object') continue
        const id = le.violation_id || le.id
        if (!id) continue
        const eventTitle = le.title || le.incident_title || le.display_name || le.type || 'Behavioral Event'

        const isStarted = le.transition === 'STARTED' || le.event_type === 'STARTED'
        const isResolved = le.transition === 'RESOLVED' || le.event_type === 'RESOLVED'
        const isUpdated = le.transition === 'UPDATED' || le.event_type === 'UPDATED'

        if (isStarted || (!map.has(id) && !isResolved)) {
          map.set(id, {
            id,
            type: le.type || le.violation_type || 'VIOLATION',
            title: eventTitle,
            incident_title: le.incident_title || eventTitle,
            display_name: le.display_name || eventTitle,
            msg: le.description || eventTitle,
            ts: le.started_at || le.start_timestamp || le.timestamp || Date.now() / 1000,
            ended_at: null,
            severity: le.severity || 'ELEVATED',
            category: le.category || le.violation_category || 'BEHAVIOR',
            current_confidence: le.confidence ?? le.current_confidence,
            peak_confidence: le.peak_confidence,
            detection_count: le.detection_count,
            duration: le.duration,
          })
        } else if (isUpdated || (map.has(id) && !isResolved)) {
          const existing = map.get(id)
          if (existing) {
            map.set(id, {
              ...existing,
              title: eventTitle,
              incident_title: le.incident_title || eventTitle,
              display_name: le.display_name || eventTitle,
              severity: le.severity || existing.severity,
              msg: le.description || existing.msg,
              current_confidence: le.confidence ?? le.current_confidence ?? existing.current_confidence,
              peak_confidence: le.peak_confidence ?? existing.peak_confidence,
              detection_count: le.detection_count ?? existing.detection_count,
              duration: le.duration ?? existing.duration,
            })
          }
        } else if (isResolved) {
          const existing = map.get(id)
          if (existing) {
            map.set(id, { ...existing, ended_at: le.ended_at ?? le.end_timestamp ?? le.timestamp ?? Date.now() / 1000 })
          }
        }
      }

      return Array.from(map.values())
        .sort((a, b) => (b.ts || 0) - (a.ts || 0))
        .slice(0, 500)
    })
  }, [frameResult?.frame_number])

  // Poll health endpoint every 3 seconds
  useEffect(() => {
    const poll = async () => {
      try {
        const r = await fetch(`${API_BASE}/health`)
        if (r.ok) setSystemHealth(await r.json())
      } catch (_) {}
    }
    poll()
    const id = setInterval(poll, 3000)
    return () => clearInterval(id)
  }, [])

  // Calibration control handlers — wired to the POST /calibration/* REST endpoints
  const handleStartCalibration = useCallback(async () => {
    try {
      await fetch(`${API_BASE}/calibration/start`, { method: 'POST' })
    } catch (e) {
      console.error('Failed to start calibration:', e)
    }
  }, [])

  const handleResetCalibration = useCallback(async () => {
    try {
      await fetch(`${API_BASE}/calibration/start`, { method: 'POST' })
    } catch (e) {
      console.error('Failed to reset calibration:', e)
    }
  }, [])

  const connectionStatus = connected ? 'connected' : connecting ? 'connecting' : 'error'

  return (
    <div className="app-shell">
      {/* Header */}
      <header className="app-header">
        <div className="app-header__brand">
          <span className="app-header__logo">◈</span>
          <span className="app-header__title">AI Monitoring Playground</span>
          <span className="app-header__subtitle">Behavioral Intelligence & Reasoning Engine</span>
        </div>
        <div className="app-header__status">
          {viewMode === 'monitoring' ? (
            <button
              className="submit-monitoring-btn"
              onClick={handleSubmitMonitoring}
              disabled={submitting}
              title="Finalize monitoring session and generate audit report"
            >
              {submitting ? '⏳ Finalizing...' : '⏹ Submit / End Monitoring'}
            </button>
          ) : (
            <button
              className="submit-monitoring-btn"
              style={{ background: 'rgba(56, 189, 248, 0.15)', borderColor: 'rgba(56, 189, 248, 0.4)', color: '#38bdf8' }}
              onClick={() => setViewMode('monitoring')}
            >
              ▶ Back to Live Camera
            </button>
          )}

          {(() => {
            const calib = frameResult?.calibration || {}
            const stage = calib.stage || calib.status || 'READY'
            const isReady = calib.status === 'CALIBRATED' || stage === 'READY'
            const label = isReady
              ? '✓ Tracking Verified'
              : stage === 'AUTO_CALIBRATING'
              ? `⏳ Verifying Tracking ${calib.progress_pct || 0}%`
              : stage === 'WARMING_UP'
              ? '⏳ Verifying Camera...'
              : '✓ Tracking Verified'
            return (
              <button className="calib-trigger-btn" onClick={() => setShowCalibModal(true)}>
                {label}
              </button>
            )
          })()}
          <span className={`status-dot status-dot--${connectionStatus}`} />
          <span className="app-header__status-text">
            {connected ? 'Pipeline Active' : connecting ? 'Connecting...' : 'Disconnected'}
          </span>
          {frameResult && (
            <span className="app-header__frame mono">
              Frame #{frameResult.frame_number?.toLocaleString()}
            </span>
          )}
        </div>
      </header>

      {/* Main Body: Switch between Report View and Live Monitoring Grid */}
      {viewMode === 'report' ? (
        <MonitoringReport
          sessionId={currentSessionId || frameResult?.active_session_id}
          onStartNewSession={handleStartNewSession}
        />
      ) : (
        <>
          {/* Main grid */}
          <div className="app-main">
            {/* LEFT — Camera */}
            <section className="app-camera" style={{ position: 'relative' }}>
              <AudioDiagnosticOverlay audioData={frameResult?.wearable_audio_debug} />
              <CalibrationDebugOverlay calibrationData={frameResult?.calibration} />
              <CameraPanel
                videoRef={videoRef}
                frameResult={frameResult}
                connected={connected}
                connectionStatus={connectionStatus}
                sessionId={currentSessionId || frameResult?.active_session_id}
                camera2Info={frameResult?.camera_2}
              />
            </section>

            {/* CENTER — Monitoring & Behavioral Reasoning */}
            <section className="app-monitoring">
              <BehaviorPanel behaviorData={frameResult?.behavior} />
              <MonitoringPanel frameResult={frameResult} />
              <PipelineDebug health={frameResult?.pipeline_health || systemHealth?.pipeline?.processors} />
            </section>

            {/* RIGHT — Evidence */}
            <aside className="app-evidence">
              <EvidenceGallery evidence={evidenceList} />
            </aside>
          </div>

          {/* Incident Dashboard (Packages 10.1 - 10.9) */}
          <IncidentDashboard incidents={incidents} onSelectIncident={selectIncident} />

          {/* Bottom — Dual Timelines */}
          <div className="app-timeline" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginTop: '12px' }}>
            <EventTimeline events={events} frameResult={frameResult} />
            <BehaviorTimeline behaviorTimeline={frameResult?.behavior?.timeline || []} />
          </div>
        </>
      )}

      {/* Incident Intelligence Modals */}
      {activeModal === 'review' && selectedIncidentId && (
        <ProctorReviewModal incidentId={selectedIncidentId} onClose={closeModal} onSubmitDecision={submitReviewDecision} />
      )}
      {activeModal === 'replay' && selectedIncidentId && (
        <ReplayViewerModal incidentId={selectedIncidentId} onClose={closeModal} />
      )}
      {activeModal === 'export' && selectedIncidentId && (
        <ExportCaseDialog incidentId={selectedIncidentId} onClose={closeModal} />
      )}

      {/* Calibration Modal */}
      {showCalibModal && (
        <CalibrationModal
          calibrationData={frameResult?.calibration}
          onStartCalibration={handleStartCalibration}
          onResetCalibration={handleResetCalibration}
          onClose={() => setShowCalibModal(false)}
        />
      )}

      {/* Status Bar */}
      <StatusBar
        frameResult={frameResult}
        systemHealth={systemHealth}
        droppedCount={droppedCount}
        inferFps={inferFps}
        connected={connected}
      />
    </div>
  )
}
