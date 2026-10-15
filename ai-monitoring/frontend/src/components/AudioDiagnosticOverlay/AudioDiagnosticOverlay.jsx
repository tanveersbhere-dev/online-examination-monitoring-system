import { useState, memo } from 'react'
import './AudioDiagnosticOverlay.css'

function AudioDiagnosticOverlay({ audioData }) {
  const [expanded, setExpanded] = useState(true)

  if (!audioData) return null

  const { ears = [], threshold = 0.46 } = audioData
  const earA = ears.find((e) => e.ear === 'EAR_A') || {}
  const earB = ears.find((e) => e.ear === 'EAR_B') || {}

  const hasAnyRoi = earA.roi_available || earB.roi_available
  const anyAboveThresh = (earA.raw_probability >= threshold) || (earB.raw_probability >= threshold)

  return (
    <div className={`audio-debug-hud ${expanded ? 'audio-debug-hud--expanded' : ''}`}>
      <div className="audio-debug-hud__toggle" onClick={() => setExpanded(!expanded)}>
        <span
          className="audio-debug-hud__dot"
          style={{ background: anyAboveThresh ? '#ff1744' : hasAnyRoi ? '#00e676' : '#718096' }}
        />
        <span className="audio-debug-hud__title mono">
          AUDIO DIAGNOSTIC (Thresh: {threshold})
        </span>
        <span className="audio-debug-hud__arrow">{expanded ? '▾' : '▴'}</span>
      </div>

      {expanded && (
        <div className="audio-debug-hud__content mono">
          <div className="audio-debug-section">
            <div className="audio-debug-section__title">EAR_A (Right Ear / Cam-Left)</div>
            <div className="audio-debug-row">
              <span>ROI:</span>
              <span style={{ color: earA.roi_available ? '#00e676' : '#718096' }}>
                {earA.roi_available ? 'AVAILABLE' : 'MISSING / GATED'}
              </span>
            </div>
            <div className="audio-debug-row">
              <span>Raw Prob:</span>
              <span style={{ color: (earA.raw_probability >= threshold) ? '#ff1744' : '#e2e8f0', fontWeight: 'bold' }}>
                {(earA.raw_probability ?? 0).toFixed(4)}
              </span>
            </div>
            <div className="audio-debug-row">
              <span>Smoothed:</span>
              <span>{(earA.smoothed_probability ?? 0).toFixed(4)}</span>
            </div>
          </div>

          <div className="audio-debug-section" style={{ marginTop: '6px' }}>
            <div className="audio-debug-section__title">EAR_B (Left Ear / Cam-Right)</div>
            <div className="audio-debug-row">
              <span>ROI:</span>
              <span style={{ color: earB.roi_available ? '#00e676' : '#718096' }}>
                {earB.roi_available ? 'AVAILABLE' : 'MISSING / GATED'}
              </span>
            </div>
            <div className="audio-debug-row">
              <span>Raw Prob:</span>
              <span style={{ color: (earB.raw_probability >= threshold) ? '#ff1744' : '#e2e8f0', fontWeight: 'bold' }}>
                {(earB.raw_probability ?? 0).toFixed(4)}
              </span>
            </div>
            <div className="audio-debug-row">
              <span>Smoothed:</span>
              <span>{(earB.smoothed_probability ?? 0).toFixed(4)}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default memo(AudioDiagnosticOverlay)
