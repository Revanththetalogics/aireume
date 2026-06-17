import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  Package,
  Plus,
  Loader2,
  AlertTriangle,
  Check,
  X,
  Edit3,
  Archive,
  RotateCcw,
  DollarSign,
  Users,
  Search,
  LayoutGrid,
  List,
} from 'lucide-react'
import { getAdminPlans, createPlan, updatePlan, archivePlan } from '../../lib/api'

const CURRENCY_OPTIONS = ['usd', 'eur', 'gbp', 'inr']

const DEFAULT_LIMITS = {
  analyses_per_month: -1,
  team_members: -1,
  storage_gb: 10,
  batch_size: 5,
}

function Toast({ message, type = 'success', onDone }) {
  useEffect(() => {
    const t = setTimeout(onDone, 3000)
    return () => clearTimeout(t)
  }, [onDone])

  return (
    <div className={`p-4 rounded-2xl ring-1 text-sm ${
      type === 'success'
        ? 'bg-green-50 text-green-700 ring-green-200'
        : 'bg-red-50 text-red-700 ring-red-200'
    }`}>
      <div className="flex items-center gap-2">
        {type === 'success' ? <Check className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
        {message}
      </div>
    </div>
  )
}

function formatPrice(cents, currency = 'usd') {
  if (cents === undefined || cents === null) return '—'
  const isoMap = { usd: 'USD', eur: 'EUR', gbp: 'GBP', inr: 'INR' }
  const iso = isoMap[currency] || 'USD'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: iso }).format(cents / 100)
}

function priceToCents(dollars) {
  const val = parseFloat(dollars)
  if (isNaN(val)) return 0
  return Math.round(val * 100)
}

function centsToDollars(cents) {
  if (cents === undefined || cents === null) return ''
  return (cents / 100).toFixed(2)
}

function generateSlug(name) {
  return name
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
}

function featuresToText(features) {
  if (!Array.isArray(features)) return ''
  return features.join('\n')
}

function textToFeatures(text) {
  return text
    .split('\n')
    .map((f) => f.trim())
    .filter((f) => f.length > 0)
}

function validatePlanForm(form, isCreate) {
  const errors = []
  if (!form.display_name?.trim()) errors.push('Display name is required')
  if (isCreate && !form.name?.trim()) errors.push('Name is required')
  const monthly = parseFloat(form.price_monthly)
  if (isNaN(monthly) || monthly < 0) errors.push('Monthly price must be >= 0')
  const yearly = parseFloat(form.price_yearly)
  if (isNaN(yearly) || yearly < 0) errors.push('Yearly price must be >= 0')
  if (!form.currency) errors.push('Currency is required')
  const limits = form.limits || {}
  for (const key of ['analyses_per_month', 'team_members', 'storage_gb', 'batch_size']) {
    const val = parseInt(limits[key], 10)
    if (isNaN(val)) errors.push(`${key} must be a number`)
  }
  return errors
}

function getPlanTier(plan, allPlans) {
  const name = (plan.name || '').toLowerCase()
  const price = plan.price_monthly || 0

  if (price === 0 || name.includes('free')) return 'free'
  if (name.includes('enterprise')) return 'enterprise'
  if (name.includes('pro')) return 'pro'

  // Fallback: closest tier by price
  const nonZeroPrices = allPlans
    .map((p) => p.price_monthly || 0)
    .filter((p) => p > 0)
    .sort((a, b) => a - b)

  if (nonZeroPrices.length === 0) return 'free'
  const maxPrice = nonZeroPrices[nonZeroPrices.length - 1]
  if (maxPrice === 0) return 'free'

  if (price >= maxPrice * 0.5) return 'enterprise'
  return 'pro'
}

export default function PlanManagementPage() {
  const [plans, setPlans] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [toast, setToast] = useState(null)
  const [search, setSearch] = useState('')
  const [viewMode, setViewMode] = useState('table')

  const [showModal, setShowModal] = useState(false)
  const [editingPlan, setEditingPlan] = useState(null)
  const [saving, setSaving] = useState(false)
  const [formErrors, setFormErrors] = useState([])

  const [showArchiveModal, setShowArchiveModal] = useState(false)
  const [archivingPlan, setArchivingPlan] = useState(null)
  const [archiveForce, setArchiveForce] = useState(false)
  const [archiving, setArchiving] = useState(false)

  const emptyForm = useMemo(() => ({
    name: '',
    display_name: '',
    description: '',
    price_monthly: '',
    price_yearly: '',
    currency: 'usd',
    limits: { ...DEFAULT_LIMITS },
    features: '',
    is_active: true,
    sort_order: 0,
  }), [])

  const [form, setForm] = useState(emptyForm)

  const fetchPlans = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await getAdminPlans()
      setPlans(data.plans || data || [])
    } catch (err) {
      console.error('Failed to fetch plans:', err)
      setError(err.response?.data?.detail || 'Failed to load plans.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchPlans()
  }, [fetchPlans])

  const filteredPlans = useMemo(() => {
    const q = search.toLowerCase().trim()
    if (!q) return plans
    return plans.filter(
      (p) =>
        (p.name || '').toLowerCase().includes(q) ||
        (p.display_name || '').toLowerCase().includes(q)
    )
  }, [plans, search])

  const openCreate = () => {
    setEditingPlan(null)
    setForm(emptyForm)
    setFormErrors([])
    setShowModal(true)
  }

  const openEdit = (plan) => {
    setEditingPlan(plan)
    setForm({
      name: plan.name || '',
      display_name: plan.display_name || '',
      description: plan.description || '',
      price_monthly: centsToDollars(plan.price_monthly),
      price_yearly: centsToDollars(plan.price_yearly),
      currency: (plan.currency || 'usd').toLowerCase(),
      limits: {
        analyses_per_month: plan.limits?.analyses_per_month ?? -1,
        team_members: plan.limits?.team_members ?? -1,
        storage_gb: plan.limits?.storage_gb ?? 10,
        batch_size: plan.limits?.batch_size ?? 5,
      },
      features: featuresToText(plan.features),
      is_active: plan.is_active ?? true,
      sort_order: plan.sort_order ?? 0,
    })
    setFormErrors([])
    setShowModal(true)
  }

  const openArchive = (plan) => {
    setArchivingPlan(plan)
    setArchiveForce(false)
    setShowArchiveModal(true)
  }

  const handleDisplayNameChange = (value) => {
    setForm((prev) => {
      const next = { ...prev, display_name: value }
      if (!editingPlan) {
        next.name = generateSlug(value)
      }
      return next
    })
  }

  const handleSubmit = async () => {
    setFormErrors([])
    const errors = validatePlanForm(form, !editingPlan)
    if (errors.length > 0) {
      setFormErrors(errors)
      return
    }

    const payload = {
      name: form.name.trim(),
      display_name: form.display_name.trim(),
      description: form.description?.trim() || undefined,
      price_monthly: priceToCents(form.price_monthly),
      price_yearly: priceToCents(form.price_yearly),
      currency: form.currency,
      limits: {
        analyses_per_month: parseInt(form.limits.analyses_per_month, 10),
        team_members: parseInt(form.limits.team_members, 10),
        storage_gb: parseInt(form.limits.storage_gb, 10),
        batch_size: parseInt(form.limits.batch_size, 10),
      },
      features: textToFeatures(form.features),
      is_active: form.is_active,
      sort_order: parseInt(form.sort_order, 10) || 0,
    }

    setSaving(true)
    try {
      if (editingPlan) {
        await updatePlan(editingPlan.id, payload)
        setToast({ message: 'Plan updated successfully.', type: 'success' })
      } else {
        await createPlan(payload)
        setToast({ message: 'Plan created successfully.', type: 'success' })
      }
      setShowModal(false)
      fetchPlans()
    } catch (err) {
      const detail = err.response?.data?.detail || err.message || 'Failed to save plan.'
      setFormErrors([detail])
    } finally {
      setSaving(false)
    }
  }

  const handleArchive = async () => {
    if (!archivingPlan) return
    setArchiving(true)
    try {
      await archivePlan(archivingPlan.id, archiveForce)
      setToast({ message: 'Plan archived successfully.', type: 'success' })
      setShowArchiveModal(false)
      fetchPlans()
    } catch (err) {
      const detail = err.response?.data?.detail || err.message || 'Failed to archive plan.'
      setToast({ message: detail, type: 'error' })
    } finally {
      setArchiving(false)
    }
  }

  const handleRestore = async (plan) => {
    try {
      await updatePlan(plan.id, { is_active: true })
      setToast({ message: 'Plan restored successfully.', type: 'success' })
      fetchPlans()
    } catch (err) {
      const detail = err.response?.data?.detail || err.message || 'Failed to restore plan.'
      setToast({ message: detail, type: 'error' })
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <h2 className="text-2xl font-extrabold text-brand-900 tracking-tight flex items-center gap-2">
          <Package className="w-6 h-6 text-brand-600" />
          Plan Management
        </h2>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 px-4 py-2 btn-brand text-white text-sm font-bold rounded-xl shadow-brand-sm"
        >
          <Plus className="w-4 h-4" />
          Create Plan
        </button>
      </div>

      {toast && <Toast message={toast.message} type={toast.type} onDone={() => setToast(null)} />}

      {error && (
        <div className="p-4 bg-red-50 rounded-2xl ring-1 ring-red-200 text-sm text-red-700">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            {error}
            <button
              onClick={fetchPlans}
              className="ml-auto px-3 py-1 text-xs font-bold bg-red-100 hover:bg-red-200 rounded-lg transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      )}

      {/* Search + View Toggle */}
      <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="relative max-w-md w-full sm:w-auto">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search plans..."
            className="w-full pl-9 pr-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
          />
        </div>
        <div className="flex items-center gap-1 bg-slate-100 rounded-xl p-1">
          <button
            onClick={() => setViewMode('table')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-semibold transition-colors ${
              viewMode === 'table'
                ? 'bg-teal-600 text-white shadow-sm'
                : 'bg-white border border-slate-200 text-slate-600 hover:text-slate-800'
            }`}
          >
            <List className="w-4 h-4" />
            Table
          </button>
          <button
            onClick={() => setViewMode('kanban')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-semibold transition-colors ${
              viewMode === 'kanban'
                ? 'bg-teal-600 text-white shadow-sm'
                : 'bg-white border border-slate-200 text-slate-600 hover:text-slate-800'
            }`}
          >
            <LayoutGrid className="w-4 h-4" />
            Kanban
          </button>
        </div>
      </div>

      {/* Plans Table / Kanban */}
      <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand overflow-hidden">
        {loading ? (
          <div className="p-6 space-y-4">
            {/* Skeleton table rows */}
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center gap-6 animate-pulse">
                <div className="h-5 w-24 bg-slate-200 rounded" />
                <div className="h-5 w-20 bg-slate-200 rounded" />
                <div className="h-5 w-16 bg-slate-200 rounded" />
                <div className="h-5 w-16 bg-slate-200 rounded" />
                <div className="h-5 w-12 bg-slate-200 rounded" />
                <div className="h-5 w-16 bg-slate-200 rounded" />
                <div className="flex-1" />
              </div>
            ))}
          </div>
        ) : filteredPlans.length === 0 ? (
          <div className="px-6 py-12 text-center text-slate-400 text-sm">
            {search ? 'No plans match your search.' : 'No plans found.'}
          </div>
        ) : viewMode === 'table' ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-brand-100 bg-brand-50/50">
                  <th className="text-left px-6 py-3 font-bold text-brand-900">Name</th>
                  <th className="text-left px-6 py-3 font-bold text-brand-900">Display Name</th>
                  <th className="text-left px-6 py-3 font-bold text-brand-900">Price (Monthly)</th>
                  <th className="text-left px-6 py-3 font-bold text-brand-900">Price (Yearly)</th>
                  <th className="text-left px-6 py-3 font-bold text-brand-900">Subscribers</th>
                  <th className="text-left px-6 py-3 font-bold text-brand-900">Status</th>
                  <th className="text-right px-6 py-3 font-bold text-brand-900">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-brand-100">
                {filteredPlans.map((plan) => (
                  <tr
                    key={plan.id}
                    className={`transition-colors ${
                      !plan.is_active ? 'bg-slate-50/50 opacity-70' : 'hover:bg-brand-50/30'
                    }`}
                  >
                    <td className="px-6 py-4">
                      <span className="font-semibold text-brand-900">{plan.name}</span>
                      <span className="block text-xs text-slate-400">{plan.currency?.toUpperCase()}</span>
                    </td>
                    <td className="px-6 py-4 text-slate-700">{plan.display_name || '—'}</td>
                    <td className="px-6 py-4 text-slate-700">
                      <div className="flex items-center gap-1">
                        <DollarSign className="w-3.5 h-3.5 text-slate-400" />
                        {formatPrice(plan.price_monthly, plan.currency)}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-slate-700">
                      <div className="flex items-center gap-1">
                        <DollarSign className="w-3.5 h-3.5 text-slate-400" />
                        {formatPrice(plan.price_yearly, plan.currency)}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-1.5">
                        <Users className="w-3.5 h-3.5 text-slate-400" />
                        <span className="font-semibold text-brand-900">{plan.subscriber_count ?? 0}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      {plan.is_active ? (
                        <span className="inline-flex px-2.5 py-0.5 rounded-full text-xs font-bold bg-green-50 text-green-700 ring-1 ring-green-200">
                          Active
                        </span>
                      ) : (
                        <span className="inline-flex px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-100 text-slate-600 ring-1 ring-slate-200">
                          Archived
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => openEdit(plan)}
                          className="p-2 rounded-xl hover:bg-brand-50 text-slate-400 hover:text-brand-600 transition-colors"
                          title="Edit"
                        >
                          <Edit3 className="w-4 h-4" />
                        </button>
                        {plan.is_active ? (
                          <button
                            onClick={() => openArchive(plan)}
                            className="p-2 rounded-xl hover:bg-red-50 text-slate-400 hover:text-red-600 transition-colors"
                            title="Archive"
                          >
                            <Archive className="w-4 h-4" />
                          </button>
                        ) : (
                          <button
                            onClick={() => handleRestore(plan)}
                            className="p-2 rounded-xl hover:bg-green-50 text-slate-400 hover:text-green-600 transition-colors"
                            title="Restore"
                          >
                            <RotateCcw className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-4">
            {(() => {
              const groups = { free: [], pro: [], enterprise: [] }
              filteredPlans.forEach((plan) => {
                const tier = getPlanTier(plan, plans)
                if (groups[tier]) groups[tier].push(plan)
                else groups.pro.push(plan)
              })

              const columns = [
                { key: 'free', label: 'Free', bg: 'bg-slate-50', header: 'text-slate-700' },
                { key: 'pro', label: 'Pro', bg: 'bg-slate-50', header: 'text-brand-700' },
                { key: 'enterprise', label: 'Enterprise', bg: 'bg-slate-50', header: 'text-amber-700' },
              ]

              return (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {columns.map((col) => (
                    <div key={col.key} className={`${col.bg} rounded-2xl p-4`}>
                      <div className="flex items-center justify-between mb-4">
                        <h3 className={`font-bold text-sm tracking-wide uppercase ${col.header}`}>
                          {col.label}
                        </h3>
                        <span className="text-xs font-bold text-slate-500 bg-white px-2 py-0.5 rounded-full ring-1 ring-slate-200">
                          {groups[col.key].length}
                        </span>
                      </div>
                      <div className="space-y-3">
                        {groups[col.key].map((plan) => (
                          <div
                            key={plan.id}
                            className={`bg-white rounded-xl shadow-sm border p-4 transition-colors ${
                              !plan.is_active ? 'opacity-70 border-slate-200' : 'border-brand-100'
                            }`}
                          >
                            <div className="flex items-start justify-between gap-2 mb-2">
                              <div>
                                <h4 className="text-base font-bold text-brand-900 leading-tight">
                                  {plan.display_name || plan.name}
                                </h4>
                                <span className="text-xs text-slate-400">{plan.currency?.toUpperCase()}</span>
                              </div>
                              {plan.is_active ? (
                                <span className="inline-flex px-2 py-0.5 rounded-full text-[10px] font-bold bg-green-50 text-green-700 ring-1 ring-green-200">
                                  Active
                                </span>
                              ) : (
                                <span className="inline-flex px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-600 ring-1 ring-slate-200">
                                  Archived
                                </span>
                              )}
                            </div>

                            <div className="flex items-center gap-3 text-sm text-slate-600 mb-3">
                              <div className="flex items-center gap-1">
                                <DollarSign className="w-3.5 h-3.5 text-slate-400" />
                                <span className="font-semibold">{formatPrice(plan.price_monthly, plan.currency)}</span>
                                <span className="text-xs text-slate-400">/mo</span>
                              </div>
                              <div className="flex items-center gap-1">
                                <DollarSign className="w-3.5 h-3.5 text-slate-400" />
                                <span>{formatPrice(plan.price_yearly, plan.currency)}</span>
                                <span className="text-xs text-slate-400">/yr</span>
                              </div>
                            </div>

                            {Array.isArray(plan.features) && plan.features.length > 0 && (
                              <ul className="space-y-1 mb-3">
                                {plan.features.slice(0, 4).map((f, i) => (
                                  <li key={i} className="flex items-start gap-1.5 text-xs text-slate-600">
                                    <Check className="w-3 h-3 text-teal-500 shrink-0 mt-0.5" />
                                    <span className="line-clamp-1">{f}</span>
                                  </li>
                                ))}
                                {plan.features.length > 4 && (
                                  <li className="text-xs text-slate-400 pl-4.5">
                                    +{plan.features.length - 4} more
                                  </li>
                                )}
                              </ul>
                            )}

                            <div className="flex items-center justify-between pt-3 border-t border-slate-100">
                              <div className="flex items-center gap-1.5">
                                <Users className="w-3.5 h-3.5 text-slate-400" />
                                <span className="text-xs font-semibold text-brand-900">
                                  {plan.subscriber_count ?? 0}
                                </span>
                                <span className="text-xs text-slate-400">subscribers</span>
                              </div>
                              <div className="flex items-center gap-1">
                                <button
                                  onClick={() => openEdit(plan)}
                                  className="p-1.5 rounded-lg hover:bg-brand-50 text-slate-400 hover:text-brand-600 transition-colors"
                                  title="Edit"
                                >
                                  <Edit3 className="w-3.5 h-3.5" />
                                </button>
                                {plan.is_active ? (
                                  <button
                                    onClick={() => openArchive(plan)}
                                    className="p-1.5 rounded-lg hover:bg-red-50 text-slate-400 hover:text-red-600 transition-colors"
                                    title="Archive"
                                  >
                                    <Archive className="w-3.5 h-3.5" />
                                  </button>
                                ) : (
                                  <button
                                    onClick={() => handleRestore(plan)}
                                    className="p-1.5 rounded-lg hover:bg-green-50 text-slate-400 hover:text-green-600 transition-colors"
                                    title="Restore"
                                  >
                                    <RotateCcw className="w-3.5 h-3.5" />
                                  </button>
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                        {groups[col.key].length === 0 && (
                          <div className="text-center py-6 text-xs text-slate-400">
                            No {col.label.toLowerCase()} plans
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )
            })()}
          </div>
        )}
      </div>

      {/* Create/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white/95 backdrop-blur-xl rounded-3xl ring-1 ring-brand-100 shadow-brand-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6 card-animate">
            <div className="flex items-center justify-between mb-5">
              <h3 className="font-extrabold text-brand-900 tracking-tight text-lg">
                {editingPlan ? 'Edit Plan' : 'Create Plan'}
              </h3>
              <button
                onClick={() => setShowModal(false)}
                className="p-1.5 hover:bg-brand-50 rounded-xl transition-colors"
              >
                <X className="w-5 h-5 text-slate-400" />
              </button>
            </div>

            {formErrors.length > 0 && (
              <div className="mb-4 p-4 bg-red-50 rounded-2xl ring-1 ring-red-200 text-sm text-red-700 space-y-1">
                {formErrors.map((err, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                    {err}
                  </div>
                ))}
              </div>
            )}

            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-bold text-slate-700 mb-1.5">
                    Display Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={form.display_name}
                    onChange={(e) => handleDisplayNameChange(e.target.value)}
                    placeholder="e.g. Professional"
                    className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-bold text-slate-700 mb-1.5">
                    Name (slug) <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    disabled={!!editingPlan}
                    placeholder="e.g. professional"
                    className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white disabled:bg-slate-50 disabled:text-slate-400"
                  />
                  {!editingPlan && (
                    <p className="text-xs text-slate-400 mt-1">Auto-generated from display name.</p>
                  )}
                </div>
              </div>

              <div>
                <label className="block text-sm font-bold text-slate-700 mb-1.5">Description</label>
                <textarea
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  placeholder="Brief description of the plan..."
                  rows={3}
                  className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white resize-none"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-bold text-slate-700 mb-1.5">
                    Monthly Price ($) <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={form.price_monthly}
                    onChange={(e) => setForm({ ...form, price_monthly: e.target.value })}
                    placeholder="49.00"
                    className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
                  />
                  <p className="text-xs text-slate-400 mt-1">Enter amount in dollars (e.g., 49.00). Stored in cents internally.</p>
                </div>
                <div>
                  <label className="block text-sm font-bold text-slate-700 mb-1.5">
                    Yearly Price ($) <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={form.price_yearly}
                    onChange={(e) => setForm({ ...form, price_yearly: e.target.value })}
                    placeholder="490.00"
                    className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
                  />
                  <p className="text-xs text-slate-400 mt-1">Enter amount in dollars (e.g., 490.00). Stored in cents internally.</p>
                </div>
                <div>
                  <label className="block text-sm font-bold text-slate-700 mb-1.5">
                    Currency <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={form.currency}
                    onChange={(e) => setForm({ ...form, currency: e.target.value })}
                    className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
                  >
                    {CURRENCY_OPTIONS.map((c) => (
                      <option key={c} value={c}>{c.toUpperCase()}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-bold text-slate-700 mb-2">Limits</label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-slate-500 mb-1">Analyses/Month (-1 = unlimited)</label>
                    <input
                      type="number"
                      value={form.limits.analyses_per_month}
                      onChange={(e) =>
                        setForm({
                          ...form,
                          limits: { ...form.limits, analyses_per_month: e.target.value },
                        })
                      }
                      className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-500 mb-1">Team Members (-1 = unlimited)</label>
                    <input
                      type="number"
                      value={form.limits.team_members}
                      onChange={(e) =>
                        setForm({
                          ...form,
                          limits: { ...form.limits, team_members: e.target.value },
                        })
                      }
                      className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-500 mb-1">Storage (GB)</label>
                    <input
                      type="number"
                      value={form.limits.storage_gb}
                      onChange={(e) =>
                        setForm({
                          ...form,
                          limits: { ...form.limits, storage_gb: e.target.value },
                        })
                      }
                      className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-500 mb-1">Batch Size</label>
                    <input
                      type="number"
                      value={form.limits.batch_size}
                      onChange={(e) =>
                        setForm({
                          ...form,
                          limits: { ...form.limits, batch_size: e.target.value },
                        })
                      }
                      className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
                    />
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-sm font-bold text-slate-700 mb-1.5">Features</label>
                <textarea
                  value={form.features}
                  onChange={(e) => setForm({ ...form, features: e.target.value })}
                  placeholder="Enter one feature per line..."
                  rows={4}
                  className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white resize-none"
                />
                <p className="text-xs text-slate-400 mt-1">One feature per line. These will be stored as a JSON array.</p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    id="is_active"
                    checked={form.is_active}
                    onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                    className="w-4 h-4 rounded border-brand-300 text-brand-600 focus:ring-brand-500"
                  />
                  <label htmlFor="is_active" className="text-sm font-semibold text-slate-700">
                    Active
                  </label>
                </div>
                <div>
                  <label className="block text-sm font-bold text-slate-700 mb-1.5">Sort Order</label>
                  <input
                    type="number"
                    value={form.sort_order}
                    onChange={(e) => setForm({ ...form, sort_order: e.target.value })}
                    className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
                  />
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-2 mt-6 pt-4 border-t border-brand-100">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 ring-1 ring-brand-200 text-sm font-semibold text-brand-700 rounded-xl hover:bg-brand-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                disabled={saving}
                className="px-4 py-2 btn-brand text-white text-sm font-bold rounded-xl disabled:opacity-60 flex items-center gap-2"
              >
                {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                {saving ? 'Saving...' : editingPlan ? 'Save Changes' : 'Create Plan'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Archive Confirmation Modal */}
      {showArchiveModal && archivingPlan && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white/95 backdrop-blur-xl rounded-3xl ring-1 ring-brand-100 shadow-brand-xl w-full max-w-md p-6 card-animate">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-red-50 flex items-center justify-center ring-1 ring-red-200">
                <Archive className="w-5 h-5 text-red-600" />
              </div>
              <div>
                <h3 className="font-extrabold text-brand-900 text-lg">Archive Plan</h3>
                <p className="text-sm text-slate-500">{archivingPlan.display_name || archivingPlan.name}</p>
              </div>
            </div>

            {(archivingPlan.subscriber_count ?? 0) > 0 && (
              <div className="mb-4 p-4 bg-amber-50 rounded-2xl ring-1 ring-amber-200 text-sm text-amber-800">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                  <div>
                    <p className="font-semibold">Warning: Active Subscribers</p>
                    <p className="mt-0.5">
                      This plan has <strong>{archivingPlan.subscriber_count}</strong> active subscriber(s).
                      Archiving will not affect existing tenants, but the plan will no longer be available for new signups.
                    </p>
                  </div>
                </div>
                <label className="flex items-center gap-2 mt-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={archiveForce}
                    onChange={(e) => setArchiveForce(e.target.checked)}
                    className="w-4 h-4 rounded border-amber-300 text-amber-600 focus:ring-amber-500"
                  />
                  <span className="text-sm font-medium">Force archive anyway</span>
                </label>
              </div>
            )}

            {(archivingPlan.subscriber_count ?? 0) === 0 && (
              <p className="text-sm text-slate-600 mb-4">
                Are you sure you want to archive this plan? It will no longer be available for new subscriptions.
              </p>
            )}

            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowArchiveModal(false)}
                className="px-4 py-2 ring-1 ring-brand-200 text-sm font-semibold text-brand-700 rounded-xl hover:bg-brand-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleArchive}
                disabled={archiving || ((archivingPlan.subscriber_count ?? 0) > 0 && !archiveForce)}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-bold rounded-xl disabled:opacity-60 disabled:cursor-not-allowed flex items-center gap-2 transition-colors"
              >
                {archiving && <Loader2 className="w-4 h-4 animate-spin" />}
                {archiving ? 'Archiving...' : 'Archive Plan'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
