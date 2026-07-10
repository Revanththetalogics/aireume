import {
  Mic, ClipboardList, Download, Share2, RefreshCw, FileWarning,
  Eye, FileText, Check, AlertTriangle,
} from 'lucide-react'
import { Button, DropdownMenu, Badge } from '../ui'
import { INTERVIEW, REPORT } from '../../lib/uxLabels'

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
  kitReadiness = null,
  className = '',
}) {
  const kitState = kitReadiness?.state || 'ready'
  const kitLoading = kitState === 'loading'
  const kitBlocked = kitLoading || kitState === 'empty'
  const kitFallback = kitState === 'fallback'

  const aiDisabled = kitBlocked
  const liveDisabled = kitBlocked

  let aiLabel = INTERVIEW.aiScreenCall
  let aiHint = INTERVIEW.aiScreenCallHint
  if (kitLoading) {
    aiLabel = 'Preparing interview kit…'
    aiHint = 'JD + resume-driven questions are generating'
  } else if (kitFallback) {
    aiHint = 'Using fallback kit — re-run analysis for best questions'
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
      {kitLoading && (
        <div className="flex items-center gap-2 text-xs text-brand-700 bg-brand-50 rounded-xl px-3 py-2 ring-1 ring-brand-100">
          <span className="inline-block w-2 h-2 rounded-full bg-brand-500 animate-pulse" />
          Interview kit preparing — both call options unlock when ready
        </div>
      )}
      {kitFallback && (
        <div className="flex items-center gap-2 text-xs text-amber-800 bg-amber-50 rounded-xl px-3 py-2 ring-1 ring-amber-200">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
          Fallback questions in use — full kit recommended before screening
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        {showAiCall && onAiScreenCall && (
          <Button
            variant="brand"
            size="sm"
            onClick={onAiScreenCall}
            disabled={aiDisabled}
            loading={kitLoading}
            className="gap-2"
          >
            {!kitLoading && <Mic className="w-4 h-4" />}
            {aiLabel}
          </Button>
        )}

        {liveScreenKitAvailable && onLiveScreenKit && (
          <Button
            variant="secondary"
            size="sm"
            onClick={onLiveScreenKit}
            disabled={liveDisabled}
            loading={kitLoading}
            className="gap-2"
          >
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
