import { memo } from 'react'
import './MonitoringPanel.css'

// ─── tiny sub-components ──────────────────────────────────────────

function MetricRow({ label, value, unit = '', color }) {
  return (
    <div className="mrow">
      <span className="mrow__label">{label}</span>
      <span className="mrow__value mono" style={color ? { color } : undefined}>
        {value}{unit && <span className="mrow__unit"> {unit}</span>}
      </span>
    </div>
  )
}

function StateIndicator({ state, label, on, offColor, onColor }) {
  return (
    <div className={`state-ind ${on ? 'state-ind--on' : 'state-ind--off'}`}
      style={{
        '--on-color': onColor || 'var(--accent-green)',
        '--off-color': offColor || 'var(--text-muted)',
      }}>
      <span className="state-ind__dot" />
      <span className="state-ind__label">{label}</span>
      {state && <span className="state-ind__state">{state}</span>}
    </div>
  )
}

function Card({ title, children, className = '' }) {
  return (
    <div className={`mcard ${className}`}>
      <div className="section-title">{title}</div>
      {children}
    </div>
  )
}

// ─── angle gauge ─────────────────────────────────────────────────

function AngleGauge({ label, value = 0, limit = 30 }) {
  const numVal = typeof value === 'number' && !isNaN(value) ? value : 0
  const pct = Math.min(Math.abs(numVal) / limit, 1)
  const isOver = Math.abs(numVal) > limit
  const fill = isOver ? 'var(--accent-red)' : numVal > 0 ? 'var(--accent-cyan)' : 'var(--accent-violet)'
  const barW = `${pct * 50}%`
  const barLeft = numVal >= 0 ? '50%' : `${50 - pct * 50}%`

  return (
    <div className="angle-gauge">
      <span className="angle-gauge__label">{label}</span>
      <div className="angle-gauge__track">
        <div className="angle-gauge__center" />
        <div className="angle-gauge__fill" style={{ width: barW, left: barLeft, background: fill }} />
      </div>
      <span className="angle-gauge__val mono" style={{ color: fill }}>{numVal.toFixed(1)}°</span>
    </div>
  )
}

// ─── risk meter ───────────────────────────────────────────────────

function RiskMeter({ score = 0, level = 'NORMAL' }) {
  const numScore = typeof score === 'number' && !isNaN(score) ? score : 0
  const fill = {
    NORMAL: '#4caf50', LOW: '#8bc34a', MEDIUM: '#ff9800', HIGH: '#ff5722', CRITICAL: '#ff1744'
  }[level] || '#4caf50'

  return (
    <div className="risk-meter">
      <div className="risk-meter__bar-bg">
        <div className="risk-meter__bar-fill" style={{ width: `${Math.min(numScore, 100)}%`, background: fill }} />
      </div>
      <div className="risk-meter__labels">
        <span className="mono" style={{ color: fill, fontWeight: 700 }}>{numScore.toFixed(0)}/100</span>
        <span className="risk-meter__level" style={{ color: fill }}>{level}</span>
      </div>
    </div>
  )
}

// ─── Main Monitoring Panel ────────────────────────────────────────

function formatViolationTitle(v) {
  const raw = v.title || v.incident_title || v.display_name || v.type || 'Behavioral Violation'
  if (raw === 'UNKNOWN_VIOLATION' || raw === 'GENERAL_ANOMALY' || raw === 'UNKNOWN') {
    return 'Behavioral Violation'
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
    EARPHONE_DEVICE: 'Unauthorized Audio Device',
    UNAUTH_VOICE: 'Unauthorized Human Voice',
    BEHAVIOR_REPEATED_PATTERN: 'Repeated Behavior Pattern',
  }
  if (map[raw]) return map[raw]
  if (map[v.type]) return map[v.type]
  return raw.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase())
}

function MonitoringPanel({ frameResult }) {
  if (!frameResult) {
    return (
      <div className="monitoring-panel monitoring-panel--empty">
        <div className="monitoring-panel__idle">Awaiting first frame…</div>
      </div>
    )
  }

  const { face, identity, head_pose, gaze, blink, mouth, objects, risk, violations, liveness } = frameResult

  const riskLevel = risk?.level || 'NORMAL'
  const riskScore = risk?.score ?? 0

  return (
    <div className="monitoring-panel">

      {/* ── Face + Identity ── */}
      <Card title="Face Detection">
        <div className="state-row">
          <StateIndicator
            on={face?.detected}
            onColor="var(--accent-green)"
            offColor="var(--accent-red)"
            label={face?.detected ? 'DETECTED' : 'ABSENT'}
            state={`${(face?.confidence * 100 || 0).toFixed(0)}%`}
          />
          <StateIndicator
            on={true}
            onColor="var(--accent-green)"
            label="IDENTITY OK"
            state={`${(identity?.confidence * 100 || 0).toFixed(0)}%`}
          />
        </div>
        <MetricRow label="Presence State" value={face?.presence_state || 'UNKNOWN'} />
        <MetricRow label="Absent Duration" value={(face?.absent_duration || 0).toFixed(1)} unit="s" />
        <MetricRow label="Identity Similarity" value={(identity?.similarity_score || 0).toFixed(3)} color="var(--accent-cyan)" />
        <MetricRow label="Detection Time" value={(face?.processing_time_ms || 0).toFixed(1)} unit="ms" />
      </Card>

      {/* ── Head Pose ── */}
      <Card title="Head Pose">
        <MetricRow label="Pose Class" value={head_pose?.pose_class || 'UNKNOWN'} color="var(--accent-cyan)" />
        <AngleGauge label="Yaw"   value={head_pose?.yaw   || 0} limit={30} />
        <AngleGauge label="Pitch" value={head_pose?.pitch || 0} limit={20} />
        <AngleGauge label="Roll"  value={head_pose?.roll  || 0} limit={20} />
      </Card>

      {/* ── Eyes ── */}
      <Card title="Eyes / Gaze / Blink">
        <div className="state-row">
          <StateIndicator on={gaze?.state === 'CENTER'} label="Gaze" state={gaze?.state || 'UNKNOWN'} onColor="var(--accent-cyan)" />
          <StateIndicator on={blink?.eye_state === 'OPEN'} label="Eye State" state={blink?.eye_state || 'UNKNOWN'} onColor="var(--accent-green)" offColor="var(--accent-orange)" />
        </div>
        <MetricRow label="Gaze Confidence" value={(gaze?.confidence || 0).toFixed(3)} color="var(--accent-cyan)" />
        <MetricRow label="Blink Frequency" value={(blink?.frequency || 0).toFixed(1)} unit="/min" />
        <MetricRow label="EAR Left"  value={(blink?.ear?.left  || 0).toFixed(3)} />
        <MetricRow label="EAR Right" value={(blink?.ear?.right || 0).toFixed(3)} />
        <MetricRow label="EAR Avg"   value={(blink?.ear?.average || 0).toFixed(3)} color="var(--accent-cyan)" />
      </Card>

      {/* ── Mouth ── */}
      <Card title="Mouth / Speech">
        <div className="state-row">
          <StateIndicator on={mouth?.is_talking} label="Talking" onColor="var(--accent-orange)" offColor="var(--text-muted)" />
        </div>
        <MetricRow label="MAR" value={(mouth?.mar || 0).toFixed(3)} color="var(--accent-cyan)" />
        <MetricRow label="Talking Duration" value={(mouth?.talking_seconds || 0).toFixed(1)} unit="s" />
        <MetricRow label="Confidence" value={(mouth?.confidence || 0).toFixed(3)} />
      </Card>

      {/* ── Risk ── */}
      <Card title={`Risk — ${riskLevel}`} className={`mcard--risk bg-risk--${riskLevel}`}>
        <RiskMeter score={riskScore} level={riskLevel} />
        <MetricRow label="Triggered Rules" value={risk?.triggered_rules ?? 0} color={riskScore > 60 ? 'var(--accent-red)' : 'var(--text-primary)'} />
        <MetricRow label="Top Rule" value={risk?.highest_rule || 'NONE'} />
        {(risk?.contributions || []).slice(0, 3).map((c) => (
          <MetricRow key={c.rule_id} label={c.rule_id} value={`+${c.contribution.toFixed(1)}`} color="var(--accent-orange)" />
        ))}
      </Card>

      {/* ── Violations ── */}
      <Card title="Active Violations">
        {(() => {
          const visibleViolations = (violations || []).filter((v) => {
            const raw = String(v.type || v.rule_id || v.id || '').toUpperCase()
            return !raw.includes('MISMATCH') && !raw.includes('INTEGRITY') && !raw.includes('INSTABILITY')
          })
          return visibleViolations.length > 0 ? (
            visibleViolations.slice(0, 5).map((v) => (
              <div key={v.id} className="violation-item fade-in">
                <div className="violation-item__header">
                  <span className={`badge badge--${v.severity === 'CRITICAL' ? 'red' : v.severity === 'HIGH' ? 'red' : 'orange'}`}>
                    {v.severity}
                  </span>
                  <span className="violation-item__type">{formatViolationTitle(v)}</span>
                  <span className="violation-item__score mono">{v.risk_score.toFixed(0)}</span>
                </div>
                <div className="violation-item__desc">{v.description}</div>
              </div>
            ))
          ) : (
            <div className="no-violations">
              <span className="status-dot status-dot--connected" />
              No active violations
            </div>
          )
        })()}
      </Card>

      {/* ── Objects ── */}
      <Card title="Detected Objects">
        {objects && objects.length > 0 ? (
          <div className="object-grid">
            {objects.map((o, i) => (
              <div key={i} className="object-chip">
                <span className="object-chip__type">{o.type}</span>
                <span className="object-chip__conf mono">{(o.confidence * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="no-objects">No prohibited objects detected</div>
        )}
      </Card>

      {/* ── Liveness ── */}
      <Card title="Liveness / Anti-Spoof">
        <div className="state-row">
          <StateIndicator
            on={liveness?.state === 'LIVE' || liveness?.state === 'GENUINE'}
            label={liveness?.state || 'UNKNOWN'}
            onColor="var(--accent-green)"
            offColor={liveness?.state === 'SPOOF' ? 'var(--accent-red)' : 'var(--text-muted)'}
          />
        </div>
        <MetricRow label="Liveness Score"    value={(liveness?.score || 0).toFixed(3)} color="var(--accent-green)" />
        <MetricRow label="Spoof Confidence"  value={(liveness?.spoof_confidence || 0).toFixed(3)} />
        <MetricRow label="Integrity Score"   value={(liveness?.integrity_score || 0).toFixed(3)} color="var(--accent-cyan)" />
        <MetricRow label="Consistency"       value={(liveness?.temporal_consistency || 0).toFixed(3)} />
        <MetricRow label="Inference"         value={(liveness?.latency_ms || 0).toFixed(1)} unit="ms" />
      </Card>

    </div>
  )
}

export default memo(MonitoringPanel)
