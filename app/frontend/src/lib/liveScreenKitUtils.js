/**
 * Live Screen Kit — readiness, fallback questions, teleprompter flattening.
 */

const CATEGORY_KEYS = [
  'technical_questions',
  'behavioral_questions',
  'culture_fit_questions',
  'experience_deep_dive_questions',
]

const GAP_PROBE_TEMPLATES = [
  (skill, context) => `The role calls for ${skill} — how have you used that in ${context}?`,
  (skill) => `I don't see much ${skill} on your resume — any hands-on exposure?`,
  (skill) => `Walk me through your experience with ${skill}, even from adjacent work.`,
]

function detectRoleFamily(roleTitle = '') {
  const blob = (roleTitle || '').toLowerCase()
  if (/talent acquisition|recruiter|recruiting|human resources|\bhr\b|hiring|onboarding|staffing/.test(blob)) {
    return 'talent_acquisition'
  }
  if (/\bsap\b|erp|s\/?4|mm\b|fico/.test(blob)) return 'sap'
  if (/finance|financial analyst|accounting|fp&a/.test(blob)) return 'finance'
  if (/engineer|developer|software|backend|frontend|devops/.test(blob)) return 'engineering'
  return 'general'
}

function isProbeableSkill(skill) {
  if (!skill || typeof skill !== 'string') return false
  const clean = skill.trim()
  if (clean.split(/\s+/).length > 5) return false
  if (/\b\d{1,2}\s*[-–—]\s*\d{1,2}\s+years?\b/i.test(clean)) return false
  if (/\byears?\s+of\s+experience\b/i.test(clean)) return false
  if (/\[.*\]|\{.*\}/.test(clean)) return false
  return true
}

const TA_IRRELEVANT = new Set([
  'machine learning', 'kubernetes', 'docker', 'react', 'python', 'java', 'sap', 'aws', 'azure',
])

function filterMissingSkills(missingSkills, roleTitle) {
  const family = detectRoleFamily(roleTitle)
  return (missingSkills || []).filter((skill) => {
    if (!isProbeableSkill(skill)) return false
    if (family === 'talent_acquisition' && TA_IRRELEVANT.has(skill.toLowerCase())) return false
    return true
  })
}

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
  const context = roleTitle || 'this role'
  const family = detectRoleFamily(roleTitle)
  const filteredMissing = filterMissingSkills(missingSkills, roleTitle)
  const company = workExperience[0]?.company?.trim()
  const title = workExperience[0]?.title?.trim()

  const technical = [
    ...filteredMissing.slice(0, 3).map((skill, idx) => {
      const template = GAP_PROBE_TEMPLATES[idx % GAP_PROBE_TEMPLATES.length]
      const text = template.length === 2 ? template(skill, context) : template(skill)
      return {
        text,
        what_to_listen_for: [`Practical ${skill} examples`, 'Adjacent experience'],
        follow_ups: [`Pick one example — what did you do with ${skill}?`],
        scoring_criteria: {
          strong: `Clear ${skill} example with context`,
          adequate: 'Some adjacent experience',
          weak: 'No exposure and no transferable example',
        },
      }
    }),
    ...matchedSkills.slice(0, 2).map((skill) => ({
      text: company
        ? `At ${company}, what did you personally own involving ${skill}?`
        : `You mention ${skill} — walk me through one project and your contribution.`,
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
    if (family === 'talent_acquisition') {
      experience.push({
        text: `At ${company} as ${title}, walk me through a tough hire from intake to close.`,
        what_to_listen_for: ['Full-cycle ownership', 'Stakeholders', 'Outcome'],
        follow_ups: ['What made that search difficult?'],
      })
    } else if (family === 'sap') {
      experience.push({
        text: `At ${company} as ${title}, what SAP modules or integrations did you own?`,
        what_to_listen_for: ['Scope owned', 'Tools used', 'Outcome'],
        follow_ups: ['What broke in production and how did you fix it?'],
      })
    } else {
      experience.push({
        text: `At ${company} as ${title}, what was your core scope and biggest deliverable?`,
        what_to_listen_for: ['Scope owned', 'Tools used', 'Outcome'],
        follow_ups: ['What was the hardest part of that work?'],
      })
    }
  }
  if (matchedSkills[0]) {
    experience.push({
      text: `What's the toughest live issue you've fixed involving ${matchedSkills[0]}?`,
      what_to_listen_for: ['Root cause', 'Resolution steps', 'Impact'],
      follow_ups: [],
    })
  }

  const behavioral = family === 'talent_acquisition'
    ? [{
        text: 'Tell me about a hiring manager who kept moving the goalposts — how did you handle it?',
        what_to_listen_for: ['Stakeholder management', 'Pushback', 'Outcome'],
        follow_ups: ['What would you do differently?'],
      }]
    : roleTitle
      ? [{
          text: `Describe a high-pressure situation in your ${roleTitle} work — how did you prioritize?`,
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
    candidate_briefing: {
      profile_snapshot: company && title ? `${title} background at ${company}.` : 'Review resume before the call.',
      strengths_to_confirm: matchedSkills.slice(0, 3).map(
        (s) => `Resume shows ${s} — ask for a concrete example`,
      ),
      areas_to_probe: filteredMissing.slice(0, 3).map(
        (s) => `JD needs ${s} — light on resume, worth a direct question`,
      ),
      context_notes: ['Keep the screen to 20–25 minutes; prioritize must-have gaps first.'],
    },
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
    roleTitle: roleTitle || analysisData?.jd_analysis?.role_title || '',
    workExperience:
      analysisData?.work_experience ||
      analysisData?.candidate_profile?.work_experience ||
      [],
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
  if (text.length > 72) {
    const words = text.split(/\s+/)
    text = words.slice(0, 10).join(' ') + (words.length > 10 ? '…' : '')
  }
  return text
}

/** Keep teleprompter questions scannable during a live call. */
export function spokenQuestionText(text, maxLen = 220) {
  if (!text || typeof text !== 'string') return String(text ?? '')
  let spoken = text.trim()
  const swaps = [
    ['The role calls for', 'This role needs'],
    ["I don't see much", 'I noticed'],
    ['on your resume', 'on the resume'],
  ]
  for (const [from, to] of swaps) {
    if (spoken.includes(from)) spoken = spoken.replace(from, to)
  }
  if (spoken.length <= maxLen) return spoken
  const sentenceEnd = spoken.search(/[.!?]\s/)
  if (sentenceEnd > 40 && sentenceEnd < maxLen) return spoken.slice(0, sentenceEnd + 1)
  return spoken.slice(0, maxLen).trimEnd() + '…'
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
  const lower = (qText || '').toLowerCase()
  if ((missingSkills || []).some((s) => lower.includes(s.toLowerCase()))) return 'high'
  if ((matchedSkills || []).some((s) => lower.includes(s.toLowerCase()))) return 'low'
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

export function applyVoiceTone(text, tone = 'conversational') {
  if (!text || typeof text !== 'string') return ''
  if (tone === 'formal') {
    return text
      .replace(/^The role calls for/i, 'This position requires')
      .replace(/I don't see much/i, 'Your background shows limited')
      .replace(/Walk me through/i, 'Please describe')
      .replace(/You mention/i, 'Your resume indicates')
  }
  return spokenQuestionText(text)
}

export function buildGlanceBullets(briefing, flatQuestions, limit = 5) {
  const bullets = []
  ;(briefing?.areas_to_probe || []).slice(0, 2).forEach((line) => {
    bullets.push(line.startsWith('JD needs') ? line : `Probe: ${line}`)
  })
  ;(briefing?.strengths_to_confirm || []).slice(0, 1).forEach((line) => {
    bullets.push(line.startsWith('Resume') ? line : `Confirm: ${line}`)
  })
  for (const item of flatQuestions || []) {
    if (bullets.length >= limit) break
    const text = item?.question?.text
    if (text) bullets.push(text)
  }
  return bullets.slice(0, limit)
}

export function formatHmDebriefText({
  candidateName = 'Candidate',
  roleTitle = 'Role',
  fitScore = null,
  recommendation = '',
  summary = '',
  debrief = null,
}) {
  const recLabel = (recommendation || '').replace(/_/g, ' ')
  const lines = [
    `Screening summary — ${candidateName}`,
    `Role: ${roleTitle}`,
    fitScore != null ? `Pre-screen fit: ${fitScore}%` : null,
    recLabel ? `Recommendation: ${recLabel}` : null,
    '',
    'Summary',
    summary || '(no summary)',
  ].filter((line) => line !== null)

  if (debrief) {
    if (debrief.overview) lines.push('', 'Overview', debrief.overview)
    if (debrief.strengths) lines.push('', 'Strengths', debrief.strengths)
    if (debrief.concerns) lines.push('', 'Concerns', debrief.concerns)
    if (debrief.recommendation_rationale) {
      lines.push('', 'Rationale', debrief.recommendation_rationale)
    }
  }
  return lines.join('\n')
}
