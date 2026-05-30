import { useLocation, useNavigate } from 'react-router-dom'
import { useEffect, useState, useRef } from 'react'
import {
  ArrowLeft, Share2, Download, CheckCircle, Check,
  ThumbsUp, ThumbsDown, Loader2, Pencil, X as XIcon, Upload, Eye, FileText, Clock,
  PhoneCall,
} from 'lucide-react'
import html2pdf from 'html2pdf.js'
import ScoreGauge from '../components/ScoreGauge'
import ResultCard from '../components/ResultCard'
import InterviewScorecard from '../components/InterviewScorecard'
import Timeline from '../components/Timeline'
import { labelTrainingExample, updateResultStatus, updateCandidateName, getCandidateAuditLog, getNarrative, viewCandidateResume, downloadCandidateResume, downloadPdfReport, getScreeningResult } from '../lib/api'
import AnimatedScore from '../components/AnimatedScore'
import StreamingText from '../components/StreamingText'
import Skeleton from '../components/Skeleton'
import PhoneScreenKit from '../components/PhoneScreenKit'
import EvaluationChecklist from '../components/EvaluationChecklist'
import api from '../lib/api'

/** Coerce any value to a render-safe string. Objects become JSON; null/undefined → '' */
function safeStr(v) {
  if (v == null) return ''
  if (typeof v === 'string') return v
  if (typeof v === 'number' || typeof v === 'boolean') return String(v)
  try { return JSON.stringify(v) } catch { return String(v) }
}

function InlineNameEditor({ initialName, candidateId, onSaved }) {
  const [editing, setEditing]   = useState(false)
  const [value, setValue]       = useState(initialName || '')
  const [saving, setSaving]     = useState(false)
  const inputRef = useRef(null)

  useEffect(() => {
    if (editing) inputRef.current?.focus()
  }, [editing])

  const save = async () => {
    if (!value.trim()) { setEditing(false); return }
    setSaving(true)
    try {
      if (candidateId) await updateCandidateName(candidateId, value.trim())
      onSaved?.(value.trim())
    } catch { /* silent */ } finally {
      setSaving(false)
      setEditing(false)
    }
  }

  if (editing) {
    return (
      <div className="flex items-center gap-2">
        <input
          ref={inputRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') save(); if (e.key === 'Escape') setEditing(false) }}
          className="text-xl font-extrabold text-brand-900 tracking-tight bg-brand-50 border border-brand-300 rounded-xl px-3 py-1 w-full focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
        <button onClick={save} disabled={saving} className="p-1.5 rounded-lg bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-50">
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
        </button>
        <button onClick={() => setEditing(false)} className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100">
          <XIcon className="w-4 h-4" />
        </button>
      </div>
    )
  }

  const hasName = value && value.trim()

  return (
    <div className="flex items-center gap-2 group">
      {hasName ? (
        <h1 className="text-xl font-extrabold text-brand-900 tracking-tight">{value}</h1>
      ) : (
        <button
          onClick={() => setEditing(true)}
          className="text-xl font-extrabold text-brand-300 tracking-tight hover:text-brand-500 transition-colors italic"
          title="Click to add candidate name"
        >
          Add name…
        </button>
      )}
      {hasName && (
        <button
          onClick={() => setEditing(true)}
          className="opacity-0 group-hover:opacity-100 p-1 rounded-lg text-slate-400 hover:text-brand-600 hover:bg-brand-50 transition-all"
          title="Edit candidate name"
        >
          <Pencil className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  )
}

export default function ReportPage() {
  const location = useLocation()
  const navigate  = useNavigate()
  const [copied, setCopied]           = useState(false)
  const [result, setResult]           = useState(location.state?.result || null)
  const [labelStatus, setLabelStatus]   = useState(null)
  const [labelLoading, setLabelLoading] = useState(false)
  const [labelDone, setLabelDone]       = useState(false)
  const [narrativePolling, setNarrativePolling] = useState(false)
  const [jdContext, setJdContext] = useState(null)
  const [resumeActionLoading, setResumeActionLoading] = useState(false)
  const [isDownloading, setIsDownloading] = useState(false)
  const [noResult, setNoResult] = useState(false)
  const [loading, setLoading] = useState(true)
  const [auditLogs, setAuditLogs] = useState([])
  const [auditExpanded, setAuditExpanded] = useState(false)

  // ── Phone Screen split-view state ─────────────────────────────────────────
  const [screenMode, setScreenMode] = useState(false)
  const [scorecardKey, setScorecardKey] = useState(0)
  const [resumeBlobUrl, setResumeBlobUrl] = useState(null)
  const [resumeLoading, setResumeLoading] = useState(false)
  const [resumeIsText, setResumeIsText] = useState(false)
  const [resumeText, setResumeText] = useState('')

  /** Resolve name from all possible result paths — returns null if unknown */
  const resolveName = (r) =>
    (r?.candidate_name || '').trim() ||
    (r?.contact_info?.name || '').trim() ||
    (r?.candidate_profile?.name || '').trim() ||
    null

  // Initialize candidate name from result
  const [candidateName, setCandidateName] = useState(resolveName(location.state?.result))

  // Load active JD context from sessionStorage
  useEffect(() => {
    const raw = sessionStorage.getItem('aria_active_jd')
    if (raw) {
      try {
        setJdContext(JSON.parse(raw))
      } catch { /* ignore */ }
    }
  }, [])

  useEffect(() => {
    // Check if result from location.state is a COMPLETE result (not just a partial card summary)
    const isCompleteResult = result && (
      result.analysis_result ||
      result.strengths !== undefined ||
      result.contact_info ||
      result.candidate_profile ||
      result.score_breakdown
    )

    if (isCompleteResult) {
      console.log('[ReportPage] Using complete result from state')
      setCandidateName(resolveName(result))
      setLoading(false)
      return
    }

    // Extract ID from either the partial result or URL params
    const params = new URLSearchParams(location.search)
    const id = params.get('id') || result?.id || result?.result_id

    if (!id) {
      setNoResult(true)
      setLoading(false)
      return
    }

    // Try sessionStorage first
    try {
      const stored = sessionStorage.getItem(`report_${id}`)
      if (stored) {
        const parsed = JSON.parse(stored)
        setResult(parsed)
        setCandidateName(resolveName(parsed))
        setLoading(false)
        return
      }
    } catch { /* ignore */ }

    // Fetch full data from API
    setLoading(true)
    getScreeningResult(id)
      .then(data => {
        setResult(data)
        setCandidateName(resolveName(data))
        try { sessionStorage.setItem(`report_${id}`, JSON.stringify(data)) } catch {}
      })
      .catch(() => {
        setNoResult(true)
      })
      .finally(() => {
        setLoading(false)
      })
  }, [location.search])

  // Fetch audit log when candidate_id is available
  useEffect(() => {
    const cid = result?.candidate_id
    if (!cid) return
    getCandidateAuditLog(cid)
      .then(setAuditLogs)
      .catch(() => setAuditLogs([]))
  }, [result?.candidate_id])

  // Poll for narrative completion if status is pending or processing
  useEffect(() => {
    if (!result?.analysis_id && !result?.result_id) return
    
    const analysisId = result.analysis_id || result.result_id
    const status = result.narrative_status || 'pending'
    
    // Only poll if narrative is pending or processing
    if (status !== 'pending' && status !== 'processing') return
    
    setNarrativePolling(true)
    let pollCount = 0
    const maxPolls = 60 // Poll for max 2 minutes (60 * 2s)
    
    const pollInterval = setInterval(async () => {
      try {
        const narrativeData = await getNarrative(analysisId)
        
        if (narrativeData.status === 'ready') {
          // Merge narrative into result
          setResult(prev => ({
            ...prev,
            ...narrativeData.narrative,
            narrative_status: 'ready',
            ai_enhanced: true,
          }))
          setNarrativePolling(false)
          clearInterval(pollInterval)
        } else if (narrativeData.status === 'fallback' || narrativeData.status === 'failed') {
          // Use fallback narrative if available
          if (narrativeData.narrative) {
            setResult(prev => ({
              ...prev,
              ...narrativeData.narrative,
              narrative_status: narrativeData.status,
              narrative_error: narrativeData.error,
              ai_enhanced: false,
            }))
          } else {
            setResult(prev => ({
              ...prev,
              narrative_status: narrativeData.status,
              narrative_error: narrativeData.error,
            }))
          }
          setNarrativePolling(false)
          clearInterval(pollInterval)
        } else if (narrativeData.status === 'processing') {
          // Update status to show processing
          setResult(prev => ({ ...prev, narrative_status: 'processing' }))
        }
        
        pollCount++
        if (pollCount >= maxPolls) {
          // Stop polling after max attempts
          setNarrativePolling(false)
          clearInterval(pollInterval)
        }
      } catch (error) {
        console.error('Narrative polling error:', error)
        // Continue polling on error (might be transient)
      }
    }, 2000) // Poll every 2 seconds
    
    return () => {
      clearInterval(pollInterval)
      setNarrativePolling(false)
    }
  }, [result?.analysis_id, result?.result_id, result?.narrative_status])

  // Load resume blob when entering screen mode
  useEffect(() => {
    if (!screenMode || !result?.candidate_id) return
    if (resumeBlobUrl || resumeIsText) return // already loaded
    let objectUrl = null
    const loadResume = async () => {
      setResumeLoading(true)
      try {
        const resp = await api.get(`/candidates/${result.candidate_id}/resume?inline=true`, { responseType: 'blob' })
        const blob = resp.data
        const contentType = blob.type || resp.headers['content-type'] || ''
        if (contentType.includes('application/pdf')) {
          objectUrl = URL.createObjectURL(blob)
          setResumeBlobUrl(objectUrl)
          setResumeIsText(false)
        } else if (contentType.startsWith('text/')) {
          const text = await blob.text()
          setResumeText(text)
          setResumeIsText(true)
        } else {
          // Fallback: use raw_resume_text from result data
          setResumeText(result?.raw_resume_text || result?.resume_text || 'Resume preview not available for this file format.')
          setResumeIsText(true)
        }
      } catch (e) {
        console.warn('PhoneScreen: failed to load resume blob', e)
      } finally {
        setResumeLoading(false)
      }
    }
    loadResume()
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [screenMode, result?.candidate_id])

  // Revoke blob URL when exiting screen mode
  useEffect(() => {
    if (!screenMode) {
      if (resumeBlobUrl) {
        URL.revokeObjectURL(resumeBlobUrl)
        setResumeBlobUrl(null)
      }
      setResumeIsText(false)
      setResumeText('')
    }
  }, [screenMode])

  if (!result) {
    if (loading) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] text-brand-700">
          <Loader2 className="w-8 h-8 animate-spin mb-3" />
          <p className="text-sm font-medium">Loading report…</p>
        </div>
      )
    }
    if (noResult) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] text-slate-500">
          <p className="text-lg font-medium mb-2">No analysis results found</p>
          <p className="text-sm mb-4">The analysis may have expired or was not completed.</p>
          <button onClick={() => navigate('/analyze')} className="px-4 py-2 bg-brand-500 text-white rounded-lg hover:bg-brand-600">
            Start New Analysis
          </button>
        </div>
      )
    }
    return null
  }

  const hasDeterministicData = result.fit_score != null
  const isNarrativeReady = result.narrative_status === 'ready'
  const isReportComplete = isNarrativeReady || result.narrative_status === 'fallback' || result.narrative_status === 'failed' || !result.narrative_status

  const role      = (result.job_role && result.job_role !== 'Not specified') ? result.job_role : ''
  const timestamp = result.analyzed_at
    ? new Date(result.analyzed_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
    : new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })

  const handleShare = () => {
    const id = crypto.randomUUID()
    sessionStorage.setItem(`report_${id}`, JSON.stringify(result))
    const shareUrl = `${window.location.origin}/report?id=${id}`
    navigator.clipboard.writeText(shareUrl).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2500)
    }).catch(() => window.prompt('Copy this report link:', shareUrl))
  }

  const fallbackClientSidePdf = async () => {
    if (isDownloading) return

    setIsDownloading(true)
    try {
      // Get the report content element
      const element = document.querySelector('.report-content')
      if (!element) {
        alert('Report content not found. Please try again.')
        setIsDownloading(false)
        return
      }

      // PDF options
      const opt = {
        margin: [10, 10, 10, 10],
        filename: `${candidateName || 'Candidate'}_Screening_Report.pdf`,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: {
          scale: 2,
          useCORS: true,
          logging: false,
          letterRendering: true
        },
        jsPDF: {
          unit: 'mm',
          format: 'a4',
          orientation: 'portrait'
        },
        pagebreak: { mode: ['avoid-all', 'css', 'legacy'] }
      }

      // Generate and download PDF
      await html2pdf().set(opt).from(element).save()
    } catch (error) {
      console.error('PDF generation error:', error)
      alert('Failed to generate PDF. Please try again or use the browser print option (Ctrl+P).')
    } finally {
      setIsDownloading(false)
    }
  }

  const handleDownload = async () => {
    if (isDownloading) return

    const resultId = result?.result_id || result?.id || new URLSearchParams(location.search).get('id')
    if (!resultId) {
      fallbackClientSidePdf()
      return
    }

    setIsDownloading(true)
    try {
      const response = await downloadPdfReport(resultId)
      const blob = new Blob([response.data], { type: 'application/pdf' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${candidateName || 'Candidate'}_Assessment_Report.pdf`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Server PDF generation failed, falling back to client-side:', error)
      fallbackClientSidePdf()
    } finally {
      setIsDownloading(false)
    }
  }

  const handleLabel = async (outcome) => {
    const resultId = result?.result_id
    if (!resultId || labelLoading) return
    setLabelLoading(true)
    try {
      await labelTrainingExample(resultId, outcome)
      await updateResultStatus(resultId, outcome)
      setLabelStatus(outcome)
      setLabelDone(true)
    } catch { /* silently fail */ } finally {
      setLabelLoading(false)
    }
  }

  // ── Phone Screen split-view layout ────────────────────────────────────────
  const interviewQs = result?.interview_questions
    || result?.analysis_result?.interview_questions
    || null
  const fitScore = result?.fit_score ?? null
  const fitLabel = fitScore != null
    ? (fitScore >= 72 ? 'Strong Fit' : fitScore >= 45 ? 'Moderate Fit' : 'Low Fit')
    : null
  const fitBadgeClass = fitScore != null
    ? (fitScore >= 72 ? 'bg-emerald-100 text-emerald-700' : fitScore >= 45 ? 'bg-amber-100 text-amber-700' : 'bg-red-100 text-red-700')
    : 'bg-slate-100 text-slate-500'

  if (screenMode) {
    return (
      <div className="flex flex-col" style={{ height: '100vh' }}>
        {/* ── Phone Screen top bar ── */}
        <div className="h-14 shrink-0 flex items-center justify-between px-5 bg-white border-b border-slate-200 shadow-sm z-20">
          <div className="flex items-center gap-3 min-w-0">
            <PhoneCall className="w-4 h-4 text-brand-600 shrink-0" />
            <span className="font-bold text-slate-900 text-sm truncate">{candidateName || 'Candidate'}</span>
            {role && <span className="text-xs text-slate-400 truncate hidden sm:block">{safeStr(role)}</span>}
            {fitScore != null && (
              <span className={`shrink-0 px-2.5 py-0.5 rounded-full text-xs font-bold ${fitBadgeClass}`}>
                {fitScore}% · {fitLabel}
              </span>
            )}
          </div>
          <button
            onClick={() => setScreenMode(false)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-semibold text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors shrink-0"
          >
            <XIcon className="w-4 h-4" />
            Exit Screen Mode
          </button>
        </div>

        {/* ── Split content ── */}
        <div className="flex-1 flex lg:flex-row flex-col min-h-0">

          {/* Left panel — Resume */}
          <div className="lg:w-1/2 w-full border-r border-slate-200 flex flex-col lg:h-full h-[45vh]">
            <div className="h-9 shrink-0 flex items-center justify-between px-4 bg-slate-50 border-b border-slate-200">
              <span className="text-xs font-semibold text-slate-600">Resume</span>
              {result?.candidate_id && (
                <button
                  onClick={async () => {
                    try { await viewCandidateResume(result.candidate_id) } catch { /* silent */ }
                  }}
                  className="text-xs text-brand-600 hover:text-brand-800 font-semibold transition-colors flex items-center gap-1"
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
              {resumeIsText ? (
                <div className="flex-1 overflow-y-auto p-6 h-full">
                  <pre className="whitespace-pre-wrap text-sm text-slate-700 font-sans leading-relaxed">{resumeText}</pre>
                </div>
              ) : resumeBlobUrl ? (
                <iframe
                  src={resumeBlobUrl}
                  className="w-full h-full border-0"
                  title="Candidate Resume"
                />
              ) : !resumeLoading ? (
                <div className="p-6 overflow-y-auto h-full">
                  <div className="flex flex-col items-center justify-center h-full text-slate-400 gap-3">
                    <FileText className="w-10 h-10 opacity-30" />
                    <p className="text-sm">Resume not available for inline preview.</p>
                    {result?.candidate_id && (
                      <button
                        onClick={async () => { try { await viewCandidateResume(result.candidate_id) } catch { /* silent */ } }}
                        className="px-4 py-2 text-sm font-semibold bg-brand-50 text-brand-700 ring-1 ring-brand-200 rounded-lg hover:bg-brand-100 transition-colors"
                      >
                        Open in new tab
                      </button>
                    )}
                  </div>
                </div>
              ) : null}
            </div>
          </div>

          {/* Right panel — Screen Kit + Scorecard */}
          <div className="lg:w-1/2 w-full flex flex-col min-h-0 lg:h-full">
            <div className="h-9 shrink-0 flex items-center px-4 bg-slate-50 border-b border-slate-200">
              <span className="text-xs font-semibold text-slate-600">Recruiter Screen Kit</span>
            </div>
            <div className="flex-1 overflow-y-auto">
              <PhoneScreenKit
                interview_questions={interviewQs}
                resultId={result?.result_id}
                analysisData={{
                  missing_skills: result?.analysis_result?.missing_skills || result?.missing_skills || [],
                  matched_skills: result?.analysis_result?.matched_skills || result?.matched_skills || [],
                }}
                onDebriefGenerated={() => setScorecardKey(prev => prev + 1)}
              />

              {/* Scorecard at the bottom */}
              {result?.result_id && (
                <div className="px-4 pb-6 pt-2 border-t border-slate-100">
                  <InterviewScorecard key={scorecardKey} resultId={result.result_id} />
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-full min-h-0 print:block">

      {/* ── Left sidebar: score + candidate info + labels ── */}
      <aside className="w-72 shrink-0 border-r border-brand-100 overflow-y-auto flex flex-col gap-5 p-5 print:hidden">

        {/* Back button */}
        <button
          onClick={() => {
            const searchParams = new URLSearchParams(location.search)
            const fromParam = searchParams.get('from')
            const destination = location.state?.from ||
              (fromParam === 'batch' ? '/analyze' :
               fromParam === 'analyze' ? '/analyze' : null)

            if (destination) {
              if (destination === '/analyze') {
                navigate('/analyze?restored=true', { replace: false })
              } else {
                navigate(destination, { state: { from: '/analyze' } })
              }
            } else {
              window.history.length > 1 ? navigate(-1) : navigate('/')
            }
          }}
          className="flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-brand-700 transition-colors self-start"
        >
          <ArrowLeft className="w-4 h-4" />
          {(() => {
            const searchParams = new URLSearchParams(location.search)
            const fromParam = searchParams.get('from')
            return location.state?.from === '/batch' || fromParam === 'batch'
              ? 'Back to Batch Results'
              : 'Back to Results'
          })()}
        </button>

        {/* Report badge + candidate name */}
        <div className="bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 shadow-brand-sm p-4">
          <span className="inline-block text-xs font-bold text-brand-600 uppercase tracking-widest mb-2 bg-brand-50 px-2.5 py-1 rounded-full ring-1 ring-brand-200">
            Screening Report
          </span>
          <InlineNameEditor
            initialName={candidateName}
            candidateId={result.candidate_id}
            onSaved={(newName) => {
              setCandidateName(newName)
              setResult(prev => ({
                ...prev,
                analysis_result: { ...prev?.analysis_result, candidate_name: newName },
                candidate_name: newName,
                contact_info: { ...prev?.contact_info, name: newName },
                candidate_profile: { ...prev?.candidate_profile, name: newName },
              }))
              // Re-fetch audit log to include the new edit
              if (result.candidate_id) {
                getCandidateAuditLog(result.candidate_id).then(setAuditLogs).catch(() => {})
              }
              // Re-fetch full result so updated fit_summary / narrative is reflected
              const rid = result?.result_id || result?.id
              if (rid) {
                getScreeningResult(rid)
                  .then(data => {
                    setResult(data)
                    setCandidateName(resolveName(data))
                    try { sessionStorage.setItem(`report_${rid}`, JSON.stringify(data)) } catch {}
                  })
                  .catch(() => {})
              }
            }}
          />
          {/* Audit trail: "Last edited" indicator */}
          {auditLogs.length > 0 && (
            <div className="mt-1">
              <button
                onClick={() => setAuditExpanded(!auditExpanded)}
                className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-brand-600 transition-colors"
              >
                <Clock className="w-3 h-3" />
                Last edited {new Date(auditLogs[0].changed_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                by {auditLogs[0].changed_by_email?.split('@')[0] || 'user'}
              </button>
              {auditExpanded && (
                <div className="mt-2 space-y-1.5 max-h-40 overflow-y-auto">
                  {auditLogs.map((log) => (
                    <div key={log.id} className="text-[10px] text-slate-400 bg-slate-50 rounded-lg px-2 py-1.5 ring-1 ring-slate-100">
                      <span className="font-semibold text-slate-600">{log.field_name}</span>
                      {': '}
                      <span className="line-through">{log.old_value || '(empty)'}</span>
                      {' → '}
                      <span className="text-brand-700 font-medium">{log.new_value || '(empty)'}</span>
                      <div className="mt-0.5 text-slate-400">
                        {log.changed_by_email?.split('@')[0] || 'User'} · {new Date(log.changed_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
          {role && <p className="text-slate-500 text-xs mt-1 font-medium">{safeStr(role)}</p>}
          <div className="mt-2 border-t border-brand-50 pt-2">
            <p className="text-xs text-slate-400">Analyzed on</p>
            <p className="text-xs font-bold text-brand-900">{timestamp}</p>
            <p className="text-xs text-slate-400 mt-0.5">Powered by ARIA · ThetaLogics</p>
          </div>
        </div>

        {/* AI Enhancement status indicator in sidebar */}
        {result.narrative_status === 'pending' && (
          <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-brand-50 ring-1 ring-brand-200 text-xs font-semibold text-brand-700">
            <span className="w-2 h-2 rounded-full bg-brand-500 animate-pulse shrink-0" />
            AI analysis in progress
            <span className="animate-pulse">…</span>
          </div>
        )}
        {result.narrative_status === 'processing' && (
          <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-blue-50 ring-1 ring-blue-200 text-xs font-semibold text-blue-700">
            <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse shrink-0" />
            AI enhancing report
            <span className="animate-pulse">…</span>
          </div>
        )}
        {/* Fallback narrative (not AI-enhanced) - show "Analysis complete" */}
        {result.narrative_status === 'ready' && result.ai_enhanced === false && (
          <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-slate-50 ring-1 ring-slate-200 text-xs font-semibold text-slate-700">
            <span className="w-2 h-2 rounded-full bg-slate-500 shrink-0" />
            Analysis complete
          </div>
        )}
        {/* Real AI-enhanced narrative - show "AI Enhanced Report" */}
        {result.narrative_status === 'ready' && result.ai_enhanced === true && (
          <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-green-50 ring-1 ring-green-200 text-xs font-semibold text-green-700">
            <span className="w-2 h-2 rounded-full bg-green-500 shrink-0" />
            AI Enhanced Report
          </div>
        )}
        {/* Fallback / Failed status */}
        {(result.narrative_status === 'fallback' || result.narrative_status === 'failed') && (
          <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-amber-50 ring-1 ring-amber-200 text-xs font-semibold text-amber-700">
            <span className="w-2 h-2 rounded-full bg-amber-500 shrink-0" />
            Using standard analysis
          </div>
        )}

        {/* Score gauge */}
        {hasDeterministicData && (
          <div className="bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 shadow-brand-sm p-4 flex flex-col items-center">
            <ScoreGauge score={result.fit_score} />
            {result.final_recommendation && (
              <div className="mt-3 flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-brand-50 ring-1 ring-brand-200 text-brand-700 text-xs font-bold">
                <CheckCircle className="w-3.5 h-3.5" />
                {safeStr(result.final_recommendation)}
              </div>
            )}
          </div>
        )}

        {/* Training label */}
        {result.result_id && (
          <div className="bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 shadow-brand-sm p-4">
            <p className="text-xs font-bold text-brand-900 mb-0.5">Help ARIA Learn</p>
            <p className="text-xs text-slate-400 mb-3">Label this outcome to improve accuracy.</p>
            {labelDone ? (
              <div className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-bold ring-1 justify-center ${
                labelStatus === 'hired'
                  ? 'bg-green-100 text-green-700 ring-green-200'
                  : 'bg-red-100 text-red-700 ring-red-200'
              }`}>
                <Check className="w-3.5 h-3.5" />
                Marked as {labelStatus === 'hired' ? 'Hired' : 'Rejected'}
              </div>
            ) : (
              <div className="flex gap-2">
                <button
                  onClick={() => handleLabel('hired')}
                  disabled={labelLoading}
                  className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl bg-green-50 ring-1 ring-green-200 text-green-700 text-xs font-bold hover:bg-green-100 disabled:opacity-50 transition-colors"
                >
                  {labelLoading && labelStatus !== 'rejected'
                    ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    : <ThumbsUp className="w-3.5 h-3.5" />}
                  Hired
                </button>
                <button
                  onClick={() => handleLabel('rejected')}
                  disabled={labelLoading}
                  className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl bg-red-50 ring-1 ring-red-200 text-red-700 text-xs font-bold hover:bg-red-100 disabled:opacity-50 transition-colors"
                >
                  {labelLoading && labelStatus !== 'hired'
                    ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    : <ThumbsDown className="w-3.5 h-3.5" />}
                  Rejected
                </button>
              </div>
            )}
          </div>
        )}

        {/* Analyze Another Resume */}
        {jdContext && (
          <div className="bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 shadow-brand-sm p-4">
            <p className="text-xs font-bold text-brand-900 mb-0.5">Same Job, New Candidate?</p>
            <p className="text-xs text-slate-400 mb-3">
              {jdContext.jd_mode === 'file'
                ? `Analyze another resume using the same JD file (${jdContext.file_name}).`
                : 'Analyze another resume using the same JD and weights.'}
            </p>
            <button
              onClick={() => {
                const saved = JSON.parse(sessionStorage.getItem('aria_active_jd') || '{}')
                sessionStorage.setItem('aria_analyze_another', 'true')
                navigate('/analyze', {
                  state: {
                    ...jdContext,
                    skillOverrides: jdContext?.skillOverrides || saved.skillOverrides,
                    jdParseResult: jdContext?.jdParseResult || saved.jdParseResult,
                    skillsConfirmed: jdContext?.skillsConfirmed ?? true
                  }
                })
              }}
              className="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl bg-brand-50 ring-1 ring-brand-200 text-brand-700 text-xs font-bold hover:bg-brand-100 transition-colors"
            >
              <Upload className="w-3.5 h-3.5" />
              Analyze Another Resume
            </button>
          </div>
        )}
      </aside>

      {/* ── Right panel: action bar + scrollable content ── */}
      <div className="flex-1 flex flex-col min-h-0 min-w-0">

        {/* Sticky action bar */}
        <div className="bg-white/80 backdrop-blur-xl border-b border-brand-100/60 shrink-0 z-10 print:hidden">
          <div className="px-6 h-14 flex items-center justify-end gap-2">
            {interviewQs && (
              <button
                onClick={() => setScreenMode(true)}
                className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold text-white bg-brand-600 hover:bg-brand-700 shadow-brand-sm transition-colors"
                title="Open split-view phone screen mode"
              >
                <PhoneCall className="w-4 h-4" />
                Start Phone Screen
              </button>
            )}
            {result?.candidate_id && (
              <>
                <button
                  onClick={async () => {
                    setResumeActionLoading(true)
                    try { await viewCandidateResume(result.candidate_id) } catch (e) { alert('Resume not available') }
                    finally { setResumeActionLoading(false) }
                  }}
                  disabled={resumeActionLoading}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl ring-1 ring-brand-200 text-sm font-semibold text-brand-700 hover:bg-brand-50 transition-colors disabled:opacity-50"
                  title="View original resume"
                >
                  <Eye className="w-4 h-4" />
                  View Resume
                </button>
                <button
                  onClick={async () => {
                    setResumeActionLoading(true)
                    try { await downloadCandidateResume(result.candidate_id, result?.candidate_name ? `${result.candidate_name}_resume.pdf` : `resume_${result.candidate_id}.pdf`) } catch (e) { alert('Resume not available') }
                    finally { setResumeActionLoading(false) }
                  }}
                  disabled={resumeActionLoading}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl ring-1 ring-brand-200 text-sm font-semibold text-brand-700 hover:bg-brand-50 transition-colors disabled:opacity-50"
                  title="Download original resume"
                >
                  <FileText className="w-4 h-4" />
                  Download Resume
                </button>
              </>
            )}
            <button
              onClick={handleShare}
              disabled={!isReportComplete}
              className="flex items-center gap-2 px-4 py-2 rounded-xl ring-1 ring-brand-200 text-sm font-semibold text-brand-700 hover:bg-brand-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {copied ? <Check className="w-4 h-4 text-green-600" /> : <Share2 className="w-4 h-4" />}
              {copied ? 'Link Copied!' : 'Share'}
            </button>
            <button
              onClick={handleDownload}
              disabled={isDownloading || !isReportComplete}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold text-white btn-brand shadow-brand-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isDownloading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Generating PDF...
                </>
              ) : (
                <>
                  <Download className="w-4 h-4" />
                  Download PDF
                </>
              )}
            </button>
          </div>
        </div>

        {/* Scrollable result content */}
        <div className="report-content flex-1 overflow-y-auto p-6 space-y-5 print:overflow-visible print:p-4">

          {/* Score Summary — visible in both screen and PDF */}
          {!hasDeterministicData ? (
            <Skeleton variant="card" />
          ) : (
            <div className="bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 shadow-brand-sm p-5 flex items-center gap-6">
              <div className="flex flex-col items-center justify-center w-24 h-24 rounded-full bg-brand-50 ring-4 ring-brand-100 shrink-0">
                <AnimatedScore score={result.fit_score} size="lg" animate={!isReportComplete} />
                <span className="text-[10px] font-bold text-brand-400 uppercase tracking-wider">/ 100</span>
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`px-3 py-1 rounded-full text-xs font-bold text-white ${
                    result.fit_score >= 72 ? 'bg-green-500' :
                    result.fit_score >= 45 ? 'bg-amber-500' : 'bg-red-500'
                  }`}>
                    {result.fit_score >= 72 ? 'Strong Fit' :
                     result.fit_score >= 45 ? 'Moderate Fit' : 'Low Fit'}
                  </span>
                  {result.final_recommendation && (
                    <span className="px-3 py-1 rounded-full text-xs font-bold bg-brand-100 text-brand-700 ring-1 ring-brand-200">
                      {safeStr(result.final_recommendation)}
                    </span>
                  )}
                  {result.risk_level && (
                    <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                      result.risk_level === 'Low' ? 'bg-green-100 text-green-700' :
                      result.risk_level === 'Medium' ? 'bg-amber-100 text-amber-700' :
                      'bg-red-100 text-red-700'
                    }`}>
                      {safeStr(result.risk_level)} Risk
                    </span>
                  )}
                </div>
                <p className="text-sm text-slate-500">Overall fit score based on skills, experience, education, and timeline analysis.</p>
              </div>
            </div>
          )}

          {/* Loading skeletons for narrative and skills areas */}
          {!hasDeterministicData && (
            <div className="space-y-5">
              <Skeleton variant="text" count={4} />
              <div className="space-y-3">
                <Skeleton variant="bar" count={5} />
              </div>
            </div>
          )}

          {/* Candidate Information Section - Visible in both screen and print */}
          <div className="mb-6 pb-4 border-b-2 border-brand-200 bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 shadow-brand-sm p-5 print:shadow-none print:ring-0 print:bg-transparent print:rounded-none">
            <div className="flex items-start justify-between mb-3">
              <div>
                <span className="text-xs font-bold text-brand-600 uppercase tracking-widest">Screening Report</span>
                <h1 className="text-2xl font-extrabold text-brand-900 mt-1">{safeStr(candidateName) || 'Unknown Candidate'}</h1>
                {role && <p className="text-base font-semibold text-slate-700 mt-1">Position: {safeStr(role)}</p>}
              </div>
              <div className="text-right text-sm">
                <p className="text-slate-400">Analyzed on {timestamp}</p>
                <p className="text-xs text-slate-400 mt-1">Powered by ARIA · ThetaLogics</p>
              </div>
            </div>
            {/* Candidate Contact Information */}
            {(result?.contact_info?.email || result?.contact_info?.phone) && (
              <div className="grid grid-cols-2 gap-4 mt-3 pt-3 border-t border-brand-100">
                {result?.contact_info?.email && (
                  <div>
                    <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Email</span>
                    <p className="text-sm text-slate-700 font-medium">{safeStr(result.contact_info.email)}</p>
                  </div>
                )}
                {result?.contact_info?.phone && (
                  <div>
                    <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Phone</span>
                    <p className="text-sm text-slate-700 font-medium">{safeStr(result.contact_info.phone)}</p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Print-only header with candidate information (DEPRECATED - keeping for backward compatibility) */}
          <div className="hidden print:hidden mb-6 pb-4 border-b-2 border-brand-200">
            <div className="flex items-start justify-between mb-3">
              <div>
                <span className="text-xs font-bold text-brand-600 uppercase tracking-widest">Screening Report</span>
                <h1 className="text-2xl font-extrabold text-brand-900 mt-1">{safeStr(candidateName) || 'Unknown Candidate'}</h1>
                {role && <p className="text-base font-semibold text-slate-700 mt-1">Position: {safeStr(role)}</p>}
              </div>
              <div className="text-right text-sm">
                <p className="text-slate-400">Analyzed on {timestamp}</p>
                <p className="text-xs text-slate-400 mt-1">Powered by ARIA · ThetaLogics</p>
              </div>
            </div>
            {/* Candidate Contact Information */}
            {(result?.contact_info?.email || result?.contact_info?.phone) && (
              <div className="grid grid-cols-2 gap-4 mt-3 pt-3 border-t border-brand-100">
                {result?.contact_info?.email && (
                  <div>
                    <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Email</span>
                    <p className="text-sm text-slate-700 font-medium">{safeStr(result.contact_info.email)}</p>
                  </div>
                )}
                {result?.contact_info?.phone && (
                  <div>
                    <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Phone</span>
                    <p className="text-sm text-slate-700 font-medium">{safeStr(result.contact_info.phone)}</p>
                  </div>
                )}
              </div>
            )}
          </div>

          {hasDeterministicData && <ResultCard result={result} defaultExpandEducation />}

          {/* Evaluation Checklist */}
          {hasDeterministicData && <EvaluationChecklist result={result} />}

          {/* Phone Screen CTA — inline banner above Recruiter Scorecard */}
          {interviewQs && (
            <div className="rounded-2xl ring-1 ring-brand-200 bg-gradient-to-r from-brand-50 to-indigo-50 p-5 flex items-center justify-between gap-4">
              <div>
                <p className="font-bold text-brand-800 text-sm">Ready to conduct a phone screen?</p>
                <p className="text-xs text-slate-500 mt-0.5">Split-view mode shows the resume and all screen kit questions side-by-side.</p>
              </div>
              <button
                onClick={() => setScreenMode(true)}
                className="shrink-0 flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold text-white bg-brand-600 hover:bg-brand-700 shadow-brand-sm transition-colors"
              >
                <PhoneCall className="w-4 h-4" />
                Start Phone Screen
              </button>
            </div>
          )}

          {/* Recruiter Scorecard Section */}
          {result?.interview_questions && result.result_id && (
            <div className="mt-6">
              <InterviewScorecard key={scorecardKey} resultId={result.result_id} showHeading />
            </div>
          )}

          <Timeline
            workExperience={result.work_experience || []}
            gaps={result.employment_gaps || []}
          />
        </div>
      </div>
    </div>
  )
}
