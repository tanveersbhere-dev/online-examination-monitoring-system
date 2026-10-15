import React from 'react'
import { formatDuration } from './reportUtils'

export default function ViolationTypeCard({ group, onViewEvidence }) {
  const { title, icon, category, occurrences, combinedDuration, peakConfidence } = group

  return (
    <div className="v-card glass">
      {/* Top Banner / Header */}
      <div className="v-card__header">
        <div className="v-card__title-group">
          <span className="v-card__icon">{icon}</span>
          <div>
            <h3 className="v-card__title">{title}</h3>
            <span className="v-card__category">{category}</span>
          </div>
        </div>
        {peakConfidence > 0 && (
          <span className="v-card__conf-badge mono" title="Peak AI Confidence">
            Peak {(peakConfidence * 100).toFixed(0)}%
          </span>
        )}
      </div>

      {/* Statistics Grid */}
      <div className="v-card__stats">
        <div className="v-stat-item">
          <span className="v-stat-label">OCCURRED</span>
          <span className="v-stat-value mono">
            {occurrences} <span className="v-stat-unit">{occurrences === 1 ? 'Time' : 'Times'}</span>
          </span>
        </div>

        <div className="v-stat-divider" />

        <div className="v-stat-item">
          <span className="v-stat-label">COMBINED DURATION</span>
          <span className="v-stat-value mono text-duration">
            {formatDuration(combinedDuration)}
          </span>
        </div>
      </div>

      {/* Action Footer */}
      <div className="v-card__footer">
        <button
          className="btn-view-evidence"
          onClick={() => onViewEvidence(group)}
        >
          <span>View Evidence</span>
          <span className="arrow-icon">➔</span>
        </button>
      </div>
    </div>
  )
}
