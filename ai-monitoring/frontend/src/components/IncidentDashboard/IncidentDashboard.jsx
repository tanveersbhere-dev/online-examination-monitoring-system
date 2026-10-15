import React from 'react'
import './IncidentDashboard.css'

const STATUS_LABEL = {
  ACTIVE: 'ACTIVE',
  OPEN: 'ACTIVE',
  REVIEWED: 'REVIEWED',
  RESOLVED: 'RESOLVED',
  CLOSED: 'CLOSED',
}

const STATUS_CLASS = {
  ACTIVE: 'incident-card--active',
  OPEN: 'incident-card--active',
  REVIEWED: 'incident-card--reviewed',
  RESOLVED: 'incident-card--resolved',
  CLOSED: 'incident-card--resolved',
}

function formatIncidentTitle(inc) {
  const raw = inc.title || inc.incident_type || inc.display_name || 'Behavioral Incident'
  if (raw === 'UNKNOWN_VIOLATION' || raw === 'GENERAL_ANOMALY' || raw === 'UNKNOWN') {
    return 'Behavioral Incident'
  }
  const map = {
    UNAUTH_PHONE: 'Unauthorized Cell Phone',
    UNAUTH_LAPTOP: 'Unauthorized Laptop',
    UNAUTH_BOOK: 'Unauthorized Book',
    UNAUTH_NOTEBOOK: 'Unauthorized Notebook',
    UNAUTH_PAPER: 'Unauthorized Paper',
    OFF_SCREEN_ATTENTION: 'Off-Screen Attention',
    ATT_LOOKING_AWAY: 'Off-Screen Attention',
    ATT_DOWNWARD_GAZE: 'Downward Gaze',
    ID_FACE_MISSING: 'Face Absence Detected',
    ID_MULTIPLE_FACES: 'Multiple Persons Detected',
    COMM_MULTIPLE_PERSONS: 'Multiple Persons Detected',
    COMM_EARPHONES: 'Unauthorized Audio Device',
    COMM_HEADPHONES: 'Unauthorized Audio Device',
    COMM_NECKBAND: 'Unauthorized Audio Device',
    UNAUTH_VOICE: 'Unauthorized Human Voice',
    BEHAVIOR_REPEATED_PATTERN: 'Repeated Behavior Pattern',
  }
  if (map[raw]) return map[raw]
  if (map[inc.incident_type]) return map[inc.incident_type]
  return raw.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase())
}

export default function IncidentDashboard({ incidents, onSelectIncident }) {
  const filteredIncidents = (incidents || []).filter((i) => {
    const raw = String(i.incident_type || i.id || '').toUpperCase()
    return !raw.includes('MISMATCH') && !raw.includes('INTEGRITY') && !raw.includes('INSTABILITY')
  })

  if (!filteredIncidents || filteredIncidents.length === 0) {
    return (
      <div className="incident-dashboard-empty">
        <div className="incident-empty-icon">🛡️</div>
        <p>No behavioral incidents recorded in session.</p>
      </div>
    )
  }

  const activeCount = filteredIncidents.filter(
    (i) => i.status === 'ACTIVE' || i.status === 'OPEN'
  ).length

  return (
    <div className="incident-dashboard">
      <div className="incident-dashboard__header">
        <h3>Incident Intelligence Dashboard</h3>
        <div className="incident-dashboard__counts">
          {activeCount > 0 && (
            <span className="incident-count-badge incident-count-badge--active">
              {activeCount} Active
            </span>
          )}
          <span className="incident-count-badge">
            {filteredIncidents.length} Total
          </span>
        </div>
      </div>
      <div className="incident-grid">
        {incidents.map((inc) => {
          const sev = inc.severity || 'ELEVATED'
          const status = inc.status || 'ACTIVE'
          const statusLabel = STATUS_LABEL[status] || status
          const isResolved = status === 'RESOLVED' || status === 'CLOSED' || status === 'REVIEWED'
          const cardClass = STATUS_CLASS[status] || 'incident-card--active'

          return (
            <div
              key={inc.incident_id}
              className={`incident-card incident-card--${sev.toLowerCase()} ${cardClass}`}
            >
              <div className="incident-card__top">
                <span className={`sev-badge sev-badge--${sev.toLowerCase()}`}>{sev}</span>
                <span
                  className={`status-badge-pill status-badge-pill--${statusLabel.toLowerCase()}`}
                >
                  {statusLabel}
                </span>
                <span className="inc-id mono">{inc.incident_id}</span>
              </div>
              <h4 className="inc-title">{formatIncidentTitle(inc)}</h4>
              <div className="inc-meta">
                <span>⏱ {inc.duration ? `${inc.duration.toFixed(1)}s` : 'Active'}</span>
                <span>🎯 Conf: {(inc.current_confidence ?? inc.peak_confidence) != null ? ((inc.current_confidence ?? inc.peak_confidence) * 100).toFixed(0) : 90}%</span>
                <span>⚡ Risk: {inc.current_risk || 50}</span>
              </div>
              {inc.reason_codes?.length > 0 && (
                <div className="inc-reasons">
                  {inc.reason_codes.map((rc) => (
                    <span key={rc} className="rc-tag">{rc}</span>
                  ))}
                </div>
              )}
              {/* Action buttons — Review/Replay/Export are always available for audit trail */}
              <div className="inc-actions">
                <button
                  className="btn-inc-action btn-review"
                  onClick={() => onSelectIncident(inc.incident_id, 'review')}
                >
                  📋 Review
                </button>
                <button
                  className="btn-inc-action btn-replay"
                  onClick={() => onSelectIncident(inc.incident_id, 'replay')}
                >
                  ▶ Replay
                </button>
                <button
                  className="btn-inc-action btn-export"
                  onClick={() => onSelectIncident(inc.incident_id, 'export')}
                >
                  📥 Export
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
