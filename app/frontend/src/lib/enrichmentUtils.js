/** Shared enrichment phase helpers for narrative, interview kit, and voice strategy. */

export const ENRICHMENT_PHASES = [
  { key: 'parsing', label: 'Parsing resume' },
  { key: 'scoring', label: 'Scoring fit' },
  { key: 'narrative', label: 'AI insights' },
  { key: 'interview_kit', label: 'Interview kit' },
  { key: 'voice_strategy', label: 'Voice interview plan' },
]

export function isNarrativePending(result) {
  const s = result?.narrative_status
  return s === 'pending' || s === 'processing' || result?.narrative_pending === true
}

export function isKitPending(result) {
  const s = result?.interview_kit_status
  return s === 'pending' || s === 'processing'
}

export function isVoiceStrategyPending(result) {
  const s = result?.voice_strategy_status
  return s === 'pending' || s === 'processing'
}

export function isVoiceStrategyReady(result) {
  return result?.voice_strategy_status === 'ready'
}

export function isVoiceStrategySkipped(result) {
  return result?.voice_strategy_status === 'skipped'
}

export function getEnrichmentPhaseStatus(result) {
  const narrative = result?.narrative_status || 'pending'
  const kit = result?.interview_kit_status || 'pending'
  const voice = result?.voice_strategy_status || 'pending'

  return {
    narrative: normalizeStatus(narrative),
    interview_kit: normalizeKitStatus(kit, narrative),
    voice_strategy: normalizeVoiceStatus(voice, narrative),
  }
}

function normalizeStatus(status) {
  if (status === 'ready') return 'complete'
  if (status === 'fallback' || status === 'failed') return 'fallback'
  if (status === 'processing') return 'active'
  return 'pending'
}

function normalizeKitStatus(kit, narrative) {
  if (kit === 'ready' || kit === 'fallback') return 'complete'
  if (kit === 'skipped') return 'skipped'
  if (kit === 'processing') return 'active'
  if (narrative === 'ready' || narrative === 'fallback') return 'pending'
  return 'waiting'
}

function normalizeVoiceStatus(voice, narrative) {
  if (voice === 'ready') return 'complete'
  if (voice === 'skipped') return 'skipped'
  if (voice === 'fallback' || voice === 'failed') return 'fallback'
  if (voice === 'processing') return 'active'
  if (narrative === 'ready' || narrative === 'fallback') return 'pending'
  return 'waiting'
}

export function mergeNarrativePollResult(prev, data) {
  const kit = data.interview_kit_status
  const voice = data.voice_strategy_status
  return {
    ...(data.narrative || {}),
    narrative_status: data.status,
    narrative_pending: kit === 'pending' || kit === 'processing',
    interview_kit_status: kit ?? prev?.interview_kit_status,
    voice_strategy_status: voice ?? prev?.voice_strategy_status,
    narrative_error: data.error ?? prev?.narrative_error,
    ai_enhanced: data.status === 'ready',
  }
}

export function shouldContinueNarrativePoll(data) {
  const narrativeDone = data.status === 'ready' || data.status === 'fallback' || data.status === 'failed'
  const kitDone =
    !data.interview_kit_status ||
    data.interview_kit_status === 'ready' ||
    data.interview_kit_status === 'fallback' ||
    data.interview_kit_status === 'skipped'
  return !(narrativeDone && kitDone)
}
