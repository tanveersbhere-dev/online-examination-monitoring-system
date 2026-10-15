import React, { useState } from 'react'
import { API_BASE } from '../../config/api'
import { formatDuration, formatTime } from './reportUtils'

export default function EvidenceViewerModal({ group, onClose }) {
  const [zoomedImage, setZoomedImage] = useState(null)

  if (!group) return null

  const { title, icon, category, occurrences, combinedDuration, violations = [] } = group

  return (
    <div className="ev-modal-backdrop" onClick={onClose}>
      <div className="ev-modal glass" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <header className="ev-modal__header">
          <div className="ev-modal__header-left">
            <div className="ev-modal__title-row">
              <span className="ev-modal__icon">{icon}</span>
              <h2 className="ev-modal__title">{title} Evidence</h2>
              <span className="badge badge--red">{category}</span>
            </div>
            <p className="ev-modal__subtitle mono">
              <strong>{occurrences}</strong> {occurrences === 1 ? 'Occurrence' : 'Occurrences'} &bull;{' '}
              <strong>{formatDuration(combinedDuration)}</strong> Combined Duration
            </p>
          </div>
          <button className="ev-modal__close-btn" onClick={onClose} title="Close Evidence Viewer">
            ✕
          </button>
        </header>

        {/* Modal Content — Occurrence Cards */}
        <div className="ev-modal__body">
          {violations.length === 0 ? (
            <div className="ev-empty-state">
              <p>No evidence records available for this violation type.</p>
            </div>
          ) : (
            <div className="ev-occurrences-list">
              {violations.map((v, idx) => {
                const occNumber = idx + 1
                const audioEvidence = (v.evidence || []).find((e) => e.filename && e.filename.endsWith('.wav'))
                const imageEvidence = (v.evidence || []).find((e) => e.filename && !e.filename.endsWith('.wav'))
                const isAudioViolation = (v.violation_type === 'UNAUTH_VOICE' || !!audioEvidence)

                const hasEvidenceImage = !!imageEvidence?.filename
                const evidenceImageSrc = hasEvidenceImage
                  ? `${API_BASE}/evidence/${imageEvidence.filename}`
                  : null

                const hasAudio = !!audioEvidence?.filename
                const audioSrc = hasAudio
                  ? `${API_BASE}/evidence/${audioEvidence.filename}`
                  : null

                const hasReplay = v.replay && v.replay.clip_path
                const replayVideoSrc = hasReplay
                  ? `${API_BASE}/evidence/${v.replay.clip_path}`
                  : null

                return (
                  <div key={v.id || idx} className="ev-occurrence-card glass">
                    {/* Occurrence Header */}
                    <div className="ev-occurrence__header">
                      <div className="ev-occ-title-group">
                        <span className="ev-occ-badge">Occurrence #{occNumber}</span>
                        <span className="ev-occ-time mono">
                          Started at {formatTime(v.start_time)}
                        </span>
                      </div>
                      <div className="ev-occ-metrics mono">
                        <span>Duration: <strong>{formatDuration(v.duration || 0.1)}</strong></span>
                        {v.peak_confidence > 0 && (
                          <span>Peak Conf: <strong>{(v.peak_confidence * 100).toFixed(0)}%</strong></span>
                        )}
                      </div>
                    </div>

                    {/* Occurrence Media Grid */}
                    <div className="ev-media-grid">
                      {isAudioViolation ? (
                        <>
                          {/* Audio Player Block */}
                          <div className="ev-media-block ev-media-block--video glass" style={{ gridColumn: hasEvidenceImage ? 'auto' : '1 / -1' }}>
                            <div className="ev-media-label">
                              <span className="media-dot" style={{ background: '#7c4dff' }} />
                              <span>Microphone Voice Audio Evidence</span>
                            </div>
                            {hasAudio ? (
                              <div className="ev-audio-container" style={{ padding: '1.75rem 1rem', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                                <div style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>🎙️</div>
                                <div style={{ fontWeight: 600, fontSize: '0.95rem', color: '#fff', marginBottom: '0.25rem' }}>
                                  Candidate Microphone Recording
                                </div>
                                <div className="mono" style={{ fontSize: '0.78rem', color: 'rgba(255,255,255,0.6)', marginBottom: '1rem' }}>
                                  {audioEvidence.filename}
                                </div>
                                <audio
                                  key={audioSrc}
                                  controls
                                  src={audioSrc}
                                  style={{ width: '100%', maxWidth: '380px' }}
                                >
                                  Your browser does not support the audio element.
                                </audio>
                              </div>
                            ) : (
                              <div className="ev-no-media">
                                <span className="no-media-icon">🎤</span>
                                <p>No audio recording available for this voice occurrence.</p>
                              </div>
                            )}
                          </div>

                          {/* Snapshot Image (if also present) */}
                          {hasEvidenceImage && (
                            <div className="ev-media-block ev-media-block--image glass">
                              <div className="ev-media-label">
                                <span className="media-dot dot-image" />
                                <span>Verified Candidate Snapshot</span>
                              </div>
                              <div
                                className="ev-image-container"
                                onClick={() => setZoomedImage(evidenceImageSrc)}
                                title="Click to view full size image"
                              >
                                <img src={evidenceImageSrc} alt={`Evidence #${occNumber}`} className="ev-snapshot-img" />
                                <div className="ev-image-overlay">
                                  <span>🔍 Click to Enlarge</span>
                                </div>
                              </div>
                            </div>
                          )}
                        </>
                      ) : (
                        <>
                          {/* Left: Replay Video */}
                          <div className="ev-media-block ev-media-block--video glass">
                            <div className="ev-media-label">
                              <span className="media-dot dot-video" />
                              <span>3-Second Incident Replay Video</span>
                            </div>
                            {hasReplay ? (
                              <div className="ev-video-container">
                                <video
                                  key={replayVideoSrc}
                                  controls
                                  autoPlay
                                  loop
                                  playsInline
                                  className="ev-video-player"
                                >
                                  <source src={replayVideoSrc} type="video/mp4" />
                                  Your browser does not support the video tag.
                                </video>
                                <div className="ev-video-tag mono">
                                  <span>3.0s Continuous Replay</span>
                                </div>
                              </div>
                            ) : (
                              <div className="ev-no-media">
                                <span className="no-media-icon">📹</span>
                                <p>No replay video available for this occurrence.</p>
                              </div>
                            )}
                          </div>

                          {/* Right: Keyframe Snapshot Image */}
                          <div className="ev-media-block ev-media-block--image glass">
                            <div className="ev-media-label">
                              <span className="media-dot dot-image" />
                              <span>Verified Evidence Snapshot</span>
                            </div>
                            {hasEvidenceImage ? (
                              <div
                                className="ev-image-container"
                                onClick={() => setZoomedImage(evidenceImageSrc)}
                                title="Click to view full size image"
                              >
                                <img src={evidenceImageSrc} alt={`Evidence #${occNumber}`} className="ev-snapshot-img" />
                                <div className="ev-image-overlay">
                                  <span>🔍 Click to Enlarge</span>
                                </div>
                              </div>
                            ) : (
                              <div className="ev-no-media">
                                <span className="no-media-icon">📸</span>
                                <p>No snapshot image available.</p>
                              </div>
                            )}
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <footer className="ev-modal__footer">
          <button className="btn btn--outline" onClick={onClose}>
            Back to Violation Summary
          </button>
        </footer>
      </div>

      {/* Image Zoom Lightbox */}
      {zoomedImage && (
        <div className="lightbox-backdrop" onClick={() => setZoomedImage(null)}>
          <div className="lightbox-content" onClick={(e) => e.stopPropagation()}>
            <img src={zoomedImage} alt="Enlarged Evidence" className="lightbox-img" />
            <button className="lightbox-close" onClick={() => setZoomedImage(null)}>
              ✕ Close
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
