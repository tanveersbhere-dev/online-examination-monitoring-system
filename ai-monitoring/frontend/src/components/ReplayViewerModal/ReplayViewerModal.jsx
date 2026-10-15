import React, { useState, useEffect } from 'react'
import { API_BASE } from '../../config/api'
import './ReplayViewerModal.css'

export default function ReplayViewerModal({ incidentId, onClose }) {
  const [currentFrame, setCurrentFrame] = useState(1)
  const [replayData, setReplayData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchReplay() {
      try {
        const res = await fetch(`${API_BASE}/api/incidents/${incidentId}/replay?frame=${currentFrame}`)
        if (res.ok) {
          const data = await res.json()
          setReplayData(data)
        }
      } catch (e) {
        console.error('Error fetching replay data:', e)
      } finally {
        setLoading(false)
      }
    }
    fetchReplay()
  }, [incidentId, currentFrame])

  // Derive max frame from session data, fallback to 100
  const maxFrame = replayData?.session?.total_frames || 100

  const seekFrame = (f) => {
    if (f >= 1 && f <= maxFrame) setCurrentFrame(f)
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="replay-modal" onClick={(e) => e.stopPropagation()}>
        <div className="replay-modal__header">
          <h3>Replay Intelligence Seeker - Incident #{incidentId}</h3>
          <button className="modal-close-btn" onClick={onClose}>×</button>
        </div>

        {loading ? (
          <div className="replay-loading">Loading Replay Frame...</div>
        ) : (
          <div className="replay-modal__body">
            <div className="replay-canvas-placeholder">
              <div className="replay-frame-indicator">
                Frame #{replayData?.frame_entry?.frame_number || currentFrame} | TS: {replayData?.frame_entry?.timestamp ? replayData.frame_entry.timestamp.toFixed(2) : '0.00'}s
              </div>
              <div className="overlay-info">
                <p><strong>Rule:</strong> {replayData?.overlay?.rule || 'N/A'}</p>
                <p><strong>Confidence:</strong> {replayData?.overlay?.confidence ? (replayData.overlay.confidence * 100).toFixed(0) : 0}%</p>
                <p><strong>Summary:</strong> {replayData?.overlay?.timeline_event_summary || 'N/A'}</p>
              </div>
            </div>

            <div className="replay-milestones">
              <label>Milestone Quick Jumps:</label>
              <div className="milestone-btns">
                <button className="btn-milestone" onClick={() => seekFrame(1)}>🚩 Start</button>
                <button className="btn-milestone" onClick={() => seekFrame(20)}>⚡ Escalation</button>
                <button className="btn-milestone" onClick={() => seekFrame(30)}>🎯 Peak Conf</button>
                <button className="btn-milestone" onClick={() => seekFrame(50)}>🔄 Recovery</button>
                <button className="btn-milestone" onClick={() => seekFrame(80)}>✅ Resolution</button>
              </div>
            </div>

            <div className="replay-scrubber">
              <label>Timeline Scrubber (Frame #{currentFrame} of {maxFrame}):</label>
              <input
                type="range"
                min={1}
                max={maxFrame}
                value={currentFrame}
                onChange={(e) => seekFrame(Number(e.target.value))}
              />
            </div>
          </div>
        )}

        <div className="replay-modal__footer">
          <button className="btn-modal-cancel" onClick={onClose}>Close Replay</button>
        </div>
      </div>
    </div>
  )
}
