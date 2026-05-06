import { useState, useEffect, useCallback } from 'react'
import { Loader2, Layers, Check, X, ToggleLeft, ToggleRight, Info } from 'lucide-react'
import { getAvailablePlans, getAdminFeatureFlags, getAdminPlanFeatures, updatePlanFeature, deletePlanFeature } from '../../lib/api'

export default function PlanFeaturesPage() {
  const [plans, setPlans] = useState([])
  const [selectedPlan, setSelectedPlan] = useState('')
  const [features, setFeatures] = useState([])
  const [planFeatures, setPlanFeatures] = useState([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const fetchPlans = useCallback(async () => {
    try {
      const data = await getAvailablePlans()
      setPlans(data.plans || data || [])
    } catch (err) {
      console.error('Failed to fetch plans:', err)
      setError('Failed to load subscription plans.')
    }
  }, [])

  const fetchFeatures = useCallback(async () => {
    try {
      const data = await getAdminFeatureFlags()
      setFeatures(data || [])
    } catch (err) {
      console.error('Failed to fetch features:', err)
    }
  }, [])

  const fetchPlanFeatures = useCallback(async (planId) => {
    if (!planId) return
    setLoading(true)
    try {
      const data = await getAdminPlanFeatures(planId)
      setPlanFeatures(data || [])
    } catch (err) {
      console.error('Failed to fetch plan features:', err)
      setPlanFeatures([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchPlans()
    fetchFeatures()
  }, [fetchPlans, fetchFeatures])

  useEffect(() => {
    fetchPlanFeatures(selectedPlan)
  }, [selectedPlan, fetchPlanFeatures])

  const isFeatureEnabledForPlan = (flagId) => {
    const mapping = planFeatures.find((pf) => pf.feature_flag_id === flagId)
    if (mapping) return mapping.enabled
    // No mapping means revert to global default
    const flag = features.find((f) => f.id === flagId)
    return flag?.enabled_globally ?? true
  }

  const handleToggle = async (flagId) => {
    setError('')
    setSuccess('')
    const currentlyEnabled = isFeatureEnabledForPlan(flagId)
    const newEnabled = !currentlyEnabled
    setSaving(true)
    try {
      const mapping = planFeatures.find((pf) => pf.feature_flag_id === flagId)
      if (mapping && newEnabled === (features.find((f) => f.id === flagId)?.enabled_globally ?? true)) {
        // If toggling back to global default, delete the mapping
        await deletePlanFeature(selectedPlan, flagId)
        setSuccess('Reverted to global default.')
      } else {
        await updatePlanFeature(selectedPlan, flagId, newEnabled)
        setSuccess(`Feature ${newEnabled ? 'enabled' : 'disabled'} for this plan.`)
      }
      fetchPlanFeatures(selectedPlan)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update feature.')
    } finally {
      setSaving(false)
    }
  }

  const selectedPlanName = plans.find((p) => String(p.id) === selectedPlan)?.display_name || ''

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-extrabold text-brand-900 tracking-tight flex items-center gap-2">
          <Layers className="w-6 h-6 text-brand-600" />
          Plan Feature Entitlements
        </h2>
      </div>

      {/* Plan Selector */}
      <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6">
        <label className="block text-sm font-bold text-brand-900 mb-2">Subscription Plan</label>
        <select
          className="w-full sm:w-80 px-4 py-2.5 rounded-xl ring-1 ring-brand-200 bg-white text-sm"
          value={selectedPlan}
          onChange={(e) => { setSelectedPlan(e.target.value); setError(''); setSuccess('') }}
        >
          <option value="">Select a plan</option>
          {plans.map((p) => (
            <option key={p.id} value={String(p.id)}>
              {p.display_name || p.name}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <div className="p-4 bg-red-50 rounded-2xl ring-1 ring-red-200 text-sm text-red-700">
          {error}
        </div>
      )}
      {success && (
        <div className="p-4 bg-green-50 rounded-2xl ring-1 ring-green-200 text-sm text-green-700">
          {success}
        </div>
      )}

      {/* Feature List */}
      {selectedPlan && (
        <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand overflow-hidden">
          <div className="px-6 py-4 border-b border-brand-100 flex items-center justify-between">
            <h3 className="text-lg font-bold text-brand-900">
              Features for {selectedPlanName}
            </h3>
            {saving && <Loader2 className="w-5 h-5 animate-spin text-brand-600" />}
          </div>

          {loading ? (
            <div className="flex justify-center py-16">
              <Loader2 className="w-8 h-8 animate-spin text-brand-600" />
            </div>
          ) : (
            <div className="divide-y divide-brand-100">
              {features.map((flag) => {
                const enabled = isFeatureEnabledForPlan(flag.id)
                const hasOverride = planFeatures.some((pf) => pf.feature_flag_id === flag.id)
                return (
                  <div
                    key={flag.id}
                    className="flex items-center justify-between px-6 py-4 hover:bg-brand-50/30 transition-colors"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-brand-900">{flag.display_name || flag.key}</span>
                        {hasOverride && (
                          <span className="inline-flex px-1.5 py-0.5 rounded-md text-[10px] font-bold bg-amber-50 text-amber-700 ring-1 ring-amber-200">
                            OVERRIDDEN
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5 truncate">{flag.description || flag.key}</p>
                    </div>
                    <button
                      onClick={() => handleToggle(flag.id)}
                      disabled={saving}
                      className="ml-4 flex items-center gap-2 shrink-0"
                    >
                      {enabled ? (
                        <ToggleRight className="w-8 h-8 text-green-600" />
                      ) : (
                        <ToggleLeft className="w-8 h-8 text-slate-300" />
                      )}
                    </button>
                  </div>
                )
              })}
              {!features.length && (
                <div className="px-6 py-12 text-center text-slate-400 text-sm">
                  No feature flags configured.
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Legend */}
      <div className="flex items-center gap-4 text-xs text-slate-500">
        <div className="flex items-center gap-1">
          <ToggleRight className="w-4 h-4 text-green-600" />
          <span>Enabled</span>
        </div>
        <div className="flex items-center gap-1">
          <ToggleLeft className="w-4 h-4 text-slate-300" />
          <span>Disabled</span>
        </div>
        <div className="flex items-center gap-1">
          <Info className="w-4 h-4 text-amber-500" />
          <span>Override reverts to global default when toggled back.</span>
        </div>
      </div>
    </div>
  )
}
