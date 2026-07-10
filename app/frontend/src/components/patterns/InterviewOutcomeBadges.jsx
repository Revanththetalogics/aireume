import { Badge } from '../ui'
import { consolidatedLabel, callSourceLabel } from '../../lib/interviewOutcomeUtils'

/**
 * Compact outcome display for list rows and JD tabs.
 */
export default function InterviewOutcomeBadges({
  analysisScore,
  callScore,
  callSource,
  consolidatedRecommendation,
  className = '',
}) {
  const callLabel = callSourceLabel(callSource)
  const recLabel = consolidatedLabel(consolidatedRecommendation)

  return (
    <div className={`flex flex-wrap items-center gap-1.5 ${className}`}>
      {analysisScore != null && (
        <Badge color="slate" className="text-[10px] px-2 py-0.5">
          Analysis {analysisScore}
        </Badge>
      )}
      {callScore != null && (
        <Badge color="brand" className="text-[10px] px-2 py-0.5">
          {callLabel || 'Call'} {callScore}
        </Badge>
      )}
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
