import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react'
import { getSubscription, checkUsage, getAvailablePlans } from '../lib/api.js'
import { useAuth } from '../contexts/AuthContext'

const SubscriptionContext = createContext(null)

export function SubscriptionProvider({ children }) {
  const { user, loading: authLoading } = useAuth()
  const [subscription, setSubscription] = useState(null)
  const [availablePlans, setAvailablePlans] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [lastFetch, setLastFetch] = useState(0)

  const fetchSubscription = useCallback(async (force = false) => {
    // Cache for 30 seconds unless forced
    const now = Date.now()
    if (!force && now - lastFetch < 10000 && subscription) {
      return subscription
    }

    setLoading(true)
    setError(null)
    try {
      const data = await getSubscription()
      setSubscription(data)
      setLastFetch(now)
      return data
    } catch (err) {
      setError(err.message || 'Failed to fetch subscription')
      setSubscription(null)
    } finally {
      setLoading(false)
    }
  }, [lastFetch, subscription])

  const fetchAvailablePlans = useCallback(async () => {
    try {
      const data = await getAvailablePlans()
      setAvailablePlans(data)
      return data
    } catch (err) {
      console.error('Failed to fetch plans:', err)
      return []
    }
  }, [])

  const checkActionAllowed = useCallback(async (action, quantity = 1) => {
    try {
      const result = await checkUsage(action, quantity)
      return result
    } catch (err) {
      console.error('Usage check failed:', err)
      // Fail closed - assume not allowed if check fails
      return { allowed: false, message: 'Unable to verify usage limits' }
    }
  }, [])

  const getUsageStats = useCallback(() => {
    if (!subscription) return null
    return {
      analysesUsed: subscription.usage.analyses_used,
      analysesLimit: subscription.usage.analyses_limit,
      storageUsedMB: subscription.usage.storage_used_mb,
      storageLimitGB: subscription.usage.storage_limit_gb,
      teamMembers: subscription.usage.team_members_count,
      teamMembersLimit: subscription.usage.team_members_limit,
      percentUsed: subscription.usage.percent_used,
      daysUntilReset: subscription.days_until_reset,
    }
  }, [subscription])

  const getCurrentPlan = useCallback(() => {
    if (!subscription) return null
    return subscription.current_plan
  }, [subscription])

  const isFeatureAvailable = useCallback((feature) => {
    if (!subscription?.current_plan?.plan) return false
    const limits = subscription.current_plan.plan.limits || {}
    
    const featureMap = {
      'batch_analysis': () => limits.batch_size > 1,
      'api_access': () => limits.api_access === true,
      'custom_weights': () => limits.custom_weights === true,
      'priority_support': () => limits.priority_support === true,
      'unlimited_analyses': () => limits.analyses_per_month < 0,
      'dedicated_support': () => limits.dedicated_support === true,
      'custom_integrations': () => limits.custom_integrations === true,
      'sso': () => limits.sso === true,
    }
    
    const checker = featureMap[feature]
    return checker ? checker() : false
  }, [subscription])

  const getRemainingAnalyses = useCallback(() => {
    if (!subscription) return 0
    const limit = subscription.usage.analyses_limit
    if (limit < 0) return Infinity
    return limit - subscription.usage.analyses_used
  }, [subscription])

  // Stable refs for callbacks to avoid infinite re-render loop
  const fetchSubRef = useRef(fetchSubscription)
  const fetchPlansRef = useRef(fetchAvailablePlans)
  useEffect(() => { fetchSubRef.current = fetchSubscription }, [fetchSubscription])
  useEffect(() => { fetchPlansRef.current = fetchAvailablePlans }, [fetchAvailablePlans])

  // Initial fetch on mount — only when user is authenticated
  useEffect(() => {
    if (authLoading || !user) {
      // Clear subscription data when user logs out
      setSubscription(null)
      setAvailablePlans([])
      return
    }
    fetchSubRef.current()
    fetchPlansRef.current()
  }, [authLoading, user])

  // Refresh subscription after analysis operations
  const refreshAfterAnalysis = useCallback(async (analysisCount = 1) => {
    // Optimistically update local state first for better UX
    if (subscription) {
      const newSubscription = {
        ...subscription,
        usage: {
          ...subscription.usage,
          analyses_used: subscription.usage.analyses_used + analysisCount,
          percent_used: Math.min(
            ((subscription.usage.analyses_used + analysisCount) / subscription.usage.analyses_limit * 100),
            100
          ),
        }
      }
      setSubscription(newSubscription)
    }
    
    // Then fetch real data after a short delay
    setTimeout(() => fetchSubscription(true), 1000)
  }, [subscription, fetchSubscription])

  const value = {
    subscription,
    availablePlans,
    loading,
    error,
    fetchSubscription,
    fetchAvailablePlans,
    checkActionAllowed,
    getUsageStats,
    getCurrentPlan,
    isFeatureAvailable,
    getRemainingAnalyses,
    refreshAfterAnalysis,
  }

  return (
    <SubscriptionContext.Provider value={value}>
      {children}
    </SubscriptionContext.Provider>
  )
}

export function useSubscription() {
  const context = useContext(SubscriptionContext)
  if (!context) {
    throw new Error('useSubscription must be used within SubscriptionProvider')
  }
  return context
}

// Hook for checking limits before operations
export function useUsageCheck() {
  const { checkActionAllowed, getRemainingAnalyses, subscription } = useSubscription()

  const checkBeforeAnalysis = useCallback(async (fileCount = 1) => {
    const remaining = getRemainingAnalyses()
    
    // Quick local check first
    if (remaining !== Infinity && remaining < fileCount) {
      return {
        allowed: false,
        message: `You only have ${remaining} analyses remaining this month. Please upgrade your plan.`,
        remaining: remaining - fileCount, // Return deficit (negative number)
      }
    }

    // Server check for accurate limits
    const result = await checkActionAllowed(fileCount > 1 ? 'batch_analysis' : 'resume_analysis', fileCount)
    return {
      ...result,
      remaining: remaining - fileCount,
    }
  }, [checkActionAllowed, getRemainingAnalyses])

  return { checkBeforeAnalysis, getRemainingAnalyses }
}
