import { useState, useEffect, useCallback } from 'react'
import {
  Search,
  ChevronLeft,
  ChevronRight,
  Loader2,
  AlertTriangle,
  Download,
  ChevronDown,
  ChevronUp,
  FileText,
} from 'lucide-react'
import {
  getAdminAuditLogs,
  exportAuditLogs,
  getAdminTenants,
} from '../../lib/api'

/* ── Constants ────────────────────────────────────────── */
const PER_PAGE = 25

const ACTION_TYPES = [
  { value: '', label: 'All Actions' },
  { value: 'tenant.create', label: 'Tenant Create' },
  { value: 'tenant.update', label: 'Tenant Update' },
  { value: 'tenant.suspend', label: 'Tenant Suspend' },
  { value: 'tenant.resume', label: 'Tenant Resume' },
  { value: 'tenant.delete', label: 'Tenant Delete' },
  { value: 'plan.change', label: 'Plan Change' },
  { value: 'user.add', label: 'User Add' },
  { value: 'user.remove', label: 'User Remove' },
  { value: 'user.delete', label: 'User Delete' },
  { value: 'webhook.create', label: 'Webhook Create' },
  { value: 'webhook.delete', label: 'Webhook Delete' },
  { value: 'rate_limit.update', label: 'Rate Limit Update' },
  { value: 'rate_limit.delete', label: 'Rate Limit Delete' },
  { value: 'sso.update', label: 'SSO Update' },
  { value: 'sso.delete', label: 'SSO Delete' },
  { value: 'impersonate.start', label: 'Impersonate Start' },
  { value: 'impersonate.end', label: 'Impersonate End' },
  { value: 'feature.toggle', label: 'Feature Toggle' },
  { value: 'billing.update', label: 'Billing Update' },
]

/* ── Action Badge ─────────────────────────────────────── */
function ActionBadge({ action }) {
  const colorMap = {
    create: 'bg-green-50 text-green-700 ring-green-200',
    update: 'bg-blue-50 text-blue-700 ring-blue-200',
    suspend: 'bg-red-50 text-red-700 ring-red-200',
    resume: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
    delete: 'bg-red-50 text-red-700 ring-red-200',
    change: 'bg-purple-50 text-purple-700 ring-purple-200',
    add: 'bg-teal-50 text-teal-700 ring-teal-200',
    remove: 'bg-orange-50 text-orange-700 ring-orange-200',
    toggle: 'bg-amber-50 text-amber-700 ring-amber-200',
    start: 'bg-indigo-50 text-indigo-700 ring-indigo-200',
    end: 'bg-slate-50 text-slate-700 ring-slate-200',
  }

  const suffix = action.split('.').pop()
  const colors = colorMap[suffix] || 'bg-gray-50 text-gray-700 ring-gray-200'

  return (
    <span className={`px-2 py-0.5 rounded-md text-xs font-semibold ring-1 ${colors}`}>
      {action}
    </span>
  )
}

/* ── Expandable Details ────────────────────────────────── */
function DetailsCell({ details }) {
  const [expanded, setExpanded] = useState(false)

  if (!details || Object.keys(details).length === 0) {
    return <span className="text-gray-400 text-sm">—</span>
  }

  return (
    <div>
      <button
        onClick={() => setExpanded(v => !v)}
        className="text-xs text-teal-600 hover:text-teal-700 font-medium flex items-center gap-1"
      >
        {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        {expanded ? 'Hide' : 'View'}
      </button>
      {expanded && (
        <pre className="mt-1 text-xs text-gray-600 bg-gray-50 rounded-lg p-2 overflow-x-auto max-w-xs whitespace-pre-wrap">
          {JSON.stringify(details, null, 2)}
        </pre>
      )}
    </div>
  )
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

/* ── Main AuditLogPage ─────────────────────────────────── */
export default function AuditLogPage() {
  // Data
  const [logs, setLogs] = useState([])
  const [totalCount, setTotalCount] = useState(0)
  const [tenants, setTenants] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [exporting, setExporting] = useState(false)
  const [toast, setToast] = useState(null)

  // Filters
  const [searchInput, setSearchInput] = useState('')
  const [actorEmail, setActorEmail] = useState('')
  const [actionFilter, setActionFilter] = useState('')
  const [tenantFilter, setTenantFilter] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  // Pagination
  const [page, setPage] = useState(1)

  /* ── Fetch logs ────────────────────────────────────── */
  const fetchLogs = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const params = { page, per_page: PER_PAGE }
      if (actorEmail.trim()) params.actor_email = actorEmail.trim()
      if (actionFilter) params.action = actionFilter
      if (tenantFilter) params.resource_type = 'tenant'
      if (dateFrom) params.date_from = dateFrom
      if (dateTo) params.date_to = dateTo
      const data = await getAdminAuditLogs(params)
      setLogs(data.items || [])
      setTotalCount(data.total || 0)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load audit logs')
    } finally {
      setLoading(false)
    }
  }, [page, actorEmail, actionFilter, tenantFilter, dateFrom, dateTo])

  const fetchTenants = useCallback(async () => {
    try {
      const data = await getAdminTenants({ per_page: 200 })
      setTenants(data.tenants || data.items || data || [])
    } catch {
      // Tenants list is optional for filter dropdown
    }
  }, [])

  useEffect(() => {
    fetchLogs()
  }, [fetchLogs])

  useEffect(() => {
    fetchTenants()
  }, [fetchTenants])

  // Reset page when filters change
  useEffect(() => {
    setPage(1)
  }, [actorEmail, actionFilter, tenantFilter, dateFrom, dateTo])

  /* ── Export CSV ─────────────────────────────────────── */
  const handleExport = async () => {
    setExporting(true)
    try {
      const params = { format: 'csv' }
      if (actionFilter) params.action = actionFilter
      if (dateFrom) params.start_date = dateFrom
      if (dateTo) params.end_date = dateTo
      const blob = await exportAuditLogs(params)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `audit-logs-${new Date().toISOString().slice(0, 10)}.csv`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
      setToast({ message: 'Audit log exported successfully.', type: 'success' })
    } catch (err) {
      setToast({ message: 'Failed to export audit logs.', type: 'error' })
    } finally {
      setExporting(false)
    }
  }

  /* ── Search handler ─────────────────────────────────── */
  const handleSearchSubmit = (e) => {
    e.preventDefault()
    setActorEmail(searchInput)
    setPage(1)
  }

  /* ── Pagination math ─────────────────────────────────── */
  const totalPages = Math.max(1, Math.ceil(totalCount / PER_PAGE))

  const hasActiveFilters = actorEmail || actionFilter || tenantFilter || dateFrom || dateTo

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Audit Log</h1>
          <p className="text-sm text-gray-500 mt-0.5">Track all platform admin actions</p>
        </div>
        <button
          onClick={handleExport}
          disabled={exporting}
          className="flex items-center gap-2 px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-sm font-bold rounded-lg transition-colors disabled:opacity-50"
        >
          {exporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
          {exporting ? 'Exporting...' : 'Export CSV'}
        </button>
      </div>

      {toast && <Toast message={toast.message} type={toast.type} onDone={() => setToast(null)} />}

      {/* Filters */}
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <div className="flex flex-wrap items-end gap-3">
          {/* Search by actor email */}
          <form onSubmit={handleSearchSubmit} className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Search by actor email..."
                className="w-full pl-10 pr-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-sm"
              />
            </div>
          </form>

          {/* Action type */}
          <div className="min-w-[160px]">
            <select
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-sm"
            >
              {ACTION_TYPES.map(o => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          {/* Tenant */}
          <div className="min-w-[160px]">
            <select
              value={tenantFilter}
              onChange={(e) => setTenantFilter(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-sm"
            >
              <option value="">All Tenants</option>
              {tenants.map(t => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          </div>

          {/* Date from */}
          <div>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-sm"
              title="From date"
            />
          </div>

          {/* Date to */}
          <div>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-sm"
              title="To date"
            />
          </div>

          {/* Clear filters */}
          {hasActiveFilters && (
            <button
              onClick={() => {
                setActorEmail('')
                setSearchInput('')
                setActionFilter('')
                setTenantFilter('')
                setDateFrom('')
                setDateTo('')
                setPage(1)
              }}
              className="px-3 py-2 text-sm font-medium text-teal-600 hover:text-teal-700 transition-colors"
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-50 rounded-xl ring-1 ring-red-200 text-sm text-red-700 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
          <button onClick={fetchLogs} className="ml-auto px-3 py-1 text-xs font-bold bg-red-100 hover:bg-red-200 rounded-lg transition-colors">
            Retry
          </button>
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="p-6 space-y-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex gap-4">
                <div className="h-4 w-36 bg-gray-200 rounded animate-pulse" />
                <div className="h-4 w-24 bg-gray-100 rounded animate-pulse" />
                <div className="h-4 w-40 bg-gray-100 rounded animate-pulse" />
                <div className="h-4 w-28 bg-gray-100 rounded animate-pulse" />
                <div className="h-4 w-20 bg-gray-100 rounded animate-pulse" />
              </div>
            ))}
          </div>
        ) : logs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-gray-400">
            <FileText className="w-12 h-12 mb-3 text-gray-300" />
            <p className="text-sm font-medium">No audit logs found</p>
            <p className="text-xs mt-1">Try adjusting your filters</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Timestamp</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Action</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">User</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Resource</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">IP Address</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {logs.map(log => (
                  <tr key={log.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 text-sm text-gray-600 whitespace-nowrap">
                      {log.created_at ? new Date(log.created_at).toLocaleString() : '—'}
                    </td>
                    <td className="px-4 py-3">
                      <ActionBadge action={log.action} />
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900 font-medium">
                      {log.actor_email || '—'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      <span className="text-xs text-gray-400">{log.resource_type}</span>
                      {log.resource_id && <span className="ml-1 text-gray-500">#{log.resource_id}</span>}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500 font-mono">
                      {log.ip_address || '—'}
                    </td>
                    <td className="px-4 py-3">
                      <DetailsCell details={log.details} />
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
    </div>
  )
}
