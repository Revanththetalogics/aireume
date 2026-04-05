import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Sparkles, CheckCircle, Loader2, Zap, Shield, Brain, BarChart3 } from 'lucide-react'
import UploadForm from '../components/UploadForm'
import { analyzeResumeStream } from '../lib/api'
import { useSubscription } from '../hooks/useSubscription'

// ─── Pipeline stage definitions ───────────────────────────────────────────────

const PIPELINE_STAGES = [
  {
    id:    'jd_parser',
    label: 'Agent 1A — Parsing job description',
    group: 1,
  },
  {
    id:    'resume_parser',
    label: 'Agent 1B — Parsing resume & extracting profile',
    group: 1,
  },
  {
    id:    'skill_domain',
    label: 'Agent 2A — Semantic skill & domain matching',
    group: 2,
  },
  {
    id:    'edu_timeline',
    label: 'Agent 2B — Education & timeline analysis',
    group: 2,
  },
  {
    id:    'scorer_explainer',
    label: 'Agent 3A — Scoring & explainability (LLM)',
    group: 3,
  },
  {
    id:    'interview_qs',
    label: 'Agent 3B — Generating interview kit',
    group: 3,
  },
]

const GROUP_LABELS = {
  1: 'Stage 1 — Extraction',
  2: 'Stage 2 — Analysis',
  3: 'Stage 3 — Scoring & Interview Kit',
}

// ─── Agent progress panel ─────────────────────────────────────────────────────

function AgentProgressPanel({ completedStages, activeStages }) {
  const groups = [1, 2, 3]

  return (
    <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand-lg p-6 card-animate h-full flex flex-col">
      <div className="flex items-center gap-2.5 mb-5">
        <div className="w-8 h-8 rounded-xl bg-brand-50 flex items-center justify-center">
          <Sparkles className="w-4 h-4 text-brand-600 animate-pulse" />
        </div>
        <h3 className="font-semibold text-brand-900">LangGraph Pipeline Running</h3>
      </div>

      <div className="space-y-4 flex-1">
        {groups.map(group => {
          const stages = PIPELINE_STAGES.filter(s => s.group === group)
          const allDone = stages.every(s => completedStages.has(s.id))
          const anyActive = stages.some(s => activeStages.has(s.id))

          return (
            <div key={group}>
              <p className={`text-xs font-bold uppercase tracking-wider mb-2 ${
                allDone   ? 'text-green-600' :
                anyActive ? 'text-brand-600' :
                            'text-slate-400'
              }`}>
                {GROUP_LABELS[group]}
              </p>
              <div className="space-y-2">
                {stages.map(stage => {
                  const isDone   = completedStages.has(stage.id)
                  const isActive = activeStages.has(stage.id)
                  return (
                    <div
                      key={stage.id}
                      className={`flex items-center gap-3 p-3 rounded-2xl transition-all duration-300 ${
                        isActive ? 'bg-brand-50 ring-1 ring-brand-200' :
                        isDone   ? 'bg-green-50 ring-1 ring-green-100' :
                                   'bg-slate-50 ring-1 ring-slate-100'
                      }`}
                    >
                      {isDone ? (
                        <CheckCircle className="w-4 h-4 text-green-500 shrink-0" />
                      ) : isActive ? (
                        <Loader2 className="w-4 h-4 text-brand-500 shrink-0 animate-spin" />
                      ) : (
                        <div className="w-4 h-4 rounded-full ring-2 ring-slate-200 shrink-0" />
                      )}
                      <span className={`text-xs font-medium ${
                        isActive ? 'text-brand-700' :
                        isDone   ? 'text-green-700' :
                                   'text-slate-400'
                      }`}>
                        {stage.label}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>

      <p className="text-xs text-slate-400 mt-4 text-center">
        Results appear progressively — report opens when complete
      </p>
    </div>
  )
}

// ─── Idle info panel ──────────────────────────────────────────────────────────

function IdlePanel() {
  const features = [
    { icon: Zap,    title: '6-Agent LangGraph Pipeline', desc: 'Parallel extraction → analysis → scoring in 3 stages' },
    { icon: Brain,  title: 'Fully LLM-Driven',           desc: 'No hardcoded rules — semantic matching and scoring' },
    { icon: Shield, title: 'On-prem, Zero Data Leak',    desc: 'Ollama runs locally — resumes never leave your server' },
  ]
  return (
    <div className="flex flex-col gap-4 h-full">
      <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6 card-animate">
        <div className="inline-flex items-center gap-2 px-3 py-1 bg-brand-50 text-brand-700 text-xs font-semibold rounded-full ring-1 ring-brand-200 mb-3">
          <Sparkles className="w-3.5 h-3.5" />
          AI-Powered Resume Screening
        </div>
        <h2 className="text-xl font-extrabold tracking-tight mb-1">
          <span className="text-gradient">Screen a Candidate</span>
        </h2>
        <p className="text-slate-500 text-sm leading-relaxed">
          Upload a resume and job description. ARIA's 6-agent LangGraph pipeline will analyse fit, score every dimension, and generate a full report with explainability.
        </p>
      </div>

      <div className="flex flex-col gap-3 flex-1">
        {features.map(({ icon: Icon, title, desc }) => (
          <div key={title} className="bg-white/70 backdrop-blur-sm rounded-2xl ring-1 ring-brand-100 p-4 flex items-start gap-3 card-animate">
            <div className="w-8 h-8 rounded-xl bg-brand-50 flex items-center justify-center shrink-0">
              <Icon className="w-4 h-4 text-brand-600" />
            </div>
            <div>
              <p className="text-sm font-semibold text-brand-900">{title}</p>
              <p className="text-xs text-slate-500 mt-0.5">{desc}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Dashboard ────────────────────────────────────────────────────────────────

function UsageWidget() {
  const { subscription, getUsageStats, loading } = useSubscription()
  const usage = getUsageStats()

  if (loading || !usage) return null

  const percent = usage.percentUsed
  const colorClass = percent > 90 ? 'bg-red-500' : percent > 70 ? 'bg-amber-500' : 'bg-brand-500'
  const isUnlimited = usage.analysesLimit < 0

  return (
    <div className="bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 shadow-brand-sm p-4 mb-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-brand-600" />
          <span className="text-sm font-semibold text-slate-700">Usage This Month</span>
        </div>
        <span className={`text-xs font-medium ${percent > 90 ? 'text-red-600' : 'text-slate-500'}`}>
          {isUnlimited ? '∞' : `${usage.analysesUsed} / ${usage.analysesLimit}`} analyses
        </span>
      </div>
      {!isUnlimited && (
        <div className="w-full bg-slate-100 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all ${colorClass}`}
            style={{ width: `${Math.min(percent, 100)}%` }}
          />
        </div>
      )}
      {isUnlimited && (
        <div className="flex items-center gap-1 text-xs text-green-600 font-medium">
          <Sparkles className="w-3 h-3" />
          Unlimited analyses
        </div>
      )}
    </div>
  )
}

// ─── Dashboard ────────────────────────────────────────────────────────────────

export default function Dashboard() {
  const navigate  = useNavigate()
  const location  = useLocation()
  const { refreshAfterAnalysis } = useSubscription()

  const [selectedFile, setSelectedFile]       = useState(null)
  const [jobDescription, setJobDescription]   = useState(location.state?.jdText || '')
  const [selectedJobFile, setSelectedJobFile] = useState(null)
  const [scoringWeights, setScoringWeights]   = useState(null)
  const [isLoading, setIsLoading]             = useState(false)
  const [error, setError]                     = useState(null)

  // Track which stages have completed — activeStages is derived from this
  const [completedStages, setCompletedStages] = useState(new Set())

  /**
   * Derive which stages are currently "in-flight" from the completed set.
   * LangGraph stage dependencies:
   *   Stage 1 (jd_parser, resume_parser) — fires immediately
   *   Stage 2 (skill_domain, edu_timeline) — fires when both Stage 1 complete
   *   Stage 3 (scorer_explainer, interview_qs) — fires when both Stage 2 complete
   */
  function deriveActiveStages(completed) {
    const s1 = ['jd_parser', 'resume_parser']
    const s2 = ['skill_domain', 'edu_timeline']
    const s3 = ['scorer_explainer', 'interview_qs']

    const s1Done = s1.every(s => completed.has(s))
    const s2Done = s2.every(s => completed.has(s))
    const s3Done = s3.every(s => completed.has(s))

    if (s3Done)  return new Set()
    if (s2Done)  return new Set(s3.filter(s => !completed.has(s)))
    if (s1Done)  return new Set(s2.filter(s => !completed.has(s)))
    return new Set(s1.filter(s => !completed.has(s)))
  }

  const activeStages = isLoading ? deriveActiveStages(completedStages) : new Set()

  const handleSubmit = async () => {
    const hasJd = jobDescription.trim() || selectedJobFile
    if (!selectedFile || !hasJd) {
      setError('Please upload a resume and provide a job description (text or file)')
      return
    }

    setIsLoading(true)
    setError(null)
    setCompletedStages(new Set())

    try {
      const data = await analyzeResumeStream(
        selectedFile,
        jobDescription,
        selectedJobFile,
        scoringWeights,
        ({ stage }) => setCompletedStages(prev => new Set([...prev, stage]))
      )

      setCompletedStages(new Set(PIPELINE_STAGES.map(s => s.id)))
      // Refresh usage stats after successful analysis
      await refreshAfterAnalysis()
      navigate('/report', { state: { result: data } })
    } catch (err) {
      setError(
        err.message ||
        'Failed to analyze resume. Please check the Ollama service and try again.'
      )
    } finally {
      setIsLoading(false)
    }
  }

  // Reset stage state when user changes file or JD
  useEffect(() => {
    if (!isLoading) setCompletedStages(new Set())
  }, [selectedFile, jobDescription])

  const showProgress = isLoading

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 h-full">
      <div className="flex gap-8 h-full items-start">
        {/* Left: Upload form */}
        <div className="flex-1 min-w-0 space-y-4">
          {/* Usage banner */}
          <UsageWidget />
          <UploadForm
            onFileSelect={setSelectedFile}
            jobDescription={jobDescription}
            onJobDescriptionChange={setJobDescription}
            onJobFileSelect={setSelectedJobFile}
            onSubmit={handleSubmit}
            isLoading={isLoading}
            selectedFile={selectedFile}
            selectedJobFile={selectedJobFile}
            error={error}
            scoringWeights={scoringWeights}
            onScoringWeightsChange={setScoringWeights}
          />
        </div>

        {/* Right: Agent progress or idle panel (desktop only) */}
        <div className="w-80 shrink-0 hidden lg:block" style={{ minHeight: '100%' }}>
          {showProgress
            ? <AgentProgressPanel
                completedStages={completedStages}
                activeStages={activeStages}
              />
            : <IdlePanel />
          }
        </div>
      </div>

      {/* Mobile: agent progress below form */}
      {showProgress && (
        <div className="mt-6 lg:hidden">
          <AgentProgressPanel
            completedStages={completedStages}
            activeStages={activeStages}
          />
        </div>
      )}
    </div>
  )
}
