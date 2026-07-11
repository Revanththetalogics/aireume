import { useState, useEffect, useCallback } from 'react'
import {
  Plug, Plus, RefreshCw, Trash2, Loader2, CheckCircle2, XCircle, ArrowUpDown,
} from 'lucide-react'
import {
  listATSConnections,
  createATSConnection,
  updateATSConnection,
  deleteATSConnection,
  getATSSyncLogs,
  pushToATS,
  syncATSRequisitions,
} from '../../lib/api'
import { Button } from '../ui'

const PROVIDERS = [
  { id: 'greenhouse', label: 'Greenhouse' },
  { id: 'lever', label: 'Lever' },
  { id: 'workday', label: 'Workday' },
  { id: 'generic', label: 'Generic / Webhook' },
]

const DIRECTIONS = [
  { id: 'push', label: 'Push only' },
  { id: 'pull', label: 'Pull only' },
  { id: 'bidirectional', label: 'Bidirectional' },
]

const EMPTY_FORM = {
  provider: 'greenhouse',
  label: '',
  api_key: '',
  api_secret: '',
  base_url: '',
  webhook_url: '',
  sync_direction: 'push',
}

export default function ATSIntegrationsPanel() {
  const [connections, setConnections] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [selectedId, setSelectedId] = useState(null)
  const [logs, setLogs] = useState([])
  const [logsLoading, setLogsLoading] = useState(false)
  const [message, setMessage] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listATSConnections()
      setConnections(Array.isArray(data) ? data : [])
    } catch {
      setConnections([])
      setMessage({ type: 'error', text: 'Could not load ATS connections.' })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const loadLogs = async (connectionId) => {
    setSelectedId(connectionId)
    setLogsLoading(true)
    try {
      const data = await getATSSyncLogs(connectionId)
      setLogs(Array.isArray(data) ? data : data?.logs || [])
    } catch {
      setLogs([])
    } finally {
      setLogsLoading(false)
    }
  }

  const handleCreate = async (e) => {
    e.preventDefault()
    if (!form.label.trim()) return
    setSaving(true)
    setMessage(null)
    try {
      await createATSConnection(form)
      setForm(EMPTY_FORM)
      setShowForm(false)
      setMessage({ type: 'success', text: 'Connection created.' })
      await load()
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to create connection.' })
    } finally {
      setSaving(false)
    }
  }

  const toggleActive = async (conn) => {
    try {
      await updateATSConnection(conn.id, { is_active: !conn.is_active })
      await load()
    } catch {
      setMessage({ type: 'error', text: 'Failed to update connection.' })
    }
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this ATS connection?')) return
    try {
      await deleteATSConnection(id)
      if (selectedId === id) {
        setSelectedId(null)
        setLogs([])
      }
      await load()
    } catch {
      setMessage({ type: 'error', text: 'Failed to delete connection.' })
    }
  }

  const handleTestPush = async (conn) => {
    setMessage(null)
    try {
      await pushToATS(conn.id, { candidate_id: 0, status: 'pending' })
      setMessage({ type: 'success', text: 'Test push sent (may fail without valid candidate).' })
      loadLogs(conn.id)
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.detail || 'Push test failed.' })
    }
  }

  const handleSyncRequisitions = async (conn) => {
    setMessage(null)
    try {
      const result = await syncATSRequisitions(conn.id)
      setMessage({
        type: 'success',
        text: result.message || `Synced ${result.synced ?? 0} requisition(s) from ATS.`,
      })
      await load()
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.detail || 'Requisition sync failed.' })
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h3 className="text-lg font-extrabold text-brand-900">ATS Integrations</h3>
          <p className="text-sm text-slate-500 mt-0.5">
            Connect Greenhouse, Lever, Workday, or a generic webhook to sync candidate status.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button size="sm" onClick={() => setShowForm((v) => !v)}>
            <Plus className="w-4 h-4" />
            Add Connection
          </Button>
        </div>
      </div>

      {message && (
        <div
          className={`p-3 rounded-xl text-sm font-medium ring-1 ${
            message.type === 'success'
              ? 'bg-green-50 text-green-800 ring-green-200'
              : 'bg-red-50 text-red-800 ring-red-200'
          }`}
        >
          {message.text}
        </div>
      )}

      {showForm && (
        <form onSubmit={handleCreate} className="bg-white/90 rounded-2xl ring-1 ring-brand-100 p-5 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <label className="block text-sm">
              <span className="font-semibold text-slate-700">Provider</span>
              <select
                value={form.provider}
                onChange={(e) => setForm((f) => ({ ...f, provider: e.target.value }))}
                className="mt-1 w-full rounded-xl border border-brand-200 px-3 py-2 text-sm"
              >
                {PROVIDERS.map((p) => (
                  <option key={p.id} value={p.id}>{p.label}</option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              <span className="font-semibold text-slate-700">Label</span>
              <input
                value={form.label}
                onChange={(e) => setForm((f) => ({ ...f, label: e.target.value }))}
                placeholder="Production Greenhouse"
                className="mt-1 w-full rounded-xl border border-brand-200 px-3 py-2 text-sm"
                required
              />
            </label>
            <label className="block text-sm">
              <span className="font-semibold text-slate-700">API Key</span>
              <input
                type="password"
                value={form.api_key}
                onChange={(e) => setForm((f) => ({ ...f, api_key: e.target.value }))}
                className="mt-1 w-full rounded-xl border border-brand-200 px-3 py-2 text-sm"
              />
            </label>
            <label className="block text-sm">
              <span className="font-semibold text-slate-700">Base URL</span>
              <input
                value={form.base_url}
                onChange={(e) => setForm((f) => ({ ...f, base_url: e.target.value }))}
                placeholder="https://api.greenhouse.io"
                className="mt-1 w-full rounded-xl border border-brand-200 px-3 py-2 text-sm"
              />
            </label>
            <label className="block text-sm sm:col-span-2">
              <span className="font-semibold text-slate-700">Sync direction</span>
              <select
                value={form.sync_direction}
                onChange={(e) => setForm((f) => ({ ...f, sync_direction: e.target.value }))}
                className="mt-1 w-full rounded-xl border border-brand-200 px-3 py-2 text-sm"
              >
                {DIRECTIONS.map((d) => (
                  <option key={d.id} value={d.id}>{d.label}</option>
                ))}
              </select>
            </label>
          </div>
          <div className="flex gap-2 justify-end">
            <Button type="button" variant="secondary" onClick={() => setShowForm(false)}>Cancel</Button>
            <Button type="submit" disabled={saving}>
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Save Connection'}
            </Button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 text-brand-500 animate-spin" />
        </div>
      ) : connections.length === 0 ? (
        <div className="text-center py-12 rounded-2xl ring-1 ring-brand-100 bg-brand-50/30">
          <Plug className="w-10 h-10 text-brand-300 mx-auto mb-3" />
          <p className="text-sm text-slate-500">No ATS connections yet.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {connections.map((conn) => (
            <div
              key={conn.id}
              className={`rounded-2xl ring-1 p-4 transition-colors ${
                selectedId === conn.id ? 'ring-brand-400 bg-brand-50/40' : 'ring-brand-100 bg-white/90'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-bold text-brand-900">{conn.label}</p>
                  <p className="text-xs text-slate-500 capitalize">{conn.provider} · {conn.sync_direction}</p>
                </div>
                <span
                  className={`text-xs font-semibold px-2 py-0.5 rounded-full ring-1 ${
                    conn.is_active
                      ? 'bg-green-50 text-green-700 ring-green-200'
                      : 'bg-slate-100 text-slate-500 ring-slate-200'
                  }`}
                >
                  {conn.is_active ? 'Active' : 'Paused'}
                </span>
              </div>
              {conn.last_sync_at && (
                <p className="text-xs text-slate-400 mt-2">
                  Last sync: {new Date(conn.last_sync_at).toLocaleString()}
                  {conn.last_sync_status ? ` (${conn.last_sync_status})` : ''}
                </p>
              )}
              <div className="flex flex-wrap gap-2 mt-4">
                <Button size="sm" variant="secondary" onClick={() => loadLogs(conn.id)}>
                  <ArrowUpDown className="w-3.5 h-3.5" />
                  Logs
                </Button>
                <Button size="sm" variant="secondary" onClick={() => toggleActive(conn)}>
                  {conn.is_active ? 'Pause' : 'Activate'}
                </Button>
                <Button size="sm" variant="secondary" onClick={() => handleSyncRequisitions(conn)}>
                  <RefreshCw className="w-3.5 h-3.5" />
                  Sync requisitions
                </Button>
                <Button size="sm" variant="secondary" onClick={() => handleTestPush(conn)}>
                  Test push
                </Button>
                <button
                  type="button"
                  onClick={() => handleDelete(conn.id)}
                  className="p-2 rounded-lg text-red-500 hover:bg-red-50"
                  aria-label="Delete"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {selectedId && (
        <div className="rounded-2xl ring-1 ring-brand-100 bg-white/90 p-5">
          <h4 className="text-sm font-bold text-brand-900 mb-3">Sync logs</h4>
          {logsLoading ? (
            <Loader2 className="w-5 h-5 animate-spin text-brand-500" />
          ) : logs.length === 0 ? (
            <p className="text-sm text-slate-400">No sync activity yet.</p>
          ) : (
            <ul className="space-y-2 max-h-64 overflow-y-auto">
              {logs.slice(0, 20).map((log) => (
                <li key={log.id} className="flex items-center gap-2 text-sm">
                  {log.success ? (
                    <CheckCircle2 className="w-4 h-4 text-green-500 shrink-0" />
                  ) : (
                    <XCircle className="w-4 h-4 text-red-500 shrink-0" />
                  )}
                  <span className="text-slate-700 capitalize">{log.direction} {log.entity_type}</span>
                  <span className="text-slate-400 text-xs ml-auto">
                    {log.created_at ? new Date(log.created_at).toLocaleString() : ''}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
