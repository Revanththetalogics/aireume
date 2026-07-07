import { Mic, Download, FileWarning, Share2, RefreshCw, Loader2 } from 'lucide-react'
import { Button } from '../ui'
import {
  isVoiceStrategyPending,
  isVoiceStrategyReady,
  isVoiceStrategySkipped,
} from '../../lib/enrichmentUtils'

export default function ActionRail({
  result,
  onScheduleInterview,
  onDownloadPdf,
  onDownloadAdverseAction,
  onShare,
  onRescore,
  isDownloading = false,
  copied = false,
  className = '',
}) {
  const voicePending = isVoiceStrategyPending(result)
  const voiceReady = isVoiceStrategyReady(result)
  const voiceSkipped = isVoiceStrategySkipped(result)

  let interviewLabel = 'Schedule AI Interview'
  let interviewHint = null
  let interviewDisabled = false

  if (voicePending) {
    interviewLabel = 'Preparing interview plan…'
    interviewHint = 'Voice strategy is being pre-built for instant dispatch'
    interviewDisabled = true
  } else if (voiceReady) {
    interviewLabel = 'Start AI Interview — Ready'
    interviewHint = 'Pre-built plan cached — instant start'
  } else if (voiceSkipped) {
    interviewLabel = 'AI Interview'
    interviewHint = 'Not pre-built for Reject candidates — will generate on start'
  }

  return (
    <div
      className={`flex flex-wrap items-center gap-2 p-3 rounded-2xl bg-white/90 backdrop-blur-md ring-1 ring-brand-100 shadow-brand-sm ${className}`}
    >
      {onScheduleInterview && (
        <div className="flex flex-col">
          <Button
            variant="brand"
            size="sm"
            onClick={onScheduleInterview}
            disabled={interviewDisabled}
            loading={voicePending}
            className="gap-2"
          >
            {!voicePending && <Mic className="w-4 h-4" />}
            {interviewLabel}
          </Button>
          {interviewHint && (
            <span className="text-[10px] text-slate-500 mt-1 px-1">{interviewHint}</span>
          )}
        </div>
      )}

      {onDownloadPdf && (
        <Button variant="secondary" size="sm" onClick={onDownloadPdf} disabled={isDownloading} className="gap-2">
          {isDownloading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
          PDF Report
        </Button>
      )}

      {onDownloadAdverseAction && (
        <Button variant="ghost" size="sm" onClick={onDownloadAdverseAction} className="gap-2">
          <FileWarning className="w-4 h-4" />
          Adverse Action
        </Button>
      )}

      {onRescore && (
        <Button variant="ghost" size="sm" onClick={onRescore} className="gap-2">
          <RefreshCw className="w-4 h-4" />
          Recalculate Fit
        </Button>
      )}

      {onShare && (
        <Button variant="ghost" size="sm" onClick={onShare} className="gap-2">
          <Share2 className="w-4 h-4" />
          {copied ? 'Link copied!' : 'Share'}
        </Button>
      )}
    </div>
  )
}
