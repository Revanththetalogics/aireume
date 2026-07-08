import { describe, it, expect } from 'vitest'
import { extractRescoreSkillClassification, normalizeSkillEntry } from '../rescoreUtils'

describe('rescoreUtils', () => {
  it('normalizes string skills to editor objects', () => {
    expect(normalizeSkillEntry('Excel')).toEqual({
      skill: 'Excel',
      confidence: 'high',
      source: 'analysis',
      proficiency_expected: 'intermediate',
    })
  })

  it('prefers jd_analysis skills used during scoring', () => {
    const data = extractRescoreSkillClassification({
      jd_analysis: {
        required_skills: ['Financial Modeling', 'SAP'],
        nice_to_have_skills: ['Power BI'],
        skill_proficiency_requirements: { 'financial modeling': 'advanced' },
      },
      skill_analysis: {
        matched_required: ['Financial Modeling'],
        missing_required: ['SAP'],
      },
    })

    expect(data.required_skills.map((s) => s.skill)).toEqual(['Financial Modeling', 'SAP'])
    expect(data.required_skills[0].proficiency_expected).toBe('advanced')
    expect(data.nice_to_have_skills.map((s) => s.skill)).toEqual(['Power BI'])
  })

  it('reconstructs from skill_analysis tiers when jd lists are missing', () => {
    const data = extractRescoreSkillClassification({
      skill_analysis: {
        matched_required: ['Python'],
        missing_required: ['Docker'],
        matched_nice_to_have: ['AWS'],
        missing_nice_to_have: ['Terraform'],
      },
    })

    expect(data.required_skills.map((s) => s.skill)).toEqual(['Python', 'Docker'])
    expect(data.nice_to_have_skills.map((s) => s.skill)).toEqual(['AWS', 'Terraform'])
  })
})
