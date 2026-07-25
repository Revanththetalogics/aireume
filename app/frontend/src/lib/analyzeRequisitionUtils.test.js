import { describe, it, expect } from 'vitest'
import {
  buildSkillStateFromRequisition,
  canUseAdHocPath,
  requiresRequisitionSelection,
  skillsFromRequisition,
} from './analyzeRequisitionUtils'

describe('analyzeRequisitionUtils', () => {
  it('requires requisition when feature enabled and mode is requisition_required', () => {
    expect(requiresRequisitionSelection(true, 'requisition_required')).toBe(true)
    expect(requiresRequisitionSelection(true, 'allow_ad_hoc')).toBe(false)
    expect(requiresRequisitionSelection(false, 'requisition_required')).toBe(false)
  })

  it('allows ad-hoc path for starter or allow_ad_hoc tenants', () => {
    expect(canUseAdHocPath(false, 'requisition_required', false)).toBe(true)
    expect(canUseAdHocPath(true, 'allow_ad_hoc', false)).toBe(true)
    expect(canUseAdHocPath(true, 'requisition_required', true)).toBe(true)
    expect(canUseAdHocPath(true, 'requisition_required', false)).toBe(false)
  })

  it('prefers skill overrides over calibrated criteria', () => {
    const skills = skillsFromRequisition({
      required_skills_override: ['Python'],
      calibrated_criteria_json: { must_haves: ['Java'] },
    })
    expect(skills.required_skills).toEqual(['Python'])
    expect(skills.source).toBe('overrides')
  })

  it('loads calibrated criteria when overrides are empty', () => {
    const skills = skillsFromRequisition({
      calibrated_criteria_json: {
        must_haves: ['Excel'],
        good_to_haves: ['SQL'],
      },
    })
    expect(skills.required_skills).toEqual(['Excel'])
    expect(skills.nice_to_have_skills).toEqual(['SQL'])
    expect(skills.source).toBe('calibrated')
  })

  it('builds confirmed skill state from requisition', () => {
    const state = buildSkillStateFromRequisition({
      calibrated_criteria_json: { must_haves: ['Playwright'] },
    })
    expect(state.skillsConfirmed).toBe(true)
    expect(state.skillOverrides.required_skills).toEqual(['Playwright'])
    expect(state.skipAutoParse).toBe(true)
  })
})
