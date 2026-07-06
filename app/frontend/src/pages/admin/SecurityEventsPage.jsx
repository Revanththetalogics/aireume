import { useState, useEffect, useCallback } from 'react'
import { Loader2, Shield, Search, AlertTriangle } from 'lucide-react'
import { getSecurityEvents } from '../../lib/api'

export default function SecurityEventsPage() {
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [filters, setFilters] = useState({ event_type: '', ip_address: '' })
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const perPage = 50

  const fetchEvents = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = { page, per_page: perPage }
      if (filters.event_type) params.event_type = filters.event_type
      if (filters.ip_address) params.ip_address = filters.ip_address
      const data = await getSecurityEvents(params)
      setEvents(data.items || [])
      setTotal(data.total || 0)
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to load security events. Please try again.')
      setEvents([])
    } finally {
      setLoading(false)
    }
  }, [page, filters])

  useEffect(() => {
    fetchEvents()
  }, [fetchEvents])

  const eventTypeColor = (type) => {
    if (type === 'login_success') return 'text-green-700 bg-green-50 ring-green-200'
    if (type === 'login_failure') return 'text-red-700 bg-red-50 ring-red-200'
    if (type === 'suspicious_activity') return 'text-amber-700 bg-amber-50 ring-amber-200'
    return 'text-slate-700 bg-slate-50 ring-slate-200'
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-extrabold text-brand-900 tracking-tight flex items-center gap-2">
          <Shield className="w-6 h-6 text-brand-600" />
          Security Events
        </h2>
        <div className="flex items-center gap-2">
          <select
            className="px-3 py-2 rounded-xl ring-1 ring-brand-200 bg-white text-sm"
            value={filters.event_type}
            onChange={(e) => { setFilters(f => ({ ...f, event_type: e.target.value })); setPage(1) }}
          >
            <option value="">All Types</option>
            <option value="login_success">Login Success</option>
            <option value="login_failure">Login Failure</option>
            <option value="impersonation_started">Impersonation Started</option>
            <option value="impersonation_ended">Impersonation Ended</option>
            <option value="suspicious_activity">Suspicious Activity</option>
          </select>
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-brand-400" />
            <input
              type="text"
              placeholder="Filter by IP..."
              className="pl-9 pr-3 py-2 rounded-xl ring-1 ring-brand-200 bg-white text-sm w-48"
              value={filters.ip_address}
              onChange={(e) => { setFilters(f => ({ ...f, ip_address: e.target.value })); setPage(1) }}
            />
          </div>
        </div>
      </div>

      {error && (
        <div className="flex items-center justify-between gap-4 bg-red-50 ring-1 ring-red-200 text-red-700 rounded-2xl px-4 py-3">
          <span className="flex items-center gap-2 text-sm font-medium">
            <AlertTriangle className="w-4 h-4" />
            {error}
          </span>
          <button
            onClick={fetchEvents}
            className="px-3 py-1.5 rounded-lg bg-red-600 text-white text-sm font-bold hover:bg-red-700"
          >
            Retry
          </button>
        </div>
      )}

      {loading && !events.length ? (
        <div className="flex justify-center py-16">
          <Loader2 className="w-8 h-8 animate-spin text-brand-600" />
        </div>
      ) : (
        <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand overflow-hidden">
          <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-brand-50/50">
              <tr>
                <th scope="col" className="text-left px-4 py-3 font-bold text-brand-900">Event</th>
                <th scope="col" className="text-left px-4 py-3 font-bold text-brand-900">IP Address</th>
                <th scope="col" className="text-left px-4 py-3 font-bold text-brand-900">User Agent</th>
                <th scope="col" className="text-left px-4 py-3 font-bold text-brand-900">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-brand-100">
              {events.map((e) => (
                <tr key={e.id} className="hover:bg-brand-50/30">
                  <td className="px-4 py-3">
                    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-bold ring-1 ${eventTypeColor(e.event_type)}`}>
                      {e.event_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-600">{e.ip_address || '—'}</td>
                  <td className="px-4 py-3 text-slate-600 truncate max-w-xs" title={e.user_agent}>
                    {e.user_agent || '—'}
                  </td>
                  <td className="px-4 py-3 text-slate-500 text-xs">{e.created_at}</td>
                </tr>
              ))}
              {!events.length && (
                <tr>
                  <td colSpan={4} className="px-4 py-12 text-center text-slate-400">
                    No security events found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          </div>
        </div>
      )}

      {total > perPage && (
        <div className="flex items-center justify-between">
          <button
            disabled={page <= 1}
            onClick={() => setPage(p => p - 1)}
            className="px-4 py-2 rounded-xl bg-white ring-1 ring-brand-200 text-sm font-bold disabled:opacity-40"
          >
            Previous
          </button>
          <span className="text-sm text-slate-500">
            Page {page} of {Math.ceil(total / perPage)}
          </span>
          <button
            disabled={page >= Math.ceil(total / perPage)}
            onClick={() => setPage(p => p + 1)}
            className="px-4 py-2 rounded-xl bg-white ring-1 ring-brand-200 text-sm font-bold disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
