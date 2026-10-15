import { useState, useEffect, useCallback } from 'react'
import { API_BASE } from '../config/api'

/**
 * Custom React store hook for Incident Intelligence Platform state management.
 *
 * Consumes `incident_platform.all_incidents` from the WebSocket frame payload,
 * which includes incidents of all statuses (ACTIVE, RESOLVED, REVIEWED).
 * Incidents persist in the dashboard with correct status badges — resolved
 * incidents do not disappear, they are shown greyed with a RESOLVED badge.
 */
export function useIncidentStore(frameResult) {
  const [incidents, setIncidents] = useState([])
  const [selectedIncidentId, setSelectedIncidentId] = useState(null)
  const [activeModal, setActiveModal] = useState(null) // 'review' | 'replay' | 'export' | null
  const [selectedIncidentDetails, setSelectedIncidentDetails] = useState(null)

  // Sync all incidents (any status) from WebSocket frame payload
  useEffect(() => {
    const rawIncoming = frameResult?.incident_platform?.all_incidents || frameResult?.incident_platform?.incidents
    if (!rawIncoming) return
    const incoming = Array.isArray(rawIncoming) ? rawIncoming : Object.values(rawIncoming)

    setIncidents((prev) => {
      // Merge by incident_id — incoming data always wins (it is the source of truth)
      const map = new Map((Array.isArray(prev) ? prev : []).map((i) => [i.incident_id, i]))
      incoming.forEach((inc) => {
        if (inc && inc.incident_id) map.set(inc.incident_id, inc)
      })
      // Sort: active first, then by start_time descending
      return Array.from(map.values()).sort((a, b) => {
        const aActive = a.status === 'ACTIVE' || a.status === 'OPEN' ? 0 : 1
        const bActive = b.status === 'ACTIVE' || b.status === 'OPEN' ? 0 : 1
        if (aActive !== bActive) return aActive - bActive
        return (b.start_time || 0) - (a.start_time || 0)
      })
    })
  }, [frameResult?.incident_platform])

  // Fetch full details for selected incident
  const selectIncident = useCallback(async (incidentId, modalType = 'review') => {
    setSelectedIncidentId(incidentId)
    setActiveModal(modalType)
    try {
      const res = await fetch(`${API_BASE}/api/incidents/${incidentId}`)
      if (res.ok) {
        const data = await res.json()
        setSelectedIncidentDetails(data)
      }
    } catch (e) {
      console.error('Failed to fetch incident details:', e)
    }
  }, [])

  const closeModal = useCallback(() => {
    setActiveModal(null)
    setSelectedIncidentId(null)
    setSelectedIncidentDetails(null)
  }, [])

  const submitReviewDecision = useCallback(async (incidentId, decision, notes) => {
    try {
      const res = await fetch(`${API_BASE}/api/incidents/${incidentId}/review/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision, notes, author: 'PROCTOR_REVIEWER' }),
      })
      if (res.ok) {
        // Update local state: mark incident as REVIEWED with the submitted decision
        setIncidents((prev) =>
          prev.map((i) =>
            i.incident_id === incidentId
              ? { ...i, review_decision: decision, status: 'REVIEWED' }
              : i
          )
        )
        closeModal()
      }
    } catch (e) {
      console.error('Failed to submit review decision:', e)
    }
  }, [closeModal])

  return {
    incidents,
    selectedIncidentId,
    selectedIncidentDetails,
    activeModal,
    selectIncident,
    closeModal,
    submitReviewDecision,
  }
}
