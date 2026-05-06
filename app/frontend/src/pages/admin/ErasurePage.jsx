import { useState, useEffect, useCallback } from 'react'
import { Loader2, Trash2, AlertTriangle, Check, Building2, Clock, FileX } from 'lucide-react'
import { getAdminTenants, requestErasure, getErasureLogs } from '../../lib/api'

export default function ErasurePage() {
  const [tenants, setTenants] = useState([])
  const [selectedTenant, setSelectedTenant] = useState('')
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(false)
  const [logsLoading, setLogsLoading] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [erasing, setErasing] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const fetchTenants = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getAdminTenants({ per_page: 100 })
      setTenants(data.tenants || [])
    } catch (err) {
      console.error('Failed to fetch tenants:', err)
      setError('Failed to load tenants.')
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchLogs = useCallback(async (tenantId) => {
    if (!tenantId) return
    setLogsLoading(true)
    try {
      const data = await getErasureLogs(tenantId)
      setLogs(data || [])
    } catch (err) {
      console.error('Failed to fetch erasure logs:', err)
      setLogs([])
    } finally {
      setLogsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchTenants()
  }, [fetchTenants])

  useEffect(() => {
    fetchLogs(selectedTenant)
  }, [selectedTenant, fetchLogs])

  const handleErase = async () => {
    setError('')
    setSuccess('')
    setErasing(true)
    try {
      const data = await requestErasure(selectedTenant)
      setSuccess(`Erasure completed. ${data.records_affected || 0} records anonymized.`)
      setConfirmOpen(false)
      fetchLogs(selectedTenant)
    } catch (err) {
      setError(err.response?.data?.detail || 'Erasure request failed.')
    } finally {
      setErasing(false)
    }
  }

  const selectedTenantName = tenants.find((t) => String(t.id) === selectedTenant)?.name || ''

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-extrabold text-brand-900 tracking-tight flex items-center gap-2">
          <Trash2 className="w-6 h-6 text-brand-600" />
          GDPR Data Erasure
        </h2>
      </div>

      {/* Tenant Selector */}
      <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6">
        <label className="block text-sm font-bold text-brand-900 mb-2">Select Tenant</label>
        <div className="flex flex-col sm:flex-row gap-3">
          <select
            className="flex-1 px-4 py-2.5 rounded-xl ring-1 ring-brand-200 bg-white text-sm"
            value={selectedTenant}
            onChange={(e) => { setSelectedTenant(e.target.value); setError(''); setSuccess('') }}
          >
            <option value="">{loading ? 'Loading tenants...' : 'Choose a tenant'}</option>
            {tenants.map((t) => (
              <option key={t.id} value={String(t.id)}>
                {t.name} (ID: {t.id})
              </option>
            ))}
          </select>
          <button
            onClick={() => { setConfirmOpen(true); setError(''); setSuccess('') }}
            disabled={!selectedTenant || erasing}
            className="px-6 py-2.5 rounded-xl bg-red-600 text-white text-sm font-bold hover:bg-red-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
          >
            <Trash2 className="w-4 h-4" />
            Request Erasure
          </button>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-red-50 rounded-xl ring-1 ring-red-200 text-sm text-red-700">
            {error}
          </div>
        )}
        {success && (
          <div className="mt-4 p-3 bg-green-50 rounded-xl ring-1 ring-green-200 text-sm text-green-700">
            {success}
          </div>
        )}
      </div>

      {/* Confirmation Modal */}
      {confirmOpen && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl ring-1 ring-brand-100 shadow-2xl max-w-md w-full p-6 space-y-4">
            <div className="flex items-center gap-3 text-red-600">
              <AlertTriangle className="w-8 h-8" />
              <h3 className="text-lg font-extrabold text-brand-900">Confirm Data Erasure</h3>
            </div>
            <p className="text-sm text-slate-600">
              This will permanently anonymize all personal data for tenant <strong>{selectedTenantName}</strong>.
              The tenant will be suspended. This action cannot be undone.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setConfirmOpen(false)}
                className="px-4 py-2 rounded-xl bg-slate-100 text-slate-700 text-sm font-bold hover:bg-slate-200 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleErase}
                disabled={erasing}
                className="px-4 py-2 rounded-xl bg-red-600 text-white text-sm font-bold hover:bg-red-700 disabled:opacity-50 transition-colors flex items-center gap-2"
              >
                {erasing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                {erasing ? 'Erasing...' : 'Confirm Erasure'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Erasure Logs */}
      <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand overflow-hidden">
        <div className="px-6 py-4 border-b border-brand-100 flex items-center justify-between">
          <h3 className="text-lg font-bold text-brand-900 flex items-center gap-2">
            <FileX className="w-5 h-5 text-brand-600" />
            Erasure Logs
          </h3>
          {selectedTenant && (
            <button
              onClick={() => fetchLogs(selectedTenant)}
              className="text-sm font-bold text-brand-600 hover:text-brand-700"
            >
              Refresh
            </button>
          )}
        </div>

        {logsLoading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="w-8 h-8 animate-spin text-brand-600" />
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-brand-50/50">
              <tr>
                <th className="text-left px-4 py-3 font-bold text-brand-900">Status</th>
                <th className="text-left px-4 py-3 font-bold text-brand-900">Actor</th>
                <th className="text-left px-4 py-3 font-bold text-brand-900">Records</th>
                <th className="text-left px-4 py-3 font-bold text-brand-900">Started</th>
                <th className="text-left px-4 py-3 font-bold text-brand-900">Completed</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-brand-100">
              {logs.map((log) => (
                <tr key={log.id} className="hover:bg-brand-50/30">
                  <td className="px-4 py-3">
                    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-bold ring-1 ${
                      log.status === 'completed'
                        ? 'text-green-700 bg-green-50 ring-green-200'
                        : log.status === 'failed'
                        ? 'text-red-700 bg-red-50 ring-red-200'
                        : 'text-amber-700 bg-amber-50 ring-amber-200'
                    }`}>
                      {log.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-700">{log.actor_email || '—'}</td>
                  <td className="px-4 py-3 text-slate-700 font-mono text-xs">{log.records_affected ?? '—'}</td>
                  <td className="px-4 py-3 text-slate-500 text-xs">{log.started_at || '—'}</td>
                  <td className="px-4 py-3 text-slate-500 text-xs">{log.completed_at || '—'}</td>
                </tr>
              ))}
              {!logs.length && (
                <tr>
                  <td colSpan={5} className="px-4 py-12 text-center text-slate-400">
                    {selectedTenant ? 'No erasure logs for this tenant.' : 'Select a tenant to view erasure logs.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
