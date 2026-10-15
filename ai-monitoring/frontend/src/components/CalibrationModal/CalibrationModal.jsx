import { memo } from 'react'
import './CalibrationModal.css'

function CalibrationModal({ calibrationData, onStartCalibration, onResetCalibration, onClose }) {
  const calib = calibrationData || {}
  const status = calib.status || 'INITIALIZING'
  const stage = calib.stage || status
  const qualityRating = calib.quality_rating || 'UNKNOWN'
  const qualityScore = calib.quality_score ?? 0
  const progress = calib.progress_pct ?? (status === 'CALIBRATED' || stage === 'READY' ? 100 : 0)
  const validSamples = calib.valid_samples ?? 0
  const targetSamples = calib.target_samples ?? 30

  const isCalibrating = stage === 'AUTO_CALIBRATING' || stage === 'WARMING_UP' || status === 'CALIBRATING'
  const isCalibrated = status === 'CALIBRATED' || stage === 'READY'
  const isFailed = status === 'FAILED' || status === 'RECALIBRATION_REQUIRED'

  return (
    <div className="calib-overlay">
      <div className="calib-modal">
        <div className="calib-modal__header">
          <div className="calib-modal__title-group">
            <span className="calib-modal__icon">◈</span>
            <div>
              <h2 className="calib-modal__title">Automatic Session Gaze Calibration</h2>
              <p className="calib-modal__subtitle">
                The system automatically learns your screen-facing baseline during the start of the session.
              </p>
            </div>
          </div>
          <button className="calib-modal__close-btn" onClick={onClose}>×</button>
        </div>
        <div className="calib-modal__body">
          <div className="calib-progress-card">
            <div className="calib-progress-card__header">
              <span className="calib-progress-card__status mono">
                STAGE: <strong className={`status-badge status-badge--${stage.toLowerCase()}`}>{stage}</strong>
              </span>
              {isCalibrating && (
                <span className="calib-progress-card__timer mono">
                  {validSamples} / {targetSamples} valid frames ({progress}%)
                </span>
              )}
            </div>
            <div className="calib-progress-bar">
              <div className="calib-progress-bar__fill" style={{ width: `${progress}%` }} />
            </div>
          </div>
          <div className="calib-checklist">
            <h3 className="calib-section-title">Passive Baseline Criteria</h3>
            <div className="calib-checklist__grid">
              <div className="calib-check-item calib-check-item--pass">
                <span className="calib-check-item__icon">✓</span>
                <span>Face & Eyes Visible</span>
              </div>
              <div className="calib-check-item calib-check-item--pass">
                <span className="calib-check-item__icon">✓</span>
                <span>Stable Head Pose</span>
              </div>
              <div className="calib-check-item calib-check-item--pass">
                <span className="calib-check-item__icon">✓</span>
                <span>Dynamic Screen Tolerance</span>
              </div>
            </div>
          </div>
          {isCalibrated && (
            <div className="calib-result-card calib-result-card--success">
              <div className="calib-result-card__rating">
                <span>Personal Baseline Profile:</span>
                <strong className={`rating-badge rating-badge--${qualityRating.toLowerCase()}`}>
                  {qualityRating} ({qualityScore}%)
                </strong>
              </div>
              <p className="calib-result-card__desc">
                Baseline calibrated. Off-screen attention compares iris gaze and head pose against your personal screen baseline with anti-drift protection.
              </p>
            </div>
          )}
          {isFailed && (
            <div className="calib-result-card calib-result-card--fail">
              <p className="calib-result-card__desc">
                Ensure your face and eyes stay clearly visible to complete auto-calibration.
              </p>
            </div>
          )}
        </div>
        <div className="calib-modal__footer">
          {isCalibrated && (
            <button className="calib-btn calib-btn--secondary" onClick={onResetCalibration}>
              ↻ Re-learn Baseline
            </button>
          )}
          {isFailed && (
            <button className="calib-btn calib-btn--primary" onClick={onStartCalibration}>
              ↻ Restart Auto-Calibration
            </button>
          )}
          {isCalibrating && (
            <button className="calib-btn calib-btn--disabled" disabled>
              ⏳ Auto-calibrating in background...
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default memo(CalibrationModal)
