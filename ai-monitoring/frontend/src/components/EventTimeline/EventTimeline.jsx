import { useRef, useEffect, memo } from 'react'
import './EventTimeline.css'

const EVENT_COLOUR = {
  FACE_ABSENT:      '#ff9800',
  FACE_MISSING:     '#ff9800',
  ID_FACE_MISSING:  '#ff9800',
  MULTIPLE_FACES:   '#ff5722',
  ID_MULTIPLE_FACES:'#ff5722',
  UNAUTH_PHONE:     '#f44336',
  UNAUTH_LAPTOP:    '#e53935',
  UNAUTH_BOOK:      '#ce93d8',
  COMM_EARPHONES:   '#e91e63',
  COMM_HEADPHONES:  '#e91e63',
  ATT_LOOKING_AWAY: '#2196f3',
  ATT_DOWNWARD_GAZE:'#42a5f5',
  ENV_CAM_OCCLUDED: '#ff9800',
  ENV_CAM_COVERED:  '#ff5722',
  DEFAULT:          '#607d8b',
}

function getColor(type) {
  for (const [k, v] of Object.entries(EVENT_COLOUR)) {
    if (type && type.includes(k)) return v
  }
  return EVENT_COLOUR.DEFAULT
}

function fmt(ts) {
  if (!ts || isNaN(ts)) return '--:--:--'
  try {
    return new Date(ts * 1000).toLocaleTimeString('en', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  } catch (_) {
    return '--:--:--'
  }
}

function fmtDuration(seconds) {
  if (seconds < 60) return `${seconds}s`
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}m ${s}s`
}

function formatEventTitle(ev) {
  if (!ev) return 'Behavioral Event'
  const raw = ev.title || ev.incident_title || ev.display_name || ev.type || 'Behavioral Event'
  if (raw === 'UNKNOWN_VIOLATION' || raw === 'GENERAL_ANOMALY' || raw === 'UNKNOWN') {
    return 'Behavioral Anomaly'
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
    BEHAVIOR_REPEATED_PATTERN: 'Repeated Behavior Pattern',
  }
  if (map[raw]) return map[raw]
  if (map[ev.type]) return map[ev.type]
  return String(raw).replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase())
}

function EventTimeline({ events = [] }) {
  const listRef = useRef(null)

  const filteredEvents = (events || []).filter((ev) => {
    const raw = String(ev.type || ev.id || ev.title || '').toUpperCase()
    return !raw.includes('MISMATCH') && !raw.includes('INTEGRITY') && !raw.includes('INSTABILITY')
  })

  // Auto-scroll to bottom when a new violation is added (not on updates)
  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight
    }
  }, [filteredEvents.length])

  const activeCount = filteredEvents.filter((ev) => !ev.ended_at).length

  return (
    <div className="timeline">
      <div className="timeline__header">
        <span className="section-title" style={{ marginBottom: 0 }}>
          Event Timeline
        </span>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {activeCount > 0 && (
            <span className="timeline__active-badge">{activeCount} active</span>
          )}
          <span className="timeline__count mono">{filteredEvents.length} violations</span>
        </div>
      </div>

      <div className="timeline__list" ref={listRef}>
        {filteredEvents.length === 0 && (
          <div className="timeline__empty">Monitoring — no violations yet</div>
        )}
        {filteredEvents.map((ev) => {
          const color = getColor(ev.type)
          const isResolved = Boolean(ev.ended_at)
          const duration =
            ev.ended_at && ev.ts
              ? fmtDuration(Math.round(ev.ended_at - ev.ts))
              : null

          return (
            <div
              key={ev.id}
              className={`tev fade-in${isResolved ? ' tev--resolved' : ' tev--active'}`}
            >
              <span
                className="tev__bar"
                style={{ background: isResolved ? '#455a64' : color }}
              />
              <span className="tev__time mono">{fmt(ev.ts)}</span>
              <span
                className={`tev__badge ${isResolved ? 'tev__badge--ended' : 'tev__badge--live'}`}
              >
                {isResolved ? 'ENDED' : 'ACTIVE'}
              </span>
              <span
                className="tev__type"
                style={{ color: isResolved ? '#78909c' : color }}
              >
                {formatEventTitle(ev)}
                {ev.camera_id && (
                  <span className="badge badge--dark" style={{ fontSize: 9, marginLeft: 6 }}>
                    {ev.camera_id === 'camera_2' ? 'Cam 2' : 'Cam 1'}
                  </span>
                )}
              </span>
              <span className="tev__msg">{ev.msg}</span>
              {isResolved && duration && (
                <span className="tev__duration mono">{duration}</span>
              )}
              {!isResolved && (
                <span className="tev__live-dot" title="Violation currently active" />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default memo(EventTimeline)
