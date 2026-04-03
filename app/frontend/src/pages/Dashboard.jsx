import { useState, useEffect, useRef } from 'react'
import { Sparkles, History, CheckCircle, Loader2 } from 'lucide-react'
import UploadForm from '../components/UploadForm'
import ScoreGauge from '../components/ScoreGauge'
import ResultCard from '../components/ResultCard'
import Timeline from '../components/Timeline'
import { analyzeResume } from '../lib/api'

const AGENT_STEPS = [
  { id: 'parse',   label: 'Agent 1 — Parsing resume & extracting profile',    duration: 3000  },
  { id: 'score',   label: 'Agent 2 — Running deterministic scoring engine',    duration: 2000  },
  { id: 'llm',     label: 'Agent 3 — Generating qualitative insights (LLM)',   duration: 45000 },
  { id: 'done',    label: 'Pipeline complete — Rendering results',             duration: 500   },
]

function AgentProgressIndicator({ activeStep }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
      <div className="flex items-center gap-2 mb-5">
        <Sparkles className="w-5 h-5 text-blue-600 animate-pulse" />
        <h3 className="font-semibold text-slate-800">Agent Pipeline Running</h3>
      </div>
      <div className="space-y-3">
        {AGENT_STEPS.slice(0, 3).map((step, idx) => {
          const stepIdx = AGENT_STEPS.findIndex(s => s.id === activeStep)
          const isDone = idx < stepIdx
          const isActive = step.id === activeStep

          return (
            <div key={step.id} className={`flex items-center gap-3 p-3 rounded-lg transition-all ${
              isActive ? 'bg-blue-50 border border-blue-200' :
              isDone   ? 'bg-green-50 border border-green-100' :
                         'bg-slate-50 border border-slate-100'
            }`}>
              {isDone ? (
                <CheckCircle className="w-5 h-5 text-green-500 shrink-0" />
              ) : isActive ? (
                <Loader2 className="w-5 h-5 text-blue-500 shrink-0 animate-spin" />
              ) : (
                <div className="w-5 h-5 rounded-full border-2 border-slate-300 shrink-0" />
              )}
              <span className={`text-sm font-medium ${
                isActive ? 'text-blue-700' : isDone ? 'text-green-700' : 'text-slate-400'
              }`}>
                {step.label}
              </span>
            </div>
          )
        })}
      </div>
      <p className="text-xs text-slate-400 mt-4 text-center">
        Agent 3 (LLM) typically takes 20-40s — results stream when complete
      </p>
    </div>
  )
}

export default function Dashboard() {
  const [selectedFile, setSelectedFile]     = useState(null)
  const [jobDescription, setJobDescription] = useState('')
  const [selectedJobFile, setSelectedJobFile] = useState(null)
  const [isLoading, setIsLoading]           = useState(false)
  const [activeStep, setActiveStep]         = useState(null)
  const [result, setResult]                 = useState(null)
  const [error, setError]                   = useState(null)
  const timerRef = useRef(null)

  // Step animation: advances through steps with realistic timing
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
    setResult(null)
    setActiveStep('parse')
    advanceSteps()

    try {
      const data = await analyzeResume(selectedFile, jobDescription, selectedJobFile)
      clearStepTimer()
      setActiveStep('done')
      setResult(data)
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
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-blue-600" />
            <h1 className="text-xl font-bold text-slate-800">AI Resume Screener</h1>
            <span className="text-sm text-slate-500 ml-2">by ThetaLogics</span>
          </div>
          <a href="/api/history" className="flex items-center gap-2 text-sm text-slate-600 hover:text-slate-800">
            <History className="w-4 h-4" />
            <span className="hidden sm:inline">History</span>
          </a>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
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
        />

        {/* Agent progress */}
        {isLoading && activeStep && activeStep !== 'done' && (
          <div className="mt-8">
            <AgentProgressIndicator activeStep={activeStep} />
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="mt-8 space-y-6">
            <div className="grid md:grid-cols-3 gap-6">
              <div className="md:col-span-1">
                <ScoreGauge score={result.fit_score} />
              </div>
              <div className="md:col-span-2">
                <ResultCard result={result} />
              </div>
            </div>
            <Timeline
              workExperience={result.work_experience || []}
              gaps={result.employment_gaps || []}
            />
          </div>
        )}
      </main>

      <footer className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6 text-center text-sm text-slate-500">
        <p>Enterprise Agent Pipeline • 3-Agent Architecture • Powered by llama3 on-prem • No data leaves your VPS</p>
      </footer>
    </div>
  )
}
