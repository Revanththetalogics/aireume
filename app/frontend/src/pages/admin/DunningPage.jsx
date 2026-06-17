import { useState, useEffect, useCallback } from 'react'
import {
  AlertCircle,
  CheckCircle,
  RefreshCw,
  AlertTriangle,
  RotateCcw,
  Clock,
} from 'lucide-react'
import { getAdminDunningRecords, resolveDunning, extractApiError } from '../../lib/api'

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function StatusBadge({ status }) {
  const map = {
    active: 'bg-yellow-50 text-yellow-700 ring-1 ring-yellow-200',
    exhausted: 'bg-red-50 text-red-700 ring-1 ring-red-200',
    resolved: 'bg-green-50 text-green-700 ring-1 ring-green-200',
  }
  const label = {
    active: 'Retrying',
    exhausted: 'Exhausted',
    resolved: 'Recovered',
  }
  return (
    <span className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-bold ${map[status] || 'bg-slate-100 text-slate-600 ring-1 ring-slate-200'}`}>
      {label[status] || status}
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
        </div>
      </div>
    </div>
  )
}

export default function DunningPage() {
  const [records, setRecords] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [resolving, setResolving] = useState(null)
  const [resolveError, setResolveError] = useState('')
  const [resolveSuccess, setResolveSuccess] = useState('')

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const params = statusFilter !== 'all' ? { status: statusFilter } : {}
      const data = await getAdminDunningRecords(params)
      const items = data?.items || (Array.isArray(data) ? data : [])
      setRecords(items)
    } catch (err) {
      setError(extractApiError(err, 'Failed to load dunning records.'))
    } finally {
      setLoading(false)
    }
  }, [statusFilter])

  useEffect(() => { fetchData() }, [fetchData])

  const handleResolve = async (tenantId, tenantName) => {
    if (!window.confirm(`Mark dunning as resolved for "${tenantName}"? This will reactivate their subscription.`)) return
    setResolving(tenantId)
    setResolveError('')
    setResolveSuccess('')
    try {
      await resolveDunning(tenantId)
      setResolveSuccess(`Dunning resolved for ${tenantName}.`)
      fetchData()
    } catch (err) {
      setResolveError(extractApiError(err, 'Failed to resolve dunning.'))
    } finally {
      setResolving(null)
    }
  }

  // Summary stats (across all records, not filtered)
  const [allRecords, setAllRecords] = useState([])
  const fetchAll = useCallback(async () => {
    try {
      const data = await getAdminDunningRecords({ status: 'all' }).catch(() =>
        getAdminDunningRecords()
      )
      const items = data?.items || (Array.isArray(data) ? data : [])
      setAllRecords(items)
    } catch {
      // ignore
    }
  }, [])

  useEffect(() => { fetchAll() }, [fetchAll])

  const activeCount = allRecords.filter((r) => r.status === 'active').length
  const exhaustedCount = allRecords.filter((r) => r.status === 'exhausted').length
  const resolvedCount = allRecords.filter((r) => r.status === 'resolved').length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-brand-500/10 flex items-center justify-center ring-1 ring-brand-200">
            <RotateCcw className="w-5 h-5 text-brand-600" />
          </div>
          <div>
            <h2 className="text-2xl font-extrabold text-brand-900 tracking-tight">Dunning Management</h2>
            <p className="text-sm text-slate-500">Track and resolve failed payment retries.</p>
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

      {/* Toast notifications */}
      {resolveSuccess && (
        <div className="p-4 bg-green-50 rounded-2xl ring-1 ring-green-200 text-sm text-green-700 flex items-center gap-2">
          <CheckCircle className="w-4 h-4 shrink-0" />
          {resolveSuccess}
          <button onClick={() => setResolveSuccess('')} className="ml-auto text-xs font-bold">Dismiss</button>
        </div>
      )}
      {resolveError && (
        <div className="p-4 bg-red-50 rounded-2xl ring-1 ring-red-200 text-sm text-red-700 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {resolveError}
          <button onClick={() => setResolveError('')} className="ml-auto text-xs font-bold">Dismiss</button>
        </div>
      )}

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
              label="Active Dunning"
              value={activeCount}
              sub="Currently in retry cycle"
              color="amber"
              icon={<RotateCcw className="w-5 h-5" />}
            />
            <KPICard
              label="Exhausted"
              value={exhaustedCount}
              sub="All retries failed"
              color="red"
              icon={<AlertCircle className="w-5 h-5" />}
            />
            <KPICard
              label="Recovered"
              value={resolvedCount}
              sub="Manually or auto resolved"
              color="green"
              icon={<CheckCircle className="w-5 h-5" />}
            />
          </>
        )}
      </div>

      {/* Filter */}
      <div className="bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 p-4">
        <div className="flex flex-wrap gap-3 items-end">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Status Filter</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 text-sm rounded-xl ring-1 ring-slate-200 bg-white text-brand-900 focus:outline-none focus:ring-2 focus:ring-brand-400"
            >
              <option value="all">All (Active + Exhausted)</option>
              <option value="active">Retrying</option>
              <option value="exhausted">Exhausted</option>
              <option value="resolved">Recovered</option>
            </select>
          </div>
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6 animate-pulse">
          <div className="h-6 w-40 bg-slate-200 rounded-lg mb-4" />
          <div className="space-y-3">
            {[1, 2, 3].map((i) => <div key={i} className="h-14 bg-slate-100 rounded-xl" />)}
          </div>
        </div>
      ) : (
        <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand overflow-hidden">
          <div className="p-6 border-b border-brand-100">
            <h3 className="font-extrabold text-brand-900">Dunning Records</h3>
            <p className="text-xs text-slate-400 mt-0.5">{records.length} record{records.length !== 1 ? 's' : ''} shown</p>
          </div>
          {records.length === 0 ? (
            <div className="px-6 py-16 text-center text-slate-400 text-sm">
              <CheckCircle className="w-10 h-10 mx-auto mb-3 opacity-30" />
              No dunning records match the current filter.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-brand-100 bg-brand-50/50">
                    <th className="text-left px-6 py-3 font-bold text-brand-900">Tenant</th>
                    <th className="text-left px-6 py-3 font-bold text-brand-900">Status</th>
                    <th className="text-left px-6 py-3 font-bold text-brand-900">Attempts</th>
                    <th className="text-left px-6 py-3 font-bold text-brand-900">Last Attempt</th>
                    <th className="text-left px-6 py-3 font-bold text-brand-900">Next Retry</th>
                    <th className="text-left px-6 py-3 font-bold text-brand-900">Failure Reason</th>
                    <th className="text-left px-6 py-3 font-bold text-brand-900">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-brand-100">
                  {records.map((r) => (
                    <tr key={r.id} className="hover:bg-brand-50/30 transition-colors">
                      <td className="px-6 py-4">
                        <p className="font-semibold text-brand-900">{r.tenant_name || r.tenant_id}</p>
                        {r.tenant_slug && (
                          <p className="text-xs text-slate-400">{r.tenant_slug}</p>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <StatusBadge status={r.status} />
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-brand-900">{r.retry_count ?? 0}</span>
                          <span className="text-slate-400">/</span>
                          <span className="text-slate-600">{r.max_retries ?? '—'}</span>
                        </div>
                        {r.max_retries > 0 && (
                          <div className="mt-1 w-20 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full ${r.retry_count >= r.max_retries ? 'bg-red-500' : 'bg-amber-400'}`}
                              style={{ width: `${Math.min(100, ((r.retry_count || 0) / r.max_retries) * 100)}%` }}
                            />
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4 text-slate-600 text-xs">{formatDate(r.last_retry_at)}</td>
                      <td className="px-6 py-4 text-slate-600 text-xs">
                        {r.status === 'active' ? (
                          <span className="flex items-center gap-1 text-amber-600">
                            <Clock className="w-3 h-3" />
                            {formatDate(r.next_retry_at)}
                          </span>
                        ) : '—'}
                      </td>
                      <td className="px-6 py-4 text-slate-600 text-xs max-w-[200px] truncate" title={r.failure_reason}>
                        {r.failure_reason || '—'}
                      </td>
                      <td className="px-6 py-4">
                        {r.status !== 'resolved' && (
                          <button
                            onClick={() => handleResolve(r.tenant_id, r.tenant_name)}
                            disabled={resolving === r.tenant_id}
                            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold bg-teal-50 text-teal-700 ring-1 ring-teal-200 rounded-lg hover:bg-teal-100 disabled:opacity-50 transition-colors"
                          >
                            {resolving === r.tenant_id ? (
                              <RefreshCw className="w-3 h-3 animate-spin" />
                            ) : (
                              <CheckCircle className="w-3 h-3" />
                            )}
                            {resolving === r.tenant_id ? 'Resolving…' : 'Mark Resolved'}
                          </button>
                        )}
                      </td>
                    </tr>
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
