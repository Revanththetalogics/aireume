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
}) {
  const technical = missingSkills.slice(0, 3).map((skill) => ({
    text: `This role requires ${skill}. Walk me through a recent situation where you applied it — what was your role and what was the outcome?`,
    what_to_listen_for: [
      `Hands-on use of ${skill}`,
      'Specific contribution and measurable outcome',
    ],
    follow_ups: [`What was the hardest part of that ${skill} work?`],
    scoring_criteria: {
      strong: 'Clear example with personal contribution and outcome',
      adequate: 'Relevant example but light on detail or personal role',
      weak: 'Vague or theoretical answer without a concrete example',
    },
  }))

  const behavioral = [
    {
      text: 'Tell me about a time you had to deliver under a tight deadline. What did you prioritize?',
      what_to_listen_for: ['Situation, action, result', 'Ownership and trade-offs'],
      follow_ups: ['What would you do differently next time?'],
      scoring_criteria: {
        strong: 'Complete STAR with clear priorities and outcome',
        adequate: 'Relevant story but missing result or detail',
        weak: 'Generic answer without a real example',
      },
    },
    {
      text: 'Describe a situation where you disagreed with a stakeholder. How did you handle it?',
      what_to_listen_for: ['Communication', 'Conflict resolution', 'Outcome'],
      follow_ups: [],
      scoring_criteria: {
        strong: 'Shows diplomacy and a positive resolution',
        adequate: 'Describes disagreement but weak resolution',
        weak: 'Avoids the conflict or blames others',
      },
    },
  ]

  const culture = [
    {
      text: roleTitle
        ? `What specifically interests you about this ${roleTitle} role?`
        : 'What specifically interests you about this position?',
      what_to_listen_for: ['Role-specific motivation', 'Research about company or role'],
      follow_ups: ['What are you looking for in your next role?'],
      scoring_criteria: {
        strong: 'Clear motivation tied to role and career goals',
        adequate: 'Generic interest without role-specific detail',
        weak: 'Cannot articulate why this role fits',
      },
    },
  ]

  const experience = matchedSkills.slice(0, 2).map((skill) => ({
    text: `Your background mentions ${skill}. Can you describe a project where that was central to your work?`,
    what_to_listen_for: ['Resume claim verification', 'Depth and specificity'],
    follow_ups: [`What tools or methods did you use with ${skill}?`],
    scoring_criteria: {
      strong: 'Detailed project story that validates resume claim',
      adequate: 'Some relevant detail but limited depth',
      weak: 'Cannot substantiate resume claim',
    },
  }))

  if (technical.length === 0 && experience.length === 0) {
    technical.push({
      text: 'Walk me through your most relevant experience for this role.',
      what_to_listen_for: ['Role alignment', 'Specific accomplishments'],
      follow_ups: [],
    })
  }

  return {
    technical_questions: technical,
    behavioral_questions: behavioral,
    culture_fit_questions: culture,
    experience_deep_dive_questions: experience,
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
