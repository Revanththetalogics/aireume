import { describe, it, expect } from 'vitest'
import {
  formatBatchProgressTitle,
  formatBatchProgressSubtitle,
  getBatchProgressPercent,
  getEffectiveBatchTotal,
  isAnalyzeStepComplete,
  canNavigateToAnalyzeStep,
} from './analyzeBatchUtils'

describe('analyzeBatchUtils', () => {
  it('never formats 0 of 0 analyzing title', () => {
    expect(formatBatchProgressTitle({ analysisDone: false, completed: 0, total: 0, successful: 0, failed: 0, preparing: false, stuck: false }))
      .toBe('Starting analysis…')
  })

  it('uses human copy while scoring', () => {
    expect(formatBatchProgressTitle({ analysisDone: false, completed: 2, total: 5, successful: 2, failed: 0, preparing: false, stuck: false }))
      .toBe('Scoring resume 3 of 5')
  })

  it('reports zero scored on complete', () => {
    expect(formatBatchProgressTitle({ analysisDone: true, completed: 3, total: 3, successful: 0, failed: 3, preparing: false, stuck: false }))
      .toBe('No resumes were scored, 3 failed')
  })

  it('computes progress percent safely', () => {
    expect(getBatchProgressPercent(0, 0)).toBe(0)
    expect(getBatchProgressPercent(2, 5)).toBe(40)
  })

  it('falls back to file status count for total', () => {
    expect(getEffectiveBatchTotal({ completed: 0, total: 0 }, [{ filename: 'a.pdf' }])).toBe(1)
  })

  it('marks step 3 complete only when analysis done', () => {
    expect(isAnalyzeStepComplete(3, { isStep1Complete: true, isStep2Complete: true, showResults: true, analysisDone: false })).toBe(false)
    expect(isAnalyzeStepComplete(3, { isStep1Complete: true, isStep2Complete: true, showResults: true, analysisDone: true })).toBe(true)
  })

  it('blocks step navigation while analyzing', () => {
    expect(canNavigateToAnalyzeStep(1, { isAnalyzing: true, showResults: true })).toBe(false)
    expect(canNavigateToAnalyzeStep(3, { isAnalyzing: true, showResults: true })).toBe(true)
  })

  it('shows helpful subtitle before first result', () => {
    expect(formatBatchProgressSubtitle({ analysisDone: false, completed: 0, total: 4, etaMs: null, successful: 0 }))
      .toContain('First result')
  })
})
