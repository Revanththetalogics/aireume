import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Sparkles,
  ArrowRight,
  ArrowLeft,
  Building2,
  CreditCard,
  Users,
  Check,
  Mail,
  Plus,
  X,
  Upload,
  FileText,
  PartyPopper,
} from 'lucide-react'

import { useOnboarding } from '../contexts/OnboardingContext'
import { useAuth } from '../contexts/AuthContext'
import {
  updateOrganization,
  selectOnboardingPlan,
  getAvailablePlans,
  seedSampleData,
} from '../lib/api'
import { INDUSTRIES, COMPANY_SIZES } from '../lib/constants'

const TOTAL_STEPS = 4

/* ─── Progress Bar ─────────────────────────────────────────────── */

function ProgressBar({ current, total }) {
  return (
    <div className="w-full mb-8">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-slate-600">Step {current} of {total}</span>
        <span className="text-sm text-slate-400">{Math.round((current / total) * 100)}%</span>
      </div>
      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
        <motion.div
          className="h-full bg-brand-600 rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${(current / total) * 100}%` }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
        />
      </div>
    </div>
  )
}

/* ─── Step 1: Welcome & Organization ───────────────────────────── */

function StepOrganization({ onNext, onSkip, initialName }) {
  const [name, setName] = useState(initialName || '')
  const [industry, setIndustry] = useState('')
  const [companySize, setCompanySize] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const canContinue = name.trim().length > 0

  const handleNext = async () => {
    setLoading(true)
    setError(null)
    try {
      await updateOrganization({
        name: name.trim(),
        industry: industry || undefined,
        company_size: companySize || undefined,
      })
      onNext()
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to save organization details.')
    } finally {
      setLoading(false)
    }
  }

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

      <div className="w-full max-w-sm space-y-4 text-left">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">Organization Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Your company name"
            className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:border-brand-400 focus:ring-2 focus:ring-brand-100 outline-none transition-all text-slate-800 placeholder:text-slate-300"
            autoFocus
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">Industry</label>
          <select
            value={industry}
            onChange={(e) => setIndustry(e.target.value)}
            className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:border-brand-400 focus:ring-2 focus:ring-brand-100 outline-none transition-all text-slate-800 bg-white appearance-none"
          >
            <option value="">Select industry</option>
            {INDUSTRIES.map((ind) => (
              <option key={ind} value={ind}>{ind}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1.5">Company Size</label>
          <select
            value={companySize}
            onChange={(e) => setCompanySize(e.target.value)}
            className="w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:border-brand-400 focus:ring-2 focus:ring-brand-100 outline-none transition-all text-slate-800 bg-white appearance-none"
          >
            <option value="">Select size</option>
            {COMPANY_SIZES.map((size) => (
              <option key={size} value={size}>{size} employees</option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div className="mt-4 w-full max-w-sm px-4 py-3 rounded-xl bg-red-50 border border-red-100 text-sm text-red-700">
          {error}
          <button onClick={() => setError(null)} className="ml-2 font-medium hover:text-red-900">Dismiss</button>
        </div>
      )}

      <div className="mt-8 flex flex-col items-center w-full max-w-sm">
        <button
          onClick={handleNext}
          disabled={!canContinue || loading}
          className="w-full flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-brand-600 text-white font-semibold hover:bg-brand-700 transition-colors shadow-brand disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
              Saving...
            </span>
          ) : (
            <>Next <ArrowRight className="w-4 h-4" /></>
          )}
        </button>

        <button
          onClick={onSkip}
          className="mt-3 text-sm text-slate-400 hover:text-slate-600 transition-colors"
        >
          Skip for now
        </button>
      </div>
    </motion.div>
  )
}

/* ─── Step 2: Choose Plan ──────────────────────────────────────── */

function StepChoosePlan({ onNext, onBack, onSkip }) {
  const [plans, setPlans] = useState([])
  const [selectedPlan, setSelectedPlan] = useState(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function fetchPlans() {
      try {
        const data = await getAvailablePlans()
        setPlans(Array.isArray(data) ? data : [])
        // Auto-select free plan
        const freePlan = (Array.isArray(data) ? data : []).find(p => p.name === 'free')
        if (freePlan) setSelectedPlan(freePlan.id)
      } catch {
        setError('Failed to load plans. You can skip this step.')
      } finally {
        setLoading(false)
      }
    }
    fetchPlans()
  }, [])

  const handleNext = async () => {
    if (!selectedPlan) return
    setSubmitting(true)
    setError(null)
    try {
      await selectOnboardingPlan(selectedPlan)
      onNext()
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to select plan.')
    } finally {
      setSubmitting(false)
    }
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
        <span className="text-sm text-slate-400">Step 2 of 4</span>
      </div>

      <div className="text-center mb-6">
        <div className="w-12 h-12 rounded-xl bg-green-50 flex items-center justify-center mx-auto mb-4">
          <CreditCard className="w-6 h-6 text-green-600" />
        </div>
        <h2 className="text-2xl font-bold text-slate-900 mb-2">Choose your plan</h2>
        <p className="text-slate-500">Start free, upgrade anytime.</p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-8">
          <svg className="animate-spin h-6 w-6 text-brand-600" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
        </div>
      ) : (
        <div className="grid gap-3">
          {plans.map((plan) => {
            const isFree = plan.name === 'free'
            const isSelected = selectedPlan === plan.id
            const price = plan.price_monthly === 0 ? 'Free' : `$${(plan.price_monthly / 100).toFixed(0)}/mo`
            const features = Array.isArray(plan.features) ? plan.features : []

            return (
              <button
                key={plan.id}
                onClick={() => setSelectedPlan(plan.id)}
                className={`
                  w-full text-left p-4 rounded-xl border-2 transition-all
                  ${isSelected
                    ? 'border-brand-500 bg-brand-50 ring-1 ring-brand-500'
                    : 'border-slate-200 hover:border-slate-300 bg-white'
                  }
                `}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-slate-900">{plan.display_name}</span>
                    {isFree && (
                      <span className="px-2 py-0.5 text-xs font-medium bg-brand-100 text-brand-700 rounded-full">Popular</span>
                    )}
                  </div>
                  <span className="font-bold text-slate-900">{price}</span>
                </div>
                <p className="text-sm text-slate-500 mb-2">{plan.description}</p>
                {features.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {features.slice(0, 4).map((f, i) => (
                      <span key={i} className="inline-flex items-center gap-1 text-xs text-slate-600 bg-slate-50 px-2 py-0.5 rounded-md">
                        <Check className="w-3 h-3 text-green-500" />{f}
                      </span>
                    ))}
                  </div>
                )}
              </button>
            )
          })}
        </div>
      )}

      {error && (
        <div className="mt-4 px-4 py-3 rounded-xl bg-red-50 border border-red-100 text-sm text-red-700">
          {error}
          <button onClick={() => setError(null)} className="ml-2 font-medium hover:text-red-900">Dismiss</button>
        </div>
      )}

      <div className="mt-8 flex flex-col items-center">
        <button
          onClick={handleNext}
          disabled={!selectedPlan || submitting || loading}
          className="w-full max-w-xs flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-brand-600 text-white font-semibold hover:bg-brand-700 transition-colors shadow-brand disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {submitting ? (
            <span className="flex items-center gap-2">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
              Saving...
            </span>
          ) : (
            <>Next <ArrowRight className="w-4 h-4" /></>
          )}
        </button>

        <button
          onClick={onSkip}
          className="mt-3 text-sm text-slate-400 hover:text-slate-600 transition-colors"
        >
          Skip for now
        </button>
      </div>
    </motion.div>
  )
}

/* ─── Step 3: Invite Team (Optional) ───────────────────────────── */

function StepInviteTeam({ onNext, onBack, onSkip }) {
  const [emails, setEmails] = useState([''])
  const [error, setError] = useState(null)

  const addEmailField = () => setEmails([...emails, ''])

  const removeEmailField = (index) => {
    if (emails.length <= 1) return
    setEmails(emails.filter((_, i) => i !== index))
  }

  const updateEmail = (index, value) => {
    const updated = [...emails]
    updated[index] = value
    setEmails(updated)
  }

  // This step just collects emails for later — actual invites are sent after completion
  // We store them in localStorage for now
  const handleNext = () => {
    const validEmails = emails.filter(e => e.trim() && e.includes('@'))
    if (validEmails.length > 0) {
      try {
        localStorage.setItem('aria_pending_invites', JSON.stringify(validEmails))
      } catch {
        // Ignore storage errors
      }
    }
    onNext()
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
        <span className="text-sm text-slate-400">Step 3 of 4</span>
      </div>

      <div className="text-center mb-6">
        <div className="w-12 h-12 rounded-xl bg-blue-50 flex items-center justify-center mx-auto mb-4">
          <Users className="w-6 h-6 text-blue-600" />
        </div>
        <h2 className="text-2xl font-bold text-slate-900 mb-2">Invite your team</h2>
        <p className="text-slate-500">Add teammates to collaborate on hiring.</p>
      </div>

      <div className="w-full max-w-sm mx-auto space-y-3">
        {emails.map((email, index) => (
          <div key={index} className="flex items-center gap-2">
            <div className="relative flex-1">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-300" />
              <input
                type="email"
                value={email}
                onChange={(e) => updateEmail(index, e.target.value)}
                autoComplete="email"
                placeholder="colleague@company.com"
                className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 focus:border-brand-400 focus:ring-2 focus:ring-brand-100 outline-none transition-all text-slate-800 placeholder:text-slate-300"
              />
            </div>
            {emails.length > 1 && (
              <button
                onClick={() => removeEmailField(index)}
                aria-label="Remove email field"
                className="p-2 text-slate-300 hover:text-red-500 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        ))}

        <button
          onClick={addEmailField}
          className="flex items-center gap-2 text-sm text-brand-600 hover:text-brand-700 font-medium transition-colors"
        >
          <Plus className="w-4 h-4" /> Add another
        </button>
      </div>

      {error && (
        <div className="mt-4 px-4 py-3 rounded-xl bg-red-50 border border-red-100 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="mt-8 flex flex-col items-center">
        <button
          onClick={handleNext}
          className="w-full max-w-xs flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-brand-600 text-white font-semibold hover:bg-brand-700 transition-colors shadow-brand"
        >
          Next <ArrowRight className="w-4 h-4" />
        </button>

        <button
          onClick={onSkip}
          className="mt-3 text-sm text-slate-400 hover:text-slate-600 transition-colors"
        >
          Skip for now
        </button>
      </div>
    </motion.div>
  )
}

/* ─── Step 4: Get Started ──────────────────────────────────────── */

function StepGetStarted({ onComplete, onExploreSample }) {
  const [loading, setLoading] = useState(false)

  const handleComplete = async () => {
    setLoading(true)
    await onComplete()
    // Navigation is handled by the parent after onComplete
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col items-center text-center"
    >
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
        className="text-6xl mb-4"
      >
        <PartyPopper className="w-16 h-16 text-amber-500 mx-auto" />
      </motion.div>

      <h2 className="text-2xl font-bold text-slate-900 mb-2">You're all set!</h2>
      <p className="text-slate-500 mb-8">Your workspace is ready. Start screening candidates in minutes.</p>

      <div className="w-full max-w-sm space-y-3 mb-8">
        <button
          onClick={onExploreSample}
          className="w-full flex items-center gap-3 p-4 rounded-xl border border-slate-200 hover:border-brand-300 hover:bg-brand-50/50 transition-all text-left"
        >
          <div className="w-10 h-10 rounded-lg bg-amber-50 flex items-center justify-center shrink-0">
            <FileText className="w-5 h-5 text-amber-600" />
          </div>
          <div>
            <p className="font-medium text-slate-800">Explore sample data</p>
            <p className="text-sm text-slate-500">Try ARIA with pre-loaded examples</p>
          </div>
        </button>

        <button
          onClick={handleComplete}
          className="w-full flex items-center gap-3 p-4 rounded-xl border border-slate-200 hover:border-brand-300 hover:bg-brand-50/50 transition-all text-left"
        >
          <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center shrink-0">
            <Upload className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <p className="font-medium text-slate-800">Upload your first JD</p>
            <p className="text-sm text-slate-500">Start with your own job description</p>
          </div>
        </button>
      </div>

      <button
        onClick={handleComplete}
        disabled={loading}
        className="w-full max-w-xs flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-brand-600 text-white font-semibold hover:bg-brand-700 transition-colors shadow-brand disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {loading ? (
          <span className="flex items-center gap-2">
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
            Setting up...
          </span>
        ) : (
          <>Go to Dashboard <ArrowRight className="w-4 h-4" /></>
        )}
      </button>
    </motion.div>
  )
}

/* ─── Main Wizard ──────────────────────────────────────────────── */

export default function OnboardingWizard() {
  const { isOnboardingComplete, markOnboardingComplete, skipOnboarding } = useOnboarding()
  const { tenant } = useAuth()
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [sampleSeeded, setSampleSeeded] = useState(false)

  // If onboarding is already complete, don't render
  if (isOnboardingComplete) return null

  const handleComplete = async () => {
    await markOnboardingComplete()
    navigate('/')
  }

  const handleExploreSample = async () => {
    if (!sampleSeeded) {
      try {
        await seedSampleData()
        setSampleSeeded(true)
      } catch {
        // Continue anyway
      }
    }
    await markOnboardingComplete()
    navigate('/')
  }

  const handleSkip = async () => {
    await markOnboardingComplete()
    navigate('/')
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-gradient-to-br from-white via-slate-50 to-brand-50/30">
      <div className="w-full max-w-lg px-6 py-10">
        <ProgressBar current={step} total={TOTAL_STEPS} />

        <AnimatePresence mode="wait">
          {step === 1 && (
            <StepOrganization
              key="org"
              initialName={tenant?.name || ''}
              onNext={() => setStep(2)}
              onSkip={handleSkip}
            />
          )}

          {step === 2 && (
            <StepChoosePlan
              key="plan"
              onNext={() => setStep(3)}
              onBack={() => setStep(1)}
              onSkip={handleSkip}
            />
          )}

          {step === 3 && (
            <StepInviteTeam
              key="team"
              onNext={() => setStep(4)}
              onBack={() => setStep(2)}
              onSkip={handleSkip}
            />
          )}

          {step === 4 && (
            <StepGetStarted
              key="start"
              onComplete={handleComplete}
              onExploreSample={handleExploreSample}
            />
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
