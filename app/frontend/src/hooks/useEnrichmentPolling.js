import { useEffect, useRef } from 'react'
import { getNarrative } from '../lib/api'
import { mergeNarrativePollResult, shouldContinueNarrativePoll, needsNarrativeHydration } from '../lib/enrichmentUtils'

/**
 * Poll GET /analysis/{id}/narrative until narrative + interview kit settle.
 *
 * @param {object|null} result - Current screening result object
 * @param {function} onUpdate - Called with merged result fields
 * @param {object} options
 * @param {function} [options.onComplete] - Called when polling finishes
 * @param {function} [options.onKitReady] - Called when interview kit becomes ready
 * @param {number} [options.intervalMs=5000]
 * @param {number} [options.maxPolls=60]
 */
export function useEnrichmentPolling(result, onUpdate, options = {}) {
  const {
    onComplete,
    onKitReady,
    intervalMs = 5000,
    maxPolls = 60,
  } = options

  const onUpdateRef = useRef(onUpdate)
  const onCompleteRef = useRef(onComplete)
  const onKitReadyRef = useRef(onKitReady)
  onUpdateRef.current = onUpdate
  onCompleteRef.current = onComplete
  onKitReadyRef.current = onKitReady

  const resultRef = useRef(result)
  resultRef.current = result

  const analysisId = result?.analysis_id || result?.result_id

  useEffect(() => {
    if (!analysisId) return

    const snapshot = resultRef.current
    const narrativeStatus = snapshot?.narrative_status || 'pending'
    const kitStatus = snapshot?.interview_kit_status || 'pending'
    const needsNarrativePoll = needsNarrativeHydration(snapshot)
    const needsKitPoll =
      (narrativeStatus === 'ready' || narrativeStatus === 'fallback') &&
      (kitStatus === 'pending' || kitStatus === 'processing')

    if (!needsNarrativePoll && !needsKitPoll) return

    let pollCount = 0
    let kitWasPending = needsKitPoll
    let cancelled = false
    let timerId = null
    let delayMs = intervalMs

    const schedule = (ms) => {
      timerId = setTimeout(tick, ms)
    }

    const tick = async () => {
      if (cancelled) return
      pollCount += 1
      try {
        const data = await getNarrative(analysisId)
        if (cancelled) return
        delayMs = intervalMs

        onUpdateRef.current?.((prev) => ({
          ...prev,
          ...mergeNarrativePollResult(prev, data),
        }))

        const kitNowReady =
          data.interview_kit_status === 'ready' || data.interview_kit_status === 'fallback'
        if (kitWasPending && kitNowReady) {
          kitWasPending = false
          onKitReadyRef.current?.(data)
        }

        if (!shouldContinueNarrativePoll(data) || pollCount >= maxPolls) {
          onCompleteRef.current?.(data)
          return
        }
        schedule(delayMs)
      } catch (err) {
        const status = err?.response?.status
        if (status === 429) {
          const retryAfter = parseInt(err?.response?.headers?.['retry-after'] || '5', 10)
          delayMs = Math.min(Math.max(retryAfter * 1000, intervalMs), 30000)
        } else {
          delayMs = Math.min(Math.round(delayMs * 1.5), 30000)
        }
        console.debug('[useEnrichmentPolling]', err?.message || err)
        if (pollCount >= maxPolls) {
          onCompleteRef.current?.(null)
          return
        }
        schedule(delayMs)
      }
    }

    tick()

    return () => {
      cancelled = true
      if (timerId) clearTimeout(timerId)
    }
  }, [analysisId, intervalMs, maxPolls])
}
