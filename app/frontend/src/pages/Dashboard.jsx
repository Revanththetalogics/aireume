import { useState, useEffect, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Sparkles, CheckCircle, Loader2, Zap, Shield, Brain } from 'lucide-react'
import UploadForm from '../components/UploadForm'
import { analyzeResume } from '../lib/api'

const AGENT_STEPS = [
  { id: 'parse', label: 'Agent 1 — Parsing resume & extracting profile',   duration: 3000  },
  { id: 'score', label: 'Agent 2 — Running deterministic scoring engine',  duration: 2000  },
  { id: 'llm',   label: 'Agent 3 — Generating qualitative insights (LLM)', duration: 45000 },
  { id: 'done',  label: 'Pipeline complete — Rendering results',           duration: 500   },
]

function AgentProgressPanel({ activeStep }) {
  return (
    <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand-lg p-6 card-animate h-full flex flex-col">
      <div className="flex items-center gap-2.5 mb-5">
        <div className="w-8 h-8 rounded-xl bg-brand-50 flex items-center justify-center">
          <Sparkles className="w-4 h-4 text-brand-600 animate-pulse" />
        </div>
        <h3 className="font-semibold text-brand-900">Agent Pipeline Running</h3>
      </div>
      <div className="space-y-3 flex-1">
        {AGENT_STEPS.slice(0, 3).map((step, idx) => {
          const stepIdx = AGENT_STEPS.findIndex(s => s.id === activeStep)
          const isDone   = idx < stepIdx
          const isActive = step.id === activeStep
          return (
            <div
              key={step.id}
              className={`flex items-center gap-3 p-3.5 rounded-2xl transition-all duration-300 ${
                isActive ? 'bg-brand-50 ring-1 ring-brand-200' :
                isDone   ? 'bg-green-50 ring-1 ring-green-100' :
                           'bg-slate-50 ring-1 ring-slate-100'
              }`}
            >
              {isDone ? (
                <CheckCircle className="w-5 h-5 text-green-500 shrink-0" />
              ) : isActive ? (
                <Loader2 className="w-5 h-5 text-brand-500 shrink-0 animate-spin" />
              ) : (
                <div className="w-5 h-5 rounded-full ring-2 ring-slate-200 shrink-0" />
              )}
              <span className={`text-sm font-medium ${
                isActive ? 'text-brand-700' : isDone ? 'text-green-700' : 'text-slate-400'
              }`}>
                {step.label}
              </span>
            </div>
          )
        })}
      </div>
      <p className="text-xs text-slate-400 mt-4 text-center">
        Agent 3 (LLM) typically takes 20–40 s — report opens when complete
      </p>
    </div>
  )
}

function IdlePanel() {
  const features = [
    { icon: Zap,    title: '3-Agent Pipeline',       desc: 'Parse → Score → LLM insights in one shot' },
    { icon: Brain,  title: 'On-prem LLM',            desc: 'llama3 runs locally — no data leaves your VPS' },
    { icon: Shield, title: 'Zero Data Leak',         desc: 'Resumes & JDs never touch external APIs' },
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
          Upload a resume and job description. ARIA's 3-agent pipeline will analyse fit, score, and generate a full report.
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

      <div className="text-center py-2">
        <div className="inline-flex items-center gap-2 text-xs text-slate-400">
          <span className="w-1.5 h-1.5 rounded-full bg-green-400 inline-block" />
          Enterprise Agent Pipeline · llama3 on-prem · No data leaves your VPS
        </div>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const location = useLocation()
  const [selectedFile, setSelectedFile]         = useState(null)
  const [jobDescription, setJobDescription]     = useState(location.state?.jdText || '')
  const [selectedJobFile, setSelectedJobFile]   = useState(null)
  const [scoringWeights, setScoringWeights]     = useState(null)
  const [isLoading, setIsLoading]               = useState(false)
  const [activeStep, setActiveStep]             = useState(null)
  const [error, setError]                       = useState(null)
  const timerRef = useRef(null)

  const advanceSteps = () => {
    let stepIdx = 0
    const steps = ['parse', 'score', 'llm']
    const next = () => {
      if (stepIdx < steps.length) {
        setActiveStep(steps[stepIdx])
        timerRef.current = setTimeout(next, AGENT_STEPS[stepIdx].duration)
        stepIdx++
      }
    }
    next()
  }

  const clearStepTimer = () => {
    if (timerRef.current) clearTimeout(timerRef.current)
  }

  const handleSubmit = async () => {
    const hasJd = jobDescription.trim() || selectedJobFile
    if (!selectedFile || !hasJd) {
      setError('Please upload a resume and provide a job description (text or file)')
      return
    }
    setIsLoading(true)
    setError(null)
    setActiveStep('parse')
    advanceSteps()
    try {
      const data = await analyzeResume(selectedFile, jobDescription, selectedJobFile, scoringWeights)
      clearStepTimer()
      setActiveStep('done')
      navigate('/report', { state: { result: data } })
    } catch (err) {
      clearStepTimer()
      setActiveStep(null)
      setError(
        err.response?.data?.detail ||
        err.message ||
        'Failed to analyze resume. Please try again.'
      )
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => () => clearStepTimer(), [])

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 h-full">
      <div className="flex gap-8 h-full items-start">
        {/* Left: Upload form (wider) */}
        <div className="flex-1 min-w-0">
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

        {/* Right: Info panel / agent progress */}
        <div className="w-80 shrink-0 hidden lg:block" style={{ minHeight: '100%' }}>
          {isLoading && activeStep && activeStep !== 'done'
            ? <AgentProgressPanel activeStep={activeStep} />
            : <IdlePanel />
          }
        </div>
      </div>

      {/* Mobile agent progress (below form) */}
      {isLoading && activeStep && activeStep !== 'done' && (
        <div className="mt-6 lg:hidden">
          <AgentProgressPanel activeStep={activeStep} />
        </div>
      )}
    </div>
  )
}
