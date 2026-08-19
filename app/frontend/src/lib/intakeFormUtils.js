/** Split list-field input: newlines first, then commas on a single line. */
export function splitIntakeListInput(raw) {
  const lines = String(raw || '')
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean)
  if (lines.length === 1 && lines[0].includes(',')) {
    return lines[0]
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
  }
  return lines
}

export function normalizeIntakeShape(intake) {
  const out = { ...(intake || {}) }
  for (const key of ['must_haves', 'good_to_haves', 'deal_breakers', 'screen_focus_topics']) {
    const value = out[key]
    if (typeof value === 'string') {
      out[key] = splitIntakeListInput(value)
    } else if (Array.isArray(value)) {
      out[key] = value.flatMap((item) => {
        if (typeof item !== 'string') return []
        return splitIntakeListInput(item)
      })
    } else if (value == null) {
      out[key] = []
    }
  }
  return out
}

const INTAKE_STATUS_LABELS = {
  draft: 'Draft',
  pending_hm: 'Pending HM',
  approved: 'Approved',
  changes_requested: 'Changes requested',
}

export function formatIntakeStatus(status) {
  if (!status) return 'Draft'
  return INTAKE_STATUS_LABELS[status] || status.replace(/_/g, ' ')
}

/** Normalize voice kit Q&A or recruiter API rows for RecruiterTranscript. */
export function normalizeTranscriptItems(items) {
  if (!Array.isArray(items)) return []
  return items.map((item, idx) => {
    if (item?.speaker && item?.text) {
      return {
        id: item.id || idx,
        question: item.speaker === 'bot' ? item.text : '',
        response: item.speaker === 'candidate' ? item.text : '',
        category: 'general',
        _voiceTurn: true,
        speaker: item.speaker,
        text: item.text,
        timestamp: item.timestamp,
      }
    }
    return {
      id: item.id || idx,
      question: item.question || item.question_text || item.spoken_text || item.text || '',
      response: item.response || item.candidate_response || item.answer || '',
      category: item.category || item.stage || 'general',
      evaluation_score: item.evaluation_score ?? item.answer_score ?? item.score ?? null,
      evaluation_notes: item.evaluation_notes
        || (typeof item.evaluation_json === 'object' ? item.evaluation_json?.notes : null),
      duration_seconds: item.duration_seconds ?? item.response_duration_seconds ?? null,
      follow_ups: item.follow_ups || [],
    }
  })
}

export function parseVoiceKitTranscript(sessionData) {
  const raw = sessionData?.transcript_json
  if (!raw) return []
  try {
    const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw
    const qa = parsed?.questions_responses || parsed?.questionsResponses || []
    return normalizeTranscriptItems(qa)
  } catch {
    return []
  }
}
