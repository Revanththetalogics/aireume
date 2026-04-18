import { useLocation, useNavigate } from 'react-router-dom'
import { useEffect, useState, useRef } from 'react'
import {
  ArrowLeft, Share2, Download, CheckCircle, Check,
  ThumbsUp, ThumbsDown, Loader2, Pencil, X as XIcon,
} from 'lucide-react'
import html2pdf from 'html2pdf.js'
import ScoreGauge from '../components/ScoreGauge'
import ResultCard from '../components/ResultCard'
import Timeline from '../components/Timeline'
import { labelTrainingExample, updateResultStatus, updateCandidateName, getNarrative } from '../lib/api'

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

  /** Resolve name from all possible result paths — returns null if unknown */
  const resolveName = (r) =>
    (r?.candidate_name || '').trim() ||
    (r?.contact_info?.name || '').trim() ||
    (r?.candidate_profile?.name || '').trim() ||
    null

  // Initialize candidate name from result
  const [candidateName, setCandidateName] = useState(resolveName(location.state?.result))

  useEffect(() => {
    if (result) {
      setCandidateName(resolveName(result))
      return
    }
    const params = new URLSearchParams(location.search)
    const id = params.get('id')
    if (id) {
      try {
        const stored = sessionStorage.getItem(`report_${id}`)
        if (stored) {
          const parsed = JSON.parse(stored)
          setResult(parsed)
          setCandidateName(resolveName(parsed))
          return
        }
      } catch { /* ignore */ }
    }
    navigate('/', { replace: true })
  }, [result, location.search, navigate])

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
        } else if (narrativeData.status === 'failed') {
          // Use fallback narrative if available
          if (narrativeData.narrative) {
            setResult(prev => ({
              ...prev,
              ...narrativeData.narrative,
              narrative_status: 'failed',
              narrative_error: narrativeData.error,
              ai_enhanced: false,
            }))
          } else {
            setResult(prev => ({
              ...prev,
              narrative_status: 'failed',
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

  if (!result) return null

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

  const [isDownloading, setIsDownloading] = useState(false)

  const handleDownload = async () => {
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

  return (
    <div className="flex h-full min-h-0 print:block">

      {/* ── Left sidebar: score + candidate info + labels ── */}
      <aside className="w-72 shrink-0 border-r border-brand-100 overflow-y-auto flex flex-col gap-5 p-5 print:hidden">

        {/* Back button */}
        <button
          onClick={() => {
            // If coming from batch page, go back to batch results
            if (location.state?.fromBatch) {
              navigate('/batch', { state: { results: location.state.batchResults } })
            } else {
              // Otherwise use browser back or go to home
              window.history.length > 1 ? navigate(-1) : navigate('/')
            }
          }}
          className="flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-brand-700 transition-colors self-start"
        >
          <ArrowLeft className="w-4 h-4" />
          {location.state?.fromBatch ? 'Back to Results' : 'Back'}
        </button>

        {/* Report badge + candidate name */}
        <div className="bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 shadow-brand-sm p-4">
          <span className="inline-block text-xs font-bold text-brand-600 uppercase tracking-widest mb-2 bg-brand-50 px-2.5 py-1 rounded-full ring-1 ring-brand-200">
            Screening Report
          </span>
          <InlineNameEditor
            initialName={candidateName}
            candidateId={result.candidate_id}
            onSaved={setCandidateName}
          />
          {role && <p className="text-slate-500 text-xs mt-1 font-medium">{role}</p>}
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
        {/* Failed status */}
        {result.narrative_status === 'failed' && (
          <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-amber-50 ring-1 ring-amber-200 text-xs font-semibold text-amber-700">
            <span className="w-2 h-2 rounded-full bg-amber-500 shrink-0" />
            Using standard analysis
          </div>
        )}

        {/* Score gauge */}
        <div className="bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 shadow-brand-sm p-4 flex flex-col items-center">
          <ScoreGauge score={result.fit_score} />
          {result.final_recommendation && (
            <div className="mt-3 flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-brand-50 ring-1 ring-brand-200 text-brand-700 text-xs font-bold">
              <CheckCircle className="w-3.5 h-3.5" />
              {result.final_recommendation}
            </div>
          )}
        </div>

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
      </aside>

      {/* ── Right panel: action bar + scrollable content ── */}
      <div className="flex-1 flex flex-col min-h-0 min-w-0">

        {/* Sticky action bar */}
        <div className="bg-white/80 backdrop-blur-xl border-b border-brand-100/60 shrink-0 z-10 print:hidden">
          <div className="px-6 h-14 flex items-center justify-end gap-2">
            <button
              onClick={handleShare}
              className="flex items-center gap-2 px-4 py-2 rounded-xl ring-1 ring-brand-200 text-sm font-semibold text-brand-700 hover:bg-brand-50 transition-colors"
            >
              {copied ? <Check className="w-4 h-4 text-green-600" /> : <Share2 className="w-4 h-4" />}
              {copied ? 'Link Copied!' : 'Share'}
            </button>
            <button
              onClick={handleDownload}
              disabled={isDownloading}
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

          {/* Print-only header with candidate information */}
          <div className="hidden print:block mb-6 pb-4 border-b-2 border-brand-200">
            <div className="flex items-start justify-between mb-3">
              <div>
                <span className="text-xs font-bold text-brand-600 uppercase tracking-widest">Screening Report</span>
                <h1 className="text-2xl font-extrabold text-brand-900 mt-1">{candidateName || 'Unknown Candidate'}</h1>
                {role && <p className="text-base font-semibold text-slate-700 mt-1">Position: {role}</p>}
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
                    <p className="text-sm text-slate-700 font-medium">{result.contact_info.email}</p>
                  </div>
                )}
                {result?.contact_info?.phone && (
                  <div>
                    <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Phone</span>
                    <p className="text-sm text-slate-700 font-medium">{result.contact_info.phone}</p>
                  </div>
                )}
              </div>
            )}
          </div>

          <ResultCard result={result} defaultExpandEducation />

          <Timeline
            workExperience={result.work_experience || []}
            gaps={result.employment_gaps || []}
          />
        </div>
      </div>
    </div>
  )
}
