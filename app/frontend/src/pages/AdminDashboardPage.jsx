import { useState, useEffect, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Shield,
  Users,
  Building2,
  Activity,
  PauseCircle,
  Search,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Loader2,
  AlertTriangle,
  Check,
  X,
  BarChart3,
  Clock,
  FileText,
  RefreshCw,
  Zap,
  Settings,
  Filter,
  Calendar,
  Eye,
  Ban,
  PlayCircle,
  CreditCard,
  SlidersHorizontal,
  AlertCircle,
  Mail,
  ShieldAlert,
  UserCheck,
  Trash2,
  Layers,
  Plus,
  UserPlus,
  Edit,
  TrendingUp,
  DollarSign,
} from 'lucide-react'
import {
  getAdminTenants,
  getAdminTenantDetail,
  suspendTenant,
  reactivateTenant,
  adminChangeTenantPlan,
  adminAdjustUsage,
  getAdminTenantUsageHistory,
  getAdminAuditLogs,
  getAvailablePlans,
  getAdminFeatureFlags,
  toggleFeatureFlag,
  getTenantFeatureOverrides,
  setTenantFeatureOverride,
  deleteTenantFeatureOverride,
  getTenantWebhooks,
  createTenantWebhook,
  deleteTenantWebhook,
  getWebhookDeliveries,
  getAdminMetricsOverview,
  getAdminUsageTrends,
  getBillingConfig,
  updateBillingConfig,
  getBillingProviders,
  getNotificationConfig,
  sendTestEmail,
  getAdminRateLimits,
  getTenantRateLimit,
  updateTenantRateLimit,
  deleteTenantRateLimit,
  createTenant,
  updateTenant,
  deleteTenant,
  addUserToTenant,
  removeUserFromTenant,
} from '../lib/api'
import {
  getSecurityEvents,
  getImpersonationSessions,
} from '../lib/api'

const TABS = [
  { id: 'overview', label: 'Overview', icon: BarChart3 },
  { id: 'tenants', label: 'Tenants', icon: Building2 },
  { id: 'audit', label: 'Audit Log', icon: FileText },
  { id: 'rate-limits', label: 'Rate Limits', icon: SlidersHorizontal },
  { id: 'features', label: 'Feature Flags', icon: SlidersHorizontal },
  { id: 'webhooks', label: 'Webhooks', icon: Zap },
  { id: 'metrics', label: 'Metrics', icon: BarChart3 },
  { id: 'billing', label: 'Billing', icon: CreditCard },
  { id: 'notifications', label: 'Notifications', icon: Mail },
]

const STATUS_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'active', label: 'Active' },
  { value: 'suspended', label: 'Suspended' },
  { value: 'trialing', label: 'Trialing' },
  { value: 'cancelled', label: 'Cancelled' },
]

const SORTABLE_COLUMNS = [
  { key: 'name', label: 'Name' },
  { key: 'plan_name', label: 'Plan' },
  { key: 'subscription_status', label: 'Status' },
  { key: 'analyses_count_this_month', label: 'Analyses' },
  { key: 'user_count', label: 'Users' },
  { key: 'created_at', label: 'Created' },
]

function StatusBadge({ status }) {
  const styles = {
    active: 'bg-green-50 text-green-700 ring-green-200',
    suspended: 'bg-red-50 text-red-700 ring-red-200',
    trialing: 'bg-blue-50 text-blue-700 ring-blue-200',
    cancelled: 'bg-slate-50 text-slate-600 ring-slate-200',
  }
  return (
    <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ring-1 ${styles[status] || styles.cancelled}`}>
      {status}
    </span>
  )
}

function SummaryCard({ title, value, icon: Icon, color = 'brand' }) {
  const colorMap = {
    brand: 'bg-brand-50 text-brand-600 ring-brand-100',
    green: 'bg-green-50 text-green-600 ring-green-100',
    red: 'bg-red-50 text-red-600 ring-red-100',
    blue: 'bg-blue-50 text-blue-600 ring-blue-100',
    amber: 'bg-amber-50 text-amber-600 ring-amber-100',
  }
  return (
    <div className="bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 shadow-brand p-5 card-animate">
      <div className="flex items-center gap-3 mb-3">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ring-1 ${colorMap[color]}`}>
          <Icon className="w-5 h-5" />
        </div>
        <p className="text-sm font-medium text-slate-500">{title}</p>
      </div>
      <p className="text-2xl font-extrabold text-brand-900">{value}</p>
    </div>
  )
}

function TenantDetailModal({ tenantId, onClose, onAction }) {
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [activeDetailTab, setActiveDetailTab] = useState('overview')
  const [usageHistory, setUsageHistory] = useState([])
  const [usageLoading, setUsageLoading] = useState(false)
  const [showAdjustUsage, setShowAdjustUsage] = useState(false)
  const [adjustForm, setAdjustForm] = useState({ analyses_count: '', storage_used_bytes: '' })
  const [adjustSaving, setAdjustSaving] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getAdminTenantDetail(tenantId)
      .then((data) => {
        if (!cancelled) setDetail(data)
      })
      .catch((err) => { if (!cancelled) setError(err.response?.data?.detail || 'Failed to load tenant') })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [tenantId])

  useEffect(() => {
    if (activeDetailTab === 'usage' && tenantId) {
      setUsageLoading(true)
      getAdminTenantUsageHistory(tenantId, 50)
        .then((data) => setUsageHistory(data))
        .catch(() => setUsageHistory([]))
        .finally(() => setUsageLoading(false))
    }
  }, [activeDetailTab, tenantId])

  const formatBytes = (bytes) => {
    if (!bytes) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`
  }

  const DETAIL_TABS = [
    { id: 'overview', label: 'Overview' },
    { id: 'usage', label: 'Usage History' },
    { id: 'actions', label: 'Actions' },
  ]

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white/95 backdrop-blur-xl rounded-3xl ring-1 ring-brand-100 shadow-brand-xl w-full max-w-3xl max-h-[85vh] overflow-y-auto p-6 card-animate">
        <div className="flex items-center justify-between mb-5">
          <h3 className="font-extrabold text-brand-900 tracking-tight text-lg">Tenant Details</h3>
          <button onClick={onClose} className="p-1.5 hover:bg-brand-50 rounded-xl transition-colors">
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>

        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-brand-600" />
          </div>
        ) : error ? (
          <div className="p-4 bg-red-50 rounded-2xl ring-1 ring-red-200 text-center">
            <AlertTriangle className="w-6 h-6 text-red-500 mx-auto mb-2" />
            <p className="text-red-700 text-sm">{error}</p>
          </div>
        ) : detail ? (
          <div>
            {/* Tabs */}
            <div className="flex gap-2 mb-5 border-b border-brand-100">
              {DETAIL_TABS.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveDetailTab(tab.id)}
                  className={`px-4 py-2 text-sm font-semibold rounded-t-lg transition-colors ${
                    activeDetailTab === tab.id
                      ? 'bg-brand-50 text-brand-700 border-b-2 border-brand-600'
                      : 'text-slate-500 hover:text-brand-700'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Overview Tab */}
            {activeDetailTab === 'overview' && (
              <div className="space-y-6">
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="font-bold text-brand-900 text-xl">{detail.name}</h4>
                    <p className="text-sm text-slate-500 mt-0.5">{detail.slug}</p>
                  </div>
                  <StatusBadge status={detail.subscription_status} />
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  <div className="p-3 bg-brand-50/50 rounded-xl ring-1 ring-brand-100">
                    <p className="text-xs text-slate-500 font-medium">Plan</p>
                    <p className="text-sm font-bold text-brand-900 mt-0.5">{detail.plan_display_name || detail.plan_name || 'None'}</p>
                  </div>
                  <div className="p-3 bg-brand-50/50 rounded-xl ring-1 ring-brand-100">
                    <p className="text-xs text-slate-500 font-medium">Analyses This Month</p>
                    <p className="text-sm font-bold text-brand-900 mt-0.5">{detail.analyses_count_this_month}</p>
                  </div>
                  <div className="p-3 bg-brand-50/50 rounded-xl ring-1 ring-brand-100">
                    <p className="text-xs text-slate-500 font-medium">Storage Used</p>
                    <p className="text-sm font-bold text-brand-900 mt-0.5">{formatBytes(detail.storage_used_bytes)}</p>
                  </div>
                  <div className="p-3 bg-brand-50/50 rounded-xl ring-1 ring-brand-100">
                    <p className="text-xs text-slate-500 font-medium">Created</p>
                    <p className="text-sm font-bold text-brand-900 mt-0.5">{detail.created_at ? new Date(detail.created_at).toLocaleDateString() : '—'}</p>
                  </div>
                  <div className="p-3 bg-brand-50/50 rounded-xl ring-1 ring-brand-100">
                    <p className="text-xs text-slate-500 font-medium">Users</p>
                    <p className="text-sm font-bold text-brand-900 mt-0.5">{detail.users?.length || 0}</p>
                  </div>
                  {detail.suspended_at && (
                    <div className="p-3 bg-red-50/50 rounded-xl ring-1 ring-red-100">
                      <p className="text-xs text-red-500 font-medium">Suspended</p>
                      <p className="text-sm font-bold text-red-700 mt-0.5">{new Date(detail.suspended_at).toLocaleDateString()}</p>
                    </div>
                  )}
                </div>

                {detail.suspended_reason && (
                  <div className="p-3 bg-red-50/50 rounded-xl ring-1 ring-red-100">
                    <p className="text-xs text-red-500 font-medium">Suspension Reason</p>
                    <p className="text-sm text-red-700 mt-0.5">{detail.suspended_reason}</p>
                  </div>
                )}

                {detail.users && detail.users.length > 0 && (
                  <div>
                    <h5 className="font-bold text-slate-800 text-sm mb-2">Users</h5>
                    <div className="divide-y divide-brand-50 ring-1 ring-brand-100 rounded-xl overflow-hidden">
                      {detail.users.map((u) => (
                        <div key={u.id} className="flex items-center justify-between px-4 py-2.5 bg-white">
                          <span className="text-sm text-slate-700">{u.email}</span>
                          <span className="text-xs font-medium text-slate-500 capitalize">{u.role}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Usage History Tab */}
            {activeDetailTab === 'usage' && (
              <div>
                {usageLoading ? (
                  <div className="flex justify-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin text-brand-600" />
                  </div>
                ) : usageHistory.length === 0 ? (
                  <div className="p-8 text-center">
                    <Activity className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                    <p className="text-sm text-slate-500">No usage history found.</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {usageHistory.map((log) => (
                      <div key={log.id} className="p-3 bg-brand-50/30 rounded-xl ring-1 ring-brand-50">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-sm font-semibold text-brand-900">{log.action}</p>
                            <p className="text-xs text-slate-500">{log.user_email || 'System'}</p>
                          </div>
                          <div className="text-right">
                            <p className="text-sm font-bold text-brand-700">{log.quantity}</p>
                            <p className="text-xs text-slate-400">{new Date(log.created_at).toLocaleString()}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Actions Tab */}
            {activeDetailTab === 'actions' && (
              <div className="space-y-3">
                <button
                  onClick={() => setShowAdjustUsage(true)}
                  className="w-full flex items-center gap-3 p-4 rounded-xl bg-brand-50 hover:bg-brand-100 ring-1 ring-brand-200 transition-colors text-left"
                >
                  <SlidersHorizontal className="w-5 h-5 text-brand-600" />
                  <div>
                    <p className="text-sm font-bold text-brand-900">Adjust Usage Counters</p>
                    <p className="text-xs text-slate-500">Override analyses or storage limits</p>
                  </div>
                </button>

                {detail.subscription_status === 'suspended' ? (
                  <button
                    onClick={() => onAction('reactivate', detail.id)}
                    className="w-full flex items-center gap-3 p-4 rounded-xl bg-green-50 hover:bg-green-100 ring-1 ring-green-200 transition-colors text-left"
                  >
                    <PlayCircle className="w-5 h-5 text-green-600" />
                    <div>
                      <p className="text-sm font-bold text-green-900">Reactivate Tenant</p>
                      <p className="text-xs text-green-600">Restore access and services</p>
                    </div>
                  </button>
                ) : (
                  <button
                    onClick={() => onAction('suspend', detail.id)}
                    className="w-full flex items-center gap-3 p-4 rounded-xl bg-red-50 hover:bg-red-100 ring-1 ring-red-200 transition-colors text-left"
                  >
                    <Ban className="w-5 h-5 text-red-600" />
                    <div>
                      <p className="text-sm font-bold text-red-900">Suspend Tenant</p>
                      <p className="text-xs text-red-600">Disable access temporarily</p>
                    </div>
                  </button>
                )}

                <button
                  onClick={() => { onClose(); setTimeout(() => onAction('change-plan', detail.id), 100) }}
                  className="w-full flex items-center gap-3 p-4 rounded-xl bg-brand-50 hover:bg-brand-100 ring-1 ring-brand-200 transition-colors text-left"
                >
                  <CreditCard className="w-5 h-5 text-brand-600" />
                  <div>
                    <p className="text-sm font-bold text-brand-900">Change Subscription Plan</p>
                    <p className="text-xs text-slate-500">Upgrade or downgrade plan</p>
                  </div>
                </button>
              </div>
            )}
          </div>
        ) : null}

        {/* Adjust Usage Modal */}
        {showAdjustUsage && (
          <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-[60] flex items-center justify-center p-4">
            <div className="bg-white/95 backdrop-blur-xl rounded-3xl ring-1 ring-brand-100 shadow-brand-xl w-full max-w-md p-6 card-animate">
              <div className="flex items-center justify-between mb-5">
                <h3 className="font-extrabold text-brand-900 tracking-tight text-lg">Adjust Usage</h3>
                <button onClick={() => setShowAdjustUsage(false)} className="p-1.5 hover:bg-brand-50 rounded-xl transition-colors">
                  <X className="w-5 h-5 text-slate-400" />
                </button>
              </div>

              <div className="space-y-4 mb-6">
                <div>
                  <label className="block text-sm font-bold text-slate-700 mb-1.5">Analyses Count</label>
                  <input
                    type="number"
                    value={adjustForm.analyses_count}
                    onChange={(e) => setAdjustForm({ ...adjustForm, analyses_count: e.target.value })}
                    placeholder={detail.analyses_count_this_month}
                    className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
                  />
                  <p className="text-xs text-slate-400 mt-1">Current: {detail.analyses_count_this_month}</p>
                </div>

                <div>
                  <label className="block text-sm font-bold text-slate-700 mb-1.5">Storage Used (bytes)</label>
                  <input
                    type="number"
                    value={adjustForm.storage_used_bytes}
                    onChange={(e) => setAdjustForm({ ...adjustForm, storage_used_bytes: e.target.value })}
                    placeholder={detail.storage_used_bytes}
                    className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
                  />
                  <p className="text-xs text-slate-400 mt-1">Current: {formatBytes(detail.storage_used_bytes)}</p>
                </div>
              </div>

              <div className="flex justify-end gap-2">
                <button
                  onClick={() => setShowAdjustUsage(false)}
                  className="px-4 py-2 ring-1 ring-brand-200 text-sm font-semibold text-brand-700 rounded-xl hover:bg-brand-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={async () => {
                    setAdjustSaving(true)
                    try {
                      const payload = {}
                      if (adjustForm.analyses_count) payload.analyses_count = parseInt(adjustForm.analyses_count, 10)
                      if (adjustForm.storage_used_bytes) payload.storage_used_bytes = parseInt(adjustForm.storage_used_bytes, 10)
                      await adminAdjustUsage(detail.id, payload)
                      setShowAdjustUsage(false)
                      // Refresh detail
                      getAdminTenantDetail(tenantId).then(setDetail)
                    } catch (err) {
                      alert(err.response?.data?.detail || 'Failed to adjust usage')
                    } finally {
                      setAdjustSaving(false)
                    }
                  }}
                  disabled={adjustSaving || (!adjustForm.analyses_count && !adjustForm.storage_used_bytes)}
                  className="px-4 py-2 btn-brand text-white text-sm font-bold rounded-xl disabled:opacity-60"
                >
                  {adjustSaving ? 'Saving...' : 'Adjust Usage'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function ChangePlanModal({ tenant, plans, onClose, onChange }) {
  const [selectedPlan, setSelectedPlan] = useState(tenant.plan_id || '')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async () => {
    if (!selectedPlan) return
    setLoading(true)
    try {
      await onChange(tenant.id, parseInt(selectedPlan, 10))
      onClose()
    } catch {
      // Error handled by parent
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white/95 backdrop-blur-xl rounded-3xl ring-1 ring-brand-100 shadow-brand-xl w-full max-w-md p-6 card-animate">
        <div className="flex items-center justify-between mb-5">
          <h3 className="font-extrabold text-brand-900 tracking-tight">Change Plan</h3>
          <button onClick={onClose} className="p-1.5 hover:bg-brand-50 rounded-xl transition-colors">
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>
        <p className="text-sm text-slate-500 mb-4">
          Change plan for <span className="font-semibold text-slate-700">{tenant.name}</span>
        </p>
        <div className="space-y-2 mb-6">
          {plans.map((plan) => (
            <label
              key={plan.id}
              className={`flex items-center gap-3 p-3 rounded-xl ring-1 cursor-pointer transition-all ${
                parseInt(selectedPlan, 10) === plan.id
                  ? 'bg-brand-50 ring-brand-300'
                  : 'bg-white ring-brand-100 hover:bg-brand-50/50'
              }`}
            >
              <input
                type="radio"
                name="plan"
                value={plan.id}
                checked={parseInt(selectedPlan, 10) === plan.id}
                onChange={(e) => setSelectedPlan(e.target.value)}
                className="w-4 h-4 text-brand-600"
              />
              <div className="flex-1">
                <p className="text-sm font-bold text-slate-800">{plan.display_name}</p>
                <p className="text-xs text-slate-500">${(plan.price_monthly / 100).toFixed(0)}/mo</p>
              </div>
            </label>
          ))}
        </div>
        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 ring-1 ring-brand-200 text-sm font-semibold text-brand-700 rounded-xl hover:bg-brand-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading || !selectedPlan}
            className="px-4 py-2 btn-brand text-white text-sm font-bold rounded-xl disabled:opacity-60 shadow-brand-sm"
          >
            {loading ? 'Changing...' : 'Change Plan'}
          </button>
        </div>
      </div>
    </div>
  )
}

function SuspendModal({ tenant, onClose, onConfirm }) {
  const [reason, setReason] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async () => {
    if (!reason.trim()) return
    setLoading(true)
    try {
      await onConfirm(tenant.id, reason.trim())
      onClose()
    } catch {
      // Error handled by parent
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white/95 backdrop-blur-xl rounded-3xl ring-1 ring-red-100 shadow-brand-xl w-full max-w-md p-6 card-animate">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-red-50 flex items-center justify-center">
            <AlertTriangle className="w-5 h-5 text-red-600" />
          </div>
          <div>
            <h3 className="font-extrabold text-brand-900 tracking-tight">Suspend Tenant</h3>
            <p className="text-sm text-slate-500">{tenant.name}</p>
          </div>
        </div>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1.5">Reason</label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Enter suspension reason..."
              rows={3}
              className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white resize-none"
            />
          </div>
          <div className="flex justify-end gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 ring-1 ring-brand-200 text-sm font-semibold text-brand-700 rounded-xl hover:bg-brand-50 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={loading || !reason.trim()}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-bold rounded-xl disabled:opacity-60 shadow-brand-sm"
            >
              {loading ? 'Suspending...' : 'Suspend'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function AdminDashboardPage() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('overview')
  const [tenantsData, setTenantsData] = useState(null)
  const [auditData, setAuditData] = useState(null)
  const [plans, setPlans] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Tenant filters
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [sortBy, setSortBy] = useState('created_at')
  const [sortOrder, setSortOrder] = useState('desc')
  const [tenantPage, setTenantPage] = useState(1)
  const [perPage] = useState(20)

  // Audit filters
  const [auditAction, setAuditAction] = useState('')
  const [auditDateFrom, setAuditDateFrom] = useState('')
  const [auditDateTo, setAuditDateTo] = useState('')
  const [auditPage, setAuditPage] = useState(1)
  const [auditPerPage] = useState(50)

  // Modals
  const [detailTenantId, setDetailTenantId] = useState(null)
  const [changePlanTenant, setChangePlanTenant] = useState(null)
  const [suspendTenantObj, setSuspendTenantObj] = useState(null)

  // Feature Flags state
  const [featureFlags, setFeatureFlags] = useState(null)
  const [featureLoading, setFeatureLoading] = useState(false)
  const [featureError, setFeatureError] = useState('')
  const [ffTenantId, setFfTenantId] = useState('')
  const [tenantOverrides, setTenantOverrides] = useState(null)
  const [overrideLoading, setOverrideLoading] = useState(false)

  // Webhooks state
  const [whTenantId, setWhTenantId] = useState('')
  const [webhooks, setWebhooks] = useState(null)
  const [whLoading, setWhLoading] = useState(false)
  const [whError, setWhError] = useState('')
  const [showAddWebhook, setShowAddWebhook] = useState(false)
  const [whUrl, setWhUrl] = useState('')
  const [whEvents, setWhEvents] = useState(['*'])
  const [whSubmitting, setWhSubmitting] = useState(false)
  const [expandedWhId, setExpandedWhId] = useState(null)
  const [whDeliveries, setWhDeliveries] = useState({})

  // Metrics state
  const [metricsData, setMetricsData] = useState(null)
  const [trendsData, setTrendsData] = useState(null)
  const [metricsLoading, setMetricsLoading] = useState(false)
  const [metricsError, setMetricsError] = useState('')

  // Billing state
  const [billingConfig, setBillingConfig] = useState(null)
  const [billingLoading, setBillingLoading] = useState(false)
  const [billingError, setBillingError] = useState('')
  const [billingSaving, setBillingSaving] = useState(false)
  const [selectedProvider, setSelectedProvider] = useState('')
  const [providerApiKey, setProviderApiKey] = useState('')
  const [providerSecretKey, setProviderSecretKey] = useState('')

  // Notifications state
  const [notificationConfig, setNotificationConfig] = useState(null)
  const [notificationLoading, setNotificationLoading] = useState(false)
  const [notificationError, setNotificationError] = useState('')
  const [testEmail, setTestEmail] = useState('')
  const [testEmailSending, setTestEmailSending] = useState(false)
  const [testEmailResult, setTestEmailResult] = useState(null)

  // Rate Limits state
  const [rateLimitsData, setRateLimitsData] = useState(null)
  const [rateLimitsLoading, setRateLimitsLoading] = useState(false)
  const [rateLimitsError, setRateLimitsError] = useState('')
  const [rateLimitSearch, setRateLimitSearch] = useState('')
  const [rateLimitPage, setRateLimitPage] = useState(1)
  const [rateLimitPerPage] = useState(20)
  const [editRateLimitTenant, setEditRateLimitTenant] = useState(null)
  const [editRateLimitForm, setEditRateLimitForm] = useState({ requests_per_minute: 60, llm_concurrent_max: 2 })
  const [editRateLimitSaving, setEditRateLimitSaving] = useState(false)

  // Tenant CRUD state
  const [showCreateTenant, setShowCreateTenant] = useState(false)
  const [createTenantForm, setCreateTenantForm] = useState({ name: '', slug: '', contact_email: '', plan_id: '' })
  const [createTenantSaving, setCreateTenantSaving] = useState(false)
  const [editTenantObj, setEditTenantObj] = useState(null)
  const [editTenantForm, setEditTenantForm] = useState({ name: '', slug: '', contact_email: '', subscription_status: '' })
  const [editTenantSaving, setEditTenantSaving] = useState(false)

  // Recent Activity state
  const [recentActivity, setRecentActivity] = useState([])
  const [activityLoading, setActivityLoading] = useState(false)

  const fetchTenants = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const params = {
        page: tenantPage,
        per_page: perPage,
        sort_by: sortBy,
        sort_order: sortOrder,
      }
      if (search.trim()) params.search = search.trim()
      if (statusFilter) params.status = statusFilter
      const data = await getAdminTenants(params)
      setTenantsData(data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load tenants')
    } finally {
      setLoading(false)
    }
  }, [tenantPage, perPage, sortBy, sortOrder, search, statusFilter])

  const fetchAuditLogs = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const params = { page: auditPage, per_page: auditPerPage }
      if (auditAction.trim()) params.action = auditAction.trim()
      if (auditDateFrom) params.date_from = auditDateFrom
      if (auditDateTo) params.date_to = auditDateTo
      const data = await getAdminAuditLogs(params)
      setAuditData(data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load audit logs')
    } finally {
      setLoading(false)
    }
  }, [auditPage, auditPerPage, auditAction, auditDateFrom, auditDateTo])

  const fetchPlans = useCallback(async () => {
    try {
      const data = await getAvailablePlans()
      setPlans(data.plans || data)
    } catch {
      // Silently fail - plans only needed for change plan action
    }
  }, [])

  // Feature Flags fetch
  const fetchFeatureFlags = useCallback(async () => {
    setFeatureLoading(true)
    setFeatureError('')
    try {
      const data = await getAdminFeatureFlags()
      setFeatureFlags(data)
    } catch (err) {
      setFeatureError(err.response?.data?.detail || 'Failed to load feature flags')
    } finally {
      setFeatureLoading(false)
    }
  }, [])

  const fetchTenantOverrides = useCallback(async (tenantId) => {
    if (!tenantId) { setTenantOverrides(null); return }
    setOverrideLoading(true)
    try {
      const data = await getTenantFeatureOverrides(tenantId)
      setTenantOverrides(data)
    } catch {
      setTenantOverrides(null)
    } finally {
      setOverrideLoading(false)
    }
  }, [])

  // Webhooks fetch
  const fetchWebhooks = useCallback(async (tenantId) => {
    if (!tenantId) { setWebhooks(null); return }
    setWhLoading(true)
    setWhError('')
    try {
      const data = await getTenantWebhooks(tenantId)
      setWebhooks(data)
    } catch (err) {
      setWhError(err.response?.data?.detail || 'Failed to load webhooks')
    } finally {
      setWhLoading(false)
    }
  }, [])

  // Metrics fetch
  const fetchMetrics = useCallback(async () => {
    setMetricsLoading(true)
    setMetricsError('')
    try {
      const [overview, trends] = await Promise.all([
        getAdminMetricsOverview(),
        getAdminUsageTrends(30),
      ])
      setMetricsData(overview)
      setTrendsData(trends)
    } catch (err) {
      setMetricsError(err.response?.data?.detail || 'Failed to load metrics')
    } finally {
      setMetricsLoading(false)
    }
  }, [])

  // Billing fetch
  const fetchBillingConfig = useCallback(async () => {
    setBillingLoading(true)
    setBillingError('')
    try {
      const [config, providers] = await Promise.all([
        getBillingConfig(),
        getBillingProviders(),
      ])
      setBillingConfig(config)
      if (config?.provider) setSelectedProvider(config.provider)
    } catch (err) {
      setBillingError(err.response?.data?.detail || 'Failed to load billing config')
    } finally {
      setBillingLoading(false)
    }
  }, [])

  // Notifications fetch
  const fetchNotificationConfig = useCallback(async () => {
    setNotificationLoading(true)
    setNotificationError('')
    try {
      const data = await getNotificationConfig()
      setNotificationConfig(data)
    } catch (err) {
      setNotificationError(err.response?.data?.detail || 'Failed to load notification config')
    } finally {
      setNotificationLoading(false)
    }
  }, [])

  useEffect(() => {
    if (activeTab === 'overview' || activeTab === 'tenants') {
      fetchTenants()
    }
  }, [activeTab, fetchTenants])

  useEffect(() => {
    if (activeTab === 'audit') {
      fetchAuditLogs()
    }
  }, [activeTab, fetchAuditLogs])

  useEffect(() => {
    fetchPlans()
  }, [fetchPlans])

  useEffect(() => {
    if (activeTab === 'features') fetchFeatureFlags()
  }, [activeTab, fetchFeatureFlags])

  useEffect(() => {
    if (activeTab === 'webhooks' && whTenantId) fetchWebhooks(whTenantId)
  }, [activeTab, whTenantId, fetchWebhooks])

  useEffect(() => {
    if (activeTab === 'metrics') fetchMetrics()
  }, [activeTab, fetchMetrics])

  useEffect(() => {
    if (activeTab === 'billing') fetchBillingConfig()
  }, [activeTab, fetchBillingConfig])

  useEffect(() => {
    if (activeTab === 'notifications') fetchNotificationConfig()
  }, [activeTab, fetchNotificationConfig])

  const fetchRateLimits = useCallback(async () => {
    setRateLimitsLoading(true)
    setRateLimitsError('')
    try {
      const params = {
        page: rateLimitPage,
        per_page: rateLimitPerPage,
      }
      if (rateLimitSearch.trim()) params.search = rateLimitSearch.trim()
      const data = await getAdminRateLimits(params)
      setRateLimitsData(data)
    } catch (err) {
      setRateLimitsError(err.response?.data?.detail || 'Failed to load rate limits')
    } finally {
      setRateLimitsLoading(false)
    }
  }, [rateLimitPage, rateLimitPerPage, rateLimitSearch])

  useEffect(() => {
    if (activeTab === 'rate-limits') fetchRateLimits()
  }, [activeTab, fetchRateLimits])

  const fetchRecentActivity = useCallback(async () => {
    setActivityLoading(true)
    try {
      const [auditLogs, securityEvents] = await Promise.allSettled([
        getAdminAuditLogs({ page: 1, per_page: 10 }),
        getSecurityEvents({ page: 1, per_page: 5 }),
      ])

      const activities = []
      if (auditLogs.status === 'fulfilled' && auditLogs.value.items) {
        auditLogs.value.items.forEach((log) => {
          activities.push({
            id: `audit-${log.id}`,
            type: 'audit',
            action: log.action,
            actor: log.actor_email,
            resource: `${log.resource_type}#${log.resource_id}`,
            timestamp: log.created_at,
          })
        })
      }
      if (securityEvents.status === 'fulfilled' && securityEvents.value.items) {
        securityEvents.value.items.forEach((evt) => {
          activities.push({
            id: `security-${evt.id}`,
            type: 'security',
            action: evt.event_type,
            actor: evt.ip_address || 'System',
            resource: `User #${evt.user_id}`,
            timestamp: evt.created_at,
          })
        })
      }

      // Sort by timestamp descending
      activities.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
      setRecentActivity(activities.slice(0, 15))
    } catch (err) {
      console.error('Failed to fetch recent activity:', err)
    } finally {
      setActivityLoading(false)
    }
  }, [])

  useEffect(() => {
    if (activeTab === 'overview') fetchRecentActivity()
  }, [activeTab, fetchRecentActivity])

  const handleSort = (key) => {
    if (sortBy === key) {
      setSortOrder((o) => (o === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortBy(key)
      setSortOrder('asc')
    }
    setTenantPage(1)
  }

  const handleAction = async (action, tenantId, extra = null) => {
    try {
      if (action === 'suspend') {
        await suspendTenant(tenantId, extra)
      } else if (action === 'reactivate') {
        await reactivateTenant(tenantId)
      } else if (action === 'change-plan') {
        await adminChangeTenantPlan(tenantId, extra)
      }
      await fetchTenants()
      setDetailTenantId(null)
      setChangePlanTenant(null)
      setSuspendTenantObj(null)
    } catch (err) {
      alert(err.response?.data?.detail || `Failed to ${action} tenant`)
    }
  }

  const overviewStats = useMemo(() => {
    if (!tenantsData?.items) return null
    const items = tenantsData.items
    const total = tenantsData.total || items.length
    const active = items.filter((t) => t.subscription_status === 'active').length
    const suspended = items.filter((t) => t.subscription_status === 'suspended').length
    const totalUsers = items.reduce((sum, t) => sum + (t.user_count || 0), 0)

    const planCounts = {}
    items.forEach((t) => {
      const key = t.plan_display_name || t.plan_name || 'No Plan'
      planCounts[key] = (planCounts[key] || 0) + 1
    })
    const topPlan = Object.entries(planCounts).sort((a, b) => b[1] - a[1])[0]

    return { total, active, suspended, totalUsers, topPlan }
  }, [tenantsData])

  const formatDate = (iso) => {
    if (!iso) return '—'
    return new Date(iso).toLocaleString()
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8 card-animate">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-2xl bg-brand-50 ring-1 ring-brand-100 flex items-center justify-center">
            <Shield className="w-5 h-5 text-brand-600" />
          </div>
          <div>
            <h1 className="text-3xl font-extrabold text-brand-900 tracking-tight">Admin Dashboard</h1>
            <p className="text-slate-500 text-sm font-medium">Platform-wide tenant management and oversight</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-8 overflow-x-auto pb-1">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all whitespace-nowrap ${
              activeTab === id
                ? 'bg-brand-50 text-brand-700 ring-1 ring-brand-200'
                : 'text-slate-600 hover:bg-brand-50/50 hover:text-brand-700'
            }`}
          >
            <Icon className={`w-4 h-4 ${activeTab === id ? 'text-brand-600' : 'text-slate-400'}`} />
            {label}
          </button>
        ))}
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 rounded-2xl ring-1 ring-red-200 flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-red-500 shrink-0" />
          <p className="text-sm text-red-700">{error}</p>
          <button
            onClick={() => { setError(''); activeTab === 'audit' ? fetchAuditLogs() : fetchTenants() }}
            className="ml-auto text-sm font-semibold text-red-600 hover:text-red-700"
          >
            Retry
          </button>
        </div>
      )}

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="space-y-6 card-animate">
          {loading && !tenantsData ? (
            <div className="flex justify-center py-16">
              <Loader2 className="w-8 h-8 animate-spin text-brand-600" />
            </div>
          ) : overviewStats ? (
            <>
              <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
                <SummaryCard title="Total Tenants" value={overviewStats.total} icon={Building2} color="brand" />
                <SummaryCard title="Active" value={overviewStats.active} icon={Activity} color="green" />
                <SummaryCard title="Suspended" value={overviewStats.suspended} icon={PauseCircle} color="red" />
                <SummaryCard title="Total Users" value={overviewStats.totalUsers} icon={Users} color="blue" />
                <SummaryCard
                  title="Top Plan"
                  value={overviewStats.topPlan ? `${overviewStats.topPlan[0]} (${overviewStats.topPlan[1]})` : '—'}
                  icon={Zap}
                  color="amber"
                />
              </div>

              <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6">
                <h3 className="font-extrabold text-brand-900 tracking-tight mb-4">Plan Distribution</h3>
                {overviewStats.topPlan ? (
                  <div className="space-y-3">
                    {Object.entries(
                      tenantsData.items.reduce((acc, t) => {
                        const key = t.plan_display_name || t.plan_name || 'No Plan'
                        acc[key] = (acc[key] || 0) + 1
                        return acc
                      }, {})
                    )
                      .sort((a, b) => b[1] - a[1])
                      .map(([plan, count]) => {
                        const pct = Math.round((count / overviewStats.total) * 100)
                        return (
                          <div key={plan}>
                            <div className="flex justify-between text-sm mb-1">
                              <span className="font-medium text-slate-700">{plan}</span>
                              <span className="text-slate-500">{count} ({pct}%)</span>
                            </div>
                            <div className="w-full bg-slate-100 rounded-full h-2">
                              <div
                                className="h-2 rounded-full bg-brand-500 transition-all"
                                style={{ width: `${pct}%` }}
                              />
                            </div>
                          </div>
                        )
                      })}
                  </div>
                ) : (
                  <p className="text-sm text-slate-500">No data available.</p>
                )}
              </div>

              <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6">
                <h3 className="font-extrabold text-brand-900 tracking-tight mb-4">Recent Tenants</h3>
                {tenantsData.items.length > 0 ? (
                  <div className="divide-y divide-brand-50">
                    {tenantsData.items.slice(0, 5).map((t) => (
                      <div key={t.id} className="flex items-center justify-between py-3">
                        <div>
                          <p className="text-sm font-bold text-brand-900">{t.name}</p>
                          <p className="text-xs text-slate-500">{t.slug}</p>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-xs text-slate-500">{t.user_count} users</span>
                          <StatusBadge status={t.subscription_status} />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-slate-500">No tenants found.</p>
                )}
              </div>

              {/* Recent Activity Feed */}
              <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-extrabold text-brand-900 tracking-tight">Recent Activity</h3>
                  <Activity className="w-5 h-5 text-brand-600" />
                </div>

                {activityLoading ? (
                  <div className="flex justify-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin text-brand-600" />
                  </div>
                ) : recentActivity.length === 0 ? (
                  <p className="text-sm text-slate-500 text-center py-4">No recent activity</p>
                ) : (
                  <div className="space-y-3 max-h-80 overflow-y-auto">
                    {recentActivity.map((activity) => (
                      <div
                        key={activity.id}
                        className={`p-3 rounded-xl ring-1 transition-colors ${
                          activity.type === 'security'
                            ? 'bg-red-50/50 ring-red-100 hover:bg-red-50'
                            : 'bg-brand-50/50 ring-brand-100 hover:bg-brand-50'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className={`px-2 py-0.5 text-xs font-bold rounded-full ${
                                activity.type === 'security'
                                  ? 'bg-red-100 text-red-700'
                                  : 'bg-brand-100 text-brand-700'
                              }`}>
                                {activity.type}
                              </span>
                              <span className="text-xs text-slate-400 truncate">{activity.action}</span>
                            </div>
                            <p className="text-sm text-slate-700 truncate">
                              <span className="font-semibold">{activity.actor}</span> → {activity.resource}
                            </p>
                          </div>
                          <span className="text-xs text-slate-400 whitespace-nowrap">
                            {new Date(activity.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Enterprise Admin Quick Links */}
              <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6">
                <h3 className="font-extrabold text-brand-900 tracking-tight mb-4">Enterprise Tools</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  <button
                    onClick={() => navigate('/admin/security-events')}
                    className="flex items-center gap-3 p-4 rounded-2xl bg-brand-50 hover:bg-brand-100 ring-1 ring-brand-200 transition-colors text-left"
                  >
                    <div className="w-10 h-10 rounded-xl bg-brand-600 text-white flex items-center justify-center shrink-0">
                      <ShieldAlert className="w-5 h-5" />
                    </div>
                    <div>
                      <p className="text-sm font-bold text-brand-900">Security Events</p>
                      <p className="text-xs text-slate-500">Login monitoring & alerts</p>
                    </div>
                  </button>
                  <button
                    onClick={() => navigate('/admin/impersonation')}
                    className="flex items-center gap-3 p-4 rounded-2xl bg-brand-50 hover:bg-brand-100 ring-1 ring-brand-200 transition-colors text-left"
                  >
                    <div className="w-10 h-10 rounded-xl bg-brand-600 text-white flex items-center justify-center shrink-0">
                      <UserCheck className="w-5 h-5" />
                    </div>
                    <div>
                      <p className="text-sm font-bold text-brand-900">Impersonation</p>
                      <p className="text-xs text-slate-500">Secure login-as-user</p>
                    </div>
                  </button>
                  <button
                    onClick={() => navigate('/admin/erasure')}
                    className="flex items-center gap-3 p-4 rounded-2xl bg-brand-50 hover:bg-brand-100 ring-1 ring-brand-200 transition-colors text-left"
                  >
                    <div className="w-10 h-10 rounded-xl bg-red-600 text-white flex items-center justify-center shrink-0">
                      <Trash2 className="w-5 h-5" />
                    </div>
                    <div>
                      <p className="text-sm font-bold text-brand-900">GDPR Erasure</p>
                      <p className="text-xs text-slate-500">Tenant data anonymization</p>
                    </div>
                  </button>
                  <button
                    onClick={() => navigate('/admin/plan-features')}
                    className="flex items-center gap-3 p-4 rounded-2xl bg-brand-50 hover:bg-brand-100 ring-1 ring-brand-200 transition-colors text-left"
                  >
                    <div className="w-10 h-10 rounded-xl bg-brand-600 text-white flex items-center justify-center shrink-0">
                      <Layers className="w-5 h-5" />
                    </div>
                    <div>
                      <p className="text-sm font-bold text-brand-900">Plan Features</p>
                      <p className="text-xs text-slate-500">Feature entitlement mapping</p>
                    </div>
                  </button>
                </div>
              </div>
            </>
          ) : (
            <p className="text-sm text-slate-500">No data available.</p>
          )}
        </div>
      )}

      {/* Tenants Tab */}
      {activeTab === 'tenants' && (
        <div className="space-y-4 card-animate">
          {/* Header with Create Button */}
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-extrabold text-brand-900">Tenant Management</h2>
            <button
              onClick={() => setShowCreateTenant(true)}
              className="flex items-center gap-2 px-4 py-2 btn-brand text-white text-sm font-bold rounded-xl shadow-brand-sm"
            >
              <Plus className="w-4 h-4" />
              Create Tenant
            </button>
          </div>

          {/* Filters */}
          <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-4">
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => { setSearch(e.target.value); setTenantPage(1) }}
                  placeholder="Search by name or slug..."
                  className="w-full pl-9 pr-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
                />
              </div>
              <div className="flex items-center gap-2">
                <Filter className="w-4 h-4 text-slate-400" />
                <select
                  value={statusFilter}
                  onChange={(e) => { setStatusFilter(e.target.value); setTenantPage(1) }}
                  className="px-3 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
                >
                  {STATUS_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Table */}
          <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand overflow-hidden">
            {loading && !tenantsData ? (
              <div className="flex justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-brand-600" />
              </div>
            ) : tenantsData?.items?.length === 0 ? (
              <div className="p-8 text-center">
                <Building2 className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                <p className="text-sm text-slate-500">No tenants found.</p>
              </div>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-brand-50">
                        {SORTABLE_COLUMNS.map((col) => (
                          <th
                            key={col.key}
                            onClick={() => handleSort(col.key)}
                            className="text-left px-5 py-3.5 text-xs font-bold text-slate-500 uppercase tracking-wide cursor-pointer select-none hover:text-brand-700 transition-colors"
                          >
                            <div className="flex items-center gap-1">
                              {col.label}
                              {sortBy === col.key && (
                                sortOrder === 'asc' ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />
                              )}
                            </div>
                          </th>
                        ))}
                        <th className="text-right px-5 py-3.5 text-xs font-bold text-slate-500 uppercase tracking-wide">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-brand-50">
                      {tenantsData?.items?.map((t) => (
                        <tr key={t.id} className="hover:bg-brand-50/30 transition-colors">
                          <td className="px-5 py-3.5">
                            <button
                              onClick={() => setDetailTenantId(t.id)}
                              className="text-left hover:text-brand-700 transition-colors"
                            >
                              <p className="font-bold text-brand-900">{t.name}</p>
                              <p className="text-xs text-slate-500">{t.slug}</p>
                            </button>
                          </td>
                          <td className="px-5 py-3.5 text-slate-700">{t.plan_display_name || t.plan_name || '—'}</td>
                          <td className="px-5 py-3.5">
                            <StatusBadge status={t.subscription_status} />
                          </td>
                          <td className="px-5 py-3.5 text-slate-700">{t.analyses_count_this_month}</td>
                          <td className="px-5 py-3.5 text-slate-700">{t.user_count}</td>
                          <td className="px-5 py-3.5 text-slate-500 text-xs">
                            {t.created_at ? new Date(t.created_at).toLocaleDateString() : '—'}
                          </td>
                          <td className="px-5 py-3.5 text-right">
                            <div className="flex items-center justify-end gap-1.5">
                              <button
                                onClick={() => {
                                  setEditTenantObj(t)
                                  setEditTenantForm({
                                    name: t.name,
                                    slug: t.slug,
                                    contact_email: t.contact_email || '',
                                    subscription_status: t.subscription_status,
                                  })
                                }}
                                className="p-1.5 rounded-lg hover:bg-brand-100 text-slate-400 hover:text-brand-600 transition-colors"
                                title="Edit"
                              >
                                <Edit className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => setDetailTenantId(t.id)}
                                className="p-1.5 rounded-lg hover:bg-brand-100 text-slate-400 hover:text-brand-600 transition-colors"
                                title="View details"
                              >
                                <Eye className="w-4 h-4" />
                              </button>
                              {t.subscription_status === 'suspended' ? (
                                <button
                                  onClick={() => setDetailTenantId(t.id)}
                                  className="p-1.5 rounded-lg hover:bg-green-100 text-slate-400 hover:text-green-600 transition-colors"
                                  title="Reactivate"
                                >
                                  <PlayCircle className="w-4 h-4" />
                                </button>
                              ) : (
                                <button
                                  onClick={() => setSuspendTenantObj(t)}
                                  className="p-1.5 rounded-lg hover:bg-red-100 text-slate-400 hover:text-red-600 transition-colors"
                                  title="Suspend"
                                >
                                  <Ban className="w-4 h-4" />
                                </button>
                              )}
                              <button
                                onClick={() => setChangePlanTenant(t)}
                                className="p-1.5 rounded-lg hover:bg-brand-100 text-slate-400 hover:text-brand-600 transition-colors"
                                title="Change plan"
                              >
                                <CreditCard className="w-4 h-4" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                {tenantsData && tenantsData.pages > 1 && (
                  <div className="flex items-center justify-between px-5 py-3 border-t border-brand-50">
                    <p className="text-xs text-slate-500">
                      Showing {(tenantsData.page - 1) * tenantsData.per_page + 1} -{' '}
                      {Math.min(tenantsData.page * tenantsData.per_page, tenantsData.total)} of {tenantsData.total}
                    </p>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => setTenantPage((p) => Math.max(1, p - 1))}
                        disabled={tenantPage <= 1}
                        className="p-1.5 rounded-lg hover:bg-brand-50 text-slate-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                      >
                        <ChevronLeft className="w-4 h-4" />
                      </button>
                      <span className="text-xs text-slate-600 font-medium px-2">
                        Page {tenantsData.page} of {tenantsData.pages}
                      </span>
                      <button
                        onClick={() => setTenantPage((p) => Math.min(tenantsData.pages, p + 1))}
                        disabled={tenantPage >= tenantsData.pages}
                        className="p-1.5 rounded-lg hover:bg-brand-50 text-slate-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                      >
                        <ChevronRight className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {/* Audit Log Tab */}
      {activeTab === 'audit' && (
        <div className="space-y-4 card-animate">
          {/* Filters */}
          <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-4">
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  type="text"
                  value={auditAction}
                  onChange={(e) => { setAuditAction(e.target.value); setAuditPage(1) }}
                  placeholder="Filter by action..."
                  className="w-full pl-9 pr-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
                />
              </div>
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-slate-400" />
                <input
                  type="date"
                  value={auditDateFrom}
                  onChange={(e) => { setAuditDateFrom(e.target.value); setAuditPage(1) }}
                  className="px-3 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
                />
                <span className="text-slate-400 text-sm">to</span>
                <input
                  type="date"
                  value={auditDateTo}
                  onChange={(e) => { setAuditDateTo(e.target.value); setAuditPage(1) }}
                  className="px-3 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
                />
              </div>
            </div>
          </div>

          {/* Audit Table */}
          <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand overflow-hidden">
            {loading && !auditData ? (
              <div className="flex justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-brand-600" />
              </div>
            ) : auditData?.items?.length === 0 ? (
              <div className="p-8 text-center">
                <FileText className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                <p className="text-sm text-slate-500">No audit logs found.</p>
              </div>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-brand-50">
                        <th className="text-left px-5 py-3.5 text-xs font-bold text-slate-500 uppercase tracking-wide">Time</th>
                        <th className="text-left px-5 py-3.5 text-xs font-bold text-slate-500 uppercase tracking-wide">Actor</th>
                        <th className="text-left px-5 py-3.5 text-xs font-bold text-slate-500 uppercase tracking-wide">Action</th>
                        <th className="text-left px-5 py-3.5 text-xs font-bold text-slate-500 uppercase tracking-wide">Resource</th>
                        <th className="text-left px-5 py-3.5 text-xs font-bold text-slate-500 uppercase tracking-wide">Details</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-brand-50">
                      {auditData?.items?.map((log) => (
                        <tr key={log.id} className="hover:bg-brand-50/30 transition-colors">
                          <td className="px-5 py-3.5 text-slate-500 text-xs whitespace-nowrap">{formatDate(log.created_at)}</td>
                          <td className="px-5 py-3.5 text-slate-700 font-medium">{log.actor_email}</td>
                          <td className="px-5 py-3.5">
                            <span className="px-2 py-0.5 bg-brand-50 text-brand-700 text-xs font-bold rounded-full ring-1 ring-brand-200">
                              {log.action}
                            </span>
                          </td>
                          <td className="px-5 py-3.5 text-slate-700">
                            {log.resource_type}
                            {log.resource_id !== null && log.resource_id !== undefined && (
                              <span className="text-slate-400 ml-1">#{log.resource_id}</span>
                            )}
                          </td>
                          <td className="px-5 py-3.5 text-slate-500 text-xs max-w-xs truncate">
                            {log.details ? JSON.stringify(log.details) : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                {auditData && auditData.pages > 1 && (
                  <div className="flex items-center justify-between px-5 py-3 border-t border-brand-50">
                    <p className="text-xs text-slate-500">
                      Showing {(auditData.page - 1) * auditData.per_page + 1} -{' '}
                      {Math.min(auditData.page * auditData.per_page, auditData.total)} of {auditData.total}
                    </p>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => setAuditPage((p) => Math.max(1, p - 1))}
                        disabled={auditPage <= 1}
                        className="p-1.5 rounded-lg hover:bg-brand-50 text-slate-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                      >
                        <ChevronLeft className="w-4 h-4" />
                      </button>
                      <span className="text-xs text-slate-600 font-medium px-2">
                        Page {auditData.page} of {auditData.pages}
                      </span>
                      <button
                        onClick={() => setAuditPage((p) => Math.min(auditData.pages, p + 1))}
                        disabled={auditPage >= auditData.pages}
                        className="p-1.5 rounded-lg hover:bg-brand-50 text-slate-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                      >
                        <ChevronRight className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {/* Rate Limits Tab */}
      {activeTab === 'rate-limits' && (
        <div className="space-y-4 card-animate">
          {/* Filters */}
          <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-4">
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  type="text"
                  value={rateLimitSearch}
                  onChange={(e) => { setRateLimitSearch(e.target.value); setRateLimitPage(1) }}
                  placeholder="Search by tenant name or slug..."
                  className="w-full pl-9 pr-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
                />
              </div>
            </div>
          </div>

          {/* Table */}
          <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand overflow-hidden">
            {rateLimitsLoading && !rateLimitsData ? (
              <div className="flex justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-brand-600" />
              </div>
            ) : rateLimitsError ? (
              <div className="p-8 text-center">
                <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-2" />
                <p className="text-sm text-red-600">{rateLimitsError}</p>
                <button
                  onClick={fetchRateLimits}
                  className="mt-3 px-4 py-2 btn-brand text-white text-sm font-bold rounded-xl"
                >
                  Retry
                </button>
              </div>
            ) : rateLimitsData?.items?.length === 0 ? (
              <div className="p-8 text-center">
                <SlidersHorizontal className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                <p className="text-sm text-slate-500">No rate limit configurations found.</p>
              </div>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-brand-50">
                        <th className="text-left px-5 py-3.5 text-xs font-bold text-slate-500 uppercase tracking-wide">Tenant</th>
                        <th className="text-left px-5 py-3.5 text-xs font-bold text-slate-500 uppercase tracking-wide">Requests/Min</th>
                        <th className="text-left px-5 py-3.5 text-xs font-bold text-slate-500 uppercase tracking-wide">LLM Concurrent</th>
                        <th className="text-left px-5 py-3.5 text-xs font-bold text-slate-500 uppercase tracking-wide">Status</th>
                        <th className="text-right px-5 py-3.5 text-xs font-bold text-slate-500 uppercase tracking-wide">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-brand-50">
                      {rateLimitsData?.items?.map((item) => (
                        <tr key={item.id} className="hover:bg-brand-50/30 transition-colors">
                          <td className="px-5 py-3.5">
                            <p className="font-bold text-brand-900">{item.tenant_name}</p>
                            <p className="text-xs text-slate-500">{item.tenant_slug}</p>
                          </td>
                          <td className="px-5 py-3.5">
                            <span className="text-sm font-semibold text-brand-900">{item.requests_per_minute}</span>
                          </td>
                          <td className="px-5 py-3.5">
                            <span className="text-sm font-semibold text-brand-900">{item.llm_concurrent_max}</span>
                          </td>
                          <td className="px-5 py-3.5">
                            <span className="px-2 py-0.5 bg-green-50 text-green-700 text-xs font-bold rounded-full ring-1 ring-green-200">
                              Configured
                            </span>
                          </td>
                          <td className="px-5 py-3.5 text-right">
                            <div className="flex items-center justify-end gap-1.5">
                              <button
                                onClick={() => {
                                  setEditRateLimitTenant(item)
                                  setEditRateLimitForm({
                                    requests_per_minute: item.requests_per_minute,
                                    llm_concurrent_max: item.llm_concurrent_max,
                                  })
                                }}
                                className="p-1.5 rounded-lg hover:bg-brand-100 text-slate-400 hover:text-brand-600 transition-colors"
                                title="Edit"
                              >
                                <Settings className="w-4 h-4" />
                              </button>
                              <button
                                onClick={async () => {
                                  if (confirm('Delete this rate limit configuration? Tenant will use defaults (60 req/min, 2 LLM concurrent).')) {
                                    try {
                                      await deleteTenantRateLimit(item.tenant_id)
                                      fetchRateLimits()
                                    } catch (err) {
                                      alert(err.response?.data?.detail || 'Failed to delete')
                                    }
                                  }
                                }}
                                className="p-1.5 rounded-lg hover:bg-red-100 text-slate-400 hover:text-red-600 transition-colors"
                                title="Delete"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                {rateLimitsData && rateLimitsData.pages > 1 && (
                  <div className="flex items-center justify-between px-5 py-3 border-t border-brand-50">
                    <p className="text-xs text-slate-500">
                      Showing {(rateLimitsData.page - 1) * rateLimitsData.per_page + 1} -{' '}
                      {Math.min(rateLimitsData.page * rateLimitsData.per_page, rateLimitsData.total)} of {rateLimitsData.total}
                    </p>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => setRateLimitPage((p) => Math.max(1, p - 1))}
                        disabled={rateLimitPage <= 1}
                        className="p-1.5 rounded-lg hover:bg-brand-50 text-slate-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                      >
                        <ChevronLeft className="w-4 h-4" />
                      </button>
                      <span className="text-xs text-slate-600 font-medium px-2">
                        Page {rateLimitsData.page} of {rateLimitsData.pages}
                      </span>
                      <button
                        onClick={() => setRateLimitPage((p) => Math.min(rateLimitsData.pages, p + 1))}
                        disabled={rateLimitPage >= rateLimitsData.pages}
                        className="p-1.5 rounded-lg hover:bg-brand-50 text-slate-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                      >
                        <ChevronRight className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {/* Edit Rate Limit Modal */}
      {editRateLimitTenant && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white/95 backdrop-blur-xl rounded-3xl ring-1 ring-brand-100 shadow-brand-xl w-full max-w-md p-6 card-animate">
            <div className="flex items-center justify-between mb-5">
              <h3 className="font-extrabold text-brand-900 tracking-tight text-lg">Edit Rate Limit</h3>
              <button onClick={() => setEditRateLimitTenant(null)} className="p-1.5 hover:bg-brand-50 rounded-xl transition-colors">
                <X className="w-5 h-5 text-slate-400" />
              </button>
            </div>

            <p className="text-sm text-slate-500 mb-4">
              Configure rate limits for <span className="font-semibold text-slate-700">{editRateLimitTenant.tenant_name}</span>
            </p>

            <div className="space-y-4 mb-6">
              <div>
                <label className="block text-sm font-bold text-slate-700 mb-1.5">Requests per Minute</label>
                <input
                  type="number"
                  value={editRateLimitForm.requests_per_minute}
                  onChange={(e) => setEditRateLimitForm({ ...editRateLimitForm, requests_per_minute: parseInt(e.target.value, 10) || 0 })}
                  min="1"
                  className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
                />
                <p className="text-xs text-slate-400 mt-1">Default: 60 requests/minute</p>
              </div>

              <div>
                <label className="block text-sm font-bold text-slate-700 mb-1.5">LLM Concurrent Requests</label>
                <input
                  type="number"
                  value={editRateLimitForm.llm_concurrent_max}
                  onChange={(e) => setEditRateLimitForm({ ...editRateLimitForm, llm_concurrent_max: parseInt(e.target.value, 10) || 0 })}
                  min="1"
                  className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
                />
                <p className="text-xs text-slate-400 mt-1">Default: 2 concurrent LLM requests</p>
              </div>
            </div>

            <div className="flex justify-end gap-2">
              <button
                onClick={() => setEditRateLimitTenant(null)}
                className="px-4 py-2 ring-1 ring-brand-200 text-sm font-semibold text-brand-700 rounded-xl hover:bg-brand-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  setEditRateLimitSaving(true)
                  try {
                    await updateTenantRateLimit(editRateLimitTenant.tenant_id, editRateLimitForm)
                    setEditRateLimitTenant(null)
                    fetchRateLimits()
                  } catch (err) {
                    alert(err.response?.data?.detail || 'Failed to update rate limit')
                  } finally {
                    setEditRateLimitSaving(false)
                  }
                }}
                disabled={editRateLimitSaving || editRateLimitForm.requests_per_minute < 1 || editRateLimitForm.llm_concurrent_max < 1}
                className="px-4 py-2 btn-brand text-white text-sm font-bold rounded-xl disabled:opacity-60"
              >
                {editRateLimitSaving ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Feature Flags Tab */}
      {activeTab === 'features' && (
        <div className="space-y-6 card-animate">
          {featureError && (
            <div className="p-4 bg-red-50 rounded-2xl ring-1 ring-red-200 flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-500 shrink-0" />
              <p className="text-sm text-red-700">{featureError}</p>
              <button onClick={() => { setFeatureError(''); fetchFeatureFlags() }} className="ml-auto text-sm font-semibold text-red-600 hover:text-red-700">Retry</button>
            </div>
          )}

          <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand overflow-hidden">
            <div className="px-6 py-4 border-b border-brand-50">
              <h3 className="font-extrabold text-brand-900 tracking-tight">Global Feature Flags</h3>
            </div>
            {featureLoading && !featureFlags ? (
              <div className="flex justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-brand-600" />
              </div>
            ) : featureFlags?.length === 0 ? (
              <div className="p-8 text-center">
                <SlidersHorizontal className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                <p className="text-sm text-slate-500">No feature flags configured.</p>
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-brand-50">
                    <th className="text-left px-5 py-3.5 text-xs font-bold text-slate-500 uppercase tracking-wide">Key</th>
                    <th className="text-left px-5 py-3.5 text-xs font-bold text-slate-500 uppercase tracking-wide">Display Name</th>
                    <th className="text-left px-5 py-3.5 text-xs font-bold text-slate-500 uppercase tracking-wide">Description</th>
                    <th className="text-center px-5 py-3.5 text-xs font-bold text-slate-500 uppercase tracking-wide">Enabled Globally</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-brand-50">
                  {featureFlags?.map((flag) => (
                    <tr key={flag.id} className="hover:bg-brand-50/30 transition-colors">
                      <td className="px-5 py-3.5 font-mono text-xs text-brand-700">{flag.key}</td>
                      <td className="px-5 py-3.5 text-slate-700 font-medium">{flag.display_name || '—'}</td>
                      <td className="px-5 py-3.5 text-slate-500 text-xs max-w-xs truncate">{flag.description || '—'}</td>
                      <td className="px-5 py-3.5 text-center">
                        <button
                          onClick={async () => {
                            try {
                              await toggleFeatureFlag(flag.id, !flag.enabled_globally)
                              fetchFeatureFlags()
                              if (ffTenantId) fetchTenantOverrides(ffTenantId)
                            } catch (err) {
                              setFeatureError(err.response?.data?.detail || 'Failed to toggle flag')
                            }
                          }}
                          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                            flag.enabled_globally ? 'bg-brand-600' : 'bg-slate-200'
                          }`}
                        >
                          <span
                            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                              flag.enabled_globally ? 'translate-x-6' : 'translate-x-1'
                            }`}
                          />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Per-Tenant Overrides */}
          <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6">
            <h3 className="font-extrabold text-brand-900 tracking-tight mb-4">Per-Tenant Overrides</h3>
            <div className="flex items-center gap-3 mb-4">
              <select
                value={ffTenantId}
                onChange={(e) => {
                  setFfTenantId(e.target.value)
                  if (e.target.value) fetchTenantOverrides(e.target.value)
                  else setTenantOverrides(null)
                }}
                className="px-3 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white flex-1"
              >
                <option value="">Select a tenant...</option>
                {tenantsData?.items?.map((t) => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </select>
            </div>
            {overrideLoading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-brand-600" />
              </div>
            ) : ffTenantId && tenantOverrides ? (
              tenantOverrides.length === 0 ? (
                <p className="text-sm text-slate-500">No overrides for this tenant. All flags use global settings.</p>
              ) : (
                <div className="divide-y divide-brand-50 ring-1 ring-brand-100 rounded-xl overflow-hidden">
                  {tenantOverrides.map((o) => (
                    <div key={o.id} className="flex items-center justify-between px-4 py-3 bg-white">
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-medium text-slate-700">{o.feature_key || `Flag #${o.feature_flag_id}`}</span>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-bold ring-1 ${o.enabled ? 'bg-green-50 text-green-700 ring-green-200' : 'bg-red-50 text-red-700 ring-red-200'}`}>
                          {o.enabled ? 'Enabled' : 'Disabled'}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={async () => {
                            try {
                              await setTenantFeatureOverride(ffTenantId, o.feature_flag_id, !o.enabled)
                              fetchTenantOverrides(ffTenantId)
                            } catch (err) {
                              setFeatureError(err.response?.data?.detail || 'Failed to update override')
                            }
                          }}
                          className="text-xs font-semibold text-brand-600 hover:text-brand-700"
                        >Toggle</button>
                        <button
                          onClick={async () => {
                            try {
                              await deleteTenantFeatureOverride(ffTenantId, o.feature_flag_id)
                              fetchTenantOverrides(ffTenantId)
                            } catch (err) {
                              setFeatureError(err.response?.data?.detail || 'Failed to remove override')
                            }
                          }}
                          className="text-xs font-semibold text-red-600 hover:text-red-700"
                        >Remove</button>
                      </div>
                    </div>
                  ))}
                </div>
              )
            ) : ffTenantId ? (
              <p className="text-sm text-slate-500">Select a tenant to view overrides.</p>
            ) : null}
          </div>
        </div>
      )}

      {/* Webhooks Tab */}
      {activeTab === 'webhooks' && (
        <div className="space-y-6 card-animate">
          {whError && (
            <div className="p-4 bg-red-50 rounded-2xl ring-1 ring-red-200 flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-500 shrink-0" />
              <p className="text-sm text-red-700">{whError}</p>
              <button onClick={() => { setWhError(''); if (whTenantId) fetchWebhooks(whTenantId) }} className="ml-auto text-sm font-semibold text-red-600 hover:text-red-700">Retry</button>
            </div>
          )}

          {/* Tenant Selector */}
          <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-4">
            <div className="flex items-center gap-3">
              <Building2 className="w-4 h-4 text-slate-400" />
              <select
                value={whTenantId}
                onChange={(e) => setWhTenantId(e.target.value)}
                className="px-3 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white flex-1"
              >
                <option value="">Select a tenant...</option>
                {tenantsData?.items?.map((t) => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </select>
            </div>
          </div>

          {whTenantId && (
            <>
              <div className="flex items-center justify-between">
                <h3 className="font-extrabold text-brand-900 tracking-tight">Webhooks</h3>
                <button
                  onClick={() => setShowAddWebhook(true)}
                  className="flex items-center gap-2 px-4 py-2 btn-brand text-white text-sm font-bold rounded-xl shadow-brand-sm"
                >
                  <Zap className="w-4 h-4" /> Add Webhook
                </button>
              </div>

              {whLoading ? (
                <div className="flex justify-center py-12">
                  <Loader2 className="w-8 h-8 animate-spin text-brand-600" />
                </div>
              ) : webhooks?.length === 0 ? (
                <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-12 text-center">
                  <Zap className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                  <p className="text-sm text-slate-500">No webhooks configured for this tenant.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {webhooks?.map((wh) => (
                    <div key={wh.id} className="bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 shadow-brand overflow-hidden">
                      <div className="p-5">
                        <div className="flex items-start justify-between">
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-bold text-brand-900 truncate">{wh.url}</p>
                            <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                              {wh.events?.map((ev) => (
                                <span key={ev} className="px-2 py-0.5 bg-brand-50 text-brand-700 text-xs font-bold rounded-full ring-1 ring-brand-200">{ev}</span>
                              ))}
                              <span className={`px-2 py-0.5 rounded-full text-xs font-bold ring-1 ${wh.is_active ? 'bg-green-50 text-green-700 ring-green-200' : 'bg-slate-50 text-slate-600 ring-slate-200'}`}>
                                {wh.is_active ? 'Active' : 'Inactive'}
                              </span>
                              {wh.failure_count > 0 && (
                                <span className="px-2 py-0.5 bg-red-50 text-red-700 text-xs font-bold rounded-full ring-1 ring-red-200">
                                  {wh.failure_count} failures
                                </span>
                              )}
                            </div>
                            <p className="text-xs text-slate-500 mt-1.5">
                              Last triggered: {wh.last_triggered_at ? new Date(wh.last_triggered_at).toLocaleString() : 'Never'}
                            </p>
                          </div>
                          <div className="flex items-center gap-2 ml-4">
                            <button
                              onClick={async () => {
                                try {
                                  const data = await getWebhookDeliveries(whTenantId, wh.id)
                                  setWhDeliveries((prev) => ({ ...prev, [wh.id]: data }))
                                  setExpandedWhId(expandedWhId === wh.id ? null : wh.id)
                                } catch {
                                  setWhError('Failed to load deliveries')
                                }
                              }}
                              className="p-1.5 rounded-lg hover:bg-brand-100 text-slate-400 hover:text-brand-600 transition-colors"
                              title="View deliveries"
                            >
                              <Eye className="w-4 h-4" />
                            </button>
                            <button
                              onClick={async () => {
                                if (!confirm('Delete this webhook?')) return
                                try {
                                  await deleteTenantWebhook(whTenantId, wh.id)
                                  fetchWebhooks(whTenantId)
                                } catch (err) {
                                  setWhError(err.response?.data?.detail || 'Failed to delete webhook')
                                }
                              }}
                              className="p-1.5 rounded-lg hover:bg-red-100 text-slate-400 hover:text-red-600 transition-colors"
                              title="Delete webhook"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      </div>
                      {/* Delivery History */}
                      {expandedWhId === wh.id && whDeliveries[wh.id] && (
                        <div className="border-t border-brand-50 bg-brand-50/30">
                          <div className="px-5 py-3">
                            <p className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-2">Delivery History</p>
                            {whDeliveries[wh.id].length === 0 ? (
                              <p className="text-sm text-slate-500">No deliveries yet.</p>
                            ) : (
                              <div className="divide-y divide-brand-100">
                                {whDeliveries[wh.id].map((d) => (
                                  <div key={d.id} className="flex items-center justify-between py-2">
                                    <div className="flex items-center gap-2">
                                      <span className={`w-2 h-2 rounded-full ${d.success ? 'bg-green-500' : 'bg-red-500'}`} />
                                      <span className="text-sm text-slate-700">{d.event}</span>
                                    </div>
                                    <div className="flex items-center gap-3">
                                      <span className="text-xs text-slate-500">HTTP {d.response_status || '—'}</span>
                                      <span className="text-xs text-slate-400">Attempt {d.attempt}</span>
                                      <span className="text-xs text-slate-400">{d.created_at ? new Date(d.created_at).toLocaleString() : '—'}</span>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}

          {/* Add Webhook Modal */}
          {showAddWebhook && (
            <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
              <div className="bg-white/95 backdrop-blur-xl rounded-3xl ring-1 ring-brand-100 shadow-brand-xl w-full max-w-md p-6 card-animate">
                <div className="flex items-center justify-between mb-5">
                  <h3 className="font-extrabold text-brand-900 tracking-tight">Add Webhook</h3>
                  <button onClick={() => setShowAddWebhook(false)} className="p-1.5 hover:bg-brand-50 rounded-xl transition-colors">
                    <X className="w-5 h-5 text-slate-400" />
                  </button>
                </div>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-bold text-slate-700 mb-1.5">URL</label>
                    <input
                      type="url"
                      value={whUrl}
                      onChange={(e) => setWhUrl(e.target.value)}
                      placeholder="https://example.com/webhook"
                      className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-bold text-slate-700 mb-1.5">Events</label>
                    <div className="flex flex-wrap gap-2">
                      {['*', 'analysis.completed', 'analysis.failed', 'tenant.suspended', 'tenant.reactivated', 'plan.changed'].map((ev) => (
                        <label key={ev} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg ring-1 ring-brand-200 cursor-pointer hover:bg-brand-50/50 transition-colors">
                          <input
                            type="checkbox"
                            checked={whEvents.includes(ev)}
                            onChange={(e) => {
                              if (ev === '*') {
                                setWhEvents(e.target.checked ? ['*'] : [])
                              } else {
                                setWhEvents((prev) => {
                                  const next = prev.filter((x) => x !== '*')
                                  return e.target.checked ? [...next, ev] : next.filter((x) => x !== ev)
                                })
                              }
                            }}
                            className="w-3.5 h-3.5 text-brand-600"
                          />
                          <span className="text-xs font-medium text-slate-700">{ev}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      onClick={() => setShowAddWebhook(false)}
                      className="px-4 py-2 ring-1 ring-brand-200 text-sm font-semibold text-brand-700 rounded-xl hover:bg-brand-50 transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={async () => {
                        if (!whUrl.trim()) return
                        setWhSubmitting(true)
                        try {
                          await createTenantWebhook(whTenantId, { url: whUrl.trim(), events: whEvents.length ? whEvents : ['*'] })
                          setShowAddWebhook(false)
                          setWhUrl('')
                          setWhEvents(['*'])
                          fetchWebhooks(whTenantId)
                        } catch (err) {
                          setWhError(err.response?.data?.detail || 'Failed to create webhook')
                        } finally {
                          setWhSubmitting(false)
                        }
                      }}
                      disabled={whSubmitting || !whUrl.trim()}
                      className="px-4 py-2 btn-brand text-white text-sm font-bold rounded-xl disabled:opacity-60 shadow-brand-sm"
                    >
                      {whSubmitting ? 'Creating...' : 'Create Webhook'}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Metrics Tab */}
      {activeTab === 'metrics' && (
        <div className="space-y-6 card-animate">
          {metricsError && (
            <div className="p-4 bg-red-50 rounded-2xl ring-1 ring-red-200 flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-500 shrink-0" />
              <p className="text-sm text-red-700">{metricsError}</p>
              <button onClick={() => { setMetricsError(''); fetchMetrics() }} className="ml-auto text-sm font-semibold text-red-600 hover:text-red-700">Retry</button>
            </div>
          )}

          {metricsLoading ? (
            <div className="flex justify-center py-16">
              <Loader2 className="w-8 h-8 animate-spin text-brand-600" />
            </div>
          ) : metricsData ? (
            <>
              {/* Summary Cards */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <SummaryCard title="Total Tenants" value={metricsData.tenants?.total ?? 0} icon={Building2} color="brand" />
                <SummaryCard title="Active Users" value={metricsData.users?.total ?? 0} icon={Users} color="blue" />
                <SummaryCard title="Analyses Today" value={metricsData.analyses?.today ?? 0} icon={Activity} color="green" />
                <SummaryCard title="MRR" value={`$${((metricsData.revenue?.mrr_cents ?? 0) / 100).toLocaleString()}`} icon={CreditCard} color="amber" />
              </div>

              {/* Plan Distribution */}
              <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6">
                <h3 className="font-extrabold text-brand-900 tracking-tight mb-4">Plan Distribution</h3>
                {metricsData.plans && Object.keys(metricsData.plans).length > 0 ? (
                  <div className="space-y-3">
                    {Object.entries(metricsData.plans).map(([plan, count]) => {
                      const total = Object.values(metricsData.plans).reduce((a, b) => a + b, 0)
                      const pct = total > 0 ? Math.round((count / total) * 100) : 0
                      return (
                        <div key={plan}>
                          <div className="flex justify-between text-sm mb-1">
                            <span className="font-medium text-slate-700">{plan}</span>
                            <span className="text-slate-500">{count} ({pct}%)</span>
                          </div>
                          <div className="w-full bg-slate-100 rounded-full h-2">
                            <div className="h-2 rounded-full bg-brand-500 transition-all" style={{ width: `${pct}%` }} />
                          </div>
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <p className="text-sm text-slate-500">No plan data available.</p>
                )}
              </div>

              {/* Usage Trends - Visual Chart */}
              <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6">
                <h3 className="font-extrabold text-brand-900 tracking-tight mb-4">Daily Analyses (Last 30 Days)</h3>
                {trendsData?.analyses?.length > 0 ? (
                  <div>
                    {/* Bar Chart Visualization */}
                    <div className="flex items-end gap-1 h-48 mb-4">
                      {(() => {
                        const maxCount = Math.max(...trendsData.analyses.map(d => d.count), 1)
                        return trendsData.analyses.map((d, idx) => {
                          const height = (d.count / maxCount) * 100
                          return (
                            <div
                              key={d.date}
                              className="flex-1 bg-brand-500 hover:bg-brand-600 transition-colors rounded-t-sm relative group"
                              style={{ height: `${Math.max(height, 2)}%` }}
                              title={`${d.date}: ${d.count} analyses`}
                            >
                              <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-brand-900 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10">
                                {d.count}
                              </div>
                            </div>
                          )
                        })
                      })()}
                    </div>

                    {/* X-axis labels */}
                    <div className="flex gap-1 text-xs text-slate-400">
                      {trendsData.analyses.filter((_, i) => i % 5 === 0).map((d) => (
                        <div key={d.date} className="flex-1 text-center truncate">
                          {new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                        </div>
                      ))}
                    </div>

                    <div className="mt-4 flex items-center gap-2 text-sm text-slate-600">
                      <TrendingUp className="w-4 h-4 text-green-600" />
                      <span>Total: <strong>{trendsData.analyses.reduce((sum, d) => sum + d.count, 0).toLocaleString()}</strong> analyses</span>
                      <span className="mx-2">•</span>
                      <span>Avg: <strong>{Math.round(trendsData.analyses.reduce((sum, d) => sum + d.count, 0) / trendsData.analyses.length).toLocaleString()}</strong>/day</span>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-slate-500">No trend data available.</p>
                )}
              </div>

              {/* Tenant Signups Trend */}
              <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6">
                <h3 className="font-extrabold text-brand-900 tracking-tight mb-4">New Tenant Signups (Last 30 Days)</h3>
                {trendsData?.signups?.length > 0 ? (
                  <div>
                    <div className="flex items-end gap-1 h-40 mb-4">
                      {(() => {
                        const maxCount = Math.max(...trendsData.signups.map(d => d.count), 1)
                        return trendsData.signups.map((d) => {
                          const height = (d.count / maxCount) * 100
                          return (
                            <div
                              key={d.date}
                              className="flex-1 bg-blue-500 hover:bg-blue-600 transition-colors rounded-t-sm relative group"
                              style={{ height: `${Math.max(height, 2)}%` }}
                              title={`${d.date}: ${d.count} signups`}
                            >
                              <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-brand-900 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10">
                                {d.count}
                              </div>
                            </div>
                          )
                        })
                      })()}
                    </div>

                    <div className="mt-4 flex items-center gap-2 text-sm text-slate-600">
                      <Building2 className="w-4 h-4 text-blue-600" />
                      <span>Total: <strong>{trendsData.signups.reduce((sum, d) => sum + d.count, 0)}</strong> new tenants</span>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-slate-500">No signup data available.</p>
                )}
              </div>
            </>
          ) : !metricsLoading ? (
            <p className="text-sm text-slate-500">No metrics data available.</p>
          ) : null}
        </div>
      )}

      {/* Billing Tab */}
      {activeTab === 'billing' && (
        <div className="space-y-6 card-animate">
          {billingError && (
            <div className="p-4 bg-red-50 rounded-2xl ring-1 ring-red-200 flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-500 shrink-0" />
              <p className="text-sm text-red-700">{billingError}</p>
              <button onClick={() => { setBillingError(''); fetchBillingConfig() }} className="ml-auto text-sm font-semibold text-red-600 hover:text-red-700">Retry</button>
            </div>
          )}

          <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6">
            <h3 className="font-extrabold text-brand-900 tracking-tight mb-4">Payment Provider</h3>
            {billingLoading ? (
              <div className="flex justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-brand-600" />
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center gap-3 p-3 bg-brand-50/50 rounded-xl ring-1 ring-brand-100">
                  <CreditCard className="w-5 h-5 text-brand-600" />
                  <div>
                    <p className="text-xs text-slate-500 font-medium">Active Provider</p>
                    <p className="text-sm font-bold text-brand-900">{billingConfig?.provider ? billingConfig.provider.charAt(0).toUpperCase() + billingConfig.provider.slice(1) : 'Not configured'}</p>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-bold text-slate-700 mb-1.5">Select Provider</label>
                  <select
                    value={selectedProvider}
                    onChange={(e) => setSelectedProvider(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
                  >
                    <option value="">None</option>
                    <option value="stripe">Stripe</option>
                    <option value="razorpay">Razorpay</option>
                    <option value="manual">Manual</option>
                  </select>
                </div>

                {(selectedProvider === 'stripe' || selectedProvider === 'razorpay') && (
                  <div className="space-y-3">
                    <div>
                      <label className="block text-sm font-bold text-slate-700 mb-1.5">
                        {selectedProvider === 'stripe' ? 'Stripe' : 'Razorpay'} API Key
                      </label>
                      <input
                        type="password"
                        value={providerApiKey}
                        onChange={(e) => setProviderApiKey(e.target.value)}
                        placeholder={billingConfig?.api_key_last4 ? `****${billingConfig.api_key_last4}` : 'Enter API key'}
                        className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
                      />
                      {billingConfig?.api_key_last4 && !providerApiKey && (
                        <p className="text-xs text-slate-500 mt-1">Current key ends in ****{billingConfig.api_key_last4}</p>
                      )}
                    </div>
                    <div>
                      <label className="block text-sm font-bold text-slate-700 mb-1.5">
                        {selectedProvider === 'stripe' ? 'Stripe' : 'Razorpay'} Secret Key
                      </label>
                      <input
                        type="password"
                        value={providerSecretKey}
                        onChange={(e) => setProviderSecretKey(e.target.value)}
                        placeholder={billingConfig?.secret_key_last4 ? `****${billingConfig.secret_key_last4}` : 'Enter secret key'}
                        className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
                      />
                      {billingConfig?.secret_key_last4 && !providerSecretKey && (
                        <p className="text-xs text-slate-500 mt-1">Current key ends in ****{billingConfig.secret_key_last4}</p>
                      )}
                    </div>
                  </div>
                )}

                <div className="flex justify-end">
                  <button
                    onClick={async () => {
                      setBillingSaving(true)
                      try {
                        const payload = { provider: selectedProvider }
                        if (providerApiKey) payload.api_key = providerApiKey
                        if (providerSecretKey) payload.secret_key = providerSecretKey
                        await updateBillingConfig(payload)
                        setProviderApiKey('')
                        setProviderSecretKey('')
                        fetchBillingConfig()
                      } catch (err) {
                        setBillingError(err.response?.data?.detail || 'Failed to save billing config')
                      } finally {
                        setBillingSaving(false)
                      }
                    }}
                    disabled={billingSaving}
                    className="px-4 py-2 btn-brand text-white text-sm font-bold rounded-xl disabled:opacity-60 shadow-brand-sm"
                  >
                    {billingSaving ? 'Saving...' : 'Save Configuration'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Notifications Tab */}
      {activeTab === 'notifications' && (
        <div className="space-y-6 card-animate">
          {notificationError && (
            <div className="p-4 bg-red-50 rounded-2xl ring-1 ring-red-200 flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-500 shrink-0" />
              <p className="text-sm text-red-700">{notificationError}</p>
              <button onClick={() => { setNotificationError(''); fetchNotificationConfig() }} className="ml-auto text-sm font-semibold text-red-600 hover:text-red-700">Retry</button>
            </div>
          )}

          <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6">
            <h3 className="font-extrabold text-brand-900 tracking-tight mb-4">SMTP Configuration</h3>
            {notificationLoading ? (
              <div className="flex justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-brand-600" />
              </div>
            ) : (
              <div className="space-y-4">
                <div className={`flex items-center gap-3 p-3 rounded-xl ring-1 ${
                  notificationConfig?.configured
                    ? 'bg-green-50/50 ring-green-200'
                    : 'bg-amber-50/50 ring-amber-200'
                }`}>
                  <Mail className={`w-5 h-5 ${notificationConfig?.configured ? 'text-green-600' : 'text-amber-600'}`} />
                  <div>
                    <p className="text-xs text-slate-500 font-medium">Status</p>
                    <p className={`text-sm font-bold ${notificationConfig?.configured ? 'text-green-700' : 'text-amber-700'}`}>
                      {notificationConfig?.configured ? 'Configured' : 'Not Configured'}
                    </p>
                  </div>
                </div>

                {notificationConfig?.configured && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div className="p-3 bg-brand-50/50 rounded-xl ring-1 ring-brand-100">
                      <p className="text-xs text-slate-500 font-medium">SMTP Host</p>
                      <p className="text-sm font-bold text-brand-900 mt-0.5">{notificationConfig.smtp_host || '—'}</p>
                    </div>
                    <div className="p-3 bg-brand-50/50 rounded-xl ring-1 ring-brand-100">
                      <p className="text-xs text-slate-500 font-medium">From Address</p>
                      <p className="text-sm font-bold text-brand-900 mt-0.5">{notificationConfig.from_address || '—'}</p>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6">
            <h3 className="font-extrabold text-brand-900 tracking-tight mb-4">Send Test Email</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-bold text-slate-700 mb-1.5">Recipient Email</label>
                <input
                  type="email"
                  value={testEmail}
                  onChange={(e) => { setTestEmail(e.target.value); setTestEmailResult(null) }}
                  placeholder="test@example.com"
                  className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
                />
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={async () => {
                    if (!testEmail.trim()) return
                    setTestEmailSending(true)
                    setTestEmailResult(null)
                    try {
                      await sendTestEmail(testEmail.trim())
                      setTestEmailResult({ success: true, message: `Test email sent to ${testEmail.trim()}` })
                    } catch (err) {
                      setTestEmailResult({ success: false, message: err.response?.data?.detail || 'Failed to send test email' })
                    } finally {
                      setTestEmailSending(false)
                    }
                  }}
                  disabled={testEmailSending || !testEmail.trim()}
                  className="flex items-center gap-2 px-4 py-2 btn-brand text-white text-sm font-bold rounded-xl disabled:opacity-60 shadow-brand-sm"
                >
                  <Mail className="w-4 h-4" />
                  {testEmailSending ? 'Sending...' : 'Send Test Email'}
                </button>
              </div>
              {testEmailResult && (
                <div className={`p-3 rounded-xl ring-1 ${
                  testEmailResult.success
                    ? 'bg-green-50 ring-green-200 text-green-700'
                    : 'bg-red-50 ring-red-200 text-red-700'
                }`}>
                  <p className="text-sm font-medium">{testEmailResult.message}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Modals */}
      {detailTenantId && (
        <TenantDetailModal
          tenantId={detailTenantId}
          onClose={() => setDetailTenantId(null)}
          onAction={handleAction}
        />
      )}
      {changePlanTenant && (
        <ChangePlanModal
          tenant={changePlanTenant}
          plans={plans}
          onClose={() => setChangePlanTenant(null)}
          onChange={(tenantId, planId) => handleAction('change-plan', tenantId, planId)}
        />
      )}
      {suspendTenantObj && (
        <SuspendModal
          tenant={suspendTenantObj}
          onClose={() => setSuspendTenantObj(null)}
          onConfirm={(tenantId, reason) => handleAction('suspend', tenantId, reason)}
        />
      )}

      {/* Create Tenant Modal */}
      {showCreateTenant && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white/95 backdrop-blur-xl rounded-3xl ring-1 ring-brand-100 shadow-brand-xl w-full max-w-md p-6 card-animate">
            <div className="flex items-center justify-between mb-5">
              <h3 className="font-extrabold text-brand-900 tracking-tight text-lg">Create New Tenant</h3>
              <button onClick={() => setShowCreateTenant(false)} className="p-1.5 hover:bg-brand-50 rounded-xl transition-colors">
                <X className="w-5 h-5 text-slate-400" />
              </button>
            </div>

            <div className="space-y-4 mb-6">
              <div>
                <label className="block text-sm font-bold text-slate-700 mb-1.5">Tenant Name <span className="text-red-500">*</span></label>
                <input
                  type="text"
                  value={createTenantForm.name}
                  onChange={(e) => setCreateTenantForm({ ...createTenantForm, name: e.target.value })}
                  placeholder="Acme Corporation"
                  className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
                />
              </div>

              <div>
                <label className="block text-sm font-bold text-slate-700 mb-1.5">Slug <span className="text-red-500">*</span></label>
                <input
                  type="text"
                  value={createTenantForm.slug}
                  onChange={(e) => setCreateTenantForm({ ...createTenantForm, slug: e.target.value.toLowerCase().replace(/\s+/g, '-') })}
                  placeholder="acme-corp"
                  className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
                />
                <p className="text-xs text-slate-400 mt-1">Lowercase, hyphens allowed</p>
              </div>

              <div>
                <label className="block text-sm font-bold text-slate-700 mb-1.5">Contact Email</label>
                <input
                  type="email"
                  value={createTenantForm.contact_email}
                  onChange={(e) => setCreateTenantForm({ ...createTenantForm, contact_email: e.target.value })}
                  placeholder="admin@acme.com"
                  className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
                />
              </div>

              <div>
                <label className="block text-sm font-bold text-slate-700 mb-1.5">Subscription Plan</label>
                <select
                  value={createTenantForm.plan_id}
                  onChange={(e) => setCreateTenantForm({ ...createTenantForm, plan_id: e.target.value })}
                  className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
                >
                  <option value="">No plan (free tier)</option>
                  {plans.map((plan) => (
                    <option key={plan.id} value={plan.id}>{plan.display_name}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowCreateTenant(false)}
                className="px-4 py-2 ring-1 ring-brand-200 text-sm font-semibold text-brand-700 rounded-xl hover:bg-brand-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  if (!createTenantForm.name || !createTenantForm.slug) {
                    alert('Name and slug are required')
                    return
                  }
                  setCreateTenantSaving(true)
                  try {
                    const payload = {
                      name: createTenantForm.name,
                      slug: createTenantForm.slug,
                      contact_email: createTenantForm.contact_email || null,
                      plan_id: createTenantForm.plan_id ? parseInt(createTenantForm.plan_id, 10) : null,
                    }
                    await createTenant(payload)
                    setShowCreateTenant(false)
                    setCreateTenantForm({ name: '', slug: '', contact_email: '', plan_id: '' })
                    fetchTenants()
                  } catch (err) {
                    alert(err.response?.data?.detail || 'Failed to create tenant')
                  } finally {
                    setCreateTenantSaving(false)
                  }
                }}
                disabled={createTenantSaving || !createTenantForm.name || !createTenantForm.slug}
                className="px-4 py-2 btn-brand text-white text-sm font-bold rounded-xl disabled:opacity-60"
              >
                {createTenantSaving ? 'Creating...' : 'Create Tenant'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Tenant Modal */}
      {editTenantObj && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white/95 backdrop-blur-xl rounded-3xl ring-1 ring-brand-100 shadow-brand-xl w-full max-w-md p-6 card-animate">
            <div className="flex items-center justify-between mb-5">
              <h3 className="font-extrabold text-brand-900 tracking-tight text-lg">Edit Tenant</h3>
              <button onClick={() => setEditTenantObj(null)} className="p-1.5 hover:bg-brand-50 rounded-xl transition-colors">
                <X className="w-5 h-5 text-slate-400" />
              </button>
            </div>

            <div className="space-y-4 mb-6">
              <div>
                <label className="block text-sm font-bold text-slate-700 mb-1.5">Tenant Name</label>
                <input
                  type="text"
                  value={editTenantForm.name}
                  onChange={(e) => setEditTenantForm({ ...editTenantForm, name: e.target.value })}
                  className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
                />
              </div>

              <div>
                <label className="block text-sm font-bold text-slate-700 mb-1.5">Slug</label>
                <input
                  type="text"
                  value={editTenantForm.slug}
                  onChange={(e) => setEditTenantForm({ ...editTenantForm, slug: e.target.value.toLowerCase().replace(/\s+/g, '-') })}
                  className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
                />
              </div>

              <div>
                <label className="block text-sm font-bold text-slate-700 mb-1.5">Contact Email</label>
                <input
                  type="email"
                  value={editTenantForm.contact_email}
                  onChange={(e) => setEditTenantForm({ ...editTenantForm, contact_email: e.target.value })}
                  className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
                />
              </div>

              <div>
                <label className="block text-sm font-bold text-slate-700 mb-1.5">Subscription Status</label>
                <select
                  value={editTenantForm.subscription_status}
                  onChange={(e) => setEditTenantForm({ ...editTenantForm, subscription_status: e.target.value })}
                  className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
                >
                  <option value="active">Active</option>
                  <option value="trialing">Trialing</option>
                  <option value="suspended">Suspended</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </div>
            </div>

            <div className="flex justify-end gap-2">
              <button
                onClick={() => setEditTenantObj(null)}
                className="px-4 py-2 ring-1 ring-brand-200 text-sm font-semibold text-brand-700 rounded-xl hover:bg-brand-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  setEditTenantSaving(true)
                  try {
                    await updateTenant(editTenantObj.id, editTenantForm)
                    setEditTenantObj(null)
                    fetchTenants()
                  } catch (err) {
                    alert(err.response?.data?.detail || 'Failed to update tenant')
                  } finally {
                    setEditTenantSaving(false)
                  }
                }}
                disabled={editTenantSaving}
                className="px-4 py-2 btn-brand text-white text-sm font-bold rounded-xl disabled:opacity-60"
              >
                {editTenantSaving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
