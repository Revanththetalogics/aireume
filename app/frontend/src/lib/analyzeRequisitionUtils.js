/** Helpers for requisition-centric Analyze flow. */

export function countJdWords(text) {
  if (!text?.trim()) return 0
  return text.trim().split(/\s+/).filter(Boolean).length
}

export function parseSkillOverride(val) {
  if (!val) return []
  if (Array.isArray(val)) return val
  if (typeof val === 'string') {
    try {
      const parsed = JSON.parse(val)
      return Array.isArray(parsed) ? parsed : []
    } catch {
      return []
    }
  }
  return []
}

export function parseCriteriaJson(val) {
  if (!val) return null
  if (typeof val === 'object') return val
  if (typeof val === 'string') {
    try {
      return JSON.parse(val)
    } catch {
      return null
    }
  }
  return null
}

/** Resolve screening skills from overrides, then calibrated criteria, then null (needs parse). */
export function skillsFromRequisition(requisition) {
  if (!requisition) return null

  const reqOverride = parseSkillOverride(requisition.required_skills_override)
  const niceOverride = parseSkillOverride(requisition.nice_to_have_skills_override)
  if (reqOverride.length > 0 || niceOverride.length > 0) {
    return {
      required_skills: reqOverride,
      nice_to_have_skills: niceOverride,
      source: 'overrides',
    }
  }

  const criteria = parseCriteriaJson(requisition.calibrated_criteria_json)
  const mustHaves = criteria?.must_haves || []
  const goodToHaves = criteria?.good_to_haves || []
  if (mustHaves.length > 0 || goodToHaves.length > 0) {
    return {
      required_skills: mustHaves,
      nice_to_have_skills: goodToHaves,
      source: 'calibrated',
    }
  }

  return null
}

export function buildSkillStateFromRequisition(requisition) {
  const skills = skillsFromRequisition(requisition)
  if (!skills) {
    return {
      skillOverrides: null,
      skillsConfirmed: false,
      jdParseResult: null,
      skipAutoParse: false,
    }
  }

  return {
    skillOverrides: {
      required_skills: skills.required_skills,
      nice_to_have_skills: skills.nice_to_have_skills,
    },
    skillsConfirmed: true,
    jdParseResult: {
      required_skills: skills.required_skills,
      nice_to_have_skills: skills.nice_to_have_skills,
      restored_from_requisition: true,
      skill_source: skills.source,
    },
    skipAutoParse: true,
  }
}

export function requiresRequisitionSelection(hasRequisitions, screeningMode) {
  return Boolean(hasRequisitions && screeningMode === 'requisition_required')
}

export function canUseAdHocPath(hasRequisitions, screeningMode, adHocMode) {
  if (!hasRequisitions) return true
  if (screeningMode === 'allow_ad_hoc') return true
  return Boolean(adHocMode)
}
