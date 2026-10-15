import { memo } from 'react'
import './BehaviorPanel.css'

function BehaviorPanel({ behaviorData }) {
  if (!behaviorData) {
    return (
      <div className="behavior-card behavior-card--empty">
        <div className="section-title">Behavioral Intelligence</div>
        <div className="behavior-card__idle">Awaiting behavior reasoning…</div>
      </div>
    )
  }

  const profile = behaviorData.profile || {}
  const metrics = behaviorData.metrics || {}
  const summary = behaviorData.summary || {}

  const state = profile.state || 'NORMAL'
  const score = profile.behavior_score ?? 0
  const trend = profile.trend || 'STABLE'
  const activeComposites = profile.active_composite_behaviors || []

  const stateColors = {
    NORMAL: '#4caf50',
    SLIGHTLY_SUSPICIOUS: '#8bc34a',
    SUSPICIOUS: '#ff9800',
    HIGH_RISK: '#ff5722',
    CRITICAL: '#ff1744',
  }

  const stateColor = stateColors[state] || '#4caf50'

  return (
    <div className="behavior-card">
      <div className="behavior-card__header">
        <span className="section-title" style={{ marginBottom: 0 }}>Behavioral Reasoning</span>
        <span className="behavior-card__badge mono" style={{ background: `${stateColor}22`, color: stateColor, borderColor: stateColor }}>
          {state}
        </span>
      </div>

      {/* Behavior Score Meter */}
      <div className="behavior-score-meter">
        <div className="behavior-score-meter__labels">
          <span>Behavior Score</span>
          <span className="behavior-score-meter__val mono" style={{ color: stateColor }}>{score.toFixed(0)} / 100</span>
        </div>
        <div className="behavior-score-meter__bar">
          <div className="behavior-score-meter__fill" style={{ width: `${Math.min(score, 100)}%`, background: stateColor }} />
        </div>
        <div className="behavior-score-meter__trend">
          <span>Trend: <strong className={`trend-badge trend-badge--${trend.toLowerCase()}`}>{trend}</strong></span>
          <span className="mono">Memory: {metrics.memory_size || 0} events (60s)</span>
        </div>
      </div>

      {/* Active Composite Behaviors */}
      <div className="composite-section">
        <h4 className="composite-section__title">Active Composite Behaviors ({activeComposites.length})</h4>

        {activeComposites.length === 0 ? (
          <div className="composite-empty">
            <span className="status-dot status-dot--connected" />
            No composite suspicious patterns detected
          </div>
        ) : (
          <div className="composite-list">
            {activeComposites.map((comp) => (
              <div key={comp.name} className="composite-item">
                <div className="composite-item__header">
                  <span className="composite-item__title">{comp.title}</span>
                  <span className="composite-item__conf mono">{comp.confidence.toFixed(0)}% CONFIDENCE</span>
                </div>

                <div className="composite-item__bar">
                  <div className="composite-item__fill" style={{ width: `${comp.confidence}%` }} />
                </div>

                {/* Explainability Bullet Points */}
                <div className="composite-item__explain">
                  {comp.explainability && comp.explainability.map((exp, idx) => (
                    <div key={idx} className="composite-item__bullet">• {exp}</div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Summary Integrity Footer */}
      {summary.overall_integrity_assessment && (
        <div className="behavior-integrity-footer">
          <span>Integrity Assessment:</span>
          <strong className={`integrity-badge integrity-badge--${summary.overall_integrity_assessment.toLowerCase()}`}>
            {summary.overall_integrity_assessment}
          </strong>
        </div>
      )}
    </div>
  )
}

export default memo(BehaviorPanel)
