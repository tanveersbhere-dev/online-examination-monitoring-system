import React from 'react'
import { API_BASE } from '../../config/api'
import './ExportCaseDialog.css'

export default function ExportCaseDialog({ incidentId, onClose }) {
  const downloadPdf = () => {
    window.open(`${API_BASE}/api/incidents/${incidentId}/export/pdf`, '_blank')
  }

  const downloadZip = () => {
    window.open(`${API_BASE}/api/incidents/${incidentId}/export/zip`, '_blank')
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="export-modal" onClick={(e) => e.stopPropagation()}>
        <div className="export-modal__header">
          <h3>Export Case Package - Incident #{incidentId}</h3>
          <button className="modal-close-btn" onClick={onClose}>×</button>
        </div>

        <div className="export-modal__body">
          <p className="export-desc">
            Download immutable investigation artifacts verified with SHA-256 integrity hash signatures.
          </p>

          <div className="export-options">
            <div className="export-card" onClick={downloadPdf}>
              <div className="export-card__icon">📄</div>
              <div className="export-card__text">
                <h4>Reviewer Report (PDF/Text)</h4>
                <p>Human-readable executive summary, evidence table, and timeline.</p>
              </div>
              <button className="btn-dl">Download</button>
            </div>

            <div className="export-card" onClick={downloadZip}>
              <div className="export-card__icon">📦</div>
              <div className="export-card__text">
                <h4>Complete Case Package (ZIP)</h4>
                <p>Full archive with manifest.json, report.pdf, and 6 domain JSON payloads.</p>
              </div>
              <button className="btn-dl btn-dl--zip">Download ZIP</button>
            </div>
          </div>
        </div>

        <div className="export-modal__footer">
          <button className="btn-modal-cancel" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  )
}
