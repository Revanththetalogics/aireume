import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Search,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  ChevronDown,
  Loader2,
  AlertTriangle,
  X,
  Plus,
  Eye,
  CreditCard,
  Ban,
  PlayCircle,
  Trash2,
  CheckSquare,
  Square,
  Pause,
  Play,
  Send,
  Download,
  Key,
} from 'lucide-react'
import SlideOutPanel from '../../components/admin/SlideOutPanel'
import {
  getAdminTenants,
  createTenant,
  suspendTenant,
  reactivateTenant,
  deleteTenant,
  adminChangeTenantPlan,
  getAvailablePlans,
  updateTenant,
} from '../../lib/api'

/* ── Constants ────────────────────────────────────────── */
const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'active', label: 'Active' },
  { value: 'suspended', label: 'Suspended' },
  { value: 'trialing', label: 'Trialing' },
  { value: 'cancelled', label: 'Cancelled' },
]

const SORTABLE_COLUMNS = [
  { key: 'name', label: 'Name' },
  { key: 'plan_name', label: 'Plan' },
  { key: 'subscription_status', label: 'Status' },
  { key: 'user_count', label: 'Users' },
  { key: 'analyses_count_this_month', label: 'Analyses' },
  { key: 'created_at', label: 'Created' },
]

const PER_PAGE = 20

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

/* ── Relative Date ─────────────────────────────────────── */
function RelativeDate({ date }) {
  if (!date) return <span className="text-gray-400">—</span>
  const d = new Date(date)
  const now = new Date()
  const diffMs = now - d
  const diffDays = Math.floor(diffMs / 86400000)
  if (diffDays === 0) return <span className="text-gray-600">Today</span>
  if (diffDays === 1) return <span className="text-gray-600">Yesterday</span>
  if (diffDays < 30) return <span className="text-gray-600">{diffDays}d ago</span>
  if (diffDays < 365) return <span className="text-gray-600">{Math.floor(diffDays / 30)}mo ago</span>
  return <span className="text-gray-600">{Math.floor(diffDays / 365)}y ago</span>
}

/* ── Slugify helper ────────────────────────────────────── */
function slugify(text) {
  return text
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, '')
    .replace(/[\s_]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
}

/* ── Create Tenant Modal ──────────────────────────────── */
function CreateTenantModal({ plans, onClose, onCreated }) {
  const [form, setForm] = useState({ name: '', slug: '', contact_email: '', plan_id: '' })
  const [slugManual, setSlugManual] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const handleNameChange = (name) => {
    setForm(prev => ({
      ...prev,
      name,
      ...(slugManual ? {} : { slug: slugify(name) }),
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.name.trim() || !form.slug.trim()) {
      setError('Name and slug are required.')
      return
    }
    setSaving(true)
    setError('')
    try {
      await createTenant({
        name: form.name.trim(),
        slug: form.slug.trim(),
        contact_email: form.contact_email.trim() || undefined,
        plan_id: form.plan_id ? parseInt(form.plan_id, 10) : undefined,
      })
      onCreated()
      onClose()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create tenant')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl ring-1 ring-gray-200 shadow-xl w-full max-w-lg p-6">
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-lg font-bold text-gray-900">Create Tenant</h3>
          <button onClick={onClose} aria-label="Close dialog" className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 rounded-lg ring-1 ring-red-200 text-sm text-red-700">{error}</div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">Name *</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => handleNameChange(e.target.value)}
              placeholder="Acme Corp"
              className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-sm"
            />
          </div>
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-sm font-semibold text-gray-700">Slug *</label>
              <button
                type="button"
                onClick={() => setSlugManual(v => !v)}
                className="text-xs text-teal-600 hover:text-teal-700 font-medium"
              >
                {slugManual ? 'Auto-generate' : 'Edit manually'}
              </button>
            </div>
            <input
              type="text"
              value={form.slug}
              onChange={(e) => setForm(prev => ({ ...prev, slug: e.target.value }))}
              placeholder="acme-corp"
              className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-sm font-mono"
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">Contact Email</label>
            <input
              type="email"
              value={form.contact_email}
              onChange={(e) => setForm(prev => ({ ...prev, contact_email: e.target.value }))}
              autoComplete="email"
              placeholder="admin@acme.com"
              className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">Plan</label>
            <select
              value={form.plan_id}
              onChange={(e) => setForm(prev => ({ ...prev, plan_id: e.target.value }))}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-sm"
            >
              <option value="">No plan</option>
              {plans.map(p => (
                <option key={p.id} value={p.id}>{p.display_name || p.name}</option>
              ))}
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
              disabled={saving || !form.name.trim() || !form.slug.trim()}
              className="px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-sm font-bold rounded-lg disabled:opacity-50 transition-colors"
            >
              {saving ? 'Creating...' : 'Create Tenant'}
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
          <button
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 text-sm font-semibold text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
          >
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
function SuspendModal({ tenant, onClose, onDone }) {
  const [reason, setReason] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async () => {
    if (!reason.trim()) return
    setLoading(true)
    setError('')
    try {
      await suspendTenant(tenant.id, reason.trim())
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
            <p className="text-sm text-gray-500">{tenant.name}</p>
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
            <button
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 text-sm font-semibold text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
            >
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

/* ── Delete Confirmation Modal ─────────────────────────── */
function DeleteModal({ tenant, onClose, onDone }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleDelete = async () => {
    setLoading(true)
    setError('')
    try {
      await deleteTenant(tenant.id)
      onDone()
      onClose()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete tenant')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl ring-1 ring-red-100 shadow-xl w-full max-w-md p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-lg bg-red-50 flex items-center justify-center">
            <Trash2 className="w-5 h-5 text-red-600" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-gray-900">Delete Tenant</h3>
            <p className="text-sm text-gray-500">{tenant.name}</p>
          </div>
        </div>
        <p className="text-sm text-gray-600 mb-4">
          This will soft-delete the tenant. All data will be retained but the tenant will be inaccessible.
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
            onClick={handleDelete}
            disabled={loading}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-bold rounded-lg disabled:opacity-50 transition-colors"
          >
            {loading ? 'Deleting...' : 'Delete Tenant'}
          </button>
        </div>
      </div>
    </div>
  )
}

/* ── Bulk Action Confirmation Modal ────────────────────── */
function BulkActionModal({ action, tenants, onClose, onDone }) {
  const [reason, setReason] = useState('')
  const [planId, setPlanId] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [plans, setPlans] = useState([])

  useEffect(() => {
    if (action === 'change-plan') {
      getAvailablePlans().then(data => setPlans(data.plans || data)).catch(() => {})
    }
  }, [action])

  const handleSubmit = async () => {
    setLoading(true)
    setError('')
    try {
      if (action === 'suspend') {
        for (const t of tenants) {
          await suspendTenant(t.id, reason.trim() || 'Bulk suspension')
        }
      } else if (action === 'reactivate') {
        for (const t of tenants) {
          await reactivateTenant(t.id)
        }
      } else if (action === 'change-plan') {
        if (!planId) { setLoading(false); return }
        for (const t of tenants) {
          await adminChangeTenantPlan(t.id, parseInt(planId, 10))
        }
      }
      onDone()
      onClose()
    } catch (err) {
      setError(err.response?.data?.detail || 'One or more operations failed')
    } finally {
      setLoading(false)
    }
  }

  const actionLabel = action === 'suspend' ? 'Suspend' : action === 'reactivate' ? 'Reactivate' : 'Change Plan For'
  const actionColor = action === 'suspend' ? 'bg-red-600 hover:bg-red-700' : action === 'reactivate' ? 'bg-green-600 hover:bg-green-700' : 'bg-teal-600 hover:bg-teal-700'

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl ring-1 ring-gray-200 shadow-xl w-full max-w-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-gray-900">Bulk {actionLabel}</h3>
          <button onClick={onClose} aria-label="Close dialog" className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>
        <p className="text-sm text-gray-600 mb-3">
          The following {tenants.length} tenant{tenants.length !== 1 ? 's' : ''} will be affected:
        </p>
        <div className="max-h-40 overflow-y-auto mb-4 p-3 bg-gray-50 rounded-lg ring-1 ring-gray-200">
          {tenants.map(t => (
            <div key={t.id} className="py-1 text-sm text-gray-700">
              <span className="font-medium">{t.name}</span>
              <span className="text-gray-400 ml-2">{t.slug}</span>
            </div>
          ))}
        </div>
        {error && (
          <div className="mb-4 p-3 bg-red-50 rounded-lg ring-1 ring-red-200 text-sm text-red-700">{error}</div>
        )}
        {action === 'suspend' && (
          <div className="mb-4">
            <label className="block text-sm font-semibold text-gray-700 mb-1">Reason</label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Reason for bulk suspension..."
              rows={2}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-red-500 focus:border-red-500 text-sm resize-none"
            />
          </div>
        )}
        {action === 'change-plan' && (
          <div className="mb-4">
            <label className="block text-sm font-semibold text-gray-700 mb-1">New Plan</label>
            <select
              value={planId}
              onChange={(e) => setPlanId(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-sm"
            >
              <option value="">Select a plan...</option>
              {plans.map(p => (
                <option key={p.id} value={p.id}>{p.display_name || p.name}</option>
              ))}
            </select>
          </div>
        )}
        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 text-sm font-semibold text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading || (action === 'suspend' && !reason.trim()) || (action === 'change-plan' && !planId)}
            className={`px-4 py-2 text-white text-sm font-bold rounded-lg disabled:opacity-50 transition-colors ${actionColor}`}
          >
            {loading ? 'Processing...' : `${actionLabel} ${tenants.length} Tenant${tenants.length !== 1 ? 's' : ''}`}
          </button>
        </div>
      </div>
    </div>
  )
}

/* ── Tenant Slide-Out Panel ───────────────────────────── */
function TenantSlideOut({ tenant, onClose, onAction, onRefresh }) {
  const [notifyText, setNotifyText] = useState('')
  const [notifySending, setNotifySending] = useState(false)

  if (!tenant) return null

  const handleResetApiKeys = () => {
    if (!confirm('Reset all API keys for this tenant? This will invalidate existing keys immediately.')) return
    alert('API keys reset placeholder — backend endpoint needed.')
  }

  const handleExportData = () => {
    alert('Export tenant data placeholder — backend endpoint needed.')
  }

  const handleAdjustUsage = () => {
    alert('Adjust usage placeholder — backend endpoint needed.')
  }

  const handleSendNotification = () => {
    if (!notifyText.trim()) return
    setNotifySending(true)
    setTimeout(() => {
      setNotifySending(false)
      setNotifyText('')
      alert('Notification sent placeholder — backend endpoint needed.')
    }, 800)
  }

  const handleSuspendReactivate = () => {
    if (tenant.subscription_status === 'suspended') {
      reactivateTenant(tenant.id)
        .then(() => { onRefresh(); onClose() })
        .catch(err => alert(err.response?.data?.detail || 'Failed to reactivate'))
    } else {
      onAction('suspend', tenant)
      onClose()
    }
  }

  return (
    <SlideOutPanel
      isOpen={!!tenant}
      onClose={onClose}
      title={tenant.name}
    >
      <div className="p-6 space-y-6">
        <div>
          <StatusBadge status={tenant.subscription_status} />
        </div>

        <div className="border-b border-gray-200 pb-6">
          <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-4">Overview</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm text-gray-500">Plan</span>
              <span className="text-sm font-medium text-gray-900">{tenant.plan_display_name || tenant.plan_name || 'None'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-500">Status</span>
              <span className="text-sm font-medium text-gray-900 capitalize">{tenant.subscription_status}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-500">Users</span>
              <span className="text-sm font-medium text-gray-900">{tenant.user_count ?? (tenant.users?.length ?? 0)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-500">Analyses (This Month)</span>
              <span className="text-sm font-medium text-gray-900">{tenant.analyses_count_this_month ?? 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-500">Created</span>
              <span className="text-sm font-medium text-gray-900">
                {tenant.created_at ? new Date(tenant.created_at).toLocaleDateString() : '—'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-500">Contact Email</span>
              <span className="text-sm font-medium text-gray-900">{tenant.contact_email || '—'}</span>
            </div>
          </div>
        </div>

        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-3">Actions</h3>

          <button
            onClick={() => { onAction('change-plan', tenant); onClose() }}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 rounded-lg transition-colors text-left"
          >
            <CreditCard className="w-4 h-4 text-gray-400" />
            Change Plan
          </button>

          <button
            onClick={handleSuspendReactivate}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 rounded-lg transition-colors text-left"
          >
            {tenant.subscription_status === 'suspended' ? (
              <><Play className="w-4 h-4 text-gray-400" /> Reactivate</>
            ) : (
              <><Pause className="w-4 h-4 text-gray-400" /> Suspend</>
            )}
          </button>

          <button
            onClick={handleAdjustUsage}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 rounded-lg transition-colors text-left"
          >
            <Key className="w-4 h-4 text-gray-400" />
            Adjust Usage
          </button>

          <button
            onClick={handleResetApiKeys}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 rounded-lg transition-colors text-left"
          >
            <Key className="w-4 h-4 text-gray-400" />
            Reset API Keys
          </button>

          <div className="px-4 py-3 bg-gray-50 rounded-lg">
            <label className="block text-xs font-semibold text-gray-700 mb-2">Send Notification</label>
            <div className="flex gap-2">
              <input
                type="text"
                value={notifyText}
                onChange={(e) => setNotifyText(e.target.value)}
                placeholder="Enter message..."
                className="flex-1 px-3 py-1.5 rounded-lg border border-gray-300 text-sm focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
              />
              <button
                onClick={handleSendNotification}
                disabled={notifySending || !notifyText.trim()}
                className="px-3 py-1.5 bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold rounded-lg disabled:opacity-50 transition-colors"
              >
                <Send className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <button
            onClick={handleExportData}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 rounded-lg transition-colors text-left"
          >
            <Download className="w-4 h-4 text-gray-400" />
            Export Tenant Data
          </button>

          <div className="border-t border-gray-200 my-3" />

          <button
            onClick={() => { onAction('delete', tenant); onClose() }}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm font-medium text-red-600 hover:bg-red-50 rounded-lg transition-colors text-left"
          >
            <Trash2 className="w-4 h-4" />
            Delete Tenant
          </button>

          <button
            onClick={() => { onAction('view-full', tenant); onClose() }}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm font-medium text-teal-600 hover:bg-teal-50 rounded-lg transition-colors text-left"
          >
            View Full Details →
          </button>
        </div>
      </div>
    </SlideOutPanel>
  )
}

/* ── Main Tenants Page ─────────────────────────────────── */
export default function TenantsPage() {
  const navigate = useNavigate()

  // Data
  const [tenants, setTenants] = useState([])
  const [totalCount, setTotalCount] = useState(0)
  const [plans, setPlans] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Filters
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [planFilter, setPlanFilter] = useState('')
  const [createdAfter, setCreatedAfter] = useState('')
  const [createdBefore, setCreatedBefore] = useState('')

  // Sort & pagination
  const [sortBy, setSortBy] = useState('created_at')
  const [sortOrder, setSortOrder] = useState('desc')
  const [page, setPage] = useState(1)

  // Selection
  const [selectedIds, setSelectedIds] = useState(new Set())

  // Modals
  const [showCreate, setShowCreate] = useState(false)
  const [changePlanTenant, setChangePlanTenant] = useState(null)
  const [suspendTenantObj, setSuspendTenantObj] = useState(null)
  const [deleteTenantObj, setDeleteTenantObj] = useState(null)
  const [bulkAction, setBulkAction] = useState(null) // { action: 'suspend'|'reactivate'|'change-plan', tenants: [...] }
  const [slideOutTenant, setSlideOutTenant] = useState(null)

  /* ── Fetch tenants ──────────────────────────────────── */
  const fetchTenants = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const params = {
        page,
        per_page: PER_PAGE,
        sort_by: sortBy,
        sort_order: sortOrder,
      }
      if (search.trim()) params.search = search.trim()
      if (statusFilter) params.status = statusFilter
      if (planFilter) params.plan_id = planFilter
      if (createdAfter) params.created_after = createdAfter
      if (createdBefore) params.created_before = createdBefore
      const data = await getAdminTenants(params)
      setTenants(data.tenants || data.items || [])
      setTotalCount(data.total || 0)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load tenants')
    } finally {
      setLoading(false)
    }
  }, [page, sortBy, sortOrder, search, statusFilter, planFilter, createdAfter, createdBefore])

  const fetchPlans = useCallback(async () => {
    try {
      const data = await getAvailablePlans()
      setPlans(data.plans || data)
    } catch {
      // Plans are optional, used for dropdowns
    }
  }, [])

  useEffect(() => {
    fetchTenants()
  }, [fetchTenants])

  useEffect(() => {
    fetchPlans()
  }, [fetchPlans])

  // Reset page when filters change
  useEffect(() => {
    setPage(1)
  }, [search, statusFilter, planFilter, createdAfter, createdBefore])

  /* ── Selection logic ────────────────────────────────── */
  const allSelected = tenants.length > 0 && tenants.every(t => selectedIds.has(t.id))

  const toggleSelectAll = () => {
    if (allSelected) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(tenants.map(t => t.id)))
    }
  }

  const toggleSelect = (id) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const selectedTenants = tenants.filter(t => selectedIds.has(t.id))

  /* ── Sort handler ────────────────────────────────────── */
  const handleSort = (key) => {
    if (sortBy === key) {
      setSortOrder(prev => (prev === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortBy(key)
      setSortOrder('asc')
    }
    setPage(1)
  }

  /* ── Row action handler ──────────────────────────────── */
  const handleRowAction = (action, tenant) => {
    switch (action) {
      case 'view':
        setSlideOutTenant(tenant)
        break
      case 'view-full':
        navigate(`/admin/tenants/${tenant.id}`)
        break
      case 'change-plan':
        setChangePlanTenant(tenant)
        break
      case 'suspend':
        setSuspendTenantObj(tenant)
        break
      case 'reactivate':
        // Immediate reactivate
        reactivateTenant(tenant.id)
          .then(() => fetchTenants())
          .catch(err => alert(err.response?.data?.detail || 'Failed to reactivate'))
        break
      case 'delete':
        setDeleteTenantObj(tenant)
        break
    }
  }

  /* ── Bulk action handler ─────────────────────────────── */
  const handleBulkAction = (action) => {
    setBulkAction({ action, tenants: selectedTenants })
  }

  /* ── Pagination math ─────────────────────────────────── */
  const totalPages = Math.max(1, Math.ceil(totalCount / PER_PAGE))

  /* ── Search debounce ─────────────────────────────────── */
  const handleSearchSubmit = (e) => {
    e.preventDefault()
    setSearch(searchInput)
    setPage(1)
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Tenants</h1>
          <p className="text-sm text-gray-500 mt-0.5">Manage tenant organizations and subscriptions</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-sm font-bold rounded-lg transition-colors"
        >
          <Plus className="w-4 h-4" />
          Create Tenant
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <div className="flex flex-wrap items-end gap-3">
          {/* Search */}
          <form onSubmit={handleSearchSubmit} className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Search by name or slug..."
                className="w-full pl-10 pr-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-sm"
              />
            </div>
          </form>

          {/* Status */}
          <div className="min-w-[140px]">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-sm"
            >
              {STATUS_OPTIONS.map(o => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          {/* Plan */}
          <div className="min-w-[140px]">
            <select
              value={planFilter}
              onChange={(e) => setPlanFilter(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-sm"
            >
              <option value="">All Plans</option>
              {plans.map(p => (
                <option key={p.id} value={p.id}>{p.display_name || p.name}</option>
              ))}
            </select>
          </div>

          {/* Date after */}
          <div>
            <input
              type="date"
              value={createdAfter}
              onChange={(e) => setCreatedAfter(e.target.value)}
              placeholder="Created after"
              className="px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-sm"
              title="Created after"
            />
          </div>

          {/* Date before */}
          <div>
            <input
              type="date"
              value={createdBefore}
              onChange={(e) => setCreatedBefore(e.target.value)}
              className="px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-sm"
              title="Created before"
            />
          </div>

          {/* Clear filters */}
          {(search || statusFilter || planFilter || createdAfter || createdBefore) && (
            <button
              onClick={() => {
                setSearch('')
                setSearchInput('')
                setStatusFilter('')
                setPlanFilter('')
                setCreatedAfter('')
                setCreatedBefore('')
                setPage(1)
              }}
              className="px-3 py-2 text-sm font-medium text-teal-600 hover:text-teal-700 transition-colors"
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      {/* Bulk Action Bar */}
      {selectedIds.size > 0 && (
        <div className="bg-teal-50 border border-teal-200 rounded-xl px-4 py-3 flex items-center justify-between">
          <span className="text-sm font-semibold text-teal-800">
            {selectedIds.size} selected
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleBulkAction('suspend')}
              className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-xs font-bold rounded-lg transition-colors"
            >
              Suspend Selected
            </button>
            <button
              onClick={() => handleBulkAction('reactivate')}
              className="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white text-xs font-bold rounded-lg transition-colors"
            >
              Reactivate Selected
            </button>
            <button
              onClick={() => handleBulkAction('change-plan')}
              className="px-3 py-1.5 bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold rounded-lg transition-colors"
            >
              Change Plan
            </button>
            <button
              onClick={() => setSelectedIds(new Set())}
              className="px-3 py-1.5 border border-gray-300 text-gray-600 text-xs font-semibold rounded-lg hover:bg-gray-50 transition-colors"
            >
              Deselect
            </button>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-50 rounded-xl ring-1 ring-red-200 text-sm text-red-700">{error}</div>
      )}

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="w-8 h-8 animate-spin text-teal-600" />
          </div>
        ) : tenants.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-gray-400">
            <svg viewBox="0 0 20 20" fill="currentColor" className="w-12 h-12 mb-3 text-gray-300">
              <path fillRule="evenodd" d="M4 4a2 2 0 012-2h8a2 2 0 012 2v12a1 1 0 110 2H4a1 1 0 110-2V4zm3 1h2v2H7V5zm2 4H7v2h2V9zm2-4h2v2h-2V5zm2 4h-2v2h2V9z" clipRule="evenodd"/>
            </svg>
            <p className="text-sm font-medium">No tenants found</p>
            <p className="text-xs mt-1">Try adjusting your filters or create a new tenant</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="px-4 py-3 w-10">
                    <button onClick={toggleSelectAll} className="text-gray-400 hover:text-teal-600 transition-colors">
                      {allSelected ? <CheckSquare className="w-4 h-4 text-teal-600" /> : <Square className="w-4 h-4" />}
                    </button>
                  </th>
                  {SORTABLE_COLUMNS.map(col => (
                    <th
                      key={col.key}
                      className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-700 select-none"
                      onClick={() => handleSort(col.key)}
                    >
                      <div className="flex items-center gap-1">
                        {col.label}
                        {sortBy === col.key && (
                          sortOrder === 'asc'
                            ? <ChevronUp className="w-3.5 h-3.5" />
                            : <ChevronDown className="w-3.5 h-3.5" />
                        )}
                      </div>
                    </th>
                  ))}
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {tenants.map(tenant => (
                  <tr
                    key={tenant.id}
                    className={`hover:bg-gray-50 transition-colors ${selectedIds.has(tenant.id) ? 'bg-teal-50/50' : ''}`}
                  >
                    <td className="px-4 py-3">
                      <button onClick={() => toggleSelect(tenant.id)} className="text-gray-400 hover:text-teal-600 transition-colors">
                        {selectedIds.has(tenant.id)
                          ? <CheckSquare className="w-4 h-4 text-teal-600" />
                          : <Square className="w-4 h-4" />
                        }
                      </button>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => setSlideOutTenant(tenant)}
                        className="text-left hover:text-teal-600 transition-colors"
                      >
                        <p className="text-sm font-semibold text-gray-900">{tenant.name}</p>
                        <p className="text-xs text-gray-400 font-mono">{tenant.slug}</p>
                      </button>
                    </td>
                    <td className="px-4 py-3">
                      <PlanBadge name={tenant.plan_display_name || tenant.plan_name} />
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={tenant.subscription_status} />
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {tenant.user_count ?? (tenant.users?.length ?? 0)}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {tenant.analyses_count_this_month ?? 0}
                    </td>
                    <td className="px-4 py-3">
                      <RelativeDate date={tenant.created_at} />
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => setSlideOutTenant(tenant)}
                          className="p-1.5 text-gray-400 hover:text-teal-600 transition-colors"
                          title="View"
                        >
                          <Eye className="w-5 h-5" />
                        </button>
                        {tenant.subscription_status === 'suspended' ? (
                          <button
                            onClick={() => handleRowAction('reactivate', tenant)}
                            className="p-1.5 text-gray-400 hover:text-teal-600 transition-colors"
                            title="Reactivate"
                          >
                            <Play className="w-5 h-5" />
                          </button>
                        ) : (
                          <button
                            onClick={() => handleRowAction('suspend', tenant)}
                            className="p-1.5 text-gray-400 hover:text-teal-600 transition-colors"
                            title="Suspend"
                          >
                            <Pause className="w-5 h-5" />
                          </button>
                        )}
                        <button
                          onClick={() => handleRowAction('change-plan', tenant)}
                          className="p-1.5 text-gray-400 hover:text-teal-600 transition-colors"
                          title="Change Plan"
                        >
                          <CreditCard className="w-5 h-5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {!loading && totalCount > 0 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 bg-gray-50">
            <p className="text-sm text-gray-500">
              Showing {((page - 1) * PER_PAGE) + 1}–{Math.min(page * PER_PAGE, totalCount)} of {totalCount}
            </p>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-2 rounded-lg border border-gray-300 hover:bg-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="w-4 h-4 text-gray-600" />
              </button>
              <span className="px-3 text-sm text-gray-600">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="p-2 rounded-lg border border-gray-300 hover:bg-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronRight className="w-4 h-4 text-gray-600" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Modals */}
      {showCreate && (
        <CreateTenantModal
          plans={plans}
          onClose={() => setShowCreate(false)}
          onCreated={fetchTenants}
        />
      )}
      {changePlanTenant && (
        <ChangePlanModal
          tenant={changePlanTenant}
          plans={plans}
          onClose={() => setChangePlanTenant(null)}
          onChanged={fetchTenants}
        />
      )}
      {suspendTenantObj && (
        <SuspendModal
          tenant={suspendTenantObj}
          onClose={() => setSuspendTenantObj(null)}
          onDone={fetchTenants}
        />
      )}
      {deleteTenantObj && (
        <DeleteModal
          tenant={deleteTenantObj}
          onClose={() => setDeleteTenantObj(null)}
          onDone={fetchTenants}
        />
      )}
      {bulkAction && (
        <BulkActionModal
          action={bulkAction.action}
          tenants={bulkAction.tenants}
          onClose={() => setBulkAction(null)}
          onDone={() => { setSelectedIds(new Set()); fetchTenants() }}
        />
      )}
      <TenantSlideOut
        tenant={slideOutTenant}
        onClose={() => setSlideOutTenant(null)}
        onAction={handleRowAction}
        onRefresh={fetchTenants}
      />
    </div>
  )
}
