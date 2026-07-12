import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  Settings,
  User,
  Building2,
  CreditCard,
  Bell,
  Shield,
  Key,
  ChevronRight,
  Check,
  Loader2,
  AlertTriangle,
  Sparkles,
  Users,
  Zap,
  BarChart3,
  Calendar,
  RefreshCw,
  FileText,
  ChevronDown,
  ChevronUp,
  X,
  Receipt,
  ArrowLeft,
  ArrowRight,
  ExternalLink,
  Plug,
  Mic,
  Palette,
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useSubscription } from '../hooks/useSubscription'
import { adminResetUsage, adminChangePlan, getUserFriendlyError, getInvoices, getInvoice, getTenantBranding, updateTenantBranding } from '../lib/api'
import { sanitizePlanFeatures, TRUST, INTERVIEW } from '../lib/uxLabels'
import ATSIntegrationsPanel from '../components/settings/ATSIntegrationsPanel'
import InterviewSettingsPanel from '../components/settings/InterviewSettingsPanel'
import RequisitionSettingsPanel from '../components/settings/RequisitionSettingsPanel'

function Section({ title, icon: Icon, children, description }) {
  return (
    <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6 card-animate">
      <div className="flex items-start gap-4 mb-5">
        <div className="w-10 h-10 rounded-2xl bg-brand-50 ring-1 ring-brand-100 flex items-center justify-center shrink-0">
          <Icon className="w-5 h-5 text-brand-600" />
        </div>
        <div>
          <h3 className="font-extrabold text-brand-900 text-lg tracking-tight">{title}</h3>
          {description && <p className="text-sm text-slate-500 mt-0.5">{description}</p>}
        </div>
      </div>
      {children}
    </div>
  )
}

function ProgressBar({ value, max, color = 'brand' }) {
  const percentage = Math.min(100, Math.round((value / max) * 100))
  const colorClasses = {
    brand: 'bg-brand-500',
    green: 'bg-green-500',
    amber: 'bg-amber-500',
    red: 'bg-red-500'
  }
  return (
    <div className="w-full bg-slate-100 rounded-full h-2">
      <div
        className={`h-2 rounded-full transition-all duration-500 ${colorClasses[color] || colorClasses.brand}`}
        style={{ width: `${percentage}%` }}
      />
    </div>
  )
}

function UsageCard({ label, used, limit, unit = '' }) {
  const isUnlimited = limit === -1
  const percentage = isUnlimited ? 0 : Math.round((used / limit) * 100)
  const color = percentage > 90 ? 'red' : percentage > 70 ? 'amber' : 'brand'

  return (
    <div className="p-4 bg-brand-50/50 rounded-2xl ring-1 ring-brand-100">
      <div className="flex justify-between items-center mb-2">
        <span className="text-sm font-medium text-slate-700">{label}</span>
        <span className={`text-xs font-bold ${percentage > 90 ? 'text-red-600' : 'text-brand-700'}`}>
          {isUnlimited ? `${used.toLocaleString()} / ∞` : `${used.toLocaleString()} / ${limit.toLocaleString()} ${unit}`}
        </span>
      </div>
      {!isUnlimited && <ProgressBar value={used} max={limit} color={color} />}
      {isUnlimited && (
        <div className="flex items-center gap-1 text-xs text-green-600 font-medium">
          <Sparkles className="w-3.5 h-3.5" />
          Unlimited
        </div>
      )}
    </div>
  )
}

// ─── Billing Helpers ────────────────────────────────────────────────────────

function formatCurrency(amountCents, currency = 'usd') {
  const symbols = { usd: '$', eur: '€', gbp: '£' }
  const symbol = symbols[currency?.toLowerCase()] || '$'
  return `${symbol}${((amountCents || 0) / 100).toFixed(2)}`
}

function formatDate(dateStr) {
  if (!dateStr) return 'N/A'
  return new Date(dateStr).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

const STATUS_STYLES = {
  paid:      'bg-green-100 text-green-700 ring-green-200',
  pending:   'bg-amber-100 text-amber-700 ring-amber-200',
  draft:     'bg-slate-100 text-slate-600 ring-slate-200',
  void:      'bg-slate-100 text-slate-500 ring-slate-200',
  refunded:  'bg-blue-100 text-blue-700 ring-blue-200',
}

function StatusBadge({ status, className = '' }) {
  const style = STATUS_STYLES[status] || STATUS_STYLES.draft
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 text-xs font-bold rounded-full ring-1 ${style} ${className}`}>
      {status?.charAt(0).toUpperCase() + status?.slice(1) || 'Unknown'}
    </span>
  )
}

function InvoiceRow({ invoice, isExpanded, onToggle, onViewDetail }) {
  return (
    <>
      <tr className="border-b border-brand-50 hover:bg-brand-50/30 transition-colors">
        <td className="py-3 px-3 text-sm font-semibold text-brand-900">{invoice.invoice_number}</td>
        <td className="py-3 px-3 text-sm text-slate-600">{formatDate(invoice.issued_at)}</td>
        <td className="py-3 px-3 text-sm text-slate-700 max-w-[200px] truncate">{invoice.description || '—'}</td>
        <td className="py-3 px-3 text-sm font-semibold text-slate-900 text-right">{formatCurrency(invoice.amount, invoice.currency)}</td>
        <td className="py-3 px-3 text-center"><StatusBadge status={invoice.status} /></td>
        <td className="py-3 px-3 text-right">
          <div className="flex items-center justify-end gap-1">
            <button
              onClick={onViewDetail}
              className="p-1.5 text-slate-400 hover:text-brand-600 hover:bg-brand-50 rounded-lg transition-colors"
              title="View details"
            >
              <ExternalLink className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={onToggle}
              className="p-1.5 text-slate-400 hover:text-brand-600 hover:bg-brand-50 rounded-lg transition-colors"
              title={isExpanded ? 'Collapse' : 'Expand'}
            >
              {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>
          </div>
        </td>
      </tr>
    </>
  )
}

function InvoiceCard({ invoice, onViewDetail }) {
  return (
    <div className="p-4 bg-brand-50/30 rounded-2xl ring-1 ring-brand-100">
      <div className="flex items-start justify-between mb-2">
        <div>
          <p className="font-semibold text-brand-900 text-sm">{invoice.invoice_number}</p>
          <p className="text-xs text-slate-500 mt-0.5">{formatDate(invoice.issued_at)}</p>
        </div>
        <StatusBadge status={invoice.status} />
      </div>
      <p className="text-sm text-slate-700 mb-2">{invoice.description || '—'}</p>
      <div className="flex items-center justify-between">
        <p className="font-bold text-brand-900">{formatCurrency(invoice.amount, invoice.currency)}</p>
        <button
          onClick={onViewDetail}
          className="flex items-center gap-1 px-3 py-1.5 bg-white text-brand-700 text-xs font-semibold rounded-xl hover:bg-brand-50 transition-colors ring-1 ring-brand-200"
        >
          <ExternalLink className="w-3 h-3" />
          Details
        </button>
      </div>
    </div>
  )
}

function InvoiceDetailModal({ invoice, loading, onClose }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm" onClick={onClose}>
      <div
        className="bg-white rounded-3xl ring-1 ring-brand-100 shadow-brand-lg max-w-lg w-full max-h-[80vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-brand-50 ring-1 ring-brand-100 flex items-center justify-center">
                <FileText className="w-5 h-5 text-brand-600" />
              </div>
              <div>
                <h3 className="font-extrabold text-brand-900 text-lg">{invoice.invoice_number || 'Invoice'}</h3>
                <p className="text-xs text-slate-500">Invoice Details</p>
              </div>
            </div>
            <button
              onClick={onClose}
              aria-label="Close dialog"
              className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {loading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-brand-600" />
            </div>
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-brand-50/50 rounded-2xl ring-1 ring-brand-100">
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-wide">Status</p>
                  <div className="mt-1"><StatusBadge status={invoice.status} /></div>
                </div>
                <div className="p-3 bg-brand-50/50 rounded-2xl ring-1 ring-brand-100">
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-wide">Amount</p>
                  <p className="font-bold text-brand-900 mt-1">{formatCurrency(invoice.amount, invoice.currency)}</p>
                </div>
                <div className="p-3 bg-brand-50/50 rounded-2xl ring-1 ring-brand-100">
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-wide">Period</p>
                  <p className="text-sm text-slate-700 mt-1">
                    {formatDate(invoice.period_start)} — {formatDate(invoice.period_end)}
                  </p>
                </div>
                <div className="p-3 bg-brand-50/50 rounded-2xl ring-1 ring-brand-100">
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-wide">Provider</p>
                  <p className="text-sm text-slate-700 mt-1 capitalize">{invoice.payment_provider || 'N/A'}</p>
                </div>
                {invoice.issued_at && (
                  <div className="p-3 bg-brand-50/50 rounded-2xl ring-1 ring-brand-100">
                    <p className="text-xs font-bold text-slate-500 uppercase tracking-wide">Issued</p>
                    <p className="text-sm text-slate-700 mt-1">{formatDate(invoice.issued_at)}</p>
                  </div>
                )}
                {invoice.paid_at && (
                  <div className="p-3 bg-brand-50/50 rounded-2xl ring-1 ring-brand-100">
                    <p className="text-xs font-bold text-slate-500 uppercase tracking-wide">Paid</p>
                    <p className="text-sm text-slate-700 mt-1">{formatDate(invoice.paid_at)}</p>
                  </div>
                )}
              </div>

              {invoice.description && (
                <div className="p-3 bg-brand-50/50 rounded-2xl ring-1 ring-brand-100">
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-wide">Description</p>
                  <p className="text-sm text-slate-700 mt-1">{invoice.description}</p>
                </div>
              )}

              {invoice.line_items && invoice.line_items.length > 0 && (
                <div>
                  <h5 className="font-bold text-slate-800 text-sm mb-2">Line Items</h5>
                  <div className="space-y-2">
                    {invoice.line_items.map((item, i) => (
                      <div key={i} className="flex justify-between items-center p-3 bg-slate-50 rounded-xl ring-1 ring-slate-200">
                        <div>
                          <p className="text-sm font-medium text-slate-700">{item.description}</p>
                          {item.quantity > 1 && <p className="text-xs text-slate-400">Qty: {item.quantity}</p>}
                        </div>
                        <p className="font-semibold text-slate-900">{formatCurrency(item.amount, invoice.currency)}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function SettingsPage() {
  const navigate = useNavigate()
  const { user, tenant, logout } = useAuth()
  const {
    subscription,
    availablePlans,
    loading,
    error,
    fetchSubscription,
    getUsageStats,
    getCurrentPlan,
    isFeatureAvailable,
    getRemainingAnalyses,
  } = useSubscription()
  const [searchParams] = useSearchParams()
  const initialTab = searchParams.get('tab') || 'subscription'
  const [activeTab, setActiveTab] = useState(initialTab)
  const [saving, setSaving] = useState(false)
  const [actionLoading, setActionLoading] = useState(null)
  const isAdmin = user?.role === 'admin'

  // White-label branding
  const [brandingForm, setBrandingForm] = useState({
    brand_name: '',
    brand_logo_url: '',
    brand_primary_color: '#7C3AED',
    brand_favicon_url: '',
    custom_domain: '',
  })
  const [brandingLoading, setBrandingLoading] = useState(false)
  const [brandingSaving, setBrandingSaving] = useState(false)
  const [brandingMessage, setBrandingMessage] = useState('')

  // Billing history state
  const [invoices, setInvoices] = useState([])
  const [invoicesTotal, setInvoicesTotal] = useState(0)
  const [invoicesLoading, setInvoicesLoading] = useState(false)
  const [invoicesError, setInvoicesError] = useState(null)
  const [invoicesPage, setInvoicesPage] = useState(0)
  const invoicesPerPage = 10
  const [selectedInvoice, setSelectedInvoice] = useState(null)
  const [invoiceDetail, setInvoiceDetail] = useState(null)
  const [invoiceDetailLoading, setInvoiceDetailLoading] = useState(false)
  const [expandedInvoice, setExpandedInvoice] = useState(null)

  const fetchInvoices = useCallback(async (page = 0) => {
    setInvoicesLoading(true)
    setInvoicesError(null)
    try {
      const offset = page * invoicesPerPage
      const data = await getInvoices(invoicesPerPage, offset)
      setInvoices(data.invoices || [])
      setInvoicesTotal(data.total || 0)
      setInvoicesPage(page)
    } catch (err) {
      setInvoicesError(getUserFriendlyError(err))
    } finally {
      setInvoicesLoading(false)
    }
  }, [])

  const fetchInvoiceDetail = useCallback(async (invoiceId) => {
    setInvoiceDetailLoading(true)
    try {
      const data = await getInvoice(invoiceId)
      setInvoiceDetail(data)
    } catch (err) {
      console.error('Failed to fetch invoice detail:', err)
    } finally {
      setInvoiceDetailLoading(false)
    }
  }, [])

  // Fetch invoices when billing tab is active
  useEffect(() => {
    if (activeTab === 'billing') {
      fetchInvoices(0)
    }
  }, [activeTab, fetchInvoices])

  useEffect(() => {
    if (activeTab !== 'branding' || !isAdmin) return
    setBrandingLoading(true)
    getTenantBranding()
      .then((data) => {
        const b = data.branding || {}
        setBrandingForm({
          brand_name: b.brand_name || tenant?.name || '',
          brand_logo_url: b.brand_logo_url || '',
          brand_primary_color: b.brand_primary_color || '#7C3AED',
          brand_favicon_url: b.brand_favicon_url || '',
          custom_domain: b.custom_domain || '',
        })
      })
      .catch(() => setBrandingMessage('Could not load branding settings'))
      .finally(() => setBrandingLoading(false))
  }, [activeTab, isAdmin, tenant?.name])

  const handleSaveBranding = async () => {
    setBrandingSaving(true)
    setBrandingMessage('')
    try {
      await updateTenantBranding(brandingForm)
      setBrandingMessage('Branding saved. Changes appear after refresh.')
    } catch (err) {
      setBrandingMessage(getUserFriendlyError(err))
    } finally {
      setBrandingSaving(false)
    }
  }

  // Profile form state
  const [profile, setProfile] = useState({
    name: user?.email?.split('@')[0] || '',
    email: user?.email || '',
    notifications: {
      emailOnComplete: true,
      emailOnBatchComplete: true,
      marketing: false
    }
  })

  const handleSaveProfile = async () => {
    setSaving(true)
    await new Promise(r => setTimeout(r, 500))
    setSaving(false)
  }

  const handleResetUsage = async () => {
    if (!confirm('Reset usage counters? This is for testing only.')) return
    setActionLoading('resetUsage')
    try {
      await adminResetUsage()
      await fetchSubscription(true)
      alert('Usage counters reset successfully')
    } catch (err) {
      alert('Failed to reset: ' + getUserFriendlyError(err))
    } finally {
      setActionLoading(null)
    }
  }

  const handleChangePlan = async (planId) => {
    if (!confirm(`Switch to ${planId} plan?`)) return
    setActionLoading(`changePlan-${planId}`)
    try {
      await adminChangePlan(planId)
      await fetchSubscription(true)
      alert(`Switched to ${planId} plan`)
    } catch (err) {
      alert('Failed to change plan: ' + getUserFriendlyError(err))
    } finally {
      setActionLoading(null)
    }
  }

  const tabs = [
    { id: 'subscription', label: 'Subscription', icon: CreditCard },
    { id: 'billing', label: 'Billing History', icon: Receipt },
    { id: 'team', label: 'Team & Access', icon: Users },
    ...(isAdmin ? [{ id: 'branding', label: 'White-label', icon: Palette }] : []),
    { id: 'interviews', label: 'Interviews', icon: Mic },
    { id: 'requisitions', label: 'Requisitions', icon: FileText },
    { id: 'integrations', label: 'Integrations', icon: Plug },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'security', label: 'Security', icon: Shield },
  ]

  const usageStats = getUsageStats()
  const currentPlan = getCurrentPlan()
  const remainingAnalyses = getRemainingAnalyses()

  // Get plan features list
  const planFeatures = sanitizePlanFeatures(currentPlan?.plan?.features || [])

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8 card-animate">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-2xl bg-brand-50 ring-1 ring-brand-100 flex items-center justify-center">
            <Settings className="w-5 h-5 text-brand-600" />
          </div>
          <div>
            <h1 className="text-3xl font-extrabold text-brand-900 tracking-tight">Settings</h1>
            <p className="text-slate-500 text-sm font-medium">
              Manage your account, subscription, and preferences
            </p>
          </div>
        </div>
      </div>

      <div className="flex flex-col lg:flex-row gap-8">
        {/* Sidebar */}
        <div className="lg:w-64 shrink-0">
          <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-2 sticky top-24">
            {tabs.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-2xl text-sm font-medium transition-all ${
                  activeTab === id
                    ? 'bg-brand-50 text-brand-700 ring-1 ring-brand-200'
                    : 'text-slate-600 hover:bg-brand-50/50 hover:text-brand-700'
                }`}
              >
                <Icon className={`w-4 h-4 ${activeTab === id ? 'text-brand-600' : 'text-slate-400'}`} />
                {label}
                {activeTab === id && <ChevronRight className="w-4 h-4 ml-auto" />}
              </button>
            ))}
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 space-y-6">
          {/* Subscription Tab */}
          {activeTab === 'subscription' && (
            <>
              {loading ? (
                <div className="flex justify-center py-16">
                  <Loader2 className="w-8 h-8 animate-spin text-brand-600" />
                </div>
              ) : error ? (
                <div className="p-6 bg-red-50 rounded-2xl ring-1 ring-red-200 text-center">
                  <AlertTriangle className="w-8 h-8 text-red-500 mx-auto mb-2" />
                  <p className="text-red-700">{error}</p>
                  <button
                    onClick={() => fetchSubscription(true)}
                    className="mt-4 px-4 py-2 bg-white text-red-600 text-sm font-semibold rounded-xl hover:bg-red-50 transition-colors"
                  >
                    Retry
                  </button>
                </div>
              ) : (
                <>
                  {/* Current Plan */}
                  <Section
                    title="Current Plan"
                    icon={Zap}
                    description={currentPlan?.plan?.description || `You're on the ${currentPlan?.plan?.display_name || 'Free'} plan.`}
                  >
                    <div className="flex items-center justify-between p-4 bg-gradient-to-br from-brand-50 to-brand-100/50 rounded-2xl ring-1 ring-brand-200 mb-6">
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="font-extrabold text-brand-900 text-xl">{currentPlan?.plan?.display_name}</h4>
                          <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-bold rounded-full ring-1 ring-green-200">
                            {currentPlan?.status === 'active' ? 'Active' : currentPlan?.status}
                          </span>
                        </div>
                        <p className="text-sm text-slate-600 mt-1">
                          {currentPlan?.price > 0
                            ? `$${(currentPlan.price / 100).toFixed(0)}/${currentPlan?.billing_cycle === 'monthly' ? 'mo' : 'yr'}`
                            : 'Free plan'
                          }
                        </p>
                      </div>
                      <div className="text-right">
                        {usageStats?.daysUntilReset !== undefined && (
                          <p className="text-xs text-slate-500">
                            Resets in <span className="font-medium text-slate-700">{usageStats.daysUntilReset} days</span>
                          </p>
                        )}
                        {currentPlan?.current_period_end && (
                          <p className="text-xs text-slate-500 mt-1">
                            Period ends: <span className="font-medium text-slate-700">{new Date(currentPlan.current_period_end).toLocaleDateString()}</span>
                          </p>
                        )}
                      </div>
                    </div>

                    {/* Usage Stats */}
                    <h5 className="font-bold text-slate-800 text-sm mb-3 flex items-center gap-2">
                      <BarChart3 className="w-4 h-4 text-brand-600" />
                      Usage This Month
                    </h5>
                    <div className="grid sm:grid-cols-2 gap-3">
                      <UsageCard
                        label="Resume Analyses"
                        used={usageStats?.analysesUsed || 0}
                        limit={usageStats?.analysesLimit || 20}
                      />
                      <UsageCard
                        label="Storage Used"
                        used={usageStats?.storageUsedMB || 0}
                        limit={(usageStats?.storageLimitGB || 1) * 1024}
                        unit="MB"
                      />
                      <UsageCard
                        label="Team Members"
                        used={usageStats?.teamMembers || 1}
                        limit={usageStats?.teamMembersLimit || 1}
                      />
                      <UsageCard
                        label="Remaining Analyses"
                        used={remainingAnalyses === Infinity ? 0 : (usageStats?.analysesLimit || 20) - (usageStats?.analysesUsed || 0)}
                        limit={remainingAnalyses === Infinity ? -1 : usageStats?.analysesLimit || 20}
                      />
                    </div>

                    {/* Features */}
                    <h5 className="font-bold text-slate-800 text-sm mt-6 mb-3 flex items-center gap-2">
                      <Check className="w-4 h-4 text-brand-600" />
                      Plan Features
                    </h5>
                    <div className="grid sm:grid-cols-2 gap-2">
                      {planFeatures.map((feature, i) => (
                        <div key={i} className="flex items-center gap-2 text-sm text-slate-700">
                          <div className="w-5 h-5 rounded-full bg-brand-50 flex items-center justify-center shrink-0">
                            <Check className="w-3 h-3 text-brand-600" />
                          </div>
                          {feature}
                        </div>
                      ))}
                    </div>

                    {/* Admin Controls */}
                    {user?.role === 'admin' && (
                      <>
                        <h5 className="font-bold text-slate-800 text-sm mt-6 mb-3 flex items-center gap-2">
                          <Sparkles className="w-4 h-4 text-brand-600" />
                          Admin Testing Controls
                        </h5>
                        <div className="flex gap-2 flex-wrap">
                          <button
                            onClick={handleResetUsage}
                            disabled={actionLoading === 'resetUsage'}
                            className="flex items-center gap-2 px-3 py-2 bg-amber-50 text-amber-700 text-xs font-semibold rounded-xl hover:bg-amber-100 transition-colors disabled:opacity-50"
                          >
                            <RefreshCw className={`w-3 h-3 ${actionLoading === 'resetUsage' ? 'animate-spin' : ''}`} />
                            {actionLoading === 'resetUsage' ? 'Resetting...' : 'Reset Usage'}
                          </button>
                        </div>
                      </>
                    )}
                  </Section>

                  {/* Available Plans */}
                  <Section
                    title="Available Plans"
                    icon={CreditCard}
                    description="Upgrade or change your plan at any time"
                  >
                    <div className="grid sm:grid-cols-3 gap-4">
                      {availablePlans.map((plan, index) => {
                        const isCurrent = currentPlan?.plan?.id === plan.id
                        const isPopular = plan.name === 'pro'
                        return (
                          <div
                            key={plan.id}
                            className={`relative p-5 rounded-2xl ring-1 transition-all ${
                              isCurrent
                                ? 'bg-brand-50 ring-brand-300'
                                : isPopular
                                  ? 'bg-white ring-brand-200 shadow-brand'
                                  : 'bg-white ring-brand-100'
                            } ${isCurrent ? '' : 'hover:shadow-brand-lg'}`}
                          >
                            {isPopular && !isCurrent && (
                              <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-brand-600 text-white text-xs font-bold rounded-full shadow-brand-sm">
                                Most Popular
                              </div>
                            )}
                            {isCurrent && (
                              <div className="absolute top-3 right-3 w-6 h-6 rounded-full bg-brand-600 text-white flex items-center justify-center">
                                <Check className="w-4 h-4" />
                              </div>
                            )}
                            <h4 className="font-extrabold text-brand-900 text-lg">{plan.display_name}</h4>
                            <p className="text-2xl font-bold text-brand-900 mt-1">
                              ${(plan.price_monthly / 100).toFixed(0)}
                              <span className="text-sm font-medium text-slate-500">/mo</span>
                            </p>
                            <p className="text-xs text-slate-500 mt-1">{plan.description}</p>
                            <ul className="mt-4 space-y-2">
                              {sanitizePlanFeatures(plan.features).slice(0, 5).map((feature, i) => (
                                <li key={i} className="flex items-center gap-2 text-xs text-slate-700">
                                  <div className="w-4 h-4 rounded-full bg-brand-50 flex items-center justify-center shrink-0">
                                    <Check className="w-2.5 h-2.5 text-brand-600" />
                                  </div>
                                  {feature}
                                </li>
                              ))}
                            </ul>
                            {user?.role === 'admin' ? (
                              <button
                                onClick={() => handleChangePlan(plan.id)}
                                disabled={isCurrent || actionLoading?.startsWith('changePlan')}
                                className={`w-full mt-4 py-2.5 rounded-xl text-sm font-bold transition-all ${
                                  isCurrent
                                    ? 'bg-brand-200 text-brand-700 cursor-default'
                                    : 'btn-brand text-white shadow-brand-sm disabled:opacity-50'
                                }`}
                              >
                                {isCurrent ? 'Current Plan' : actionLoading === `changePlan-${plan.id}` ? 'Changing...' : actionLoading?.startsWith('changePlan') ? 'Please wait...' : 'Switch Plan'}
                              </button>
                            ) : (
                              <button
                                disabled={isCurrent}
                                className={`w-full mt-4 py-2.5 rounded-xl text-sm font-bold transition-all ${
                                  isCurrent
                                    ? 'bg-brand-200 text-brand-700 cursor-default'
                                    : 'bg-slate-100 text-slate-400 cursor-not-allowed'
                                }`}
                              >
                                {isCurrent ? 'Current Plan' : 'Contact Admin'}
                              </button>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </Section>
                </>
              )}
            </>
          )}

          {/* Billing History Tab */}
          {activeTab === 'billing' && (
            <>
              {/* Upcoming Billing */}
              <Section
                title="Upcoming Billing"
                icon={Calendar}
                description="Your next scheduled payment"
              >
                {currentPlan?.price > 0 ? (
                  <div className="p-4 bg-gradient-to-br from-brand-50 to-brand-100/50 rounded-2xl ring-1 ring-brand-200">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div>
                        <p className="text-sm font-medium text-slate-600">Next billing date</p>
                        <p className="font-bold text-brand-900 text-lg mt-0.5">
                          {currentPlan?.current_period_end
                            ? new Date(currentPlan.current_period_end).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
                            : 'N/A'}
                        </p>
                      </div>
                      <div className="sm:text-right">
                        <p className="text-sm font-medium text-slate-600">Amount</p>
                        <p className="font-bold text-brand-900 text-lg mt-0.5">
                          ${((currentPlan?.price || 0) / 100).toFixed(2)}
                          <span className="text-sm font-medium text-slate-500">/{currentPlan?.billing_cycle === 'monthly' ? 'mo' : 'yr'}</span>
                        </p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="p-4 bg-slate-50 rounded-2xl ring-1 ring-slate-200 text-center">
                    <p className="text-slate-600 text-sm">You're on the free plan. No upcoming charges.</p>
                  </div>
                )}
              </Section>

              {/* Invoice List */}
              <Section
                title="Invoice History"
                icon={FileText}
                description="View and download your past invoices"
              >
                {invoicesLoading ? (
                  <div className="flex justify-center py-12">
                    <Loader2 className="w-6 h-6 animate-spin text-brand-600" />
                  </div>
                ) : invoicesError ? (
                  <div className="p-4 bg-red-50 rounded-2xl ring-1 ring-red-200 text-center">
                    <AlertTriangle className="w-6 h-6 text-red-500 mx-auto mb-2" />
                    <p className="text-red-700 text-sm">{invoicesError}</p>
                    <button
                      onClick={() => fetchInvoices(0)}
                      className="mt-3 px-3 py-1.5 bg-white text-red-600 text-xs font-semibold rounded-xl hover:bg-red-50 transition-colors"
                    >
                      Retry
                    </button>
                  </div>
                ) : invoices.length === 0 ? (
                  <div className="py-12 text-center">
                    <FileText className="w-10 h-10 text-slate-300 mx-auto mb-3" />
                    <p className="text-slate-500 font-medium">No invoices yet</p>
                    <p className="text-slate-400 text-sm mt-1">Invoices will appear here once you make a payment</p>
                  </div>
                ) : (
                  <>
                    {/* Desktop Table */}
                    <div className="hidden sm:block overflow-x-auto">
                      <table className="w-full">
                        <thead>
                          <tr className="border-b border-brand-100">
                            <th className="text-left py-3 px-3 text-xs font-bold text-slate-500 uppercase tracking-wider">Invoice #</th>
                            <th className="text-left py-3 px-3 text-xs font-bold text-slate-500 uppercase tracking-wider">Date</th>
                            <th className="text-left py-3 px-3 text-xs font-bold text-slate-500 uppercase tracking-wider">Description</th>
                            <th className="text-right py-3 px-3 text-xs font-bold text-slate-500 uppercase tracking-wider">Amount</th>
                            <th className="text-center py-3 px-3 text-xs font-bold text-slate-500 uppercase tracking-wider">Status</th>
                            <th className="text-right py-3 px-3 text-xs font-bold text-slate-500 uppercase tracking-wider">Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {invoices.map((inv) => (
                            <InvoiceRow
                              key={inv.id}
                              invoice={inv}
                              isExpanded={expandedInvoice === inv.id}
                              onToggle={() => {
                                if (expandedInvoice === inv.id) {
                                  setExpandedInvoice(null)
                                } else {
                                  setExpandedInvoice(inv.id)
                                  if (!invoiceDetail || invoiceDetail?.id !== inv.id) {
                                    fetchInvoiceDetail(inv.id)
                                  }
                                }
                              }}
                              onViewDetail={() => {
                                setSelectedInvoice(inv)
                                fetchInvoiceDetail(inv.id)
                              }}
                            />
                          ))}
                        </tbody>
                      </table>
                    </div>

                    {/* Mobile Cards */}
                    <div className="sm:hidden space-y-3">
                      {invoices.map((inv) => (
                        <InvoiceCard
                          key={inv.id}
                          invoice={inv}
                          onViewDetail={() => {
                            setSelectedInvoice(inv)
                            fetchInvoiceDetail(inv.id)
                          }}
                        />
                      ))}
                    </div>

                    {/* Pagination */}
                    {invoicesTotal > invoicesPerPage && (
                      <div className="flex items-center justify-between mt-6 pt-4 border-t border-brand-100">
                        <p className="text-xs text-slate-500">
                          Showing {invoicesPage * invoicesPerPage + 1}–{Math.min((invoicesPage + 1) * invoicesPerPage, invoicesTotal)} of {invoicesTotal}
                        </p>
                        <div className="flex gap-2">
                          <button
                            onClick={() => fetchInvoices(invoicesPage - 1)}
                            disabled={invoicesPage === 0}
                            className="flex items-center gap-1 px-3 py-1.5 bg-brand-50 text-brand-700 text-xs font-semibold rounded-xl hover:bg-brand-100 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                          >
                            <ArrowLeft className="w-3 h-3" />
                            Prev
                          </button>
                          <button
                            onClick={() => fetchInvoices(invoicesPage + 1)}
                            disabled={(invoicesPage + 1) * invoicesPerPage >= invoicesTotal}
                            className="flex items-center gap-1 px-3 py-1.5 bg-brand-50 text-brand-700 text-xs font-semibold rounded-xl hover:bg-brand-100 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                          >
                            Next
                            <ArrowRight className="w-3 h-3" />
                          </button>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </Section>

              {/* Expanded Invoice Detail (inline) */}
              {expandedInvoice && invoiceDetail && invoiceDetail.id === expandedInvoice && (
                <Section
                  title={`Invoice ${invoiceDetail.invoice_number}`}
                  icon={FileText}
                  description="Invoice details"
                >
                  <div className="space-y-4">
                    <div className="grid sm:grid-cols-2 gap-4">
                      <div className="p-3 bg-brand-50/50 rounded-2xl ring-1 ring-brand-100">
                        <p className="text-xs font-bold text-slate-500 uppercase tracking-wide">Status</p>
                        <StatusBadge status={invoiceDetail.status} className="mt-1" />
                      </div>
                      <div className="p-3 bg-brand-50/50 rounded-2xl ring-1 ring-brand-100">
                        <p className="text-xs font-bold text-slate-500 uppercase tracking-wide">Amount</p>
                        <p className="font-bold text-brand-900 mt-1">{formatCurrency(invoiceDetail.amount, invoiceDetail.currency)}</p>
                      </div>
                      <div className="p-3 bg-brand-50/50 rounded-2xl ring-1 ring-brand-100">
                        <p className="text-xs font-bold text-slate-500 uppercase tracking-wide">Period</p>
                        <p className="text-sm text-slate-700 mt-1">
                          {formatDate(invoiceDetail.period_start)} — {formatDate(invoiceDetail.period_end)}
                        </p>
                      </div>
                      <div className="p-3 bg-brand-50/50 rounded-2xl ring-1 ring-brand-100">
                        <p className="text-xs font-bold text-slate-500 uppercase tracking-wide">Payment Provider</p>
                        <p className="text-sm text-slate-700 mt-1 capitalize">{invoiceDetail.payment_provider || 'N/A'}</p>
                      </div>
                      {invoiceDetail.issued_at && (
                        <div className="p-3 bg-brand-50/50 rounded-2xl ring-1 ring-brand-100">
                          <p className="text-xs font-bold text-slate-500 uppercase tracking-wide">Issued</p>
                          <p className="text-sm text-slate-700 mt-1">{formatDate(invoiceDetail.issued_at)}</p>
                        </div>
                      )}
                      {invoiceDetail.paid_at && (
                        <div className="p-3 bg-brand-50/50 rounded-2xl ring-1 ring-brand-100">
                          <p className="text-xs font-bold text-slate-500 uppercase tracking-wide">Paid</p>
                          <p className="text-sm text-slate-700 mt-1">{formatDate(invoiceDetail.paid_at)}</p>
                        </div>
                      )}
                    </div>

                    {/* Line Items */}
                    {invoiceDetail.line_items && invoiceDetail.line_items.length > 0 && (
                      <div>
                        <h5 className="font-bold text-slate-800 text-sm mb-2">Line Items</h5>
                        <div className="space-y-2">
                          {invoiceDetail.line_items.map((item, i) => (
                            <div key={i} className="flex justify-between items-center p-3 bg-slate-50 rounded-xl ring-1 ring-slate-200">
                              <div>
                                <p className="text-sm font-medium text-slate-700">{item.description}</p>
                                {item.quantity > 1 && <p className="text-xs text-slate-400">Qty: {item.quantity}</p>}
                              </div>
                              <p className="font-semibold text-slate-900">{formatCurrency(item.amount, invoiceDetail.currency)}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="flex justify-end mt-4">
                    <button
                      onClick={() => setExpandedInvoice(null)}
                      className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-800 transition-colors"
                    >
                      Close Details
                    </button>
                  </div>
                </Section>
              )}

              {/* Invoice Detail Modal */}
              {selectedInvoice && (
                <InvoiceDetailModal
                  invoice={invoiceDetail || selectedInvoice}
                  loading={invoiceDetailLoading}
                  onClose={() => {
                    setSelectedInvoice(null)
                    setInvoiceDetail(null)
                  }}
                />
              )}
            </>
          )}

          {/* Team & Access Tab */}
          {activeTab === 'team' && (
            <>
              <Section
                title="Organization"
                icon={Building2}
                description="Manage your team and tenant settings"
              >
                <div className="space-y-4">
                  <div className="p-4 bg-brand-50/50 rounded-2xl ring-1 ring-brand-100">
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wide mb-1">Organization Name</label>
                    <p className="font-semibold text-brand-900">{tenant?.name || 'Your Organization'}</p>
                  </div>
                  <div className="p-4 bg-brand-50/50 rounded-2xl ring-1 ring-brand-100">
                    <label className="block text-xs font-bold text-slate-700 uppercase tracking-wide mb-1">Tenant ID</label>
                    <p className="font-mono text-sm text-slate-600">{tenant?.slug || 'your-org'}</p>
                  </div>
                  <div className="flex gap-2 mt-4">
                    <button
                      onClick={() => navigate('/team')}
                      className="flex items-center gap-2 px-4 py-2.5 btn-brand text-white text-sm font-bold rounded-xl shadow-brand-sm"
                    >
                      <Users className="w-4 h-4" />
                      Manage Team Members
                    </button>
                  </div>
                </div>
              </Section>

              <Section
                title="API Access"
                icon={Key}
                description="API keys for integrations"
              >
                <div className="p-4 bg-slate-50 rounded-2xl ring-1 ring-slate-200">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-sm font-medium text-slate-700">API Key</span>
                    <span className={`px-2 py-0.5 text-xs font-bold rounded-full ring-1 ${
                      isFeatureAvailable('api_access')
                        ? 'bg-brand-100 text-brand-700 ring-brand-200'
                        : 'bg-amber-100 text-amber-700 ring-amber-200'
                    }`}>
                      {isFeatureAvailable('api_access') ? 'Available' : 'Pro Required'}
                    </span>
                  </div>
                  {isFeatureAvailable('api_access') ? (
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value="••••••••••••••••••••••••••"
                        readOnly
                        className="flex-1 px-4 py-2 bg-white rounded-xl text-sm font-mono text-slate-500 ring-1 ring-slate-200"
                      />
                      <button className="px-4 py-2 bg-brand-50 text-brand-700 text-sm font-semibold rounded-xl hover:bg-brand-100 transition-colors">
                        Reveal
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 text-sm text-slate-500">
                      <AlertTriangle className="w-4 h-4 text-amber-500" />
                      Upgrade to Pro to access API keys
                    </div>
                  )}
                </div>
              </Section>
            </>
          )}

          {activeTab === 'interviews' && (
            <Section
              title={INTERVIEW.settingsLink}
              icon={Mic}
              description={INTERVIEW.hubSubtitle}
            >
              <InterviewSettingsPanel />
            </Section>
          )}

          {activeTab === 'requisitions' && (
            <Section
              title="Requisition workflow"
              icon={FileText}
              description="Intake gates and hiring manager permissions"
            >
              <RequisitionSettingsPanel />
            </Section>
          )}

          {activeTab === 'integrations' && (
            <Section
              title="ATS & External Systems"
              icon={Plug}
              description="Push and pull candidate status with your applicant tracking system"
            >
              <ATSIntegrationsPanel />
            </Section>
          )}

          {/* Notifications Tab */}
          {activeTab === 'notifications' && (
            <Section
              title="Notification Preferences"
              icon={Bell}
              description="Control when and how you receive updates"
            >
              <div className="space-y-4">
                {[{
                  id: 'emailOnComplete',
                  label: 'Email when analysis completes',
                  description: 'Receive an email when a single resume analysis is finished'
                }, {
                  id: 'emailOnBatchComplete',
                  label: 'Email when batch completes',
                  description: 'Receive an email summary when a batch screening is finished'
                }, {
                  id: 'marketing',
                  label: 'Product updates & tips',
                  description: 'Occasional emails about new features and best practices'
                }].map(({ id, label, description }) => (
                  <label
                    key={id}
                    className="flex items-start gap-4 p-4 bg-brand-50/30 rounded-2xl ring-1 ring-brand-100 cursor-pointer hover:bg-brand-50/50 transition-colors"
                  >
                    <input
                      type="checkbox"
                      checked={profile.notifications[id]}
                      onChange={(e) => setProfile(prev => ({
                        ...prev,
                        notifications: { ...prev.notifications, [id]: e.target.checked }
                      }))}
                      className="mt-0.5 w-5 h-5 rounded-lg border-brand-300 text-brand-600 focus:ring-brand-500"
                    />
                    <div className="flex-1">
                      <p className="font-semibold text-slate-800 text-sm">{label}</p>
                      <p className="text-xs text-slate-500 mt-0.5">{description}</p>
                    </div>
                  </label>
                ))}
              </div>
              <div className="flex justify-end mt-6">
                <button
                  onClick={handleSaveProfile}
                  disabled={saving}
                  className="flex items-center gap-2 px-5 py-2.5 btn-brand text-white text-sm font-bold rounded-xl shadow-brand-sm disabled:opacity-60"
                >
                  {saving ? <><Loader2 className="w-4 h-4 animate-spin" /> Saving...</> : <><Check className="w-4 h-4" /> Save Preferences</>}
                </button>
              </div>
            </Section>
          )}

          {/* Security Tab */}
          {activeTab === 'branding' && isAdmin && (
            <Section
              title="White-label & Custom Domain"
              icon={Palette}
              description="Customize how ARIA appears to your team. Point a custom domain at this workspace for a fully branded experience."
            >
              {brandingLoading ? (
                <div className="flex justify-center py-12">
                  <Loader2 className="w-8 h-8 animate-spin text-brand-600" />
                </div>
              ) : (
                <div className="space-y-4">
                  {brandingMessage && (
                    <p className="text-sm text-slate-600 bg-brand-50 rounded-xl px-4 py-3 ring-1 ring-brand-100">{brandingMessage}</p>
                  )}
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                      <label className="block text-sm font-semibold text-slate-700 mb-1">Brand name</label>
                      <input
                        type="text"
                        value={brandingForm.brand_name}
                        onChange={(e) => setBrandingForm((f) => ({ ...f, brand_name: e.target.value }))}
                        className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 text-sm"
                        placeholder={tenant?.name || 'Your company'}
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-semibold text-slate-700 mb-1">Primary color</label>
                      <input
                        type="color"
                        value={brandingForm.brand_primary_color}
                        onChange={(e) => setBrandingForm((f) => ({ ...f, brand_primary_color: e.target.value }))}
                        className="w-full h-11 rounded-xl ring-1 ring-brand-200 cursor-pointer"
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <label className="block text-sm font-semibold text-slate-700 mb-1">Logo URL</label>
                      <input
                        type="url"
                        value={brandingForm.brand_logo_url}
                        onChange={(e) => setBrandingForm((f) => ({ ...f, brand_logo_url: e.target.value }))}
                        className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 text-sm"
                        placeholder="https://cdn.example.com/logo.png"
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <label className="block text-sm font-semibold text-slate-700 mb-1">Favicon URL</label>
                      <input
                        type="url"
                        value={brandingForm.brand_favicon_url}
                        onChange={(e) => setBrandingForm((f) => ({ ...f, brand_favicon_url: e.target.value }))}
                        className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 text-sm"
                        placeholder="https://cdn.example.com/favicon.ico"
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <label className="block text-sm font-semibold text-slate-700 mb-1">Custom domain</label>
                      <input
                        type="text"
                        value={brandingForm.custom_domain}
                        onChange={(e) => setBrandingForm((f) => ({ ...f, custom_domain: e.target.value }))}
                        className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 text-sm font-mono"
                        placeholder="hiring.yourcompany.com"
                      />
                      <p className="text-xs text-slate-400 mt-1">
                        CNAME this hostname to your ARIA deployment, then enter it here. Branding resolves automatically via the Host header.
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={handleSaveBranding}
                    disabled={brandingSaving}
                    className="px-5 py-2.5 rounded-xl bg-brand-600 text-white text-sm font-semibold hover:bg-brand-700 disabled:opacity-50"
                  >
                    {brandingSaving ? 'Saving…' : 'Save branding'}
                  </button>
                </div>
              )}
            </Section>
          )}

          {activeTab === 'security' && (
            <>
              <Section
                title="Account Security"
                icon={Shield}
                description="Manage your password and security settings"
              >
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1.5">Email Address</label>
                    <input
                      type="email"
                      value={profile.email}
                      disabled
                      autoComplete="email"
                      className="w-full px-4 py-2.5 bg-slate-50 rounded-xl text-sm text-slate-500 ring-1 ring-slate-200 cursor-not-allowed"
                    />
                    <p className="text-xs text-slate-400 mt-1">Contact support to change your email</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1.5">Current Password</label>
                    <input
                      type="password"
                      placeholder="••••••••"
                      disabled
                      autoComplete="current-password"
                      className="w-full px-4 py-2.5 bg-slate-50 rounded-xl text-sm text-slate-500 ring-1 ring-slate-200 cursor-not-allowed"
                    />
                  </div>

                  <div className="flex gap-2 pt-2">
                    <button
                      onClick={() => alert('Password change coming soon')}
                      className="px-4 py-2.5 bg-brand-50 text-brand-700 text-sm font-semibold rounded-xl hover:bg-brand-100 transition-colors"
                    >
                      Change Password
                    </button>
                  </div>
                </div>
              </Section>

              <Section
                title={TRUST.aiProcessingTitle}
                icon={Shield}
                description="How ARIA processes candidate and job data"
              >
                <p className="text-sm text-slate-600 leading-relaxed mb-4">{TRUST.aiProcessingBody}</p>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">AI subprocessors</p>
                <ul className="space-y-1.5">
                  {TRUST.aiSubprocessors.map((name) => (
                    <li key={name} className="text-sm text-slate-700 flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-brand-500 shrink-0" />
                      {name}
                    </li>
                  ))}
                </ul>
              </Section>

              <Section
                title="Danger Zone"
                icon={AlertTriangle}
                description="Actions that can't be undone"
              >
                <div className="p-4 bg-red-50/50 rounded-2xl ring-1 ring-red-200">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-bold text-red-800 text-sm">Delete Account</h4>
                      <p className="text-xs text-red-600 mt-0.5">This will permanently delete your account and all data</p>
                    </div>
                    <button
                      onClick={() => {
                        if (confirm('Are you sure? This cannot be undone.')) logout()
                      }}
                      className="px-4 py-2 bg-red-100 text-red-700 text-sm font-semibold rounded-xl hover:bg-red-200 transition-colors"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </Section>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
