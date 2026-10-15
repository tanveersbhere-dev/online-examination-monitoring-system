/**
 * Monitoring Report Formatting and Grouping Utilities
 */

export const VIOLATION_META = {
  UNAUTH_PHONE: { title: 'Phone Violation', icon: '📱', category: 'Unauthorized Object' },
  UNAUTH_LAPTOP: { title: 'Laptop Violation', icon: '💻', category: 'Unauthorized Object' },
  PHONE_DETECTED: { title: 'Phone Violation', icon: '📱', category: 'Unauthorized Object' },
  ATT_DOWNWARD_GAZE: { title: 'Downward Gaze', icon: '👁', category: 'Attention / Gaze' },
  ATT_LOOKING_AWAY: { title: 'Looking Away', icon: '👁', category: 'Attention / Gaze' },
  LOOKING_AWAY: { title: 'Looking Away', icon: '👁', category: 'Attention / Gaze' },
  GAZE_OFF_SCREEN: { title: 'Off-Screen Gaze', icon: '👀', category: 'Attention / Gaze' },
  MULTIPLE_PEOPLE: { title: 'Multiple Persons Detected', icon: '👥', category: 'Identity & Environment' },
  MULTIPLE_FACES: { title: 'Multiple Faces Detected', icon: '👥', category: 'Identity & Environment' },
  NO_FACE: { title: 'Candidate Missing / No Face', icon: '🚫', category: 'Identity & Environment' },
  FACE_NOT_VISIBLE: { title: 'Face Not Visible', icon: '🚫', category: 'Identity & Environment' },
  COMM_EARPHONES: { title: 'Unauthorized Audio Device', icon: '🎧', category: 'Communication Device' },
  COMM_HEADPHONES: { title: 'Unauthorized Audio Device', icon: '🎧', category: 'Communication Device' },
  COMM_NECKBAND: { title: 'Unauthorized Audio Device', icon: '🎧', category: 'Communication Device' },
  EARBUDS_DETECTED: { title: 'Unauthorized Audio Device', icon: '🎧', category: 'Communication Device' },
  UNAUTH_VOICE: { title: 'Unauthorized Human Voice', icon: '🎤', category: 'Communication & Speech' },
  BOOK_MATERIAL: { title: 'Unauthorized Book / Material', icon: '📖', category: 'Unauthorized Object' },
  UNAUTHORIZED_MATERIAL: { title: 'Unauthorized Book / Material', icon: '📖', category: 'Unauthorized Object' },
}

// Internal diagnostic event types that should not be displayed as standalone examiner violations
export const INTERNAL_DIAGNOSTIC_TYPES = new Set([
  'ID_MISMATCH',
  'IDENTITY_REPEATED_MISMATCH',
  'IDENTITY_MISMATCH',
  'IDENTITY_LOW_INTEGRITY',
  'IDENTITY_INTEGRITY',
  'IDENTITY_INSTABILITY',
])

/**
 * Maps raw backend violation enum variants to their canonical human-readable category.
 */
export function getCanonicalViolationInfo(rawType, fallbackTitle, fallbackCategory) {
  const norm = (rawType || '').toUpperCase().trim()

  // 1. Audio Device / Earphones / Earbuds / Headphones / Neckbands
  if (
    norm.includes('EARPHONE') ||
    norm.includes('EARBUD') ||
    norm.includes('AUDIO') ||
    norm.includes('HEADPHONE') ||
    norm.includes('HEADSET') ||
    norm.includes('NECKBAND') ||
    norm.includes('EARPOD') ||
    norm.includes('HANDSFREE')
  ) {
    return {
      key: 'COMM_EARPHONES',
      title: 'Unauthorized Audio Device',
      icon: '🎧',
      category: 'Communication Device',
    }
  }

  // 1b. Phone / Unauthorized Device (strictly excluding earphones/headphones)
  if (
    (norm.includes('PHONE') || norm.includes('CELL')) &&
    !norm.includes('EARPHONE') &&
    !norm.includes('HEADPHONE')
  ) {
    return {
      key: 'UNAUTH_PHONE',
      title: 'Phone Violation',
      icon: '📱',
      category: 'Unauthorized Object',
    }
  }

  // 1c. Laptop / Unauthorized Device
  if (norm.includes('LAPTOP')) {
    return {
      key: 'UNAUTH_LAPTOP',
      title: 'Laptop Violation',
      icon: '💻',
      category: 'Unauthorized Object',
    }
  }

  // 2b. Human Voice / Speech
  if (norm.includes('VOICE') || norm.includes('SPEECH') || norm.includes('TALK')) {
    return {
      key: 'UNAUTH_VOICE',
      title: 'Unauthorized Human Voice',
      icon: '🎤',
      category: 'Communication & Speech',
    }
  }

  // 3. Downward Gaze
  if (norm.includes('DOWNWARD') || norm === 'ATT_DOWNWARD_GAZE') {
    return {
      key: 'ATT_DOWNWARD_GAZE',
      title: 'Downward Gaze',
      icon: '👁',
      category: 'Attention / Gaze',
    }
  }

  // 3b. Attention / Looking Away / Gaze Off Screen
  if (norm.includes('LOOKING_AWAY') || norm.includes('GAZE') || norm.includes('OFF_SCREEN')) {
    return {
      key: 'ATT_LOOKING_AWAY',
      title: 'Looking Away',
      icon: '👁',
      category: 'Attention / Gaze',
    }
  }

  // 4. Multiple Persons / Faces
  if (norm.includes('MULTIPLE_PERSON') || norm.includes('MULTIPLE_PEOPLE') || norm.includes('MULTIPLE_FACE')) {
    return {
      key: 'MULTIPLE_PEOPLE',
      title: 'Multiple Persons Detected',
      icon: '👥',
      category: 'Identity & Environment',
    }
  }

  // 5. Face Missing / Face Not Visible / Candidate Absent
  if (norm.includes('NO_FACE') || norm.includes('FACE_NOT_VISIBLE') || norm.includes('FACE_ABSENT') || norm.includes('CANDIDATE_ABSENT') || norm.includes('FACE_MISSING')) {
    return {
      key: 'NO_FACE',
      title: 'Candidate Missing / Face Not Visible',
      icon: '🚫',
      category: 'Identity & Environment',
    }
  }

  // 6. Unauthorized Books / Paper Materials
  if (norm.includes('BOOK') || norm.includes('MATERIAL') || norm.includes('PAPER') || norm.includes('REGISTER')) {
    return {
      key: 'UNAUTHORIZED_MATERIAL',
      title: 'Unauthorized Book / Material',
      icon: '📖',
      category: 'Unauthorized Object',
    }
  }

  // Fallback dynamic format
  const humanTitle = fallbackTitle && fallbackTitle !== rawType
    ? fallbackTitle
    : rawType.split('_').map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ')

  return {
    key: norm,
    title: humanTitle,
    icon: '🚨',
    category: fallbackCategory || 'Behavior Anomaly',
  }
}

/**
 * Format raw seconds into a clean human-readable duration string.
 * Examples:
 * 0 -> "0 sec"
 * 5 -> "5 sec"
 * 59 -> "59 sec"
 * 60 -> "1 min"
 * 75 -> "1 min 15 sec"
 * 125 -> "2 min 5 sec"
 * 3665 -> "1 hr 1 min 5 sec"
 */
export function formatDuration(seconds) {
  const total = Math.round(Number(seconds) || 0)
  if (total <= 0) return '0 sec'

  const hrs = Math.floor(total / 3600)
  const mins = Math.floor((total % 3600) / 60)
  const secs = total % 60

  const parts = []
  if (hrs > 0) parts.push(`${hrs} hr`)
  if (mins > 0) parts.push(`${mins} min`)
  if (secs > 0 || parts.length === 0) parts.push(`${secs} sec`)

  return parts.join(' ')
}

/**
 * Format epoch timestamp to localized time string (HH:MM:SS AM/PM)
 */
export function formatTime(ts) {
  if (!ts) return '—'
  return new Date(ts * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

/**
 * Format epoch timestamp to localized date string
 */
export function formatDate(ts) {
  if (!ts) return '—'
  return new Date(ts * 1000).toLocaleDateString([], { year: 'numeric', month: 'short', day: 'numeric' })
}

/**
 * Dynamically group raw report violations by canonical violation type.
 * Computes exact occurrence counts, combined durations, and lists of evidence/replays.
 */
export function groupViolationsByType(violations = []) {
  if (!Array.isArray(violations)) return []

  const groups = new Map()

  for (const v of violations) {
    if (!v) continue
    const rawType = v.violation_type || 'OTHER_ANOMALY'

    // Skip internal shadow diagnostic events and removed violations
    const upperRaw = String(rawType).toUpperCase()
    if (
      INTERNAL_DIAGNOSTIC_TYPES.has(rawType) ||
      upperRaw.includes('MISMATCH') ||
      upperRaw.includes('INTEGRITY') ||
      upperRaw.includes('INSTABILITY')
    ) {
      continue
    }

    const info = getCanonicalViolationInfo(rawType, v.title, v.category)

    if (!groups.has(info.key)) {
      groups.set(info.key, {
        typeKey: info.key,
        title: info.title,
        icon: info.icon,
        category: info.category,
        occurrences: 0,
        combinedDuration: 0,
        peakConfidence: 0,
        violations: [],
      })
    }

    const group = groups.get(info.key)
    group.occurrences += 1
    const dur = Math.max(0.1, typeof v.duration === 'number' ? v.duration : 0.1)
    group.combinedDuration += dur

    if (v.peak_confidence && v.peak_confidence > group.peakConfidence) {
      group.peakConfidence = v.peak_confidence
    }

    group.violations.push({
      ...v,
      occurrenceIndex: group.occurrences,
    })
  }

  // Sort groups by total combined duration descending
  return Array.from(groups.values()).sort((a, b) => b.combinedDuration - a.combinedDuration)
}
