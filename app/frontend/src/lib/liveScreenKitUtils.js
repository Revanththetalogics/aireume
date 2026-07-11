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

export function isPlaybookKit(kit) {
  return Boolean(kit && kit.kit_version === 2 && Array.isArray(kit.threads) && kit.threads.length > 0)
}

const THREAD_KIND_TO_CATEGORY = {
  risk: 'technical',
  ownership: 'experience_deep_dive',
  judgment: 'behavioral',
  technical: 'technical',
  general: 'experience_deep_dive',
}

export function getThreadsFromKit(interviewQuestions) {
  if (!isPlaybookKit(interviewQuestions)) return []
  return interviewQuestions.threads
}

export function countKitQuestions(interviewQuestions) {
  if (!interviewQuestions || typeof interviewQuestions !== 'object') return 0
  if (isPlaybookKit(interviewQuestions)) {
    return interviewQuestions.threads.reduce(
      (n, t) => n + (Array.isArray(t.steps) ? t.steps.length : 0),
      0,
    )
  }
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
  candidateName = '',
}) {
  const context = roleTitle || 'this role'
  const family = detectRoleFamily(roleTitle)
  const filteredMissing = filterMissingSkills(missingSkills, roleTitle)
  const company = workExperience[0]?.company?.trim() || 'your last employer'
  const title = workExperience[0]?.title?.trim() || 'your role'
  const primary = matchedSkills[0] || roleTitle || 'core skills'
  const riskSkill = filteredMissing[0]

  const ownershipSteps = family === 'sap'
    ? [{
        text: `Talk me through your most recent MM/ERP engagement — phase, modules, and what you personally owned.`,
        what_to_listen_for: ['Implementation phase', 'Modules', 'Personal deliverables'],
        follow_ups: ['What did you sign off before go-live?'],
      }]
    : family === 'talent_acquisition'
      ? [{
          text: 'Walk me through a search you owned end to end — from intake to offer.',
          what_to_listen_for: ['Full-cycle ownership', 'Stakeholders', 'Outcome'],
          follow_ups: ['What made that search difficult?'],
        }]
      : [{
          text: `Walk me through your most recent role at ${company} — what you owned and your biggest deliverable.`,
          what_to_listen_for: ['Scope owned', 'Tools/skills', 'Outcome'],
          follow_ups: ['What would your manager say you were accountable for?'],
        }]

  const riskSteps = riskSkill
    ? [{
        text: `This role needs ${riskSkill} — where has that shown up in your work, and what was your hands-on part?`,
        what_to_listen_for: [`Practical ${riskSkill}`, 'Personal contribution', 'Honest depth'],
        follow_ups: [`Pick one example — what did you personally do with ${riskSkill}?`],
      }]
    : []

  const judgmentStep = family === 'talent_acquisition'
    ? {
        text: 'Tell me about a hiring manager who kept moving the goalposts — how did you handle it?',
        what_to_listen_for: ['Stakeholder management', 'Pushback', 'Outcome'],
        follow_ups: ['What would you do differently?'],
      }
    : family === 'sap'
      ? {
          text: 'Describe a go-live or hypercare issue you handled — your role under pressure.',
          what_to_listen_for: ['Ownership', 'Resolution', 'Outcome'],
          follow_ups: [],
        }
      : {
          text: `Tell me about a time you had to push back on a stakeholder in your ${context} work.`,
          what_to_listen_for: ['Judgment', 'Communication', 'Outcome'],
          follow_ups: [],
        }

  const threads = [
    {
      id: 'thread_ownership',
      title: 'Core role ownership',
      kind: 'ownership',
      hypothesis_ids: ['H1'],
      time_minutes: 6,
      priority: 'must_have',
      steps: ownershipSteps,
    },
  ]
  if (riskSteps.length) {
    threads.push({
      id: 'thread_risk',
      title: `Risk area — ${riskSkill}`,
      kind: 'risk',
      hypothesis_ids: ['H2'],
      time_minutes: 7,
      priority: 'risk',
      steps: riskSteps,
    })
  }
  threads.push({
    id: 'thread_judgment',
    title: 'Stakeholder judgment',
    kind: 'judgment',
    hypothesis_ids: ['H3'],
    time_minutes: 5,
    priority: 'must_have',
    steps: [judgmentStep],
  })

  const legacy = { technical_questions: [], behavioral_questions: [], culture_fit_questions: [], experience_deep_dive_questions: [] }
  threads.forEach((thread) => {
    const cat = THREAD_KIND_TO_CATEGORY[thread.kind] || 'experience_deep_dive'
    const key = `${cat === 'technical' ? 'technical' : cat === 'behavioral' ? 'behavioral' : 'experience_deep_dive'}_questions`
    legacy[key].push(...thread.steps)
  })

  const screenObjective = `Validate fit for ${context} — confirm ${primary}${riskSkill ? `, de-risk ${riskSkill}` : ''}.`

  return {
    kit_version: 2,
    screen_objective: screenObjective,
    candidate_briefing: {
      profile_snapshot: company && title ? `${title} at ${company}.` : 'Review resume before the call.',
      strengths_to_confirm: matchedSkills.slice(0, 3).map((s) => `Confirm depth on ${s} with a concrete example`),
      areas_to_probe: filteredMissing.slice(0, 3).map((s) => `JD needs ${s} — dedicate a thread`),
      context_notes: ['Run threads in order; use one follow-up if answers are vague.'],
    },
    hypotheses: [
      { id: 'H1', label: `Can they own ${primary} work end-to-end?`, priority: 'must_have', why: 'Core role fit' },
      ...(riskSkill ? [{ id: 'H2', label: `Is ${riskSkill} a real gap?`, priority: 'risk', why: 'Top missing must-have' }] : []),
      { id: 'H3', label: 'Can they handle stakeholders under pressure?', priority: 'must_have', why: 'Judgment bar' },
    ],
    open: {
      script: `Hi ${candidateName || 'there'}, thanks for your time. I'd like to understand what you've owned recently and clarify fit for this ${context} role.`,
      listen_for: ['Ownership language', 'Clarifying questions about the role'],
    },
    threads,
    close: {
      script: 'What are you looking for next — type of work and start timing?',
      logistics: ['Notice period', 'Location / travel', 'Contract vs permanent'],
    },
    hm_debrief_template: {
      fit_summary_prompt: `Summarize fit for ${context}`,
      must_haves: [{ requirement: primary, status: 'pending' }],
      hm_focus_if_proceed: riskSkill ? [`Deep-dive ${riskSkill}`] : ['Validate ownership on latest engagement'],
      residual_risks: riskSkill ? [`Unverified: ${riskSkill}`] : [],
    },
    technical_questions: legacy.technical_questions.slice(0, 5),
    behavioral_questions: legacy.behavioral_questions.slice(0, 2),
    culture_fit_questions: [],
    experience_deep_dive_questions: legacy.experience_deep_dive_questions.slice(0, 3),
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
    candidateName: analysisData?.candidate_profile?.name || analysisData?.candidate_name || '',
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

export const THREAD_PRIORITY_META = {
  must_have: { label: 'Must-have', color: 'text-blue-700', bg: 'bg-blue-50', ring: 'ring-blue-200' },
  risk: { label: 'Risk / gap', color: 'text-amber-800', bg: 'bg-amber-50', ring: 'ring-amber-200' },
  nice_to_have: { label: 'Nice-to-have', color: 'text-slate-600', bg: 'bg-slate-50', ring: 'ring-slate-200' },
}

export function flattenQuestions(interviewQuestions) {
  if (isPlaybookKit(interviewQuestions)) {
    const flat = []
    const categoryIndices = {}
    interviewQuestions.threads.forEach((thread) => {
      const category = THREAD_KIND_TO_CATEGORY[thread.kind] || 'experience_deep_dive'
      if (categoryIndices[category] == null) categoryIndices[category] = 0
      ;(thread.steps || []).forEach((rawQ) => {
        const index = categoryIndices[category]
        flat.push({
          category,
          categoryLabel: CATEGORY_META[category]?.label || category,
          threadId: thread.id,
          threadTitle: thread.title,
          threadPriority: thread.priority,
          index,
          question: normalizeQuestion(rawQ),
        })
        categoryIndices[category] += 1
      })
    })
    return flat
  }

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

export function buildGlanceBullets(briefing, flatQuestions, kit, limit = 5) {
  const bullets = []
  if (kit?.screen_objective) {
    bullets.push(kit.screen_objective)
  }
  ;(briefing?.areas_to_probe || []).slice(0, 2).forEach((line) => {
    bullets.push(line.startsWith('JD needs') ? line : `Probe: ${line}`)
  })
  if (isPlaybookKit(kit)) {
    kit.threads.slice(0, 2).forEach((t) => {
      const first = t.steps?.[0]?.text
      if (first && bullets.length < limit) bullets.push(`${t.title}: ${first}`)
    })
  }
  for (const item of flatQuestions || []) {
    if (bullets.length >= limit) break
    const text = item?.question?.text
    if (text && !bullets.some((b) => b.includes(text.slice(0, 40)))) bullets.push(text)
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

export function formatHmDebriefWithTemplate({
  candidateName = 'Candidate',
  roleTitle = 'Role',
  kit = null,
  summary = '',
  recommendation = '',
}) {
  const base = formatHmDebriefText({ candidateName, roleTitle, recommendation, summary })
  const tmpl = kit?.hm_debrief_template
  if (!tmpl) return base
  const extra = []
  if (tmpl.residual_risks?.length) {
    extra.push('', 'Residual risks', ...tmpl.residual_risks.map((r) => `• ${r}`))
  }
  if (tmpl.hm_focus_if_proceed?.length) {
    extra.push('', 'HM focus if proceed', ...tmpl.hm_focus_if_proceed.map((r) => `• ${r}`))
  }
  return base + extra.join('\n')
}
