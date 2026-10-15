import { useState, memo } from 'react'
import { API_BASE } from '../../config/api'
import './EvidenceGallery.css'

function fmt(ts) {
  if (!ts || isNaN(ts)) return '--:--:--'
  try {
    return new Date(ts * 1000).toLocaleTimeString('en', { hour12: false })
  } catch (_) {
    return '--:--:--'
  }
}

function formatRuleName(ruleId, ruleName) {
  if (ruleName) return ruleName
  if (!ruleId) return 'Violation'
  const map = {
    UNAUTH_PHONE: 'Unauthorized Cell Phone',
    UNAUTH_LAPTOP: 'Unauthorized Laptop',
    UNAUTH_BOOK: 'Unauthorized Book',
    UNAUTH_NOTEBOOK: 'Unauthorized Notebook',
    UNAUTH_PAPER: 'Unauthorized Paper',
    ID_FACE_MISSING: 'Face Missing',
    ID_MULTIPLE_FACES: 'Multiple Faces',
    ATT_LOOKING_AWAY: 'Looking Away',
    ATT_DOWNWARD_GAZE: 'Downward Gaze',
    BEHAVIOR_REPEATED_PATTERN: 'Repeated Behavior Pattern',
    UNAUTH_VOICE: 'Unauthorized Human Voice'
  }
  if (map[ruleId]) return map[ruleId]
  return ruleId.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase())
}

function formatObjectType(typeStr) {
  if (!typeStr) return 'Object'
  const map = {
    CELL_PHONE: 'Cell Phone',
    BOOK: 'Book',
    NOTEBOOK: 'Notebook',
    PAPER: 'Paper',
    LAPTOP: 'Laptop',
    TABLET: 'Tablet',
    MONITOR: 'Monitor',
    EARBUDS: 'Earbuds',
    HEADPHONES: 'Headphones',
    PERSON: 'Person'
  }
  if (map[typeStr]) return map[typeStr]
  return typeStr.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase())
}

function getViolations(ev) {
  if (Array.isArray(ev.contributing_violations) && ev.contributing_violations.length > 0) {
    return ev.contributing_violations
  }
  return [{ rule_id: ev.rule_id, category: ev.category }]
}

function getFacesInfo(ev) {
  const faces = []
  if (ev.identity_verification_result) {
    const idRes = ev.identity_verification_result
    if (idRes.consistent) {
      faces.push('Candidate')
    } else {
      faces.push('Unknown Person')
    }
  } else if (Array.isArray(ev.detected_faces) && ev.detected_faces.length > 0) {
    faces.push('Candidate')
  }
  return faces
}

function EvidenceGallery({ evidence = [] }) {
  const [selected, setSelected] = useState(null)
  const [activeSnapshotIdx, setActiveSnapshotIdx] = useState(0)

  // Ensure newest evidence items are displayed first and exclude removed violations
  const displayList = [...evidence]
    .filter((ev) => {
      const raw = String(ev.rule_id || ev.incident_type || ev.violation_type || ev.category || '').toUpperCase()
      return !raw.includes('MISMATCH') && !raw.includes('INTEGRITY') && !raw.includes('INSTABILITY')
    })
    .sort(
      (a, b) => (b.timestamp || b.frame_id || 0) - (a.timestamp || a.frame_id || 0)
    )

  return (
    <div className="evidence-gallery">
      <div className="evidence-gallery__header">
        <span className="section-title" style={{ marginBottom: 0 }}>Evidence Gallery</span>
        <span className="badge badge--red">{displayList.length}</span>
      </div>

      {displayList.length === 0 ? (
        <div className="evidence-gallery__empty">
          <div className="evidence-gallery__empty-icon">📷</div>
          <div>No evidence captured yet</div>
          <div className="evidence-gallery__empty-sub">Snapshots are saved when violations are confirmed</div>
        </div>
      ) : (
        <div className="evidence-gallery__list">
          {displayList.map((ev) => {
            const key = ev.violation_id || ev.id || ev.episode_id || ev.filename
            const isSelected = selected && (selected.violation_id === ev.violation_id || selected.id === ev.id)
            const violations = getViolations(ev)
            const isComposite = violations.length > 1
            const snapshotCount = Array.isArray(ev.snapshots) ? ev.snapshots.length : 1
            const currentImg = ev.latest_filename || ev.filename
            const isAudio = Boolean((currentImg && currentImg.endsWith('.wav')) || ev.evidence_type === 'AUDIO' || ev.rule_id === 'UNAUTH_VOICE')

            return (
              <div
                key={key}
                className={`evidence-item ${isSelected ? 'evidence-item--selected' : ''}`}
                onClick={() => {
                  setSelected(isSelected ? null : ev)
                  setActiveSnapshotIdx(0)
                }}
              >
                <div className="evidence-item__thumb">
                  {isAudio ? (
                    <div style={{
                      width: '100%',
                      height: '100%',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      background: 'linear-gradient(135deg, #1e1b4b 0%, #312e81 100%)',
                      color: '#a5b4fc',
                    }}>
                      <span style={{ fontSize: 20 }}>🎤</span>
                      <span style={{ fontSize: 9, fontWeight: 700, marginTop: 2, letterSpacing: '0.5px' }}>AUDIO</span>
                    </div>
                  ) : (
                    <img
                      src={`${API_BASE}/evidence/${currentImg}`}
                      alt={ev.rule_id || 'Evidence'}
                      loading="lazy"
                      onError={(e) => {
                        e.target.onerror = null
                        e.target.style.opacity = '0.4'
                      }}
                    />
                  )}
                  {snapshotCount > 1 && (
                    <span className="badge badge--dark" style={{ position: 'absolute', bottom: 4, right: 4, fontSize: 9, padding: '2px 5px' }}>
                      📸 {snapshotCount}
                    </span>
                  )}
                </div>
                <div className="evidence-item__meta">
                  <div className="evidence-item__rule-container">
                    <span className="evidence-item__rule badge badge--red">
                      {ev.title || ev.incident_title || ev.behavior_type || (isComposite ? 'Multi-Signal Anomaly' : formatRuleName(ev.rule_id))}
                    </span>
                    {isComposite && (
                      <span className="badge badge--dark" style={{ fontSize: 9, marginLeft: 4 }}>
                        +{violations.length}
                      </span>
                    )}
                    {ev.camera_id && (
                      <span className="badge badge--dark" style={{ fontSize: 9, marginLeft: 4 }}>
                        {ev.camera_id === 'camera_2' ? 'Cam 2 (Phone)' : 'Cam 1 (Webcam)'}
                      </span>
                    )}
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 4 }}>
                    <span className="evidence-item__time mono">{fmt(ev.timestamp)}</span>
                    <span className={`badge ${ev.status === 'ACTIVE' ? 'badge--yellow' : 'badge--green'}`} style={{ fontSize: 9 }}>
                      {ev.status === 'ACTIVE' ? `ACTIVE ${ev.total_duration ? `${ev.total_duration.toFixed(1)}s` : ''}` : 'RESOLVED'}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>
                    <span className="mono">UUID: {(ev.violation_id || ev.id || '').replace('EV-', '')}</span>
                    <span className="mono">Conf: {Math.round((ev.current_confidence ?? ev.peak_confidence ?? ev.confidence ?? 0.9) * 100)}%</span>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Detail view modal */}
      {selected && (
        <div className="evidence-detail" onClick={() => setSelected(null)}>
          <div className="evidence-detail__content" onClick={(e) => e.stopPropagation()}>
            {(() => {
              const snapshotsList = Array.isArray(selected.snapshots) && selected.snapshots.length > 0
                ? selected.snapshots
                : [{ filename: selected.filename, snapshot_type: 'INITIAL_CONFIRMATION' }]
              const currentSnap = snapshotsList[Math.min(activeSnapshotIdx, snapshotsList.length - 1)] || snapshotsList[0]

              return (
                <>
                  <div style={{ position: 'relative' }}>
                    {Boolean(currentSnap?.filename?.endsWith('.wav') || selected.evidence_type === 'AUDIO' || selected.rule_id === 'UNAUTH_VOICE') ? (
                      <div style={{
                        padding: '40px 24px',
                        background: 'linear-gradient(180deg, #0f172a 0%, #1e1b4b 100%)',
                        textAlign: 'center',
                        borderRadius: 8,
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                      }}>
                        <div style={{ fontSize: 48, marginBottom: 12 }}>🎤</div>
                        <div style={{ fontSize: 16, fontWeight: 700, color: '#f8fafc', marginBottom: 4 }}>
                          Human Voice Audio Evidence
                        </div>
                        <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 20 }}>
                          Laptop Microphone Recording • 16kHz Mono PCM
                        </div>
                        <audio
                          controls
                          src={`${API_BASE}/evidence/${currentSnap.filename}`}
                          style={{ width: '100%', maxWidth: 420, outline: 'none' }}
                        />
                      </div>
                    ) : (
                      <img
                        src={`${API_BASE}/evidence/${currentSnap.filename}`}
                        alt={selected.rule_id}
                        className="evidence-detail__img"
                      />
                    )}
                    {snapshotsList.length > 1 && (
                      <div style={{ display: 'flex', gap: 6, padding: '8px 12px', background: 'rgba(0,0,0,0.85)', overflowX: 'auto' }}>
                        {snapshotsList.map((snap, sIdx) => (
                          <div
                            key={snap.id || sIdx}
                            onClick={() => setActiveSnapshotIdx(sIdx)}
                            style={{
                              border: activeSnapshotIdx === sIdx ? '2px solid #ff4444' : '1px solid #444',
                              borderRadius: 4,
                              overflow: 'hidden',
                              cursor: 'pointer',
                              opacity: activeSnapshotIdx === sIdx ? 1 : 0.6,
                              width: 60,
                              height: 45,
                              flexShrink: 0
                            }}
                          >
                            <img
                              src={`${API_BASE}/evidence/${snap.filename}`}
                              alt={`Keyframe ${sIdx + 1}`}
                              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                            />
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="evidence-detail__card">
                    <div className="evidence-detail__title">
                      {selected.title || selected.incident_title || selected.behavior_type || (getViolations(selected).length > 1
                        ? 'Multi-Signal Anomaly'
                        : formatRuleName(selected.rule_id))}
                    </div>

                    <div style={{ display: 'flex', gap: 8, margin: '8px 0', fontSize: 11, flexWrap: 'wrap' }}>
                      <span className="badge badge--red">UUID: {(selected.violation_id || selected.id || '').replace('EV-', '')}</span>
                      {((currentSnap && currentSnap.camera_id) || selected.camera_id) && (
                        <span className="badge badge--dark">
                          {((currentSnap && currentSnap.camera_id) || selected.camera_id) === 'camera_2' ? 'Camera 2 (Mobile)' : 'Camera 1 (Laptop)'}
                        </span>
                      )}
                      <span className="badge badge--dark">Duration: {selected.total_duration ? `${selected.total_duration.toFixed(1)}s` : '0.1s'}</span>
                      <span className="badge badge--dark">Current Conf: {Math.round((selected.current_confidence ?? selected.peak_confidence ?? selected.confidence ?? 0.9) * 100)}%</span>
                      <span className={`badge ${selected.status === 'ACTIVE' ? 'badge--yellow' : 'badge--green'}`}>Status: {selected.status || 'ACTIVE'}</span>
                    </div>

                    <div className="evidence-detail__section">
                      <div className="evidence-detail__subtitle">Contributing Triggers:</div>
                      <div className="evidence-detail__v-list">
                        {getViolations(selected).map((v, idx) => (
                          <div key={idx} className="evidence-detail__v-item">
                            <span className="checkmark">✓</span> {formatRuleName(v.rule_id, v.rule_name)}
                          </div>
                        ))}
                      </div>
                    </div>

                    {Array.isArray(selected.detected_objects) && selected.detected_objects.length > 0 && (
                      <div className="evidence-detail__section">
                        <div className="evidence-detail__subtitle">Associated Objects:</div>
                        <div className="evidence-detail__sub-list">
                          {selected.detected_objects.map((obj, idx) => (
                            <div key={idx} className="evidence-detail__subitem">
                              - {formatObjectType(obj.type)} ({typeof obj.confidence === 'number' ? obj.confidence.toFixed(2) : obj.confidence})
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {getFacesInfo(selected).length > 0 && (
                      <div className="evidence-detail__section">
                        <div className="evidence-detail__subtitle">Biometric Face Info:</div>
                        <div className="evidence-detail__sub-list">
                          {getFacesInfo(selected).map((fText, idx) => (
                            <div key={idx} className="evidence-detail__subitem">
                              - {fText}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </>
              )
            })()}
            <div className="evidence-detail__close" onClick={() => setSelected(null)}>✕ close</div>
          </div>
        </div>
      )}
    </div>
  )
}


export default memo(EvidenceGallery)
