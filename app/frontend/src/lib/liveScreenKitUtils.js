/**
 * Live Screen Kit — readiness, fallback questions, teleprompter flattening.
 */

const CATEGORY_KEYS = [
  'technical_questions',
  'behavioral_questions',
  'culture_fit_questions',
  'experience_deep_dive_questions',
]

export function normalizeQuestion(q) {
  if (typeof q === 'string') return { text: q, what_to_listen_for: [], follow_ups: [] }
  if (q && typeof q === 'object') {
    return {
      text: q.text || String(q),
      what_to_listen_for: q.what_to_listen_for || [],
      follow_ups: q.follow_ups || [],
    }
  }
  return { text: String(q), what_to_listen_for: [], follow_ups: [] }
}

export function countKitQuestions(interviewQuestions) {
  if (!interviewQuestions || typeof interviewQuestions !== 'object') return 0
  return CATEGORY_KEYS.reduce(
    (n, key) => n + (Array.isArray(interviewQuestions[key]) ? interviewQuestions[key].length : 0),
    0,
  )
}

export function buildFallbackKit({
  missingSkills = [],
  matchedSkills = [],
  roleTitle = '',
  workExperience = [],
}) {
  const company = workExperience[0]?.company?.trim()
  const title = workExperience[0]?.title?.trim()

  const technical = [
    ...missingSkills.slice(0, 3).map((skill) => ({
      text: `${skill} isn't on your resume — have you used it for ${roleTitle || 'this role'}?`,
      what_to_listen_for: [`Honest ${skill} exposure`, 'Adjacent experience'],
      follow_ups: [`What ${skill} work have you done hands-on?`],
      scoring_criteria: {
        strong: `Clear ${skill} example with context`,
        adequate: 'Some adjacent experience',
        weak: 'No exposure and no transferable example',
      },
    })),
    ...matchedSkills.slice(0, 2).map((skill) => ({
      text: company
        ? `At ${company}, what did you personally deliver with ${skill}?`
        : `You list ${skill} — walk me through one real project where you used it.`,
      what_to_listen_for: [`Hands-on ${skill}`, 'Personal contribution', 'Outcome'],
      follow_ups: [`What was the hardest part of that ${skill} work?`],
      scoring_criteria: {
        strong: `Detailed ${skill} example with ownership`,
        adequate: 'Relevant but light on detail',
        weak: 'Cannot substantiate resume claim',
      },
    })),
  ]

  const experience = []
  if (company && title) {
    experience.push({
      text: `At ${company} as ${title}, what modules or integrations did you own?`,
      what_to_listen_for: ['Scope owned', 'Tools used', 'Outcome'],
      follow_ups: ['What broke in production and how did you fix it?'],
    })
  }
  if (matchedSkills[0]) {
    experience.push({
      text: `What's the toughest live issue you've fixed involving ${matchedSkills[0]}?`,
      what_to_listen_for: ['Root cause', 'Resolution steps', 'Impact'],
      follow_ups: [],
    })
  }

  const behavioral = roleTitle
    ? [{
        text: `Describe a go-live or UAT issue you handled as a ${roleTitle}.`,
        what_to_listen_for: ['Problem clarity', 'Stakeholder handling', 'Resolution'],
        follow_ups: ['Who did you coordinate with?'],
      }]
    : [{
        text: 'Describe a deadline slip — what did you do to recover?',
        what_to_listen_for: ['Ownership', 'Prioritization', 'Outcome'],
        follow_ups: [],
      }]

  if (technical.length === 0 && experience.length === 0) {
    technical.push({
      text: 'Walk me through your most relevant project for this role — what did you own?',
      what_to_listen_for: ['Role alignment', 'Specific accomplishments'],
      follow_ups: [],
    })
  }

  return {
    technical_questions: technical.slice(0, 5),
    behavioral_questions: behavioral.slice(0, 1),
    culture_fit_questions: [],
    experience_deep_dive_questions: experience.slice(0, 3),
    _fallback: true,
  }
}

/** Merge AI kit with deterministic fallback when categories are empty. */
export function resolveInterviewKit(interviewQuestions, analysisData, roleTitle) {
  const aiCount = countKitQuestions(interviewQuestions)
  if (aiCount > 0) {
    return { kit: interviewQuestions, isFallback: false, totalQ: aiCount }
  }

  const fallback = buildFallbackKit({
    missingSkills: analysisData?.missing_skills || [],
    matchedSkills: analysisData?.matched_skills || [],
    roleTitle,
    workExperience: analysisData?.work_experience
      || analysisData?.candidate_profile?.work_experience
      || [],
  })
  const fallbackCount = countKitQuestions(fallback)
  if (fallbackCount > 0) {
    return { kit: fallback, isFallback: true, totalQ: fallbackCount }
  }

  return { kit: null, isFallback: false, totalQ: 0 }
}

/**
 * @returns {{ state: 'loading'|'ready'|'fallback'|'empty', totalQ: number, isFallback: boolean, kit: object|null }}
 */
export function getKitReadiness(interviewKitStatus, interviewQuestions, analysisData, roleTitle) {
  if (interviewKitStatus === 'pending' || interviewKitStatus === 'processing') {
    return { state: 'loading', totalQ: 0, isFallback: false, kit: null }
  }

  const resolved = resolveInterviewKit(interviewQuestions, analysisData, roleTitle)
  if (resolved.totalQ > 0) {
    return {
      state: resolved.isFallback ? 'fallback' : 'ready',
      totalQ: resolved.totalQ,
      isFallback: resolved.isFallback,
      kit: resolved.kit,
    }
  }

  return { state: 'empty', totalQ: 0, isFallback: false, kit: null }
}

export function hasBriefingContent(briefing) {
  if (!briefing) return false
  const sanitized = sanitizeBriefingForDisplay(briefing)
  if (sanitized.profile_snapshot?.trim()) return true
  if (sanitized.strengths_to_confirm?.length) return true
  if (sanitized.areas_to_probe?.length) return true
  return false
}

/** Strip internal fallback diagnostics and shorten probe lines for live screen display. */
export function sanitizeBriefingForDisplay(briefing) {
  if (!briefing) return briefing
  let snapshot = (briefing.profile_snapshot || '').trim()
  snapshot = snapshot
    .replace(/Fallback analysis generated[^.]*\.?\s*/gi, '')
    .replace(/LLM narrative was unavailable\.?\s*/gi, '')
    .replace(/LLM-enhanced analysis was not available\.?\s*/gi, '')
    .trim()

  return {
    ...briefing,
    profile_snapshot: snapshot,
    strengths_to_confirm: (briefing.strengths_to_confirm || []).map(sanitizeStrengthLine),
    areas_to_probe: (briefing.areas_to_probe || []).map(sanitizeProbeLine),
  }
}

function sanitizeStrengthLine(line) {
  if (!line) return line
  return line
    .replace(/^Validate\s+/i, 'Confirm ')
    .replace(/\s*\(matched must-have\)\s*$/i, '')
}

function sanitizeProbeLine(line) {
  if (!line || typeof line !== 'string') return line
  let text = line.trim()
  const gapIdx = text.search(/\s—\sHIGH priority gap/i)
  if (gapIdx > 0) text = text.slice(0, gapIdx).trim()
  text = text.replace(/^\?\s*/, '').replace(/^Probe:\s*/i, '')
  if (text.length > 48) {
    const words = text.split(/\s+/)
    text = words.slice(0, 6).join(' ') + (words.length > 6 ? '…' : '')
  }
  return text
}

/** Keep teleprompter questions scannable during a live call. */
export function spokenQuestionText(text, maxLen = 220) {
  if (!text || typeof text !== 'string') return String(text ?? '')
  const t = text.trim()
  if (t.length <= maxLen) return t
  const sentenceEnd = t.search(/[.!?]\s/)
  if (sentenceEnd > 40 && sentenceEnd < maxLen) return t.slice(0, sentenceEnd + 1)
  return t.slice(0, maxLen).trimEnd() + '…'
}

export const CATEGORY_META = {
  technical: { label: 'Technical', color: 'text-blue-700', bg: 'bg-blue-50', ring: 'ring-blue-200', dot: 'bg-blue-500' },
  behavioral: { label: 'Behavioral', color: 'text-violet-700', bg: 'bg-violet-50', ring: 'ring-violet-200', dot: 'bg-violet-500' },
  culture_fit: { label: 'Culture Fit', color: 'text-teal-700', bg: 'bg-teal-50', ring: 'ring-teal-200', dot: 'bg-teal-500' },
  experience_deep_dive: { label: 'Experience', color: 'text-orange-700', bg: 'bg-orange-50', ring: 'ring-orange-200', dot: 'bg-orange-500' },
}

export function getCategoriesFromKit(interviewQuestions) {
  return [
    { key: 'technical', questions: interviewQuestions?.technical_questions || [] },
    { key: 'behavioral', questions: interviewQuestions?.behavioral_questions || [] },
    { key: 'culture_fit', questions: interviewQuestions?.culture_fit_questions || [] },
    { key: 'experience_deep_dive', questions: interviewQuestions?.experience_deep_dive_questions || [] },
  ].filter((c) => c.questions.length > 0)
}

export function flattenQuestions(interviewQuestions) {
  const categories = getCategoriesFromKit(interviewQuestions)
  const flat = []
  categories.forEach((cat) => {
    cat.questions.forEach((rawQ, index) => {
      flat.push({
        category: cat.key,
        categoryLabel: CATEGORY_META[cat.key]?.label || cat.key,
        index,
        question: normalizeQuestion(rawQ),
      })
    })
  })
  return flat
}

export function shouldWarnRoleMismatch(fitScore) {
  return fitScore != null && fitScore < 40
}

export function getQuestionPriority(qText, missingSkills, matchedSkills) {
  const lower = qText.toLowerCase()
  if (missingSkills.some((s) => lower.includes(s.toLowerCase()))) return 'high'
  if (matchedSkills.some((s) => lower.includes(s.toLowerCase()))) return 'low'
  return 'medium'
}

export function starsToRating(stars) {
  if (stars >= 4) return 'strong'
  if (stars === 3) return 'adequate'
  return 'weak'
}

export function ratingToStars(rating) {
  if (rating === 'strong') return 5
  if (rating === 'adequate') return 3
  if (rating === 'weak') return 1
  return 0
}
