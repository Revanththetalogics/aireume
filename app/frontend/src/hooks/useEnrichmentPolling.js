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
 * @param {number} [options.intervalMs=2000]
 * @param {number} [options.maxPolls=90]
 */
export function useEnrichmentPolling(result, onUpdate, options = {}) {
  const {
    onComplete,
    onKitReady,
    intervalMs = 2000,
    maxPolls = 90,
  } = options

  const onUpdateRef = useRef(onUpdate)
  const onCompleteRef = useRef(onComplete)
  const onKitReadyRef = useRef(onKitReady)
  onUpdateRef.current = onUpdate
  onCompleteRef.current = onComplete
  onKitReadyRef.current = onKitReady

  const analysisId = result?.analysis_id || result?.result_id
  const narrativeStatus = result?.narrative_status || 'pending'
  const kitStatus = result?.interview_kit_status || 'pending'

  useEffect(() => {
    if (!analysisId) return

    const needsNarrativePoll = needsNarrativeHydration(result)
    const needsKitPoll =
      (narrativeStatus === 'ready' || narrativeStatus === 'fallback') &&
      (kitStatus === 'pending' || kitStatus === 'processing')

    if (!needsNarrativePoll && !needsKitPoll) return

    let pollCount = 0
    let kitWasPending = needsKitPoll
    let cancelled = false

    const tick = async () => {
      if (cancelled) return
      pollCount += 1
      try {
        const data = await getNarrative(analysisId)
        if (cancelled) return

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
          clearInterval(interval)
          onCompleteRef.current?.(data)
        }
      } catch (err) {
        console.error('[useEnrichmentPolling]', err)
        if (pollCount >= maxPolls) {
          clearInterval(interval)
          onCompleteRef.current?.(null)
        }
      }
    }

    const interval = setInterval(tick, intervalMs)
    tick()

    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [analysisId, narrativeStatus, kitStatus, intervalMs, maxPolls, result])
}
