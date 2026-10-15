import { useRef, useEffect, memo } from 'react'
import './BehaviorTimeline.css'

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

function formatBehaviorTitle(ev) {
  const raw = ev.title || ev.incident_title || ev.display_name || ev.type || 'Behavior Pattern'
  if (raw === 'UNKNOWN_VIOLATION' || raw === 'GENERAL_ANOMALY' || raw === 'UNKNOWN') {
    return 'Behavior Pattern'
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
  return raw.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase())
}

function BehaviorTimeline({ behaviorTimeline = [] }) {
  const listRef = useRef(null)

  const filteredTimeline = (behaviorTimeline || []).filter((ev) => {
    const raw = String(ev.type || ev.id || ev.description || '').toUpperCase()
    return !raw.includes('MISMATCH') && !raw.includes('INTEGRITY') && !raw.includes('INSTABILITY')
  })

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight
    }
  }, [filteredTimeline.length])

  return (
    <div className="b-timeline">
      <div className="b-timeline__header">
        <span className="section-title" style={{ marginBottom: 0 }}>
          Behavior Intelligence Timeline
        </span>
        <span className="b-timeline__count mono">{filteredTimeline.length} patterns</span>
      </div>

      <div className="b-timeline__list" ref={listRef}>
        {filteredTimeline.length === 0 && (
          <div className="b-timeline__empty">No composite behavior patterns detected yet</div>
        )}
        {filteredTimeline.map((ev) => {
          const isResolved = ev.transition === 'RESOLVED' || ev.transition === 'RECOVERED'
          return (
            <div key={ev.id} className={`b-tev ${isResolved ? 'b-tev--resolved' : 'b-tev--active'}`}>
              <span className="b-tev__bar" style={{ background: isResolved ? '#607d8b' : '#ff5722' }} />
              <span className="b-tev__time mono">{fmt(ev.timestamp)}</span>
              <span className={`b-tev__badge b-tev__badge--${ev.transition.toLowerCase()}`}>
                {ev.transition}
              </span>
              <span className="b-tev__type">{formatBehaviorTitle(ev)}</span>
              <span className="b-tev__msg">{ev.description}</span>
              {ev.duration_seconds > 0 && (
                <span className="b-tev__dur mono">{ev.duration_seconds}s</span>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default memo(BehaviorTimeline)
