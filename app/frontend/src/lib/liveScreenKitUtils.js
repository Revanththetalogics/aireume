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
  const technical = missingSkills.slice(0, 5).map((skill) => ({
    text: `Tell me about your experience with ${skill}. Can you walk me through a recent example?`,
    what_to_listen_for: [
      `Concrete examples of ${skill}`,
      'Depth of knowledge vs surface familiarity',
    ],
    follow_ups: [`How would you rate your proficiency in ${skill}?`],
  }))

  const behavioral = [
    {
      text: 'Describe a challenging situation at work and how you handled it.',
      what_to_listen_for: ['Clear situation, action, and result', 'Ownership and accountability'],
      follow_ups: ['What would you do differently next time?'],
    },
    {
      text: 'Tell me about a time you had to influence someone without direct authority.',
      what_to_listen_for: ['Communication style', 'Outcome achieved'],
      follow_ups: [],
    },
  ]

  const culture = [
    {
      text: roleTitle
        ? `Why are you interested in this ${roleTitle} role specifically?`
        : 'Why are you interested in this position?',
      what_to_listen_for: ['Motivation', 'Research about the role and company'],
      follow_ups: ['What are you looking for in your next role?'],
    },
  ]

  const experience = matchedSkills.slice(0, 3).map((skill) => ({
    text: `Your resume mentions ${skill} — how have you applied it in practice?`,
    what_to_listen_for: ['Verification of resume claims', 'Specificity of examples'],
    follow_ups: [`What was the most complex project where you used ${skill}?`],
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
  if (briefing.profile_snapshot?.trim()) return true
  if (briefing.strengths_to_confirm?.length) return true
  if (briefing.areas_to_probe?.length) return true
  return false
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
