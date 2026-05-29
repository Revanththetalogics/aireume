import { useState, useEffect, useCallback } from 'react'
import {
  FileText,
  DollarSign,
  AlertTriangle,
  Clock,
  RefreshCw,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  Loader2,
} from 'lucide-react'
import { getAdminInvoices, getAdminTenants } from '../../lib/api'

function formatCurrency(cents) {
  if (cents === undefined || cents === null) return '—'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(cents / 100)
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function StatusBadge({ status }) {
  const map = {
    paid: 'bg-green-50 text-green-700 ring-1 ring-green-200',
    pending: 'bg-yellow-50 text-yellow-700 ring-1 ring-yellow-200',
    overdue: 'bg-red-50 text-red-700 ring-1 ring-red-200',
    failed: 'bg-red-50 text-red-800 ring-1 ring-red-300',
    void: 'bg-slate-100 text-slate-600 ring-1 ring-slate-200',
    draft: 'bg-blue-50 text-blue-700 ring-1 ring-blue-200',
  }
  return (
    <span className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-bold ${map[status] || 'bg-slate-100 text-slate-600 ring-1 ring-slate-200'}`}>
      {status}
    </span>
  )
}

function KPICard({ label, value, sub, icon, color = 'teal' }) {
  const colorMap = {
    teal: 'bg-teal-500/10 text-teal-600 ring-teal-200',
    amber: 'bg-amber-500/10 text-amber-600 ring-amber-200',
    red: 'bg-red-500/10 text-red-600 ring-red-200',
    green: 'bg-green-500/10 text-green-600 ring-green-200',
  }
  return (
    <div className="bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 shadow-brand p-5">
      <div className="flex items-start gap-4">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ring-1 ${colorMap[color]}`}>
          {icon}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">{label}</p>
          <p className="mt-0.5 text-2xl font-bold text-brand-900">{value}</p>
          {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
        </div>
      </div>
    </div>
  )
}

function SkeletonCard() {
  return (
    <div className="bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 p-5 animate-pulse">
      <div className="flex items-start gap-4">
        <div className="w-10 h-10 rounded-xl bg-slate-200" />
        <div className="flex-1 space-y-2">
          <div className="h-3 w-20 bg-slate-200 rounded" />
          <div className="h-6 w-32 bg-slate-200 rounded" />
          <div className="h-3 w-16 bg-slate-100 rounded" />
        </div>
      </div>
    </div>
  )
}

export default function InvoicesPage() {
  const [invoices, setInvoices] = useState([])
  const [tenants, setTenants] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [tenantFilter, setTenantFilter] = useState('all')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [expandedRow, setExpandedRow] = useState(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [inv, t] = await Promise.all([
        getAdminInvoices().catch(() => null),
        getAdminTenants().catch(() => null),
      ])
      const items = inv?.invoices || inv?.items || (Array.isArray(inv) ? inv : [])
      setInvoices(items)
      const tenantList = t?.items || t?.tenants || (Array.isArray(t) ? t : [])
      setTenants(tenantList)
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to load invoices.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  // Filtering
  const filtered = invoices.filter((inv) => {
    if (statusFilter !== 'all' && inv.status !== statusFilter) return false
    if (tenantFilter !== 'all' && String(inv.tenant_id) !== tenantFilter) return false
    if (dateFrom && inv.issued_at && inv.issued_at < dateFrom) return false
    if (dateTo && inv.issued_at && inv.issued_at > dateTo + 'T23:59:59') return false
    return true
  })

  // Summary stats
  const outstanding = invoices
    .filter((i) => i.status === 'pending' || i.status === 'overdue')
    .reduce((sum, i) => sum + (i.amount || 0), 0)
  const overdueCount = invoices.filter((i) => i.status === 'overdue').length
  const now = new Date()
  const thisMonthStart = new Date(now.getFullYear(), now.getMonth(), 1).toISOString()
  const collectedThisMonth = invoices
    .filter((i) => i.status === 'paid' && i.paid_at && i.paid_at >= thisMonthStart)
    .reduce((sum, i) => sum + (i.amount || 0), 0)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-brand-500/10 flex items-center justify-center ring-1 ring-brand-200">
            <FileText className="w-5 h-5 text-brand-600" />
          </div>
          <div>
            <h2 className="text-2xl font-extrabold text-brand-900 tracking-tight">Invoices</h2>
            <p className="text-sm text-slate-500">View and manage all tenant invoices.</p>
          </div>
        </div>
        {!loading && (
          <button
            onClick={fetchData}
            className="flex items-center gap-2 px-4 py-2 ring-1 ring-brand-200 text-sm font-semibold text-brand-700 rounded-xl hover:bg-brand-50 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-50 rounded-2xl ring-1 ring-red-200 text-sm text-red-700 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
          <button onClick={fetchData} className="ml-auto px-3 py-1 text-xs font-bold bg-red-100 hover:bg-red-200 rounded-lg transition-colors">
            Retry
          </button>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {loading ? (
          <><SkeletonCard /><SkeletonCard /><SkeletonCard /></>
        ) : (
          <>
            <KPICard
              label="Total Outstanding"
              value={formatCurrency(outstanding)}
              sub="Pending + overdue invoices"
              color="amber"
              icon={<DollarSign className="w-5 h-5" />}
            />
            <KPICard
              label="Overdue Invoices"
              value={overdueCount}
              sub="Require immediate attention"
              color="red"
              icon={<AlertTriangle className="w-5 h-5" />}
            />
            <KPICard
              label="Collected This Month"
              value={formatCurrency(collectedThisMonth)}
              sub="Paid invoices in current month"
              color="green"
              icon={<CheckCircle className="w-5 h-5" />}
            />
          </>
        )}
      </div>

      {/* Filters */}
      <div className="bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 p-4">
        <div className="flex flex-wrap gap-3 items-end">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Status</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 text-sm rounded-xl ring-1 ring-slate-200 bg-white text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-400"
            >
              <option value="all">All Statuses</option>
              <option value="paid">Paid</option>
              <option value="pending">Pending</option>
              <option value="overdue">Overdue</option>
              <option value="failed">Failed</option>
              <option value="void">Void</option>
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Tenant</label>
            <select
              value={tenantFilter}
              onChange={(e) => setTenantFilter(e.target.value)}
              className="px-3 py-2 text-sm rounded-xl ring-1 ring-slate-200 bg-white text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-400"
            >
              <option value="all">All Tenants</option>
              {tenants.map((t) => (
                <option key={t.id} value={String(t.id)}>{t.name}</option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">From</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="px-3 py-2 text-sm rounded-xl ring-1 ring-slate-200 bg-white text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-400"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">To</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="px-3 py-2 text-sm rounded-xl ring-1 ring-slate-200 bg-white text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-400"
            />
          </div>
          {(statusFilter !== 'all' || tenantFilter !== 'all' || dateFrom || dateTo) && (
            <button
              onClick={() => { setStatusFilter('all'); setTenantFilter('all'); setDateFrom(''); setDateTo('') }}
              className="px-3 py-2 text-xs font-semibold text-slate-500 hover:text-red-600 transition-colors"
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6 animate-pulse">
          <div className="h-6 w-32 bg-slate-200 rounded-lg mb-4" />
          <div className="space-y-3">
            {[1, 2, 3, 4].map((i) => <div key={i} className="h-12 bg-slate-100 rounded-xl" />)}
          </div>
        </div>
      ) : (
        <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand overflow-hidden">
          <div className="p-6 border-b border-brand-100 flex items-center justify-between">
            <div>
              <h3 className="font-extrabold text-brand-900">Invoice List</h3>
              <p className="text-xs text-slate-400 mt-0.5">{filtered.length} invoice{filtered.length !== 1 ? 's' : ''} shown</p>
            </div>
          </div>
          {filtered.length === 0 ? (
            <div className="px-6 py-16 text-center text-slate-400 text-sm">
              <FileText className="w-10 h-10 mx-auto mb-3 opacity-30" />
              No invoices match the current filters.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-brand-100 bg-brand-50/50">
                    <th className="text-left px-6 py-3 font-bold text-brand-900">Invoice #</th>
                    <th className="text-left px-6 py-3 font-bold text-brand-900">Tenant</th>
                    <th className="text-left px-6 py-3 font-bold text-brand-900">Amount</th>
                    <th className="text-left px-6 py-3 font-bold text-brand-900">Status</th>
                    <th className="text-left px-6 py-3 font-bold text-brand-900">Issued</th>
                    <th className="text-left px-6 py-3 font-bold text-brand-900">Paid</th>
                    <th className="text-left px-6 py-3 font-bold text-brand-900">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-brand-100">
                  {filtered.map((inv) => (
                    <>
                      <tr
                        key={inv.id}
                        className="hover:bg-brand-50/30 transition-colors"
                      >
                        <td className="px-6 py-4 font-mono text-xs text-brand-700 font-semibold">
                          {inv.invoice_number || `#${inv.id}`}
                        </td>
                        <td className="px-6 py-4 font-semibold text-brand-900">
                          {inv.tenant_name || inv.tenant_id || '—'}
                        </td>
                        <td className="px-6 py-4 font-bold text-brand-900">
                          {formatCurrency(inv.amount)}
                          {inv.currency && inv.currency !== 'usd' && (
                            <span className="ml-1 text-xs text-slate-400 uppercase">{inv.currency}</span>
                          )}
                        </td>
                        <td className="px-6 py-4">
                          <StatusBadge status={inv.status} />
                        </td>
                        <td className="px-6 py-4 text-slate-600">{formatDate(inv.issued_at)}</td>
                        <td className="px-6 py-4 text-slate-600">{formatDate(inv.paid_at)}</td>
                        <td className="px-6 py-4">
                          <button
                            onClick={() => setExpandedRow(expandedRow === inv.id ? null : inv.id)}
                            className="flex items-center gap-1 text-xs font-semibold text-brand-600 hover:text-brand-800 transition-colors"
                          >
                            {expandedRow === inv.id ? (
                              <><ChevronUp className="w-3 h-3" /> Hide</>
                            ) : (
                              <><ChevronDown className="w-3 h-3" /> Details</>
                            )}
                          </button>
                        </td>
                      </tr>
                      {expandedRow === inv.id && (
                        <tr key={`${inv.id}-detail`} className="bg-brand-50/40">
                          <td colSpan={7} className="px-8 py-5">
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
                              <div>
                                <p className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1">Description</p>
                                <p className="text-slate-700">{inv.description || '—'}</p>
                              </div>
                              <div>
                                <p className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1">Payment Provider</p>
                                <p className="text-slate-700">{inv.payment_provider || '—'}</p>
                              </div>
                              <div>
                                <p className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1">Period</p>
                                <p className="text-slate-700">
                                  {inv.period_start ? `${formatDate(inv.period_start)} → ${formatDate(inv.period_end)}` : '—'}
                                </p>
                              </div>
                              {inv.line_items && inv.line_items.length > 0 && (
                                <div className="col-span-full">
                                  <p className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-2">Line Items</p>
                                  <div className="space-y-1">
                                    {inv.line_items.map((li, idx) => (
                                      <div key={idx} className="flex justify-between text-xs bg-white rounded-lg px-3 py-2 ring-1 ring-brand-100">
                                        <span className="text-slate-700">{li.description || li.name || `Item ${idx + 1}`}</span>
                                        <span className="font-bold text-brand-900">{formatCurrency(li.amount)}</span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
