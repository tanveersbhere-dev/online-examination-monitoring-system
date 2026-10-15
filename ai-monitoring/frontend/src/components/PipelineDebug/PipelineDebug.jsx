import { useState } from 'react'
import './PipelineDebug.css'

const STATUS_ORDER = ['READY', 'RUNNING', 'SKIPPED', 'FAILED', 'NOT_INITIALIZED']

const STAGE_ICONS = {
  FaceDetector:         '👁',
  LandmarkDetector:     '🗺',
  HeadPoseEstimator:    '🧭',
  EARProcessor:         '👀',
  GazeExtractor:        '🎯',
  BlinkDetector:        '🔺',
  MARProcessor:         '💬',
  FacePresenceTracker:  '📍',
  FaceIdentityProcessor:'🔐',
  ObjectDetector:       '📦',
  ObjectFilter:         '🧹',
  ObjectTracker:        '📡',
  ObjectValidator:      '✅',
  IdentityProtection:   '🛡',
  ObservationFusion:    '🔀',
  RuleEngine:           '⚖',
  BehaviorEngine:       '🧠',
  RiskEngine:           '📊',
  ViolationManager:     '🚨',
}

export default function PipelineDebug({ health }) {
  const [open, setOpen] = useState(false)

  if (!health || typeof health !== 'object') return null

  const entries = Object.entries(health).filter(([k, v]) => v && typeof v === 'object')
  const failedCount = entries.filter(([, v]) => v?.status === 'FAILED').length
  const readyCount  = entries.filter(([, v]) => v?.status === 'READY').length

  return (
    <div className="pipeline-debug glass">
      <button className="pipeline-debug__toggle" onClick={() => setOpen((o) => !o)}>
        <span className="pipeline-debug__title">
          Pipeline Debug
          <span className="pipeline-debug__counts">
            <span className="badge badge--green">{readyCount} READY</span>
            {failedCount > 0 && <span className="badge badge--red">{failedCount} FAILED</span>}
          </span>
        </span>
        <span className="pipeline-debug__chevron">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="pipeline-debug__table-wrap">
          <table className="pipeline-debug__table">
            <thead>
              <tr>
                <th>Stage</th>
                <th>Status</th>
                <th>Time</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              {entries.map(([name, info], idx) => (
                <tr key={name} className={`proc-row proc-row--${info?.status || 'READY'}`}>
                  <td className="proc-row__name">
                    <span className="proc-row__idx">{(idx + 1).toString().padStart(2, '0')}</span>
                    <span className="proc-row__icon">{STAGE_ICONS[name] || '◉'}</span>
                    <span>{name}</span>
                  </td>
                  <td>
                    <span className={`proc-${info?.status || 'READY'}`}>{info?.status || 'READY'}</span>
                  </td>
                  <td className="mono proc-row__time">
                    {typeof info?.time_ms === 'number' && info.time_ms > 0 ? `${info.time_ms.toFixed(1)}ms` : '—'}
                  </td>
                  <td className="proc-row__note">
                    {info?.error && <span title={info.error} className="proc-row__err">⚠ {String(info.error).slice(0, 40)}</span>}
                    {info?.skip_reason && <span className="proc-row__skip">{info.skip_reason}</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
