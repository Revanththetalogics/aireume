import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Sparkles,
  Target,
  BarChart3,
  ArrowRight,
  ArrowLeft,
  Upload,
  FileText,
  Check,
} from 'lucide-react'

import { useOnboarding } from '../contexts/OnboardingContext'
import AnimatedScore from './AnimatedScore'
import RecommendationBadge from './RecommendationBadge'
import ScoreBadge from './ScoreBadge'
import { createTemplate, analyzeResume } from '../lib/api'

// Placeholder — will be implemented by Task 16
async function seedSampleData() {
  throw new Error('seedSampleData not yet implemented')
}

const SAMPLE_JD = `Senior React Developer

We are looking for a Senior React Developer to join our engineering team.

Requirements:
- 5+ years of professional React development experience
- Strong proficiency in JavaScript/TypeScript, HTML5, CSS3
- Experience with state management (Redux, Zustand, or Context API)
- Familiarity with RESTful APIs and GraphQL
- Experience with testing frameworks (Jest, React Testing Library)
- Knowledge of modern build tools (Vite, Webpack)
- Excellent problem-solving and communication skills

Nice to have:
- Experience with Next.js or Remix
- Cloud platform experience (AWS, GCP, or Azure)
- CI/CD pipeline knowledge
- Experience with micro-frontend architecture

We offer competitive salary, remote-first culture, and excellent benefits.`

/* ─── Step indicators ─────────────────────────────────────────────── */

function ProgressDots({ current, total }) {
  return (
    <div className="flex items-center justify-center gap-2 mb-8">
      {Array.from({ length: total }, (_, i) => (
        <div
          key={i}
          className={`h-2 rounded-full transition-all duration-300 ${
            i < current
              ? 'w-6 bg-brand-600'
              : i === current
                ? 'w-6 bg-brand-400'
                : 'w-2 bg-slate-200'
          }`}
        />
      ))}
    </div>
  )
}

/* ─── Step 1: Welcome ─────────────────────────────────────────────── */

function StepWelcome({ onNext, onSkip }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -16 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col items-center text-center"
    >
      <div className="w-16 h-16 rounded-2xl bg-brand-100 flex items-center justify-center mb-6">
        <Sparkles className="w-8 h-8 text-brand-600" />
      </div>

      <h1 className="text-3xl font-bold text-slate-900 mb-2">Welcome to ARIA</h1>
      <p className="text-slate-500 mb-8">AI-Powered Recruitment Intelligence</p>

      <div className="space-y-4 mb-10 text-left w-full max-w-xs">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 w-8 h-8 rounded-lg bg-green-50 flex items-center justify-center shrink-0">
            <Sparkles className="w-4 h-4 text-green-600" />
          </div>
          <div>
            <p className="font-medium text-slate-800">Screen resumes in seconds</p>
            <p className="text-sm text-slate-500">AI-powered analysis, instantly</p>
          </div>
        </div>
        <div className="flex items-start gap-3">
          <div className="mt-0.5 w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center shrink-0">
            <Target className="w-4 h-4 text-blue-600" />
          </div>
          <div>
            <p className="font-medium text-slate-800">AI-ranked candidate matching</p>
            <p className="text-sm text-slate-500">Find the best fit, every time</p>
          </div>
        </div>
        <div className="flex items-start gap-3">
          <div className="mt-0.5 w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center shrink-0">
            <BarChart3 className="w-4 h-4 text-amber-600" />
          </div>
          <div>
            <p className="font-medium text-slate-800">Data-driven hiring decisions</p>
            <p className="text-sm text-slate-500">Objective scoring and insights</p>
          </div>
        </div>
      </div>

      <button
        onClick={onNext}
        className="w-full max-w-xs flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-brand-600 text-white font-semibold hover:bg-brand-700 transition-colors shadow-brand"
      >
        Get Started <ArrowRight className="w-4 h-4" />
      </button>

      <button
        onClick={onSkip}
        className="mt-3 text-sm text-slate-400 hover:text-slate-600 transition-colors"
      >
        Skip
      </button>
    </motion.div>
  )
}

/* ─── Step 2: Job Title ───────────────────────────────────────────── */

function StepJobTitle({ value, onChange, onNext, onBack, onSkip }) {
  const canContinue = value.trim().length > 0

  return (
    <motion.div
      initial={{ opacity: 0, x: 40 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -40 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col"
    >
      <div className="flex items-center justify-between mb-8">
        <button onClick={onBack} className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back
        </button>
        <span className="text-sm text-slate-400">Step 2 of 5</span>
      </div>

      <h2 className="text-2xl font-bold text-slate-900 mb-2">What role are you hiring for?</h2>
      <p className="text-slate-500 mb-6">We'll use this to set up your first job description.</p>

      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder='e.g., "Senior React Developer"'
        className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:border-brand-400 focus:ring-2 focus:ring-brand-100 outline-none transition-all text-slate-800 placeholder:text-slate-300"
        autoFocus
      />

      <div className="mt-8 flex flex-col items-center">
        <button
          onClick={onNext}
          disabled={!canContinue}
          className="w-full max-w-xs flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-brand-600 text-white font-semibold hover:bg-brand-700 transition-colors shadow-brand disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Continue <ArrowRight className="w-4 h-4" />
        </button>

        <button
          onClick={onSkip}
          className="mt-3 text-sm text-slate-400 hover:text-slate-600 transition-colors"
        >
          Skip
        </button>
      </div>
    </motion.div>
  )
}

/* ─── Step 3: Job Description ─────────────────────────────────────── */

function StepJobDescription({ value, onChange, onNext, onBack, onSkip, onUseSample, loading }) {
  const canContinue = value.trim().length > 20

  return (
    <motion.div
      initial={{ opacity: 0, x: 40 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -40 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col"
    >
      <div className="flex items-center justify-between mb-8">
        <button onClick={onBack} className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back
        </button>
        <span className="text-sm text-slate-400">Step 3 of 5</span>
      </div>

      <h2 className="text-2xl font-bold text-slate-900 mb-2">Paste your job description</h2>
      <p className="text-slate-500 mb-6">Or use a sample to try ARIA right away.</p>

      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Paste the full job description here..."
        rows={8}
        className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:border-brand-400 focus:ring-2 focus:ring-brand-100 outline-none transition-all text-slate-800 placeholder:text-slate-300 resize-none"
      />

      <button
        onClick={onUseSample}
        className="mt-3 self-start text-sm text-brand-600 hover:text-brand-700 font-medium transition-colors"
      >
        Use Sample JD
      </button>

      <div className="mt-8 flex flex-col items-center">
        <button
          onClick={onNext}
          disabled={!canContinue || loading}
          className="w-full max-w-xs flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-brand-600 text-white font-semibold hover:bg-brand-700 transition-colors shadow-brand disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
              Saving...
            </span>
          ) : (
            <>Continue <ArrowRight className="w-4 h-4" /></>
          )}
        </button>

        <button
          onClick={onSkip}
          className="mt-3 text-sm text-slate-400 hover:text-slate-600 transition-colors"
        >
          Skip
        </button>
      </div>
    </motion.div>
  )
}

/* ─── Step 4: Upload Resume ───────────────────────────────────────── */

function StepUploadResume({ onAnalyze, onBack, onSkip, onTrySample, loading }) {
  const [file, setFile] = useState(null)

  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      setFile(acceptedFiles[0])
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc'],
    },
    maxFiles: 1,
  })

  const handleAnalyze = () => {
    if (file) onAnalyze(file)
  }

  return (
    <motion.div
      initial={{ opacity: 0, x: 40 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -40 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col"
    >
      <div className="flex items-center justify-between mb-8">
        <button onClick={onBack} className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back
        </button>
        <span className="text-sm text-slate-400">Step 4 of 5</span>
      </div>

      <h2 className="text-2xl font-bold text-slate-900 mb-2">Upload a resume to analyze</h2>
      <p className="text-slate-500 mb-6">Drop a resume file or click to browse.</p>

      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all
          ${file ? 'border-brand-300 bg-brand-50' : isDragActive ? 'border-brand-400 bg-brand-50' : 'border-slate-200 hover:border-brand-300 hover:bg-slate-50'}
        `}
      >
        <input {...getInputProps()} />
        {file ? (
          <div className="flex flex-col items-center gap-2">
            <div className="w-12 h-12 rounded-xl bg-brand-100 flex items-center justify-center">
              <FileText className="w-6 h-6 text-brand-600" />
            </div>
            <p className="font-medium text-slate-800">{file.name}</p>
            <p className="text-sm text-slate-400">{(file.size / 1024).toFixed(1)} KB</p>
            <button
              onClick={(e) => { e.stopPropagation(); setFile(null) }}
              className="text-xs text-slate-400 hover:text-red-500 transition-colors mt-1"
            >
              Remove
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-slate-100 flex items-center justify-center">
              <Upload className="w-6 h-6 text-slate-400" />
            </div>
            <div>
              <p className="font-medium text-slate-700">
                {isDragActive ? 'Drop your resume here' : 'Drag & drop a resume'}
              </p>
              <p className="text-sm text-slate-400 mt-1">or click to browse — PDF, DOCX supported</p>
            </div>
          </div>
        )}
      </div>

      <button
        onClick={onTrySample}
        className="mt-3 self-start text-sm text-brand-600 hover:text-brand-700 font-medium transition-colors"
      >
        Try with sample data
      </button>

      <div className="mt-8 flex flex-col items-center">
        <button
          onClick={handleAnalyze}
          disabled={!file || loading}
          className="w-full max-w-xs flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-brand-600 text-white font-semibold hover:bg-brand-700 transition-colors shadow-brand disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
              Analyzing...
            </span>
          ) : (
            <>Analyze <ArrowRight className="w-4 h-4" /></>
          )}
        </button>

        <button
          onClick={onSkip}
          className="mt-3 text-sm text-slate-400 hover:text-slate-600 transition-colors"
        >
          Skip
        </button>
      </div>
    </motion.div>
  )
}

/* ─── Step 5: Result Reveal ───────────────────────────────────────── */

function StepResult({ result, onContinue, onUploadMore }) {
  const score = result?.fit_score ?? result?.score ?? 85
  const highlights = result?.strengths || result?.highlights || [
    '8 years relevant experience',
    'Strong technical skills',
  ]
  const gaps = result?.gaps || result?.weaknesses || [
    'Missing cloud certification',
  ]

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col items-center text-center"
    >
      <div className="text-5xl mb-4">🎉</div>
      <h2 className="text-2xl font-bold text-slate-900 mb-6">Your First AI Screening!</h2>

      <div className="mb-4">
        <ScoreBadge score={score} size="lg" animated className="mx-auto" />
      </div>

      <RecommendationBadge score={score} size="md" className="mb-6" />

      <div className="w-full text-left space-y-2 mb-8">
        {highlights.map((item, i) => (
          <div key={i} className="flex items-start gap-2">
            <Check className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
            <span className="text-sm text-slate-700">{item}</span>
          </div>
        ))}
        {gaps.map((item, i) => (
          <div key={`gap-${i}`} className="flex items-start gap-2">
            <span className="w-4 h-4 flex items-center justify-center text-amber-500 mt-0.5 shrink-0 text-xs font-bold">!</span>
            <span className="text-sm text-slate-500">{item}</span>
          </div>
        ))}
      </div>

      <div className="flex flex-col gap-3 w-full max-w-xs">
        <button
          onClick={onContinue}
          className="w-full flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-brand-600 text-white font-semibold hover:bg-brand-700 transition-colors shadow-brand"
        >
          Continue to Dashboard <ArrowRight className="w-4 h-4" />
        </button>
        <button
          onClick={onUploadMore}
          className="w-full px-6 py-3 rounded-xl border border-slate-200 text-slate-700 font-medium hover:bg-slate-50 transition-colors"
        >
          Upload More Resumes
        </button>
      </div>
    </motion.div>
  )
}

/* ─── Main Wizard ─────────────────────────────────────────────────── */

export default function OnboardingWizard() {
  const { currentStep, completeStep, skipOnboarding, dismissOnboarding } = useOnboarding()

  const [jobTitle, setJobTitle] = useState('')
  const [jdText, setJdText] = useState('')
  const [templateId, setTemplateId] = useState(null)
  const [analysisResult, setAnalysisResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Step is 1-indexed for the wizard (1–5)
  // currentStep from context: 0 = not started, 1-5 = wizard steps, 6 = completed
  // Treat step 0 (not started) as step 1 so the wizard renders immediately
  // for existing users who have no aria_onboarding localStorage entry.
  const step = currentStep > 5 ? 0 : (currentStep === 0 ? 1 : currentStep)

  // Only return null if onboarding is completed (step > 5)
  if (currentStep > 5) return null

  const goToStep = (nextStep) => {
    // We update the context step directly
    completeStep(nextStep - 1) // completeStep advances step + 1
  }

  const handleStep3Next = async () => {
    setLoading(true)
    setError(null)
    try {
      const template = await createTemplate({
        title: jobTitle || 'New Role',
        content: jdText,
      })
      setTemplateId(template.id || template.template_id)
      completeStep(3)
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to save job description. You can skip this step.')
    } finally {
      setLoading(false)
    }
  }

  const handleAnalyze = async (file) => {
    setLoading(true)
    setError(null)
    try {
      const result = await analyzeResume(file, jdText, null, null, templateId)
      setAnalysisResult(result)
      completeStep(4)
    } catch (err) {
      setError(err?.response?.data?.detail || 'Analysis failed. You can skip this step.')
    } finally {
      setLoading(false)
    }
  }

  const handleTrySample = async () => {
    setLoading(true)
    setError(null)
    try {
      await seedSampleData()
      // Use a mock result for the reveal step
      setAnalysisResult({
        fit_score: 85,
        strengths: ['8 years relevant experience', 'Strong technical skills'],
        gaps: ['Missing cloud certification'],
      })
      completeStep(4)
    } catch {
      // seedSampleData not implemented yet — use mock data
      setAnalysisResult({
        fit_score: 85,
        strengths: ['8 years relevant experience', 'Strong technical skills'],
        gaps: ['Missing cloud certification'],
      })
      completeStep(4)
    } finally {
      setLoading(false)
    }
  }

  const handleContinue = () => {
    completeStep(5) // marks onboarding as complete
  }

  const handleUploadMore = () => {
    // Go back to step 4 (upload)
    completeStep(3) // step 4 is index 3
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-white">
      <div className="w-full max-w-lg px-6 py-10">
        <ProgressDots current={step - 1} total={5} />

        {error && (
          <div className="mb-4 px-4 py-3 rounded-xl bg-red-50 border border-red-100 text-sm text-red-700">
            {error}
            <button onClick={() => setError(null)} className="ml-2 font-medium hover:text-red-900">Dismiss</button>
          </div>
        )}

        <AnimatePresence mode="wait">
          {step === 1 && (
            <StepWelcome
              key="welcome"
              onNext={() => completeStep(1)}
              onSkip={skipOnboarding}
            />
          )}

          {step === 2 && (
            <StepJobTitle
              key="title"
              value={jobTitle}
              onChange={setJobTitle}
              onNext={() => completeStep(2)}
              onBack={() => goToStep(1)}
              onSkip={skipOnboarding}
            />
          )}

          {step === 3 && (
            <StepJobDescription
              key="jd"
              value={jdText}
              onChange={setJdText}
              onNext={handleStep3Next}
              onBack={() => goToStep(2)}
              onSkip={skipOnboarding}
              onUseSample={() => {
                setJdText(SAMPLE_JD)
                if (!jobTitle) setJobTitle('Senior React Developer')
              }}
              loading={loading}
            />
          )}

          {step === 4 && (
            <StepUploadResume
              key="upload"
              onAnalyze={handleAnalyze}
              onBack={() => goToStep(3)}
              onSkip={skipOnboarding}
              onTrySample={handleTrySample}
              loading={loading}
            />
          )}

          {step === 5 && (
            <StepResult
              key="result"
              result={analysisResult}
              onContinue={handleContinue}
              onUploadMore={handleUploadMore}
            />
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
