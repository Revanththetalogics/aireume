/** Labels and helpers for analysis + call + consolidated hiring signals. */

export const CONSOLIDATED_LABELS = {
  advance_hm: 'Advance to HM',
  strong_advance: 'Strong Advance',
  advance: 'Advance',
  hold: 'Hold',
  reject: 'Reject',
  strong_reject: 'Strong Reject',
}

export function consolidatedLabel(key) {
  if (!key) return null
  return CONSOLIDATED_LABELS[key] || key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export function callSourceLabel(source) {
  if (source === 'human') return 'Live Screen'
  if (source === 'ai') return 'AI Call'
  return null
}

export function hasInterviewOutcome(result) {
  return result?.call_fit_score != null || !!result?.consolidated_recommendation
}
