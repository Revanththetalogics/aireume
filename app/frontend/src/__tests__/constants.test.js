import { describe, it, expect } from 'vitest'
import {
  getScoreHexColor,
  getScoreColor,
  getRecommendation,
  SCORE_THRESHOLDS,
  INDUSTRIES,
  COMPANY_SIZES,
} from '../lib/constants'

describe('getScoreHexColor', () => {
  it('maps high scores to green', () => {
    expect(getScoreHexColor(90)).toBe('#22c55e')
    expect(getScoreHexColor(80)).toBe('#22c55e')
  })
  it('maps medium scores to amber', () => {
    expect(getScoreHexColor(79)).toBe('#f59e0b')
    expect(getScoreHexColor(60)).toBe('#f59e0b')
  })
  it('maps low scores to orange', () => {
    expect(getScoreHexColor(59)).toBe('#fb923c')
    expect(getScoreHexColor(40)).toBe('#fb923c')
  })
  it('maps poor scores to red', () => {
    expect(getScoreHexColor(39)).toBe('#ef4444')
    expect(getScoreHexColor(0)).toBe('#ef4444')
  })
  it('returns slate for missing scores', () => {
    expect(getScoreHexColor(null)).toBe('#94a3b8')
    expect(getScoreHexColor(undefined)).toBe('#94a3b8')
  })

  it('stays consistent with getScoreColor tier boundaries', () => {
    // hex and tailwind mappings must agree on tier boundaries
    expect(getScoreColor(SCORE_THRESHOLDS.HIGH.min)).toBe(getScoreColor(100))
    expect(getScoreHexColor(SCORE_THRESHOLDS.HIGH.min)).toBe(getScoreHexColor(100))
  })
})

describe('getRecommendation', () => {
  it('labels a strong match', () => {
    expect(getRecommendation(85).label).toBe('Strong Match')
  })
  it('labels a not-recommended candidate', () => {
    expect(getRecommendation(10).label).toBe('Not Recommended')
  })
  it('handles missing score', () => {
    expect(getRecommendation(null).label).toBe('—')
  })
})

describe('onboarding option constants', () => {
  it('exposes industries and company sizes', () => {
    expect(INDUSTRIES).toContain('Technology')
    expect(COMPANY_SIZES).toContain('500+')
  })
})
