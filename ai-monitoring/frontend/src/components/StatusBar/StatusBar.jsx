import './StatusBar.css'

function Stat({ label, value, warn = false, critical = false }) {
  return (
    <div className="sb-stat">
      <span className="sb-stat__label">{label}</span>
      <span
        className="sb-stat__value mono"
        style={{
          color: critical
            ? 'var(--accent-critical)'
            : warn
            ? 'var(--accent-orange)'
            : 'var(--text-primary)',
        }}
      >
        {value}
      </span>
    </div>
  )
}

export default function StatusBar({ frameResult, systemHealth, droppedCount, inferFps, connected }) {
  const sys = systemHealth?.system
  const cpu = sys?.cpu_percent ?? 0
  const ram = sys?.ram_percent ?? 0
  const uptime = systemHealth?.uptime_seconds ?? 0
  const latency = frameResult?.latency_ms ?? 0
  const fps = frameResult?.fps ?? 0
  const pipelineAvg = systemHealth?.pipeline?.avg_latency_ms ?? latency
  const totalFrames = systemHealth?.pipeline?.total_frames_processed ?? frameResult?.frame_number ?? 0

  const uptimeStr = uptime > 0
    ? `${Math.floor(uptime / 60)}m ${Math.floor(uptime % 60)}s`
    : '—'

  const riskLevel = frameResult?.risk?.level || 'NORMAL'
  const riskScore = frameResult?.risk?.score ?? 0

  return (
    <div className="status-bar">
      <div className="status-bar__left">
        <span className={`status-dot status-dot--${connected ? 'connected' : 'error'}`} />
        <span className="status-bar__label">
          {connected ? 'AI Engine Connected' : 'Disconnected'}
        </span>
        <span className="status-bar__divider" />
        <span className={`badge badge--${riskLevel === 'CRITICAL' ? 'red' : riskLevel === 'HIGH' ? 'red' : riskLevel === 'MEDIUM' ? 'orange' : 'green'}`}>
          RISK {riskLevel} — {riskScore.toFixed(0)}
        </span>
      </div>

      <div className="status-bar__metrics">
        <Stat label="Cam FPS"     value={fps.toFixed(1)} />
        <Stat label="Infer FPS"   value={inferFps} warn={inferFps < 5 && connected} />
        <Stat label="Latency"     value={`${latency.toFixed(0)}ms`} warn={latency > 150} critical={latency > 300} />
        <Stat label="Avg Latency" value={`${pipelineAvg.toFixed(0)}ms`} />
        <Stat label="Dropped"     value={droppedCount} warn={droppedCount > 0} />
        <Stat label="Frames"      value={totalFrames.toLocaleString()} />
        <Stat label="CPU"         value={`${cpu.toFixed(0)}%`} warn={cpu > 70} critical={cpu > 90} />
        <Stat label="RAM"         value={`${ram.toFixed(0)}%`} warn={ram > 80} critical={ram > 95} />
        <Stat label="Uptime"      value={uptimeStr} />
      </div>

      <div className="status-bar__right">
        {frameResult?.session?.student_id && (
          <span className="badge badge--dark" style={{ marginRight: 8, fontSize: 10, padding: '2px 6px' }}>
            {frameResult.session.mode === 'ppr' ? '🔗 PPR' : '⚙ STANDALONE'}: {frameResult.session.student_id}
          </span>
        )}
        <span className="status-bar__ver">AI Monitoring Unit Host v1.0</span>
      </div>
    </div>
  )
}
