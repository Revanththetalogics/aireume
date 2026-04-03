import { useState, useEffect, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Sparkles, CheckCircle, Loader2 } from 'lucide-react'
import UploadForm from '../components/UploadForm'
import NavBar from '../components/NavBar'
import { analyzeResume } from '../lib/api'

const AGENT_STEPS = [
  { id: 'parse', label: 'Agent 1 — Parsing resume & extracting profile',  duration: 3000  },
  { id: 'score', label: 'Agent 2 — Running deterministic scoring engine', duration: 2000  },
  { id: 'llm',   label: 'Agent 3 — Generating qualitative insights (LLM)', duration: 45000 },
  { id: 'done',  label: 'Pipeline complete — Rendering results',           duration: 500   },
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
          const isDone   = idx < stepIdx
          const isActive = step.id === activeStep
          return (
            <div
              key={step.id}
              className={`flex items-center gap-3 p-3 rounded-lg transition-all ${
                isActive ? 'bg-blue-50 border border-blue-200' :
                isDone   ? 'bg-green-50 border border-green-100' :
                           'bg-slate-50 border border-slate-100'
              }`}
            >
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
        Agent 3 (LLM) typically takes 20–40 s — report opens when complete
      </p>
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
      // Navigate to dedicated report page
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
    <div className="min-h-screen bg-slate-50">
      <NavBar />

      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        {/* Hero text */}
        <div className="text-center mb-8">
          <h2 className="text-3xl font-bold text-slate-900 mb-2">Screen a Candidate</h2>
          <p className="text-slate-500">Upload a resume and job description. ARIA's 3-agent pipeline will analyze fit, score, and generate a full report.</p>
        </div>

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

        {/* Agent progress */}
        {isLoading && activeStep && activeStep !== 'done' && (
          <div className="mt-8">
            <AgentProgressIndicator activeStep={activeStep} />
          </div>
        )}
      </main>

      <footer className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-6 text-center text-sm text-slate-500">
        <p>Enterprise Agent Pipeline · 3-Agent Architecture · Powered by llama3 on-prem · No data leaves your VPS</p>
      </footer>
    </div>
  )
}
