import { describe, it, expect } from 'vitest'
import {
  isNarrativePending,
  isKitPending,
  isVoiceStrategyReady,
  mergeNarrativePollResult,
  shouldContinueNarrativePoll,
  getEnrichmentPhaseStatus,
  hasNarrativeContent,
  needsNarrativeHydration,
} from './enrichmentUtils'

describe('enrichmentUtils', () => {
  it('detects narrative pending states', () => {
    expect(isNarrativePending({ narrative_status: 'pending' })).toBe(true)
    expect(isNarrativePending({ narrative_status: 'processing' })).toBe(true)
    expect(isNarrativePending({ narrative_status: 'ready' })).toBe(false)
  })

  it('detects kit pending states', () => {
    expect(isKitPending({ interview_kit_status: 'processing' })).toBe(true)
    expect(isKitPending({ interview_kit_status: 'ready' })).toBe(false)
  })

  it('detects voice strategy ready', () => {
    expect(isVoiceStrategyReady({ voice_strategy_status: 'ready' })).toBe(true)
    expect(isVoiceStrategyReady({ voice_strategy_status: 'pending' })).toBe(false)
  })

  it('merges poll result into previous state', () => {
    const prev = { fit_score: 80, interview_kit_status: 'pending' }
    const merged = mergeNarrativePollResult(prev, {
      status: 'ready',
      interview_kit_status: 'processing',
      voice_strategy_status: 'pending',
      narrative: { strengths: ['Leadership'] },
    })
    expect(merged.narrative_status).toBe('ready')
    expect(merged.ai_enhanced).toBe(true)
    expect(merged.strengths).toEqual(['Leadership'])
    expect(merged.narrative_pending).toBe(false)
    expect(merged.interview_kit_status).toBe('processing')
  })

  it('detects missing narrative hydration when status is ready but body empty', () => {
    expect(needsNarrativeHydration({ narrative_status: 'ready', strengths: [] })).toBe(true)
    expect(needsNarrativeHydration({
      narrative_status: 'ready',
      fit_summary: 'Strong FP&A background.',
    })).toBe(false)
    expect(hasNarrativeContent({ strengths: ['Excel'] })).toBe(true)
  })

  it('continues polling while kit is pending', () => {
    expect(shouldContinueNarrativePoll({
      status: 'ready',
      interview_kit_status: 'processing',
    })).toBe(true)
    expect(shouldContinueNarrativePoll({
      status: 'ready',
      interview_kit_status: 'ready',
    })).toBe(false)
  })

  it('maps enrichment phases from result', () => {
    const phases = getEnrichmentPhaseStatus({
      narrative_status: 'ready',
      interview_kit_status: 'processing',
      voice_strategy_status: 'pending',
    })
    expect(phases.narrative).toBe('complete')
    expect(phases.interview_kit).toBe('active')
    expect(phases.voice_strategy).toBe('pending')
  })
})
