import React, { useState, useEffect, useMemo } from 'react'
import { API_BASE } from '../../config/api'
import { formatDuration, formatTime, formatDate, groupViolationsByType } from './reportUtils'
import ViolationTypeCard from './ViolationTypeCard'
import EvidenceViewerModal from './EvidenceViewerModal'
import './MonitoringReport.css'

export default function MonitoringReport({ sessionId, onStartNewSession }) {
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedGroup, setSelectedGroup] = useState(null)

  useEffect(() => {
    let isMounted = true
    setLoading(true)
    setError(null)

    async function fetchReportData() {
      try {
        let targetId = sessionId
        if (!targetId) {
          // Fallback: fetch latest session from database
          const listRes = await fetch(`${API_BASE}/api/monitoring/sessions?limit=1`)
          if (listRes.ok) {
            const listData = await listRes.json()
            const sList = Array.isArray(listData) ? listData : listData?.sessions
            if (Array.isArray(sList) && sList.length > 0) {
              targetId = sList[0].id
            }
          }
        }

        if (!targetId) {
          const sessionRes = await fetch(`${API_BASE}/api/session`)
          if (sessionRes.ok) {
            const sessionData = await sessionRes.json()
            targetId = sessionData?.session_id
          }
        }

        if (!targetId) {
          throw new Error('No active or previous monitoring session found.')
        }

        const res = await fetch(`${API_BASE}/api/monitoring/sessions/${targetId}/report`)
        if (!res.ok) throw new Error(`Report not found (Status: ${res.status})`)
        const data = await res.json()

        if (isMounted) {
          setReport(data)
          setLoading(false)
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message)
          setLoading(false)
        }
      }
    }

    fetchReportData()

    return () => {
      isMounted = false
    }
  }, [sessionId])

  // Group raw report violations by canonical violation type
  const groupedViolations = useMemo(() => {
    if (!report?.violations) return []
    return groupViolationsByType(report.violations)
  }, [report?.violations])

  // Compute aggregate statistics
  const aggregateStats = useMemo(() => {
    if (!report) return { totalViolations: 0, distinctTypes: 0, totalViolationDuration: 0, integrityScore: 100 }

    const violations = report.violations || []
    const totalViolations = violations.length
    const distinctTypes = groupedViolations.length
    const totalViolationDuration = violations.reduce((acc, v) => acc + (typeof v.duration === 'number' ? v.duration : 0.1), 0)
    const integrityScore = report.summary?.integrity_score ?? Math.max(0, 100 - totalViolations * 12)

    return {
      totalViolations,
      distinctTypes,
      totalViolationDuration,
      integrityScore,
    }
  }, [report, groupedViolations])

  if (loading) {
    return (
      <div className="report-container glass">
        <div className="report-loading">
          <span className="spinner" />
          <p>Generating AI Monitoring Report for session {sessionId}...</p>
        </div>
      </div>
    )
  }

  if (error || !report) {
    return (
      <div className="report-container glass">
        <div className="report-error">
          <h3>Failed to Load Report</h3>
          <p>{error || 'Session report data could not be retrieved.'}</p>
          <button className="btn btn--primary" onClick={onStartNewSession}>
            Return to Live Monitoring
          </button>
        </div>
      </div>
    )
  }

  const { session, summary } = report
  const sessionDuration = session?.total_duration || summary?.duration_seconds || 0

  return (
    <div className="report-container">
      {/* SECTION 1 — REPORT HEADER */}
      <header className="report-header glass">
        <div className="report-header__left">
          <div className="report-header__badge-row">
            <span className="badge badge--purple">EXAMINATION AUDIT</span>
            <span className={`badge badge--${session.status === 'COMPLETED' ? 'green' : 'orange'}`}>
              {session.status}
            </span>
          </div>
          <h1 className="report-title">AI Monitoring Report</h1>
          <div className="report-meta-grid mono">
            <span>Session: <strong className="highlight-text">{session.id}</strong></span>
            {session.student_id && <span>Student: <strong>{session.student_id}</strong></span>}
            <span>Date: <strong>{formatDate(session.started_at)}</strong></span>
            <span>Duration: <strong>{formatDuration(sessionDuration)}</strong> ({formatTime(session.started_at)} – {formatTime(session.ended_at)})</span>
          </div>
        </div>
        <div className="report-header__actions">
          <button className="btn btn--outline" onClick={() => window.print()}>
            🖨 Print / Export
          </button>
          <button className="btn btn--primary" onClick={onStartNewSession}>
            ▶ Start New Monitoring Run
          </button>
        </div>
      </header>

      {/* SECTION 2 — OVERALL MONITORING SUMMARY */}
      <section className="report-section-wrapper">
        <h2 className="section-heading">
          <span className="heading-dot" />
          <span>Monitoring Summary</span>
        </h2>

        <div className="report-kpi-grid">
          {/* Total Violations */}
          <div className="report-kpi-card glass">
            <div className="kpi-header">
              <span className="kpi-icon">🚨</span>
              <span className="report-kpi-label">TOTAL VIOLATIONS</span>
            </div>
            <span className={`report-kpi-value mono ${aggregateStats.totalViolations > 0 ? 'text-danger' : 'text-success'}`}>
              {aggregateStats.totalViolations}
            </span>
            <span className="report-kpi-sub">
              {aggregateStats.totalViolations === 0 ? 'No violations observed' : `${aggregateStats.totalViolations} total incident occurrences`}
            </span>
          </div>

          {/* Violation Types */}
          <div className="report-kpi-card glass">
            <div className="kpi-header">
              <span className="kpi-icon">📊</span>
              <span className="report-kpi-label">VIOLATION TYPES</span>
            </div>
            <span className="report-kpi-value mono text-accent">
              {aggregateStats.distinctTypes}
            </span>
            <span className="report-kpi-sub">Distinct violation categories</span>
          </div>

          {/* Combined Violation Duration */}
          <div className="report-kpi-card glass">
            <div className="kpi-header">
              <span className="kpi-icon">⏱</span>
              <span className="report-kpi-label">COMBINED VIOLATION TIME</span>
            </div>
            <span className="report-kpi-value mono text-warning">
              {formatDuration(aggregateStats.totalViolationDuration)}
            </span>
            <span className="report-kpi-sub">Total time candidate was in non-compliance</span>
          </div>

          {/* Integrity Rating */}
          <div className="report-kpi-card glass">
            <div className="kpi-header">
              <span className="kpi-icon">🛡</span>
              <span className="report-kpi-label">INTEGRITY RATING</span>
            </div>
            <span className={`report-kpi-value mono ${aggregateStats.integrityScore >= 80 ? 'text-success' : aggregateStats.integrityScore >= 50 ? 'text-warning' : 'text-danger'}`}>
              {aggregateStats.integrityScore}%
            </span>
            <span className="report-kpi-sub">AI Proctoring Trust Score</span>
          </div>
        </div>
      </section>

      {/* SECTION 3 — VIOLATION SUMMARY (GROUPED BY TYPE) */}
      <section className="report-section-wrapper">
        <div className="section-header-row">
          <h2 className="section-heading">
            <span className="heading-dot" />
            <span>Violation Summary</span>
          </h2>
          <span className="section-count-tag mono">
            {groupedViolations.length} {groupedViolations.length === 1 ? 'Violation Type' : 'Violation Types'}
          </span>
        </div>

        {groupedViolations.length === 0 ? (
          <div className="clean-session-card glass">
            <span className="clean-icon">🛡️</span>
            <h3>Clean Monitoring Run!</h3>
            <p>No anomalous behavior or integrity violations were detected during this session.</p>
          </div>
        ) : (
          <div className="violation-cards-grid">
            {groupedViolations.map((group) => (
              <ViolationTypeCard
                key={group.typeKey}
                group={group}
                onViewEvidence={(g) => setSelectedGroup(g)}
              />
            ))}
          </div>
        )}
      </section>

      {/* SECTION 4 — DEDICATED EVIDENCE VIEWER MODAL */}
      {selectedGroup && (
        <EvidenceViewerModal
          group={selectedGroup}
          onClose={() => setSelectedGroup(null)}
        />
      )}
    </div>
  )
}
