import { useLocation, useNavigate } from 'react-router-dom'
import { useEffect, useState, useRef } from 'react'
import {
  ArrowLeft, Share2, Download, CheckCircle, Check,
  ThumbsUp, ThumbsDown, Loader2, Pencil, X as XIcon,
} from 'lucide-react'
import ScoreGauge from '../components/ScoreGauge'
import ResultCard from '../components/ResultCard'
import Timeline from '../components/Timeline'
import { labelTrainingExample, updateResultStatus, updateCandidateName } from '../lib/api'

function InlineNameEditor({ initialName, candidateId, onSaved }) {
  const [editing, setEditing]   = useState(false)
  const [value, setValue]       = useState(initialName || 'Candidate')
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

  return (
    <div className="flex items-center gap-2 group">
      <h1 className="text-xl font-extrabold text-brand-900 tracking-tight">{value}</h1>
      <button
        onClick={() => setEditing(true)}
        className="opacity-0 group-hover:opacity-100 p-1 rounded-lg text-slate-400 hover:text-brand-600 hover:bg-brand-50 transition-all"
        title="Edit candidate name"
      >
        <Pencil className="w-3.5 h-3.5" />
      </button>
    </div>
  )
}

export default function ReportPage() {
  const location = useLocation()
  const navigate  = useNavigate()
  const [copied, setCopied]           = useState(false)
  const [result, setResult]           = useState(location.state?.result || null)
  const [candidateName, setCandidateName] = useState(null)
  const [labelStatus, setLabelStatus]   = useState(null)
  const [labelLoading, setLabelLoading] = useState(false)
  const [labelDone, setLabelDone]       = useState(false)

  useEffect(() => {
    if (result) {
      setCandidateName(result.candidate_name || result.contact_info?.name || 'Candidate')
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
          setCandidateName(parsed.candidate_name || parsed.contact_info?.name || 'Candidate')
          return
        }
      } catch { /* ignore */ }
    }
    navigate('/', { replace: true })
  }, [result, location.search, navigate])

  if (!result) return null

  const role      = result.job_role || ''
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

  const handleDownload = () => window.print()

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
          onClick={() => navigate('/')}
          className="flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-brand-700 transition-colors self-start"
        >
          <ArrowLeft className="w-4 h-4" />
          Analyze Another
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
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold text-white btn-brand shadow-brand-sm"
            >
              <Download className="w-4 h-4" />
              Download PDF
            </button>
          </div>
        </div>

        {/* Scrollable result content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5 print:overflow-visible print:p-4">

          {/* Print-only header */}
          <div className="hidden print:block mb-4">
            <span className="text-xs font-bold text-brand-600 uppercase tracking-widest">Screening Report</span>
            <h1 className="text-2xl font-extrabold text-brand-900">{candidateName}</h1>
            {role && <p className="text-slate-500">{role}</p>}
            <p className="text-sm text-slate-400">Analyzed on {timestamp} · Powered by ARIA · ThetaLogics</p>
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
