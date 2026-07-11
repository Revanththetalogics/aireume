import { describe, it, expect } from 'vitest'
import {
  countKitQuestions,
  buildFallbackKit,
  resolveInterviewKit,
  getKitReadiness,
  hasBriefingContent,
  flattenQuestions,
  shouldWarnRoleMismatch,
  isPlaybookKit,
} from '../liveScreenKitUtils'

describe('liveScreenKitUtils', () => {
  it('counts questions across categories', () => {
    const kit = {
      technical_questions: ['Q1'],
      behavioral_questions: [{ text: 'Q2' }],
      culture_fit_questions: [],
      experience_deep_dive_questions: [],
    }
    expect(countKitQuestions(kit)).toBe(2)
  })

  it('builds playbook v2 fallback kit from skills', () => {
    const kit = buildFallbackKit({
      missingSkills: ['Python', 'AWS'],
      matchedSkills: ['SQL'],
      roleTitle: 'Engineer',
    })
    expect(isPlaybookKit(kit)).toBe(true)
    expect(countKitQuestions(kit)).toBeGreaterThan(0)
    expect(kit.threads.length).toBeGreaterThan(0)
  })

  it('resolves to fallback when AI kit empty', () => {
    const resolved = resolveInterviewKit({}, { missing_skills: ['React'] }, 'Dev')
    expect(resolved.isFallback).toBe(true)
    expect(resolved.totalQ).toBeGreaterThan(0)
  })

  it('getKitReadiness returns loading state', () => {
    expect(getKitReadiness('processing', null, {}, '').state).toBe('loading')
  })

  it('hasBriefingContent false for empty shell', () => {
    expect(hasBriefingContent({})).toBe(false)
    expect(hasBriefingContent({ profile_snapshot: 'Hi' })).toBe(true)
  })

  it('flattenQuestions preserves order', () => {
    const flat = flattenQuestions({
      technical_questions: ['T1'],
      behavioral_questions: ['B1'],
    })
    expect(flat).toHaveLength(2)
    expect(flat[0].category).toBe('technical')
  })

  it('shouldWarnRoleMismatch below 40', () => {
    expect(shouldWarnRoleMismatch(0)).toBe(true)
    expect(shouldWarnRoleMismatch(75)).toBe(false)
  })
})
