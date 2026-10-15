import { useState, memo } from 'react'
import './CalibrationDebugOverlay.css'

function CalibrationDebugOverlay({ calibrationData }) {
  const [expanded, setExpanded] = useState(false)
  if (!calibrationData) return null

  const {
    status = 'INITIALIZING',
    stage = 'INITIALIZING',
    progress_pct = 0,
    valid_samples = 0,
    target_samples = 30,
    quality_rating = 'UNKNOWN',
    quality_score = 0,
    head_pose_deviation = {},
    gaze_deviation = {},
    gaze_measurement = {},
    gaze_decision = {},
    landmark_quality = 0,
    face_distance_deviation = 0,
    baseline_averages,
    last_rejection_reason = null,
  } = calibrationData

  const safeBaseline = baseline_averages || {}
  const state = gaze_decision.state || (status === 'CALIBRATED' || stage === 'READY' ? 'ON_SCREEN' : 'UNCERTAIN')
  const isReady = status === 'CALIBRATED' || stage === 'READY'
  const stateColor = state === 'ON_SCREEN' ? '#00e676' : state === 'OFF_SCREEN' ? '#ff1744' : '#ff9800'

  const titleText = isReady
    ? `GAZE: ACTIVE (${state})`
    : stage === 'AUTO_CALIBRATING'
    ? `CAMERA VERIFY: ${progress_pct}% (${valid_samples}/${target_samples})`
    : stage === 'WARMING_UP'
    ? `CAMERA VERIFY: WARMING UP...`
    : `GAZE: ${stage || status}`

  return (
    <div className={`calib-debug-hud ${expanded ? 'calib-debug-hud--expanded' : ''}`}>
      <div className="calib-debug-hud__toggle" onClick={() => setExpanded(!expanded)}>
        <span className="calib-debug-hud__dot" style={{ background: isReady ? '#00e676' : '#ff9800' }} />
        <span className="calib-debug-hud__title mono">{titleText}</span>
        <span className="calib-debug-hud__arrow">{expanded ? '▾' : '▴'}</span>
      </div>
      {expanded && (
        <div className="calib-debug-hud__content mono">
          <div className="calib-debug-row"><span>Gaze State:</span><span style={{ color: stateColor }}>{state}</span></div>
          <div className="calib-debug-row"><span>Auto-Calib:</span><span>{isReady ? 'COMPLETE' : `${stage} (${valid_samples}/${target_samples})`}</span></div>
          {!isReady && last_rejection_reason && (
            <div className="calib-debug-row"><span>Reject Reason:</span><span style={{ color: '#ffb74d' }}>{last_rejection_reason}</span></div>
          )}
          <div className="calib-debug-row"><span>Reason:</span><span>{gaze_decision.reason || (isReady ? 'WITHIN_CALIBRATED_SCREEN_REGION' : 'CALIBRATION_IN_PROGRESS')}</span></div>
          <div className="calib-debug-row"><span>Baseline Yaw/Pitch:</span><span>{safeBaseline.yaw ?? 0}° / {safeBaseline.pitch ?? 0}°</span></div>
          <div className="calib-debug-row"><span>Baseline Gaze X/Y:</span><span>{safeBaseline.gaze_x ?? 0} / {safeBaseline.gaze_y ?? 0}</span></div>
          <div className="calib-debug-row"><span>Head Yaw/Pitch Delta:</span><span>{head_pose_deviation.delta_yaw ?? 0}° / {head_pose_deviation.delta_pitch ?? 0}°</span></div>
          <div className="calib-debug-row"><span>Eye Gaze X/Y Delta:</span><span>{gaze_deviation.delta_gaze_x ?? 0} / {gaze_deviation.delta_gaze_y ?? 0}</span></div>
          <div className="calib-debug-row"><span>Raw Gaze X/Y:</span><span>{(gaze_measurement.raw_x ?? gaze_measurement.x ?? 0).toFixed(3)} / {(gaze_measurement.raw_y ?? gaze_measurement.y ?? 0).toFixed(3)}</span></div>
          <div className="calib-debug-row"><span>Filtered Gaze X/Y:</span><span>{(gaze_measurement.filtered_x ?? gaze_measurement.x ?? 0).toFixed(3)} / {(gaze_measurement.filtered_y ?? gaze_measurement.y ?? 0).toFixed(3)}</span></div>
          <div className="calib-debug-row"><span>Eye Quality:</span><span>{Math.round((gaze_measurement.confidence || landmark_quality || 0) * 100)}% {gaze_measurement.iris_visible ? 'IRIS OK' : 'IRIS MISSING'}</span></div>
          <div className="calib-debug-row"><span>Off-Screen Evidence:</span><span>{Math.round((gaze_decision.combined_score || 0) * 100)}% (Req: {Math.round((gaze_decision.required_threshold || 0.45) * 100)}%)</span></div>
          <div className="calib-debug-row"><span>Evidence Breakdown:</span><span>Eye: {Math.round((gaze_decision.eye_score || 0) * 100)}% | Head: {Math.round((gaze_decision.head_support || 0) * 100)}%</span></div>
          <div className="calib-debug-row"><span>Face Distance Delta:</span><span>{face_distance_deviation}</span></div>
        </div>
      )}
    </div>
  )
}

export default memo(CalibrationDebugOverlay)