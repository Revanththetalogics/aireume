import { useState } from 'react'
import { PhoneCall, X, Eye, FileText, Loader2, AlertTriangle, PanelLeftClose, PanelLeftOpen } from 'lucide-react'
import { Button, Badge } from '../ui'
import { INTERVIEW, LIVE_SCREEN } from '../../lib/uxLabels'
import { shouldWarnRoleMismatch } from '../../lib/liveScreenKitUtils'
import LiveScreenKit from './LiveScreenKit'
import { viewCandidateResume } from '../../lib/api'

/**
 * Full-viewport live call shell — resume reference + kit teleprompter.
 */
export default function LiveScreenCallShell({
  candidateName,
  roleTitle,
  fitScore,
  fitTierClass,
  fitTierLabel,
  result,
  kit,
  kitIsFallback,
  resumeLoading,
  resumeIsText,
  resumeText,
  resumeBlobUrl,
  ResumeTextRenderer,
  onExit,
  onDebriefGenerated,
}) {
  const [resumeOpen, setResumeOpen] = useState(true)

  const analysisData = {
    missing_skills: result?.analysis_result?.missing_skills || result?.missing_skills || [],
    matched_skills: result?.analysis_result?.matched_skills || result?.matched_skills || [],
  }

  const showMismatch = shouldWarnRoleMismatch(fitScore)

  return (
    <div className="flex flex-col h-full min-h-0 bg-surface">
      {/* Call chrome — no global nav, no bot CTA */}
      <header className="shrink-0 h-14 flex items-center justify-between gap-3 px-4 sm:px-5 bg-white/95 backdrop-blur-md border-b border-brand-100 z-20">
        <div className="flex items-center gap-2 min-w-0">
          <PhoneCall className="w-4 h-4 text-brand-600 shrink-0" />
          <span className="font-bold text-brand-900 text-sm truncate">{candidateName || 'Candidate'}</span>
          {roleTitle && (
            <span className="text-xs text-slate-400 truncate hidden md:block">{roleTitle}</span>
          )}
          {fitScore != null && (
            <Badge color="slate" className="hidden sm:inline-flex shrink-0" title={LIVE_SCREEN.prescreenNote}>
              Pre-screen {fitScore}%
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant="ghost"
            size="sm"
            className="lg:hidden"
            onClick={() => setResumeOpen((v) => !v)}
          >
            {resumeOpen ? <PanelLeftClose className="w-4 h-4" /> : <PanelLeftOpen className="w-4 h-4" />}
            {LIVE_SCREEN.resumePanel}
          </Button>
          <Button variant="secondary" size="sm" onClick={onExit} className="gap-1.5">
            <X className="w-4 h-4" />
            Exit
          </Button>
        </div>
      </header>

      {showMismatch && (
        <div className="shrink-0 px-4 py-2 bg-amber-50 border-b border-amber-200 flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
          <div>
            <p className="text-xs font-bold text-amber-900">{LIVE_SCREEN.roleMismatchTitle}</p>
            <p className="text-xs text-amber-800">{LIVE_SCREEN.roleMismatchHint}</p>
          </div>
        </div>
      )}

      <div className="flex-1 flex min-h-0 flex-col lg:flex-row">
        {/* Resume — collapsible on mobile, sidebar on desktop */}
        <aside
          className={`${
            resumeOpen ? 'flex' : 'hidden'
          } lg:flex flex-col border-b lg:border-b-0 lg:border-r border-brand-100 bg-white lg:w-[38%] xl:w-[35%] min-h-0 h-[40vh] lg:h-auto`}
        >
          <div className="h-9 shrink-0 flex items-center justify-between px-4 bg-brand-50/80 border-b border-brand-100">
            <span className="text-xs font-semibold text-slate-600">{LIVE_SCREEN.resumePanel}</span>
            {result?.candidate_id && (
              <button
                type="button"
                onClick={() => viewCandidateResume(result.candidate_id).catch(() => {})}
                className="text-xs text-brand-600 font-semibold flex items-center gap-1 hover:text-brand-800"
              >
                <Eye className="w-3 h-3" /> Open in tab
              </button>
            )}
          </div>
          <div className="flex-1 min-h-0 relative">
            {resumeLoading && (
              <div className="absolute inset-0 flex items-center justify-center bg-white/80 z-10">
                <Loader2 className="w-6 h-6 animate-spin text-brand-500" />
              </div>
            )}
            {resumeIsText && ResumeTextRenderer ? (
              <div className="absolute inset-0 overflow-y-auto px-4 py-3">
                <ResumeTextRenderer text={resumeText} />
              </div>
            ) : resumeBlobUrl ? (
              <iframe src={resumeBlobUrl} className="absolute inset-0 w-full h-full border-0" title="Resume" />
            ) : !resumeLoading ? (
              <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-400 gap-2 p-6">
                <FileText className="w-8 h-8 opacity-40" />
                <p className="text-sm">Resume preview unavailable</p>
              </div>
            ) : null}
          </div>
        </aside>

        {/* Kit — primary focus */}
        <main className="flex-1 min-h-0 flex flex-col min-w-0">
          <LiveScreenKit
            kit={kit}
            isFallback={kitIsFallback}
            interviewKitStatus={result?.interview_kit_status}
            resultId={result?.result_id}
            analysisData={analysisData}
            onDebriefGenerated={onDebriefGenerated}
          />
        </main>
      </div>
    </div>
  )
}
