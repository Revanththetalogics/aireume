import { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { getOnboardingStatus, completeOnboarding as completeOnboardingAPI } from '../lib/api'
import { useAuth } from './AuthContext'

const OnboardingContext = createContext(null)

const STORAGE_KEY = 'aria_onboarding'
const CHECKLIST_KEY = 'aria_getting_started'

const DEFAULT_CHECKLIST = {
  createdJob: false,
  analyzedResume: false,
  shortlistedCandidate: false,
  invitedTeamMember: false,
  sharedWithHM: false,
}

function loadFromStorage(key, fallback) {
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : fallback
  } catch {
    return fallback
  }
}

function saveToStorage(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // localStorage unavailable — continue without persistence
  }
}

export function OnboardingProvider({ children }) {
  const { user, loading: authLoading } = useAuth()
  const [currentStep, setCurrentStep] = useState(() => loadFromStorage(STORAGE_KEY, { step: 0 }).step)
  const [isOnboardingComplete, setIsOnboardingComplete] = useState(() => loadFromStorage(STORAGE_KEY, { complete: false }).complete)
  const [checklist, setChecklist] = useState(() => loadFromStorage(CHECKLIST_KEY, { items: DEFAULT_CHECKLIST, dismissed: false }).items)
  const [checklistDismissed, setChecklistDismissed] = useState(() => loadFromStorage(CHECKLIST_KEY, { items: DEFAULT_CHECKLIST, dismissed: false }).dismissed)
  const [onboardingStatus, setOnboardingStatus] = useState(null)
  const [statusLoading, setStatusLoading] = useState(true)

  // Fetch onboarding status from backend — only when authenticated
  useEffect(() => {
    if (authLoading) return                // wait for auth to resolve
    if (!user) {
      setStatusLoading(false)              // not authenticated — rely on localStorage
      return
    }
    let cancelled = false
    async function fetchStatus() {
      try {
        const data = await getOnboardingStatus()
        if (!cancelled) {
          setOnboardingStatus(data)
          setIsOnboardingComplete(data.completed)
          setStatusLoading(false)
        }
      } catch {
        if (!cancelled) {
          setStatusLoading(false)
        }
      }
    }
    fetchStatus()
    return () => { cancelled = true }
  }, [authLoading, user])

  // Persist onboarding state whenever it changes
  useEffect(() => {
    saveToStorage(STORAGE_KEY, { step: currentStep, complete: isOnboardingComplete })
  }, [currentStep, isOnboardingComplete])

  // Persist checklist state whenever it changes
  useEffect(() => {
    saveToStorage(CHECKLIST_KEY, { items: checklist, dismissed: checklistDismissed })
  }, [checklist, checklistDismissed])

  const completeStep = useCallback((step) => {
    setCurrentStep((prev) => {
      // Only advance if the completed step is the current one (or earlier)
      if (step >= prev) {
        const next = step + 1
        if (next > 5) {
          setIsOnboardingComplete(true)
        }
        return next
      }
      return prev
    })
  }, [])

  const skipOnboarding = useCallback(() => {
    setCurrentStep(6)
    setIsOnboardingComplete(true)
  }, [])

  const dismissOnboarding = useCallback(() => {
    setCurrentStep(6)
    setIsOnboardingComplete(true)
  }, [])

  const resetOnboarding = useCallback(() => {
    setCurrentStep(0)
    setIsOnboardingComplete(false)
    setChecklist({ ...DEFAULT_CHECKLIST })
    setChecklistDismissed(false)
    saveToStorage(STORAGE_KEY, { step: 0, complete: false })
    saveToStorage(CHECKLIST_KEY, { items: DEFAULT_CHECKLIST, dismissed: false })
  }, [])

  const completeChecklistItem = useCallback((key) => {
    setChecklist((prev) => {
      if (key in prev) {
        return { ...prev, [key]: true }
      }
      return prev
    })
  }, [])

  const isChecklistComplete = useCallback(() => {
    return Object.values(checklist).every(Boolean)
  }, [checklist])

  const dismissChecklist = useCallback(() => {
    setChecklistDismissed(true)
  }, [])

  // Mark onboarding as complete on the backend and locally
  const markOnboardingComplete = useCallback(async () => {
    try {
      await completeOnboardingAPI()
    } catch {
      // Best-effort — still mark locally
    }
    setIsOnboardingComplete(true)
    setOnboardingStatus((prev) => prev ? { ...prev, completed: true } : prev)
  }, [])

  return (
    <OnboardingContext.Provider
      value={{
        currentStep,
        isOnboardingComplete,
        onboardingStatus,
        statusLoading,
        checklist,
        checklistDismissed,
        completeStep,
        skipOnboarding,
        dismissOnboarding,
        resetOnboarding,
        completeChecklistItem,
        isChecklistComplete,
        dismissChecklist,
        markOnboardingComplete,
      }}
    >
      {children}
    </OnboardingContext.Provider>
  )
}

export function useOnboarding() {
  const ctx = useContext(OnboardingContext)
  if (!ctx) throw new Error('useOnboarding must be used within OnboardingProvider')
  return ctx
}
