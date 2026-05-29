import { useState, useEffect, useCallback } from 'react'
import {
  Loader2,
  AlertTriangle,
  ChevronDown,
  Edit3,
  Save,
  X,
  Trash2,
  Gauge,
  RotateCcw,
} from 'lucide-react'
import {
  getAdminTenants,
  getTenantRateLimit,
  updateTenantRateLimit,
  deleteTenantRateLimit,
} from '../../lib/api'

/* ── Default Limits ────────────────────────────────────── */
const DEFAULT_LIMITS = {
  requests_per_minute: 60,
  llm_concurrent_max: 2,
}

/* ── Toast ─────────────────────────────────────────────── */
function Toast({ message, type = 'success', onDone }) {
  useEffect(() => {
    const t = setTimeout(onDone, 3500)
    return () => clearTimeout(t)
  }, [onDone])

  return (
    <div className={`p-4 rounded-xl ring-1 text-sm ${
      type === 'success' ? 'bg-green-50 text-green-700 ring-green-200' : 'bg-red-50 text-red-700 ring-red-200'
    }`}>
      {message}
    </div>
  )
}

/* ── Limit Row ─────────────────────────────────────────── */
function LimitField({ label, value, editValue, editing, onChange, unit }) {
  return (
    <div>
      <label className="block text-xs font-semibold text-gray-500 mb-1">{label}</label>
      {editing ? (
        <div className="flex items-center gap-2">
          <input
            type="number"
            min="1"
            value={editValue}
            onChange={(e) => onChange(parseInt(e.target.value, 10) || 1)}
            className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-sm"
          />
          {unit && <span className="text-xs text-gray-400 whitespace-nowrap">{unit}</span>}
        </div>
      ) : (
        <div className="flex items-baseline gap-1">
          <p className="text-2xl font-bold text-gray-900">{value ?? '—'}</p>
          {unit && <span className="text-xs text-gray-400">{unit}</span>}
        </div>
      )}
    </div>
  )
}

/* ── Delete Confirmation Modal ─────────────────────────── */
function ResetModal({ tenantName, onClose, onDone }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleReset = async () => {
    setLoading(true)
    setError('')
    try {
      await deleteTenantRateLimit()
      onDone()
      onClose()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to reset rate limits')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl ring-1 ring-amber-100 shadow-xl w-full max-w-md p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-lg bg-amber-50 flex items-center justify-center">
            <RotateCcw className="w-5 h-5 text-amber-600" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-gray-900">Reset to Defaults</h3>
            <p className="text-sm text-gray-500">{tenantName}</p>
          </div>
        </div>
        <p className="text-sm text-gray-600 mb-4">
          This will remove custom rate limits and revert to the plan defaults.
        </p>
        {error && (
          <div className="mb-4 p-3 bg-red-50 rounded-lg ring-1 ring-red-200 text-sm text-red-700">{error}</div>
        )}
        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 text-sm font-semibold text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleReset}
            disabled={loading}
            className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-sm font-bold rounded-lg disabled:opacity-50 transition-colors"
          >
            {loading ? 'Resetting...' : 'Reset to Defaults'}
          </button>
        </div>
      </div>
    </div>
  )
}

/* ── Main RateLimitsPage ───────────────────────────────── */
export default function RateLimitsPage() {
  // Data
  const [tenants, setTenants] = useState([])
  const [selectedTenantId, setSelectedTenantId] = useState('')
  const [rateLimit, setRateLimit] = useState(null)
  const [loadingTenants, setLoadingTenants] = useState(true)
  const [loadingRateLimit, setLoadingRateLimit] = useState(false)
  const [error, setError] = useState('')
  const [toast, setToast] = useState(null)

  // Edit mode
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({ requests_per_minute: 60, llm_concurrent_max: 2 })
  const [saving, setSaving] = useState(false)

  // Reset modal
  const [showReset, setShowReset] = useState(false)

  /* ── Fetch tenants ──────────────────────────────────── */
  const fetchTenants = useCallback(async () => {
    setLoadingTenants(true)
    setError('')
    try {
      const data = await getAdminTenants({ per_page: 200 })
      setTenants(data.tenants || data.items || data || [])
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load tenants')
    } finally {
      setLoadingTenants(false)
    }
  }, [])

  useEffect(() => {
    fetchTenants()
  }, [fetchTenants])

  /* ── Fetch rate limit for selected tenant ───────────── */
  const fetchRateLimit = useCallback(async () => {
    if (!selectedTenantId) {
      setRateLimit(null)
      return
    }
    setLoadingRateLimit(true)
    setError('')
    setEditing(false)
    try {
      const data = await getTenantRateLimit(Number(selectedTenantId))
      setRateLimit(data)
      if (data) {
        setForm({
          requests_per_minute: data.requests_per_minute ?? DEFAULT_LIMITS.requests_per_minute,
          llm_concurrent_max: data.llm_concurrent_max ?? DEFAULT_LIMITS.llm_concurrent_max,
        })
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load rate limits')
    } finally {
      setLoadingRateLimit(false)
    }
  }, [selectedTenantId])

  useEffect(() => {
    fetchRateLimit()
  }, [fetchRateLimit])

  /* ── Get tenant info ────────────────────────────────── */
  const selectedTenant = tenants.find(t => t.id === Number(selectedTenantId))
  const isCustom = rateLimit?.configured === true

  /* ── Save handler ───────────────────────────────────── */
  const handleSave = async () => {
    setSaving(true)
    try {
      await updateTenantRateLimit(Number(selectedTenantId), form)
      setEditing(false)
      setToast({ message: 'Rate limits updated successfully.', type: 'success' })
      fetchRateLimit()
    } catch (err) {
      setToast({ message: err.response?.data?.detail || 'Failed to update rate limits', type: 'error' })
    } finally {
      setSaving(false)
    }
  }

  /* ── Reset handler ──────────────────────────────────── */
  const handleReset = async () => {
    try {
      await deleteTenantRateLimit(Number(selectedTenantId))
      setToast({ message: 'Rate limits reset to defaults.', type: 'success' })
      fetchRateLimit()
    } catch (err) {
      setToast({ message: err.response?.data?.detail || 'Failed to reset rate limits', type: 'error' })
    }
  }

  /* ── Loading skeletons ──────────────────────────────── */
  if (loadingTenants) {
    return (
      <div className="space-y-5">
        <div className="h-8 w-48 bg-gray-200 rounded-lg animate-pulse" />
        <div className="h-64 bg-gray-100 rounded-xl animate-pulse" />
      </div>
    )
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Rate Limits</h1>
        <p className="text-sm text-gray-500 mt-0.5">Configure rate limits per tenant</p>
      </div>

      {toast && <Toast message={toast.message} type={toast.type} onDone={() => setToast(null)} />}

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-50 rounded-xl ring-1 ring-red-200 text-sm text-red-700 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
          <button onClick={() => selectedTenantId ? fetchRateLimit() : fetchTenants()} className="ml-auto px-3 py-1 text-xs font-bold bg-red-100 hover:bg-red-200 rounded-lg transition-colors">
            Retry
          </button>
        </div>
      )}

      {/* Tenant selector */}
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <label className="block text-sm font-semibold text-gray-700 mb-2">Select Tenant</label>
        <div className="relative max-w-md">
          <select
            value={selectedTenantId}
            onChange={(e) => setSelectedTenantId(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-sm appearance-none cursor-pointer"
          >
            <option value="">Choose a tenant...</option>
            {tenants.map(t => (
              <option key={t.id} value={t.id}>{t.name} ({t.slug})</option>
            ))}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
        </div>
        {selectedTenant && (
          <div className="mt-2 text-xs text-gray-400">
            Plan: {selectedTenant.plan_display_name || selectedTenant.plan_name || '—'} · Status: {selectedTenant.subscription_status}
          </div>
        )}
      </div>

      {/* Rate limit configuration */}
      {selectedTenantId && (
        <>
          {loadingRateLimit ? (
            <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4 animate-pulse">
              <div className="h-6 w-48 bg-gray-200 rounded-lg" />
              <div className="grid grid-cols-2 gap-6">
                <div className="h-20 bg-gray-100 rounded-lg" />
                <div className="h-20 bg-gray-100 rounded-lg" />
              </div>
            </div>
          ) : rateLimit ? (
            <div className="space-y-4">
              {/* Current limits card */}
              <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Gauge className="w-4 h-4 text-gray-500" />
                    <h3 className="text-sm font-bold text-gray-900">Current Limits</h3>
                    {isCustom ? (
                      <span className="px-2 py-0.5 rounded-full text-xs font-bold ring-1 bg-teal-50 text-teal-700 ring-teal-200">Custom</span>
                    ) : (
                      <span className="px-2 py-0.5 rounded-full text-xs font-bold ring-1 bg-gray-100 text-gray-600 ring-gray-200">Plan Default</span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {isCustom && !editing && (
                      <button
                        onClick={() => setShowReset(true)}
                        className="px-3 py-1.5 border border-amber-300 text-amber-700 text-xs font-semibold rounded-lg hover:bg-amber-50 transition-colors flex items-center gap-1"
                      >
                        <RotateCcw className="w-3 h-3" /> Reset to Default
                      </button>
                    )}
                    {!editing ? (
                      <button
                        onClick={() => setEditing(true)}
                        className="px-3 py-1.5 bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold rounded-lg transition-colors flex items-center gap-1"
                      >
                        <Edit3 className="w-3 h-3" /> Edit
                      </button>
                    ) : (
                      <>
                        <button
                          onClick={() => { setEditing(false); fetchRateLimit() }}
                          className="px-3 py-1.5 border border-gray-300 text-gray-700 text-xs font-semibold rounded-lg hover:bg-gray-50 transition-colors flex items-center gap-1"
                        >
                          <X className="w-3 h-3" /> Cancel
                        </button>
                        <button
                          onClick={handleSave}
                          disabled={saving}
                          className="px-3 py-1.5 bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold rounded-lg disabled:opacity-50 transition-colors flex items-center gap-1"
                        >
                          {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
                          {saving ? 'Saving...' : 'Save'}
                        </button>
                      </>
                    )}
                  </div>
                </div>

                <div className="p-6">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                    <LimitField
                      label="Requests per Minute"
                      value={rateLimit.requests_per_minute}
                      editValue={form.requests_per_minute}
                      editing={editing}
                      onChange={(v) => setForm(prev => ({ ...prev, requests_per_minute: v }))}
                      unit="req/min"
                    />
                    <LimitField
                      label="LLM Concurrency Limit"
                      value={rateLimit.llm_concurrent_max}
                      editValue={form.llm_concurrent_max}
                      editing={editing}
                      onChange={(v) => setForm(prev => ({ ...prev, llm_concurrent_max: v }))}
                      unit="concurrent"
                    />
                  </div>

                  {rateLimit.updated_at && (
                    <p className="text-xs text-gray-400 mt-4">
                      Last updated: {new Date(rateLimit.updated_at).toLocaleString()}
                    </p>
                  )}
                </div>
              </div>

              {/* Default limits info card */}
              <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                <div className="px-4 py-3 border-b border-gray-200">
                  <h3 className="text-sm font-bold text-gray-900">Plan Default Limits</h3>
                </div>
                <div className="p-4">
                  <p className="text-xs text-gray-500 mb-3">
                    These are the default rate limits applied when no custom override is configured.
                  </p>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <p className="text-xs text-gray-500">Requests per Minute</p>
                      <p className="text-lg font-bold text-gray-700 mt-0.5">{DEFAULT_LIMITS.requests_per_minute}</p>
                    </div>
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <p className="text-xs text-gray-500">LLM Concurrency</p>
                      <p className="text-lg font-bold text-gray-700 mt-0.5">{DEFAULT_LIMITS.llm_concurrent_max}</p>
                    </div>
                  </div>

                  {/* Comparison when custom */}
                  {isCustom && (
                    <div className="mt-3 p-3 bg-teal-50 rounded-lg ring-1 ring-teal-200">
                      <p className="text-xs text-teal-700 font-semibold">Custom vs Default</p>
                      <div className="mt-2 space-y-1 text-xs">
                        <div className="flex justify-between">
                          <span className="text-gray-600">Requests/min:</span>
                          <span>
                            <span className="font-semibold text-teal-700">{rateLimit.requests_per_minute}</span>
                            <span className="text-gray-400"> vs </span>
                            <span className="text-gray-500">{DEFAULT_LIMITS.requests_per_minute}</span>
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600">LLM Concurrent:</span>
                          <span>
                            <span className="font-semibold text-teal-700">{rateLimit.llm_concurrent_max}</span>
                            <span className="text-gray-400"> vs </span>
                            <span className="text-gray-500">{DEFAULT_LIMITS.llm_concurrent_max}</span>
                          </span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
              <Gauge className="w-10 h-10 text-gray-300 mx-auto mb-2" />
              <p className="text-sm text-gray-500">No rate limit data available for this tenant.</p>
            </div>
          )}
        </>
      )}

      {/* No tenant selected */}
      {!selectedTenantId && !loadingTenants && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <Gauge className="w-10 h-10 text-gray-300 mx-auto mb-2" />
          <p className="text-sm text-gray-500">Select a tenant above to view rate limits.</p>
        </div>
      )}

      {/* Reset modal */}
      {showReset && (
        <ResetModal
          tenantName={selectedTenant?.name || `Tenant #${selectedTenantId}`}
          onClose={() => setShowReset(false)}
          onDone={handleReset}
        />
      )}
    </div>
  )
}
