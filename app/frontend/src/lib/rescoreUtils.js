/**
 * Resolve the skill classification used for a screening result so Rescore
 * pre-fills the same must-have / good-to-have lists from the original analysis.
 */

function proficiencyMapFromJd(jd = {}) {
  const map = {}
  const reqs = jd.skill_proficiency_requirements
  if (reqs && typeof reqs === 'object') {
    for (const [skill, level] of Object.entries(reqs)) {
      if (skill && level) map[String(skill).toLowerCase()] = String(level).toLowerCase()
    }
  }
  return map
}

export function normalizeSkillEntry(item, options = {}) {
  const { proficiencyMap = {}, defaultProficiency = 'intermediate' } = options
  if (item == null || item === '') return null

  if (typeof item === 'string') {
    const prof = proficiencyMap[item.toLowerCase()] || defaultProficiency
    return {
      skill: item,
      confidence: 'high',
      source: 'analysis',
      proficiency_expected: prof,
    }
  }

  if (typeof item === 'object') {
    const name = item.skill || item.name || ''
    if (!name) return null
    return {
      skill: name,
      confidence: item.confidence || 'high',
      source: item.source || 'analysis',
      proficiency_expected:
        item.proficiency_expected ||
        item.proficiency ||
        proficiencyMap[String(name).toLowerCase()] ||
        defaultProficiency,
      is_hot: item.is_hot,
      is_in_demand: item.is_in_demand,
    }
  }

  return null
}

function normalizeSkillList(items, options) {
  if (!Array.isArray(items)) return []
  const seen = new Set()
  const out = []
  for (const item of items) {
    const normalized = normalizeSkillEntry(item, options)
    if (!normalized) continue
    const key = normalized.skill.toLowerCase()
    if (seen.has(key)) continue
    seen.add(key)
    out.push(normalized)
  }
  return out
}

function pickSkillLists(source) {
  if (!source || typeof source !== 'object') return { required: [], nice: [] }
  return {
    required: source.required_skills || [],
    nice: source.nice_to_have_skills || [],
  }
}

function listsFromSkillAnalysis(skillAnalysis = {}) {
  const required = [
    ...(skillAnalysis.matched_required || []),
    ...(skillAnalysis.missing_required || []),
  ]
  const nice = [
    ...(skillAnalysis.matched_nice_to_have || []),
    ...(skillAnalysis.missing_nice_to_have || []),
  ]
  return { required, nice }
}

/** @returns {{ required_skills: object[], nice_to_have_skills: object[], excluded_skills?: string[], suggested_additions?: string[] }} */
export function extractRescoreSkillClassification(result) {
  if (!result) {
    return { required_skills: [], nice_to_have_skills: [] }
  }

  const jd =
    result.jd_analysis ||
    result.analysis_result?.jd_analysis ||
    {}

  const skillAnalysis =
    result.skill_analysis ||
    result.analysis_result?.skill_analysis ||
    {}

  const proficiencyMap = proficiencyMapFromJd(jd)

  // Priority: jd_analysis (what scoring used) → top-level → skill tier reconstruction
  let { required, nice } = pickSkillLists(jd)

  if (!required.length && !nice.length) {
    const top = pickSkillLists(result)
    required = top.required
    nice = top.nice
  }

  if (!required.length && !nice.length) {
    const top = pickSkillLists(result.analysis_result)
    required = top.required
    nice = top.nice
  }

  if (!required.length && !nice.length) {
    const fromTiers = listsFromSkillAnalysis(skillAnalysis)
    required = fromTiers.required
    nice = fromTiers.nice
  }

  return {
    required_skills: normalizeSkillList(required, {
      proficiencyMap,
      defaultProficiency: 'intermediate',
    }),
    nice_to_have_skills: normalizeSkillList(nice, {
      proficiencyMap,
      defaultProficiency: 'basic',
    }),
    excluded_skills: jd.excluded_skills || [],
    suggested_additions: jd.suggested_additions || [],
    jd_quality: jd.jd_quality,
    market_summary: jd.market_summary,
  }
}
