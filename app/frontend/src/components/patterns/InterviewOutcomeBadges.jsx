import { Badge } from '../ui'
import { consolidatedLabel, callSourceLabel } from '../../lib/interviewOutcomeUtils'

/**
 * Score progression: 72 → 81 after screen, or resume-only with pending badge.
 */
export function ScoreProgression({ analysisScore, callScore, callSource, compact = false, inverted = false }) {
  const scoreCls = inverted ? 'text-white' : 'text-brand-800'
  const mutedCls = inverted ? 'text-white/70' : 'text-slate-500'
  const arrowCls = inverted ? 'text-white/60' : 'text-brand-400'
  const strongCls = inverted ? 'text-white' : 'text-brand-700'

  if (analysisScore == null) return null
  if (callScore == null) {
    return (
      <span className={`inline-flex items-center gap-1.5 ${compact ? 'text-xs' : 'text-sm'}`}>
        <span className={`font-bold tabular-nums ${scoreCls}`}>{analysisScore}</span>
        <Badge color={inverted ? 'slate' : 'slate'} className="text-[10px] px-1.5 py-0">Interview pending</Badge>
      </span>
    )
  }
  const screenBadge = callSource === 'human' ? 'Live screened' : callSource === 'ai' ? 'AI screened' : 'Screened'
  return (
    <span className={`inline-flex items-center gap-1.5 flex-wrap ${compact ? 'text-xs' : 'text-sm'}`}>
      <span className={`font-bold tabular-nums ${mutedCls}`}>{analysisScore}</span>
      <span className={`font-bold ${arrowCls}`}>→</span>
      <span className={`font-black tabular-nums ${strongCls}`}>{callScore}</span>
      <Badge color="brand" className="text-[10px] px-1.5 py-0">{screenBadge}</Badge>
    </span>
  )
}

/**
 * Compact outcome display for list rows and pipeline cards.
 */
export default function InterviewOutcomeBadges({
  analysisScore,
  callScore,
  callSource,
  consolidatedRecommendation,
  className = '',
}) {
  const recLabel = consolidatedLabel(consolidatedRecommendation)

  return (
    <div className={`flex flex-wrap items-center gap-1.5 ${className}`}>
      <ScoreProgression
        analysisScore={analysisScore}
        callScore={callScore}
        callSource={callSource}
        compact
      />
      {recLabel && (
        <Badge
          color={
            consolidatedRecommendation?.includes('advance') ? 'emerald'
              : consolidatedRecommendation?.includes('reject') ? 'red'
                : 'amber'
          }
          className="text-[10px] px-2 py-0.5 font-semibold"
        >
          {recLabel}
        </Badge>
      )}
    </div>
  )
}
