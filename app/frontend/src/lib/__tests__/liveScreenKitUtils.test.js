import { describe, it, expect } from 'vitest'
import {
  countKitQuestions,
  buildFallbackKit,
  resolveInterviewKit,
  getKitReadiness,
  hasBriefingContent,
  flattenQuestions,
  flattenStrategyQuestions,
  getSpokenLine,
  isKitV3,
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

  it('marks stored kit as fallback when interview_kit_status is fallback', () => {
    const kit = {
      kit_version: 2,
      threads: [{ steps: [{ text: 'How do you handle budgeting?' }] }],
    }
    const resolved = resolveInterviewKit(kit, {}, 'Analyst', 'fallback')
    expect(resolved.isFallback).toBe(true)
    expect(resolved.totalQ).toBe(1)
  })

  it('getKitReadiness reports fallback state from status', () => {
    const kit = {
      kit_version: 2,
      threads: [{ steps: [{ text: 'Probe topic?' }] }],
    }
    const readiness = getKitReadiness('fallback', kit, {}, 'Analyst')
    expect(readiness.state).toBe('fallback')
    expect(readiness.isFallback).toBe(true)
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

  it('isKitV3 detects v3 kits', () => {
    expect(isKitV3({ kit_version: 3, threads: [] })).toBe(true)
    expect(isKitV3({ kit_version: 2, threads: [] })).toBe(false)
  })

  it('getSpokenLine prefers spoken_text', () => {
    expect(getSpokenLine({ spoken_text: 'Hi', text: 'Old' })).toBe('Hi')
  })

  it('flattenStrategyQuestions maps v3 threads', () => {
    const questions = flattenStrategyQuestions({
      kit_version: 3,
      threads: [{
        id: 'thread_ownership',
        kind: 'ownership',
        steps: [{
          spoken_text: 'At Acme — what did you own?',
          intent: 'Verify ownership',
          what_to_listen_for: ['Personal scope'],
        }],
      }],
    })
    expect(questions).toHaveLength(1)
    expect(questions[0].question_text).toContain('Acme')
    expect(questions[0].intent).toBe('Verify ownership')
  })
})
