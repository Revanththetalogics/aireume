import {
  Mic, ClipboardList, Download, Share2, RefreshCw, FileWarning,
  Eye, FileText, Check,
} from 'lucide-react'
import { Button, DropdownMenu } from '../ui'
import { INTERVIEW, REPORT } from '../../lib/uxLabels'
import {
  isVoiceStrategyPending,
  isVoiceStrategyReady,
} from '../../lib/enrichmentUtils'

/**
 * Single action zone for screening reports — replaces duplicate sticky bars.
 */
export default function ReportActionBar({
  result,
  onAiScreenCall,
  onLiveScreenKit,
  onViewResume,
  onDownloadResume,
  onDownloadPdf,
  onDownloadAdverseAction,
  onShare,
  onRescore,
  isDownloading = false,
  resumeLoading = false,
  copied = false,
  actionsReady = true,
  liveScreenKitAvailable = true,
  showAiCall = true,
  className = '',
}) {
  const voicePending = isVoiceStrategyPending(result)
  const voiceReady = isVoiceStrategyReady(result)

  let aiLabel = INTERVIEW.aiScreenCall
  let aiHint = INTERVIEW.aiScreenCallHint
  if (voicePending) {
    aiLabel = 'Preparing call plan…'
    aiHint = 'AI interview plan is generating'
  } else if (voiceReady) {
    aiHint = 'Call plan ready — start instantly'
  }

  const exportItems = [
    onDownloadPdf && {
      id: 'pdf',
      label: isDownloading ? 'Generating PDF…' : 'Download PDF report',
      icon: Download,
      disabled: isDownloading || !actionsReady,
      onClick: onDownloadPdf,
    },
    onShare && {
      id: 'share',
      label: copied ? 'Link copied!' : 'Copy share link',
      icon: copied ? Check : Share2,
      disabled: !actionsReady,
      onClick: onShare,
    },
    onDownloadResume && {
      id: 'resume-dl',
      label: 'Download original resume',
      icon: FileText,
      disabled: resumeLoading,
      onClick: onDownloadResume,
    },
    onViewResume && {
      id: 'resume-view',
      label: 'View original resume',
      icon: Eye,
      disabled: resumeLoading,
      onClick: onViewResume,
    },
    onDownloadAdverseAction && {
      id: 'adverse',
      label: 'Adverse action letter',
      icon: FileWarning,
      onClick: onDownloadAdverseAction,
    },
    onRescore && {
      id: 'rescore',
      label: 'Recalculate fit score',
      icon: RefreshCw,
      onClick: onRescore,
    },
  ].filter(Boolean)

  return (
    <div
      className={`flex flex-col gap-2 p-3 rounded-2xl bg-white/90 backdrop-blur-md ring-1 ring-brand-100 shadow-brand-sm print:hidden ${className}`}
    >
      <div className="flex flex-wrap items-center gap-2">
        {showAiCall && onAiScreenCall && (
          <div className="flex flex-col">
            <Button
              variant="brand"
              size="sm"
              onClick={onAiScreenCall}
              disabled={voicePending}
              loading={voicePending}
              className="gap-2"
            >
              {!voicePending && <Mic className="w-4 h-4" />}
              {aiLabel}
            </Button>
          </div>
        )}

        {liveScreenKitAvailable && onLiveScreenKit && (
          <Button variant="secondary" size="sm" onClick={onLiveScreenKit} className="gap-2">
            <ClipboardList className="w-4 h-4" />
            {INTERVIEW.liveScreenKit}
          </Button>
        )}

        {exportItems.length > 0 && (
          <DropdownMenu
            label={REPORT.exportMenu}
            items={exportItems}
            variant="secondary"
            size="sm"
          />
        )}
      </div>
      {aiHint && showAiCall && (
        <p className="text-[11px] text-slate-500 px-0.5">{aiHint}</p>
      )}
      {liveScreenKitAvailable && onLiveScreenKit && (
        <p className="text-[11px] text-slate-400 px-0.5">{INTERVIEW.liveScreenKitHint}</p>
      )}
    </div>
  )
}
