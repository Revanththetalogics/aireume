/** Session bucketing and grouping for the Interviews hub. */

const ATTENTION_STATUSES = new Set(['in_progress', 'ringing', 'failed', 'no_answer'])
const UPCOMING_STATUSES = new Set(['scheduled', 'pending_strategy', 'strategy_ready'])

/** Sessions stuck in_progress after the call ended should not block the hub. */
export function effectiveSessionStatus(session) {
  if (
    session.status === 'in_progress' &&
    (session.duration_seconds > 0 || session.score != null)
  ) {
    return 'completed'
  }
  return session.status
}

export function bucketSessions(sessions) {
  const attention = []
  const upcoming = []
  const recent = []

  for (const s of sessions) {
    const status = effectiveSessionStatus(s)
    const normalized = status === s.status ? s : { ...s, status }
    if (ATTENTION_STATUSES.has(status)) attention.push(normalized)
    else if (UPCOMING_STATUSES.has(status)) upcoming.push(normalized)
    else recent.push(normalized)
  }

  const byDate = (a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0)
  attention.sort(byDate)
  upcoming.sort((a, b) => new Date(a.scheduled_at || a.created_at || 0) - new Date(b.scheduled_at || b.created_at || 0))
  recent.sort(byDate)

  return { attention, upcoming, recent }
}

export function groupSessionsByCandidate(sessions) {
  const map = new Map()

  for (const s of sessions) {
    const key = s.candidate_id ?? s.candidate_name
    const existing = map.get(key)
    if (!existing) {
      map.set(key, {
        ...s,
        sessionCount: 1,
        sessions: [s],
      })
      continue
    }
    existing.sessionCount += 1
    existing.sessions.push(s)
    if (new Date(s.created_at || 0) > new Date(existing.created_at || 0)) {
      Object.assign(existing, s)
    }
  }

  return Array.from(map.values()).sort(
    (a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0),
  )
}

export const DEPTH_DEFAULT_MINUTES = {
  quick: 5,
  standard: 15,
  deep: 25,
}

export function depthLabel(depth) {
  const labels = {
    quick: 'Quick Screen',
    standard: 'Standard',
    deep: 'Deep Assessment',
  }
  return labels[depth] || depth
}

export function formatSessionWhen(session) {
  const raw = session.status === 'scheduled' && session.scheduled_at
    ? session.scheduled_at
    : session.created_at
  if (!raw) return ''
  try {
    return new Date(raw).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      timeZoneName: 'short',
    })
  } catch {
    return ''
  }
}

export function recommendationLabel(rec) {
  if (!rec) return null
  return rec.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}
