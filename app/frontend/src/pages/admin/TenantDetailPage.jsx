import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  ArrowLeft,
  Loader2,
  AlertTriangle,
  X,
  Plus,
  Trash2,
  CreditCard,
  Ban,
  PlayCircle,
  SlidersHorizontal,
  Users,
  Activity,
  Settings,
  BarChart3,
  Shield,
  Check,
  UserPlus,
  HeartPulse,
  MessageSquare,
} from 'lucide-react'
import {
  getAdminTenantDetail,
  getAdminTenantUsageHistory,
  suspendTenant,
  reactivateTenant,
  adminChangeTenantPlan,
  adminAdjustUsage,
  getAvailablePlans,
  addUserToTenant,
  removeUserFromTenant,
  getTenantFeatureOverrides,
  setTenantFeatureOverride,
  deleteTenantFeatureOverride,
  getTenantRateLimit,
  updateTenantRateLimit,
  getTenantCrmHealth,
  getTenantCrmNotes,
  addTenantCrmNote,
  getTenantCrmNps,
} from '../../lib/api'

/* ── Constants ────────────────────────────────────────── */
const DETAIL_TABS = [
  { id: 'overview', label: 'Overview', icon: BarChart3 },
  { id: 'users', label: 'Users', icon: Users },
  { id: 'usage', label: 'Usage', icon: Activity },
  { id: 'crm', label: 'CRM', icon: HeartPulse },
  { id: 'config', label: 'Config', icon: Settings },
]

/* ── Status Badge ─────────────────────────────────────── */
function StatusBadge({ status }) {
  const styles = {
    active: 'bg-green-50 text-green-700 ring-green-200',
    suspended: 'bg-red-50 text-red-700 ring-red-200',
    trialing: 'bg-yellow-50 text-yellow-700 ring-yellow-200',
    cancelled: 'bg-gray-100 text-gray-600 ring-gray-200',
  }
  return (
    <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ring-1 ${styles[status] || styles.cancelled}`}>
      {status}
    </span>
  )
}

/* ── Plan Badge ────────────────────────────────────────── */
function PlanBadge({ name }) {
  return (
    <span className="px-2 py-0.5 rounded-md text-xs font-semibold bg-teal-50 text-teal-700 ring-1 ring-teal-200">
      {name || 'None'}
    </span>
  )
}

/* ── Format bytes ──────────────────────────────────────── */
function formatBytes(bytes) {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

/* ── Add User Modal ───────────────────────────────────── */
function AddUserModal({ onClose, onAdded }) {
  const { id: tenantId } = useParams()
  const [email, setEmail] = useState('')
  const [role, setRole] = useState('recruiter')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!email.trim()) return
    setLoading(true)
    setError('')
    try {
      await addUserToTenant(tenantId, { email: email.trim(), role })
      onAdded()
      onClose()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to add user')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl ring-1 ring-gray-200 shadow-xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-lg font-bold text-gray-900">Add User</h3>
          <button onClick={onClose} aria-label="Close dialog" className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>
        {error && (
          <div className="mb-4 p-3 bg-red-50 rounded-lg ring-1 ring-red-200 text-sm text-red-700">{error}</div>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">Email *</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              placeholder="user@company.com"
              className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-sm"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">Role</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-sm"
            >
              <option value="admin">Admin</option>
              <option value="recruiter">Recruiter</option>
              <option value="viewer">Viewer</option>
            </select>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 text-sm font-semibold text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !email.trim()}
              className="px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-sm font-bold rounded-lg disabled:opacity-50 transition-colors"
            >
              {loading ? 'Adding...' : 'Add User'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

/* ── Change Plan Modal ─────────────────────────────────── */
function ChangePlanModal({ tenant, plans, onClose, onChanged }) {
  const [selectedPlan, setSelectedPlan] = useState(tenant.plan_id || '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async () => {
    if (!selectedPlan) return
    setLoading(true)
    setError('')
    try {
      await adminChangeTenantPlan(tenant.id, parseInt(selectedPlan, 10))
      onChanged()
      onClose()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to change plan')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl ring-1 ring-gray-200 shadow-xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-lg font-bold text-gray-900">Change Plan</h3>
          <button onClick={onClose} aria-label="Close dialog" className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>
        <p className="text-sm text-gray-600 mb-4">
          Change plan for <span className="font-semibold text-gray-800">{tenant.name}</span>
        </p>
        {error && (
          <div className="mb-4 p-3 bg-red-50 rounded-lg ring-1 ring-red-200 text-sm text-red-700">{error}</div>
        )}
        <div className="space-y-2 mb-6">
          {plans.map(plan => (
            <label
              key={plan.id}
              className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
                parseInt(selectedPlan, 10) === plan.id
                  ? 'bg-teal-50 border-teal-300'
                  : 'bg-white border-gray-200 hover:bg-gray-50'
              }`}
            >
              <input
                type="radio"
                name="plan"
                value={plan.id}
                checked={parseInt(selectedPlan, 10) === plan.id}
                onChange={(e) => setSelectedPlan(e.target.value)}
                className="w-4 h-4 text-teal-600"
              />
              <div className="flex-1">
                <p className="text-sm font-semibold text-gray-800">{plan.display_name || plan.name}</p>
                {plan.price_monthly != null && (
                  <p className="text-xs text-gray-500">${(plan.price_monthly / 100).toFixed(0)}/mo</p>
                )}
              </div>
            </label>
          ))}
        </div>
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 border border-gray-300 text-sm font-semibold text-gray-700 rounded-lg hover:bg-gray-50 transition-colors">
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading || !selectedPlan}
            className="px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-sm font-bold rounded-lg disabled:opacity-50 transition-colors"
          >
            {loading ? 'Changing...' : 'Change Plan'}
          </button>
        </div>
      </div>
    </div>
  )
}

/* ── Suspend Modal ─────────────────────────────────────── */
function SuspendModal({ tenantId, tenantName, onClose, onDone }) {
  const [reason, setReason] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async () => {
    if (!reason.trim()) return
    setLoading(true)
    setError('')
    try {
      await suspendTenant(tenantId, reason.trim())
      onDone()
      onClose()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to suspend tenant')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl ring-1 ring-red-100 shadow-xl w-full max-w-md p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-lg bg-red-50 flex items-center justify-center">
            <AlertTriangle className="w-5 h-5 text-red-600" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-gray-900">Suspend Tenant</h3>
            <p className="text-sm text-gray-500">{tenantName}</p>
          </div>
        </div>
        {error && (
          <div className="mb-4 p-3 bg-red-50 rounded-lg ring-1 ring-red-200 text-sm text-red-700">{error}</div>
        )}
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">Reason *</label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Enter suspension reason..."
              rows={3}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 text-sm resize-none"
            />
          </div>
          <div className="flex justify-end gap-2">
            <button onClick={onClose} className="px-4 py-2 border border-gray-300 text-sm font-semibold text-gray-700 rounded-lg hover:bg-gray-50 transition-colors">
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={loading || !reason.trim()}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-bold rounded-lg disabled:opacity-50 transition-colors"
            >
              {loading ? 'Suspending...' : 'Suspend'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

/* ── Adjust Usage Modal ────────────────────────────────── */
function AdjustUsageModal({ detail, onClose, onDone }) {
  const [form, setForm] = useState({ analyses_count: '', storage_used_bytes: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async () => {
    setSaving(true)
    setError('')
    try {
      const payload = {}
      if (form.analyses_count) payload.analyses_count = parseInt(form.analyses_count, 10)
      if (form.storage_used_bytes) payload.storage_used_bytes = parseInt(form.storage_used_bytes, 10)
      await adminAdjustUsage(detail.id, payload)
      onDone()
      onClose()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to adjust usage')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl ring-1 ring-gray-200 shadow-xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-lg font-bold text-gray-900">Adjust Usage</h3>
          <button onClick={onClose} aria-label="Close dialog" className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>
        {error && (
          <div className="mb-4 p-3 bg-red-50 rounded-lg ring-1 ring-red-200 text-sm text-red-700">{error}</div>
        )}
        <div className="space-y-4 mb-6">
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">Analyses Count</label>
            <input
              type="number"
              value={form.analyses_count}
              onChange={(e) => setForm({ ...form, analyses_count: e.target.value })}
              placeholder={String(detail.analyses_count_this_month ?? 0)}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-sm"
            />
            <p className="text-xs text-gray-400 mt-1">Current: {detail.analyses_count_this_month ?? 0}</p>
          </div>
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">Storage Used (bytes)</label>
            <input
              type="number"
              value={form.storage_used_bytes}
              onChange={(e) => setForm({ ...form, storage_used_bytes: e.target.value })}
              placeholder={String(detail.storage_used_bytes ?? 0)}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-sm"
            />
            <p className="text-xs text-gray-400 mt-1">Current: {formatBytes(detail.storage_used_bytes)}</p>
          </div>
        </div>
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 border border-gray-300 text-sm font-semibold text-gray-700 rounded-lg hover:bg-gray-50 transition-colors">
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={saving || (!form.analyses_count && !form.storage_used_bytes)}
            className="px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-sm font-bold rounded-lg disabled:opacity-50 transition-colors"
          >
            {saving ? 'Saving...' : 'Adjust Usage'}
          </button>
        </div>
      </div>
    </div>
  )
}

/* ── Main TenantDetailPage ─────────────────────────────── */
export default function TenantDetailPage() {
  const { id: tenantId } = useParams()
  const navigate = useNavigate()

  // Core data
  const [detail, setDetail] = useState(null)
  const [usageHistory, setUsageHistory] = useState([])
  const [featureOverrides, setFeatureOverrides] = useState(null)
  const [rateLimit, setRateLimit] = useState(null)
  const [plans, setPlans] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Active tab
  const [activeTab, setActiveTab] = useState('overview')

  // Modals
  const [showAddUser, setShowAddUser] = useState(false)
  const [showChangePlan, setShowChangePlan] = useState(false)
  const [showSuspend, setShowSuspend] = useState(false)
  const [showAdjustUsage, setShowAdjustUsage] = useState(false)

  // Rate limit edit
  const [editRateLimit, setEditRateLimit] = useState(false)
  const [rateLimitForm, setRateLimitForm] = useState({ requests_per_minute: 60, llm_concurrent_max: 2 })
  const [rateLimitSaving, setRateLimitSaving] = useState(false)

  // CRM tab
  const [crmHealth, setCrmHealth] = useState(null)
  const [crmNotes, setCrmNotes] = useState([])
  const [crmNps, setCrmNps] = useState(null)
  const [crmLoading, setCrmLoading] = useState(false)
  const [noteBody, setNoteBody] = useState('')
  const [noteSaving, setNoteSaving] = useState(false)

  /* ── Fetch detail ───────────────────────────────────── */
  const fetchDetail = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await getAdminTenantDetail(tenantId)
      setDetail(data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load tenant')
    } finally {
      setLoading(false)
    }
  }, [tenantId])

  const fetchUsageHistory = useCallback(async () => {
    try {
      const data = await getAdminTenantUsageHistory(tenantId)
      setUsageHistory(Array.isArray(data) ? data : data.items || [])
    } catch {
      setUsageHistory([])
    }
  }, [tenantId])

  const fetchFeatureOverrides = useCallback(async () => {
    try {
      const data = await getTenantFeatureOverrides(tenantId)
      setFeatureOverrides(data)
    } catch {
      setFeatureOverrides(null)
    }
  }, [tenantId])

  const fetchRateLimit = useCallback(async () => {
    try {
      const data = await getTenantRateLimit(tenantId)
      setRateLimit(data)
      if (data) {
        setRateLimitForm({
          requests_per_minute: data.requests_per_minute ?? 60,
          llm_concurrent_max: data.llm_concurrent_max ?? 2,
        })
      }
    } catch {
      setRateLimit(null)
    }
  }, [tenantId])

  const fetchCrmData = useCallback(async () => {
    setCrmLoading(true)
    try {
      const [health, notes, nps] = await Promise.all([
        getTenantCrmHealth(tenantId),
        getTenantCrmNotes(tenantId),
        getTenantCrmNps(tenantId),
      ])
      setCrmHealth(health)
      setCrmNotes(notes.notes || [])
      setCrmNps(nps)
    } catch {
      setCrmHealth(null)
      setCrmNotes([])
      setCrmNps(null)
    } finally {
      setCrmLoading(false)
    }
  }, [tenantId])

  const fetchPlans = useCallback(async () => {
    try {
      const data = await getAvailablePlans()
      setPlans(data.plans || data)
    } catch {
      setPlans([])
    }
  }, [])

  useEffect(() => {
    fetchDetail()
  }, [fetchDetail])

  useEffect(() => {
    fetchPlans()
  }, [fetchPlans])

  // Lazy-load tab data
  useEffect(() => {
    if (activeTab === 'usage') fetchUsageHistory()
    if (activeTab === 'config') {
      fetchFeatureOverrides()
      fetchRateLimit()
    }
    if (activeTab === 'crm') fetchCrmData()
  }, [activeTab, fetchUsageHistory, fetchFeatureOverrides, fetchRateLimit, fetchCrmData])

  const handleReactivate = async () => {
    try {
      await reactivateTenant(tenantId)
      fetchDetail()
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to reactivate')
    }
  }

  const handleRemoveUser = async (userId) => {
    if (!confirm('Remove this user from the tenant?')) return
    try {
      await removeUserFromTenant(tenantId, userId)
      fetchDetail()
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to remove user')
    }
  }

  const handleToggleFeature = async (flagId, enabled) => {
    try {
      if (enabled === null || enabled === undefined) {
        // Override was deleted, setting new value
        await setTenantFeatureOverride(tenantId, flagId, true)
      } else {
        // Toggle
        await deleteTenantFeatureOverride(tenantId, flagId)
      }
      fetchFeatureOverrides()
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to toggle feature')
    }
  }

  const handleSaveRateLimit = async () => {
    setRateLimitSaving(true)
    try {
      await updateTenantRateLimit(tenantId, rateLimitForm)
      setEditRateLimit(false)
      fetchRateLimit()
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to update rate limit')
    } finally {
      setRateLimitSaving(false)
    }
  }

  /* ── Render ─────────────────────────────────────────── */
  if (loading) {
    return (
      <div className="flex justify-center py-24">
        <Loader2 className="w-8 h-8 animate-spin text-teal-600" />
      </div>
    )
  }

  if (error && !detail) {
    return (
      <div className="flex flex-col items-center justify-center py-24">
        <AlertTriangle className="w-10 h-10 text-red-400 mb-3" />
        <p className="text-red-600 font-medium">{error}</p>
        <button onClick={() => navigate('/admin/tenants')} className="mt-4 text-teal-600 hover:text-teal-700 text-sm font-medium">
          Back to Tenants
        </button>
      </div>
    )
  }

  if (!detail) return null

  return (
    <div className="space-y-6">
      {/* Back link */}
      <Link
        to="/admin/tenants"
        className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-teal-600 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Tenants
      </Link>

      {/* Header */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-gray-900">{detail.name}</h1>
              <StatusBadge status={detail.subscription_status} />
              <PlanBadge name={detail.plan_display_name || detail.plan_name} />
            </div>
            <p className="text-sm text-gray-400 font-mono mt-1">{detail.slug}</p>
            {detail.contact_email && (
              <p className="text-sm text-gray-500 mt-1">{detail.contact_email}</p>
            )}
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {detail.subscription_status === 'suspended' ? (
              <button
                onClick={handleReactivate}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white text-sm font-semibold rounded-lg transition-colors"
              >
                <PlayCircle className="w-4 h-4" /> Reactivate
              </button>
            ) : (
              <button
                onClick={() => setShowSuspend(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-sm font-semibold rounded-lg transition-colors"
              >
                <Ban className="w-4 h-4" /> Suspend
              </button>
            )}
            <button
              onClick={() => setShowChangePlan(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-gray-300 text-gray-700 text-sm font-semibold rounded-lg hover:bg-gray-50 transition-colors"
            >
              <CreditCard className="w-4 h-4" /> Change Plan
            </button>
            <button
              onClick={() => setShowAdjustUsage(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-gray-300 text-gray-700 text-sm font-semibold rounded-lg hover:bg-gray-50 transition-colors"
            >
              <SlidersHorizontal className="w-4 h-4" /> Adjust Usage
            </button>
          </div>
        </div>
        {detail.suspended_reason && (
          <div className="mt-4 p-3 bg-red-50 rounded-lg ring-1 ring-red-200">
            <p className="text-xs font-medium text-red-500">Suspension Reason</p>
            <p className="text-sm text-red-700 mt-0.5">{detail.suspended_reason}</p>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <div className="flex gap-0">
          {DETAIL_TABS.map(tab => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-semibold border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-teal-600 text-teal-700'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            )
          })}
        </div>
      </div>

      {/* ── Overview Tab ──────────────────────────────── */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Stats grid */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-xs text-gray-500 font-medium">Plan</p>
              <p className="text-lg font-bold text-gray-900 mt-1">{detail.plan_display_name || detail.plan_name || 'None'}</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-xs text-gray-500 font-medium">Analyses This Month</p>
              <p className="text-lg font-bold text-gray-900 mt-1">{detail.analyses_count_this_month ?? 0}</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-xs text-gray-500 font-medium">Storage Used</p>
              <p className="text-lg font-bold text-gray-900 mt-1">{formatBytes(detail.storage_used_bytes)}</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-xs text-gray-500 font-medium">Users</p>
              <p className="text-lg font-bold text-gray-900 mt-1">{detail.users?.length ?? 0}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-xs text-gray-500 font-medium">Contact Email</p>
              <p className="text-sm font-semibold text-gray-900 mt-1">{detail.contact_email || '—'}</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-xs text-gray-500 font-medium">Created</p>
              <p className="text-sm font-semibold text-gray-900 mt-1">
                {detail.created_at ? new Date(detail.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' }) : '—'}
              </p>
            </div>
          </div>

          {detail.suspended_at && (
            <div className="bg-white rounded-xl border border-red-200 p-4">
              <p className="text-xs text-red-500 font-medium">Suspended At</p>
              <p className="text-sm font-semibold text-red-700 mt-1">{new Date(detail.suspended_at).toLocaleDateString()}</p>
            </div>
          )}
        </div>
      )}

      {/* ── Users Tab ─────────────────────────────────── */}
      {activeTab === 'users' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-gray-900">Users</h2>
            <button
              onClick={() => setShowAddUser(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-teal-600 hover:bg-teal-700 text-white text-sm font-bold rounded-lg transition-colors"
            >
              <UserPlus className="w-4 h-4" /> Add User
            </button>
          </div>

          {detail.users && detail.users.length > 0 ? (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200">
                    <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Email</th>
                    <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Role</th>
                    <th scope="col" className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Status</th>
                    <th scope="col" className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {detail.users.map(user => (
                    <tr key={user.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 text-sm text-gray-900 font-medium">{user.email}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded-md text-xs font-semibold ring-1 ${
                          user.role === 'admin'
                            ? 'bg-purple-50 text-purple-700 ring-purple-200'
                            : user.role === 'recruiter'
                            ? 'bg-blue-50 text-blue-700 ring-blue-200'
                            : 'bg-gray-50 text-gray-600 ring-gray-200'
                        }`}>
                          {user.role}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-bold ring-1 ${
                          user.is_active !== false
                            ? 'bg-green-50 text-green-700 ring-green-200'
                            : 'bg-gray-100 text-gray-600 ring-gray-200'
                        }`}>
                          {user.is_active !== false ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => handleRemoveUser(user.id)}
                          className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                          title="Remove user"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
              <Users className="w-10 h-10 text-gray-300 mx-auto mb-2" />
              <p className="text-sm text-gray-500">No users found for this tenant.</p>
            </div>
          )}
        </div>
      )}

      {/* ── Usage Tab ─────────────────────────────────── */}
      {activeTab === 'usage' && (
        <div className="space-y-6">
          {/* Usage summary cards */}
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-xs text-gray-500 font-medium">Analyses This Month</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{detail.analyses_count_this_month ?? 0}</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-xs text-gray-500 font-medium">Storage Used</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{formatBytes(detail.storage_used_bytes)}</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-xs text-gray-500 font-medium">Usage Events</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{usageHistory.length}</p>
            </div>
          </div>

          {/* Usage history table */}
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-200">
              <h3 className="text-sm font-bold text-gray-900">Usage History</h3>
            </div>
            {usageHistory.length === 0 ? (
              <div className="p-8 text-center">
                <Activity className="w-10 h-10 text-gray-300 mx-auto mb-2" />
                <p className="text-sm text-gray-500">No usage history found.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200">
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Action</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">User</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Quantity</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {usageHistory.map(log => (
                      <tr key={log.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-4 py-3 text-sm font-medium text-gray-900">{log.action}</td>
                        <td className="px-4 py-3 text-sm text-gray-500">{log.user_email || 'System'}</td>
                        <td className="px-4 py-3 text-sm font-semibold text-gray-700">{log.quantity}</td>
                        <td className="px-4 py-3 text-sm text-gray-500">
                          {log.created_at ? new Date(log.created_at).toLocaleString() : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── CRM Tab ───────────────────────────────────── */}
      {activeTab === 'crm' && (
        <div className="space-y-6">
          {crmLoading ? (
            <div className="flex justify-center py-16"><Loader2 className="w-8 h-8 animate-spin text-teal-600" /></div>
          ) : (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="bg-white rounded-xl border border-gray-200 p-5">
                  <p className="text-xs font-medium text-gray-500 uppercase">Health Score</p>
                  <p className="text-3xl font-bold text-gray-900 mt-1">{crmHealth?.health_score ?? '—'}</p>
                  <div className="mt-2 h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        (crmHealth?.health_score ?? 0) >= 70 ? 'bg-green-500' :
                        (crmHealth?.health_score ?? 0) >= 40 ? 'bg-amber-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${crmHealth?.health_score ?? 0}%` }}
                    />
                  </div>
                </div>
                <div className="bg-white rounded-xl border border-gray-200 p-5">
                  <p className="text-xs font-medium text-gray-500 uppercase">Churn Risk</p>
                  <p className={`text-xl font-bold mt-1 capitalize ${
                    crmHealth?.churn_risk === 'high' ? 'text-red-700' :
                    crmHealth?.churn_risk === 'medium' ? 'text-amber-700' : 'text-green-700'
                  }`}>{crmHealth?.churn_risk || '—'}</p>
                </div>
                <div className="bg-white rounded-xl border border-gray-200 p-5">
                  <p className="text-xs font-medium text-gray-500 uppercase">NPS</p>
                  <p className="text-3xl font-bold text-gray-900 mt-1">
                    {crmNps?.nps != null ? crmNps.nps : '—'}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    {crmNps?.count ? `${crmNps.count} responses · avg ${crmNps.average}` : 'No responses yet'}
                  </p>
                </div>
              </div>

              {crmHealth?.signals && (
                <div className="bg-white rounded-xl border border-gray-200 p-4">
                  <h3 className="text-sm font-bold text-gray-900 mb-3">Health Signals</h3>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                    {Object.entries(crmHealth.signals).map(([key, val]) => (
                      <div key={key} className="bg-gray-50 rounded-lg px-3 py-2">
                        <p className="text-xs text-gray-500">{key.replace(/_/g, ' ')}</p>
                        <p className="font-semibold text-gray-800">{String(val)}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                <div className="px-4 py-3 border-b border-gray-200 flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-gray-400" />
                  <h3 className="text-sm font-bold text-gray-900">Account Notes</h3>
                </div>
                <div className="p-4 border-b border-gray-100">
                  <textarea
                    value={noteBody}
                    onChange={(e) => setNoteBody(e.target.value)}
                    placeholder="Add a note about this account…"
                    rows={3}
                    className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:ring-2 focus:ring-teal-500"
                  />
                  <div className="flex justify-end mt-2">
                    <button
                      type="button"
                      disabled={noteSaving || !noteBody.trim()}
                      onClick={async () => {
                        setNoteSaving(true)
                        try {
                          await addTenantCrmNote(tenantId, noteBody.trim())
                          setNoteBody('')
                          fetchCrmData()
                        } catch {
                          // ignore
                        } finally {
                          setNoteSaving(false)
                        }
                      }}
                      className="px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-sm font-bold rounded-lg disabled:opacity-50"
                    >
                      {noteSaving ? 'Saving…' : 'Add Note'}
                    </button>
                  </div>
                </div>
                {crmNotes.length === 0 ? (
                  <div className="p-8 text-center text-sm text-gray-500">No notes yet.</div>
                ) : (
                  <ul className="divide-y divide-gray-100">
                    {crmNotes.map((note) => (
                      <li key={note.id} className="px-4 py-3">
                        <p className="text-sm text-gray-800">{note.body}</p>
                        <p className="text-xs text-gray-400 mt-1">
                          {note.author_email || 'System'} · {note.created_at ? new Date(note.created_at).toLocaleString() : ''}
                        </p>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {/* ── Config Tab ────────────────────────────────── */}
      {activeTab === 'config' && (
        <div className="space-y-6">
          {/* Feature Flag Overrides */}
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
              <h3 className="text-sm font-bold text-gray-900">Feature Flag Overrides</h3>
              <Shield className="w-4 h-4 text-gray-400" />
            </div>
            <div className="divide-y divide-gray-100">
              {featureOverrides && Array.isArray(featureOverrides) && featureOverrides.length > 0 ? (
                featureOverrides.map(fo => (
                  <div key={fo.flag_id || fo.id} className="flex items-center justify-between px-4 py-3">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{fo.flag_name || fo.name || `Flag ${fo.flag_id}`}</p>
                      <p className="text-xs text-gray-400">{fo.flag_key || fo.key || ''}</p>
                    </div>
                    <button
                      onClick={() => handleToggleFeature(fo.flag_id || fo.id, fo.enabled)}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                        fo.enabled ? 'bg-teal-600' : 'bg-gray-200'
                      }`}
                    >
                      <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        fo.enabled ? 'translate-x-6' : 'translate-x-1'
                      }`} />
                    </button>
                  </div>
                ))
              ) : (
                <div className="px-4 py-6 text-center">
                  <p className="text-sm text-gray-500">No feature flag overrides for this tenant.</p>
                </div>
              )}
            </div>
          </div>

          {/* Rate Limit Configuration */}
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
              <h3 className="text-sm font-bold text-gray-900">Rate Limit Configuration</h3>
              {!editRateLimit && (
                <button
                  onClick={() => setEditRateLimit(true)}
                  className="text-xs font-medium text-teal-600 hover:text-teal-700"
                >
                  Edit
                </button>
              )}
            </div>
            <div className="p-4 space-y-4">
              {rateLimit ? (
                editRateLimit ? (
                  <div className="space-y-3">
                    <div>
                      <label className="block text-xs font-semibold text-gray-600 mb-1">Requests per Minute</label>
                      <input
                        type="number"
                        value={rateLimitForm.requests_per_minute}
                        onChange={(e) => setRateLimitForm(prev => ({ ...prev, requests_per_minute: parseInt(e.target.value, 10) || 0 }))}
                        className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-gray-600 mb-1">LLM Concurrent Max</label>
                      <input
                        type="number"
                        value={rateLimitForm.llm_concurrent_max}
                        onChange={(e) => setRateLimitForm(prev => ({ ...prev, llm_concurrent_max: parseInt(e.target.value, 10) || 0 }))}
                        className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-sm"
                      />
                    </div>
                    <div className="flex justify-end gap-2 pt-1">
                      <button
                        onClick={() => setEditRateLimit(false)}
                        className="px-3 py-1.5 border border-gray-300 text-sm font-semibold text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleSaveRateLimit}
                        disabled={rateLimitSaving}
                        className="px-3 py-1.5 bg-teal-600 hover:bg-teal-700 text-white text-sm font-bold rounded-lg disabled:opacity-50 transition-colors"
                      >
                        {rateLimitSaving ? 'Saving...' : 'Save'}
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-xs text-gray-500 font-medium">Requests per Minute</p>
                      <p className="text-lg font-bold text-gray-900 mt-0.5">{rateLimit.requests_per_minute ?? '—'}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 font-medium">LLM Concurrent Max</p>
                      <p className="text-lg font-bold text-gray-900 mt-0.5">{rateLimit.llm_concurrent_max ?? '—'}</p>
                    </div>
                  </div>
                )
              ) : (
                <p className="text-sm text-gray-500">Using default rate limits. Click Edit to set custom limits.</p>
              )}
            </div>
          </div>

          {/* Scoring Weights (display only) */}
          {detail.scoring_weights && (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-200">
                <h3 className="text-sm font-bold text-gray-900">Scoring Weights</h3>
              </div>
              <div className="p-4">
                <pre className="text-xs text-gray-600 bg-gray-50 rounded-lg p-3 overflow-x-auto">
                  {JSON.stringify(detail.scoring_weights, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Modals ────────────────────────────────────── */}
      {showAddUser && (
        <AddUserModal
          onClose={() => setShowAddUser(false)}
          onAdded={fetchDetail}
        />
      )}
      {showChangePlan && (
        <ChangePlanModal
          tenant={detail}
          plans={plans}
          onClose={() => setShowChangePlan(false)}
          onChanged={fetchDetail}
        />
      )}
      {showSuspend && (
        <SuspendModal
          tenantId={tenantId}
          tenantName={detail.name}
          onClose={() => setShowSuspend(false)}
          onDone={fetchDetail}
        />
      )}
      {showAdjustUsage && (
        <AdjustUsageModal
          detail={detail}
          onClose={() => setShowAdjustUsage(false)}
          onDone={fetchDetail}
        />
      )}
    </div>
  )
}
