import { useState, useCallback, useEffect } from 'react'
import { useDropzone } from 'react-dropzone'
import {
  Upload, FileText, X, Loader2, AlertTriangle, CheckCircle2,
  XCircle, MinusCircle, ChevronRight, ChevronLeft, User, Briefcase,
  Video, MessageSquareText, BarChart2, ShieldCheck, History,
} from 'lucide-react'
import {
  getCandidates, getTemplates, analyzeTranscript, getTranscriptAnalyses,
} from '../lib/api'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function ScoreRing({ value, label, color }) {
  const radius = 28
  const circ = 2 * Math.PI * radius
  const offset = circ - (value / 100) * circ
  return (
    <div className="flex flex-col items-center gap-1">
      <svg width="72" height="72" className="-rotate-90">
        <circle cx="36" cy="36" r={radius} strokeWidth="6" fill="none" className="stroke-brand-100" />
        <circle
          cx="36" cy="36" r={radius} strokeWidth="6" fill="none"
          strokeDasharray={circ} strokeDashoffset={offset}
          strokeLinecap="round"
          className={`transition-all duration-700 ${color}`}
        />
      </svg>
      <span className="text-xl font-extrabold text-brand-900 -mt-10">{value}</span>
      <span className="text-[11px] text-slate-500 font-semibold mt-6 text-center leading-tight">{label}</span>
    </div>
  )
}

function RecommendBadge({ rec }) {
  const map = {
    proceed: { icon: <CheckCircle2 className="w-4 h-4" />, cls: 'bg-green-100 text-green-700 ring-1 ring-green-200' },
    hold:    { icon: <MinusCircle  className="w-4 h-4" />, cls: 'bg-amber-100 text-amber-700 ring-1 ring-amber-200' },
    reject:  { icon: <XCircle     className="w-4 h-4" />, cls: 'bg-red-100 text-red-700 ring-1 ring-red-200' },
  }
  const style = map[rec?.toLowerCase()] || map.hold
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-bold ${style.cls}`}>
      {style.icon}
      {rec ? rec.charAt(0).toUpperCase() + rec.slice(1) : 'Hold'}
    </span>
  )
}

const PLATFORMS = [
  { id: 'zoom',   label: 'Zoom' },
  { id: 'teams',  label: 'Microsoft Teams' },
  { id: 'meet',   label: 'Google Meet' },
  { id: 'manual', label: 'Other / Manual' },
]

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function TranscriptPage() {
  const [step, setStep] = useState(1)   // 1 = context, 2 = upload, 3 = results

  // Step 1 state
  const [candidates,    setCandidates]    = useState([])
  const [templates,     setTemplates]     = useState([])
  const [candidateId,   setCandidateId]   = useState('')
  const [templateId,    setTemplateId]    = useState('')
  const [platform,      setPlatform]      = useState('zoom')
  const [loadingMeta,   setLoadingMeta]   = useState(true)

  // Step 2 state
  const [transcriptFile, setTranscriptFile] = useState(null)
  const [pastedText,     setPastedText]     = useState('')
  const [inputMode,      setInputMode]      = useState('file')  // 'file' | 'paste'

  // Result / loading state
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [result,      setResult]      = useState(null)
  const [error,       setError]       = useState('')

  // History tab
  const [history,        setHistory]        = useState([])
  const [showHistory,    setShowHistory]    = useState(false)
  const [loadingHistory, setLoadingHistory] = useState(false)

  // ── Load candidates + templates on mount ──────────────────────────────────
  useEffect(() => {
    async function load() {
      setLoadingMeta(true)
      try {
        const [cRes, tRes] = await Promise.all([getCandidates(), getTemplates()])
        setCandidates(cRes.candidates || [])
        setTemplates(tRes || [])
      } catch {
        // non-fatal
      } finally {
        setLoadingMeta(false)
      }
    }
    load()
  }, [])

  // ── Dropzone ──────────────────────────────────────────────────────────────
  const onDrop = useCallback((accepted) => {
    if (accepted.length) setTranscriptFile(accepted[0])
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/plain':   ['.txt'],
      'text/vtt':     ['.vtt'],
      'text/x-srt':   ['.srt'],
      'application/octet-stream': ['.vtt', '.srt'],
    },
    maxFiles: 1,
    maxSize: 5 * 1024 * 1024,
  })

  // ── Validate step 1 ───────────────────────────────────────────────────────
  const step1Valid = templateId !== ''

  // ── Load history ──────────────────────────────────────────────────────────
  async function loadHistory() {
    setLoadingHistory(true)
    try {
      const data = await getTranscriptAnalyses()
      setHistory(data.analyses || [])
    } catch {
      setHistory([])
    } finally {
      setLoadingHistory(false)
    }
  }

  function handleToggleHistory() {
    if (!showHistory) loadHistory()
    setShowHistory(!showHistory)
    setResult(null)
  }

  // ── Submit analysis ───────────────────────────────────────────────────────
  async function handleAnalyze() {
    const hasContent = inputMode === 'file' ? !!transcriptFile : pastedText.trim().length > 0
    if (!hasContent) {
      setError('Please upload a transcript file or paste transcript text.')
      return
    }
    setError('')
    setIsAnalyzing(true)
    try {
      const data = await analyzeTranscript(
        inputMode === 'file' ? transcriptFile : null,
        inputMode === 'paste' ? pastedText : null,
        candidateId || null,
        templateId  || null,
        platform,
      )
      setResult(data)
      setStep(3)
    } catch (err) {
      setError(err.response?.data?.detail || 'Analysis failed. Please try again.')
    } finally {
      setIsAnalyzing(false)
    }
  }

  function handleReset() {
    setStep(1)
    setTranscriptFile(null)
    setPastedText('')
    setResult(null)
    setError('')
    setShowHistory(false)
  }

  // ── History item click ────────────────────────────────────────────────────
  function viewHistoryItem(item) {
    setResult(item)
    setShowHistory(false)
    setStep(3)
  }

  // ─────────────────────────────────────────────────────────────────────────
  return (
    <div>
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">

        {/* Header */}
        <div className="flex items-start justify-between flex-wrap gap-3 card-animate">
          <div>
            <h2 className="text-3xl font-extrabold text-brand-900 tracking-tight">Interview Transcript Analysis</h2>
            <p className="text-slate-500 text-sm mt-1 font-medium">
              Upload a Teams / Zoom transcript, select a candidate profile &amp; job description,
              and receive an unbiased AI evaluation.
            </p>
          </div>
          <button
            onClick={handleToggleHistory}
            className="flex items-center gap-2 px-4 py-2.5 ring-1 ring-brand-200 text-sm font-semibold text-brand-700 rounded-xl hover:bg-brand-50 transition-colors"
          >
            <History className="w-4 h-4" />
            {showHistory ? 'Hide History' : 'Past Analyses'}
          </button>
        </div>

        {/* ── History panel ── */}
        {showHistory && (
          <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand overflow-hidden card-animate">
            <div className="px-5 py-4 border-b border-brand-50">
              <h3 className="text-base font-extrabold text-brand-900 tracking-tight">Past Transcript Analyses</h3>
            </div>
            {loadingHistory ? (
              <div className="flex items-center justify-center py-10 text-slate-400">
                <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading…
              </div>
            ) : history.length === 0 ? (
              <p className="text-center py-10 text-slate-400 text-sm">No analyses yet.</p>
            ) : (
              <div className="divide-y divide-slate-100">
                {history.map((h) => (
                    <button
                    key={h.id}
                    onClick={() => viewHistoryItem(h)}
                    className="w-full flex items-center justify-between px-5 py-3 hover:bg-brand-50/40 transition-colors text-left"
                  >
                    <div>
                      <p className="text-sm font-medium text-slate-800">
                        {h.candidate_name || 'Unknown Candidate'}
                        {h.role_template_name && <span className="text-slate-400 font-normal"> — {h.role_template_name}</span>}
                      </p>
                      <p className="text-xs text-slate-400 mt-0.5">
                        {h.source_platform} · {new Date(h.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      {h.fit_score != null && (
                        <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ring-1 ${
                          h.fit_score >= 70 ? 'bg-green-50 text-green-700 ring-green-200' :
                          h.fit_score >= 45 ? 'bg-amber-50 text-amber-700 ring-amber-200' : 'bg-red-50 text-red-700 ring-red-200'
                        }`}>{h.fit_score}</span>
                      )}
                      <RecommendBadge rec={h.recommendation} />
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── Step indicator (only when not showing history) ── */}
        {!showHistory && step < 3 && (
          <div className="flex items-center gap-2">
            {[
              { n: 1, label: 'Select Context' },
              { n: 2, label: 'Upload Transcript' },
            ].map(({ n, label }, idx, arr) => (
              <div key={n} className="flex items-center gap-2">
                <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                  step === n
                    ? 'bg-brand-600 text-white'
                    : step > n
                    ? 'bg-green-100 text-green-700'
                    : 'bg-brand-50 text-brand-300'
                }`}>
                  <span className="w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold
                    border border-current">{n}</span>
                  {label}
                </div>
                {idx < arr.length - 1 && <ChevronRight className="w-4 h-4 text-slate-300" />}
              </div>
            ))}
          </div>
        )}

        {/* ════════════════════════════════════════════════════
            STEP 1 — Select Context
        ════════════════════════════════════════════════════ */}
        {!showHistory && step === 1 && (
          <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6 space-y-5 card-animate">

            {/* Candidate dropdown */}
            <div>
              <label className="block text-sm font-bold text-slate-700 mb-1.5 flex items-center gap-1.5">
                <User className="w-4 h-4 text-brand-500" />
                Candidate Profile
                <span className="text-slate-400 font-normal">(optional)</span>
              </label>
              {loadingMeta ? (
                <div className="h-10 bg-slate-100 rounded-lg animate-pulse" />
              ) : (
                <select
                  value={candidateId}
                  onChange={(e) => setCandidateId(e.target.value)}
                  className="w-full px-3 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-slate-700 text-sm bg-white"
                >
                  <option value="">— No candidate selected —</option>
                  {candidates.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name || 'Unnamed'}{c.email ? ` (${c.email})` : ''}
                    </option>
                  ))}
                </select>
              )}
              {!loadingMeta && candidates.length === 0 && (
                <p className="text-xs text-slate-400 mt-1">
                  No candidates yet — add them on the <a href="/candidates" className="text-blue-600 hover:underline">Candidates</a> page.
                </p>
              )}
            </div>

            {/* Job Description dropdown */}
            <div>
              <label className="block text-sm font-bold text-slate-700 mb-1.5 flex items-center gap-1.5">
                <Briefcase className="w-4 h-4 text-brand-500" />
                Job Description
                <span className="text-red-500 text-xs ml-1">*required</span>
              </label>
              {loadingMeta ? (
                <div className="h-10 bg-slate-100 rounded-lg animate-pulse" />
              ) : (
                <select
                  value={templateId}
                  onChange={(e) => setTemplateId(e.target.value)}
                  className="w-full px-3 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-slate-700 text-sm bg-white"
                >
                  <option value="">— Select a job description —</option>
                  {templates.map((t) => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
              )}
              {!loadingMeta && templates.length === 0 && (
                <p className="text-xs text-slate-400 mt-1">
                  No templates yet — create one on the <a href="/templates" className="text-blue-600 hover:underline">Templates</a> page.
                </p>
              )}
            </div>

            {/* Platform selector */}
            <div>
              <label className="block text-sm font-bold text-slate-700 mb-1.5 flex items-center gap-1.5">
                <Video className="w-4 h-4 text-brand-400" />
                Interview Platform
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {PLATFORMS.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => setPlatform(p.id)}
                    className={`px-3 py-2 rounded-lg border text-sm font-medium transition-all ${
                      platform === p.id
                        ? 'ring-2 ring-brand-500 bg-brand-50 text-brand-700'
                        : 'ring-1 ring-slate-200 text-slate-600 hover:ring-brand-200 hover:bg-brand-50/40'
                    }`}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="pt-1">
              <button
                onClick={() => setStep(2)}
                disabled={!step1Valid}
                className="flex items-center gap-2 px-6 py-2.5 btn-brand text-white text-sm font-bold rounded-xl disabled:opacity-50 disabled:cursor-not-allowed shadow-brand-sm"
              >
                Next: Upload Transcript <ChevronRight className="w-4 h-4" />
              </button>
              {!step1Valid && (
                <p className="text-xs text-slate-400 mt-1.5">Select a job description to continue.</p>
              )}
            </div>
          </div>
        )}

        {/* ════════════════════════════════════════════════════
            STEP 2 — Upload / Paste Transcript
        ════════════════════════════════════════════════════ */}
        {!showHistory && step === 2 && (
          <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6 space-y-5 card-animate">

            {/* Context summary */}
            <div className="flex flex-wrap gap-3 p-3 bg-brand-50/60 rounded-2xl ring-1 ring-brand-100 text-sm">
              {candidateId && (
                <span className="flex items-center gap-1 text-slate-600">
                  <User className="w-3.5 h-3.5 text-blue-500" />
                  {candidates.find(c => String(c.id) === String(candidateId))?.name || 'Candidate'}
                </span>
              )}
              <span className="flex items-center gap-1 text-slate-600">
                <Briefcase className="w-3.5 h-3.5 text-purple-500" />
                {templates.find(t => String(t.id) === String(templateId))?.name || 'JD'}
              </span>
              <span className="flex items-center gap-1 text-slate-600">
                <Video className="w-3.5 h-3.5 text-sky-500" />
                {PLATFORMS.find(p => p.id === platform)?.label}
              </span>
            </div>

            {/* Input mode toggle */}
            <div className="flex gap-2">
              {[
                { id: 'file',  icon: <Upload         className="w-4 h-4" />, label: 'Upload File' },
                { id: 'paste', icon: <MessageSquareText className="w-4 h-4" />, label: 'Paste Text' },
              ].map((m) => (
                <button
                  key={m.id}
                  onClick={() => setInputMode(m.id)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-sm font-medium transition-all ${
                    inputMode === m.id
                      ? 'ring-2 ring-brand-500 bg-brand-50 text-brand-700'
                      : 'ring-1 ring-slate-200 text-slate-600 hover:ring-brand-200 hover:bg-brand-50/40'
                  }`}
                >
                  {m.icon} {m.label}
                </button>
              ))}
            </div>

            {/* File dropzone */}
            {inputMode === 'file' && (
              <div className="space-y-3">
                <div
                  {...getRootProps()}
                  className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors ${
                    isDragActive
                      ? 'border-brand-500 bg-brand-50'
                      : transcriptFile
                      ? 'border-green-400 bg-green-50'
                      : 'border-brand-200 hover:border-brand-400 hover:bg-brand-50/40'
                  }`}
                >
                  <input {...getInputProps()} />
                  {transcriptFile ? (
                    <div className="flex flex-col items-center gap-2">
                      <FileText className="w-10 h-10 text-green-500" />
                      <p className="font-medium text-slate-800">{transcriptFile.name}</p>
                      <p className="text-sm text-slate-400">{(transcriptFile.size / 1024).toFixed(1)} KB</p>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center gap-2">
                      <Upload className="w-10 h-10 text-slate-400" />
                      <p className="text-slate-600 font-medium">
                        {isDragActive ? 'Drop transcript here…' : 'Drag & drop or click to upload'}
                      </p>
                      <p className="text-sm text-slate-400">Supports .txt, .vtt (Zoom/Teams), .srt — max 5 MB</p>
                    </div>
                  )}
                </div>
                {transcriptFile && (
                  <button
                    onClick={() => setTranscriptFile(null)}
                    className="flex items-center gap-1 text-xs text-red-500 hover:text-red-700"
                  >
                    <X className="w-3 h-3" /> Remove file
                  </button>
                )}
              </div>
            )}

            {/* Paste text area */}
            {inputMode === 'paste' && (
              <div>
                <textarea
                  value={pastedText}
                  onChange={(e) => setPastedText(e.target.value)}
                  placeholder="Paste the interview transcript here…"
                  rows={12}
                  className="w-full px-4 py-3 rounded-2xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 resize-none text-slate-700 placeholder-slate-400 text-sm font-mono bg-white"
                />
                <p className="text-xs text-slate-400 mt-1">{pastedText.length} characters</p>
              </div>
            )}

            {error && (
              <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                <AlertTriangle className="w-4 h-4 shrink-0" /> {error}
              </div>
            )}

            <div className="flex items-center gap-3">
              <button
                onClick={() => { setStep(1); setError('') }}
                className="flex items-center gap-2 px-4 py-2.5 ring-1 ring-brand-200 text-brand-700 text-sm font-semibold rounded-xl hover:bg-brand-50 transition-colors"
              >
                <ChevronLeft className="w-4 h-4" /> Back
              </button>
              <button
                onClick={handleAnalyze}
                disabled={isAnalyzing}
                className="flex items-center gap-2 px-6 py-2.5 btn-brand text-white text-sm font-bold rounded-xl disabled:opacity-50 disabled:cursor-not-allowed shadow-brand-sm"
              >
                {isAnalyzing
                  ? <><Loader2 className="w-4 h-4 animate-spin" /> Analyzing…</>
                  : <><BarChart2 className="w-4 h-4" /> Run Analysis</>}
              </button>
            </div>
          </div>
        )}

        {/* ════════════════════════════════════════════════════
            STEP 3 — Results
        ════════════════════════════════════════════════════ */}
        {!showHistory && step === 3 && result && (
          <ResultsPanel result={result} onReset={handleReset} />
        )}
      </main>
    </div>
  )
}

// ─── Results Panel ────────────────────────────────────────────────────────────

function ResultsPanel({ result, onReset }) {
  const ar = result.analysis_result || {}

  return (
    <div className="space-y-5">
      {/* Header card */}
      <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-5 card-animate">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h3 className="text-lg font-bold text-slate-900">
              {result.candidate_name || 'Unknown Candidate'}
            </h3>
            <p className="text-sm text-slate-500 mt-0.5">
              {result.role_template_name && <span>{result.role_template_name} · </span>}
              {result.source_platform && (
                <span className="capitalize">{result.source_platform}</span>
              )}
              {result.created_at && (
                <span> · {new Date(result.created_at).toLocaleDateString()}</span>
              )}
            </p>
          </div>
          <RecommendBadge rec={ar.recommendation} />
        </div>

        {/* Score rings */}
        <div className="flex flex-wrap gap-8 mt-6 justify-center sm:justify-start">
          <ScoreRing value={ar.fit_score ?? 0}              label="Overall Fit"     color="stroke-brand-600" />
          <ScoreRing value={ar.technical_depth ?? 0}        label="Technical Depth" color="stroke-violet-500" />
          <ScoreRing value={ar.communication_quality ?? 0}  label="Communication"   color="stroke-indigo-500" />
        </div>
      </div>

      {/* JD Alignment */}
      {ar.jd_alignment?.length > 0 && (
        <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-5">
          <h4 className="text-sm font-bold text-brand-900 mb-3 flex items-center gap-2">
            <Briefcase className="w-4 h-4 text-brand-500" /> JD Requirements Alignment
          </h4>
          <div className="space-y-2">
            {ar.jd_alignment.map((item, i) => (
              <div key={i} className="flex items-start gap-3 text-sm">
                {item.demonstrated
                  ? <CheckCircle2 className="w-4 h-4 text-green-500 shrink-0 mt-0.5" />
                  : <XCircle      className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />}
                <div>
                  <span className={item.demonstrated ? 'text-slate-800' : 'text-slate-500'}>
                    {item.requirement}
                  </span>
                  {item.evidence && (
                    <p className="text-xs text-slate-400 mt-0.5 italic">"{item.evidence}"</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Strengths & Areas */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-5">
          <h4 className="text-sm font-bold text-brand-900 mb-3 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-green-500" /> Strengths
          </h4>
          {ar.strengths?.length ? (
            <ul className="space-y-1.5">
              {ar.strengths.map((s, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                  <span className="mt-1 w-1.5 h-1.5 rounded-full bg-green-400 shrink-0" />
                  {s}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-400">No strengths identified.</p>
          )}
        </div>

        <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-5">
          <h4 className="text-sm font-bold text-brand-900 mb-3 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-500" /> Areas for Improvement
          </h4>
          {ar.areas_for_improvement?.length ? (
            <ul className="space-y-1.5">
              {ar.areas_for_improvement.map((a, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                  <span className="mt-1 w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0" />
                  {a}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-400">No improvement areas noted.</p>
          )}
        </div>
      </div>

      {/* Bias note */}
      {ar.bias_note && (
        <div className="flex items-start gap-3 p-4 bg-brand-50 ring-1 ring-brand-200 rounded-2xl text-sm text-brand-700">
          <ShieldCheck className="w-5 h-5 shrink-0 mt-0.5 text-brand-500" />
          <span>{ar.bias_note}</span>
        </div>
      )}

      {/* Actions */}
      <button
        onClick={onReset}
        className="flex items-center gap-2 px-5 py-2.5 ring-1 ring-brand-200 text-brand-700 text-sm font-semibold rounded-xl hover:bg-brand-50 transition-colors"
      >
        <ChevronLeft className="w-4 h-4" /> New Analysis
      </button>
    </div>
  )
}
