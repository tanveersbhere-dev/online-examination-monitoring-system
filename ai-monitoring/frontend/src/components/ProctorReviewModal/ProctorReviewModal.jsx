import React, { useState, useEffect } from 'react'
import { API_BASE } from '../../config/api'
import './ProctorReviewModal.css'

export default function ProctorReviewModal({ incidentId, onClose, onSubmitDecision }) {
  const [reviewData, setReviewData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selectedDecision, setSelectedDecision] = useState('CONFIRMED')
  const [notesText, setNotesText] = useState('')

  useEffect(() => {
    let isMounted = true
    async function fetchReview() {
      try {
        const res = await fetch(`${API_BASE}/api/incidents/${incidentId}/review`)
        if (res.ok) {
          const data = await res.json()
          if (isMounted) setReviewData(data)
        }
      } catch (e) {
        console.error('Error fetching review data:', e)
      } finally {
        if (isMounted) setLoading(false)
      }
    }
    fetchReview()
    return () => { isMounted = false }
  }, [incidentId])

  const handleSave = () => {
    onSubmitDecision(incidentId, selectedDecision, notesText)
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="review-modal" onClick={(e) => e.stopPropagation()}>
        <div className="review-modal__header">
          <h3>Proctor Decision Workspace</h3>
          <button className="modal-close-btn" onClick={onClose}>×</button>
        </div>

        {loading ? (
          <div className="review-loading">Loading Review Package...</div>
        ) : (
          <div className="review-modal__body">
            <div className="review-summary-card">
              <h4>Incident #{incidentId}</h4>
              <p><strong>Title:</strong> {reviewData?.incident?.title || 'Behavioral Incident'}</p>
              <p><strong>Severity:</strong> {reviewData?.incident?.severity || 'ELEVATED'}</p>
              <p><strong>Current Status:</strong> <span className="status-highlight">{reviewData?.review_status}</span></p>
              <p><strong>Current Decision:</strong> <span className="decision-highlight">{reviewData?.review_decision}</span></p>
            </div>

            <div className="review-decision-selector">
              <label>Select Review Decision:</label>
              <div className="decision-buttons">
                {['CONFIRMED', 'DISMISSED', 'FALSE_POSITIVE', 'NEEDS_ESCALATION'].map((dec) => (
                  <button
                    key={dec}
                    className={`btn-decision btn-decision--${dec.toLowerCase()} ${selectedDecision === dec ? 'active' : ''}`}
                    onClick={() => setSelectedDecision(dec)}
                  >
                    {dec.replace('_', ' ')}
                  </button>
                ))}
              </div>
            </div>

            <div className="review-notes-input">
              <label>Reviewer Notes / Observations:</label>
              <textarea
                rows={3}
                placeholder="Enter proctor audit notes here..."
                value={notesText}
                onChange={(e) => setNotesText(e.target.value)}
              />
            </div>

            {reviewData?.audit_trail?.length > 0 && (
              <div className="review-audit-trail">
                <h5>Audit Trail History</h5>
                <ul>
                  {reviewData.audit_trail.map((entry) => (
                    <li key={entry.entry_id}>
                      <span className="mono">[{new Date(entry.timestamp * 1000).toLocaleTimeString()}]</span>{' '}
                      <strong>{entry.action}:</strong> {entry.details}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        <div className="review-modal__footer">
          <button className="btn-modal-cancel" onClick={onClose}>Cancel</button>
          <button className="btn-modal-submit" onClick={handleSave}>Save Decision</button>
        </div>
      </div>
    </div>
  )
}
