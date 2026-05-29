import { useState, useEffect, useCallback } from 'react'
import {
  Loader2,
  AlertTriangle,
  X,
  Plus,
  Trash2,
  ChevronDown,
  Link,
  CheckCircle,
  XCircle,
  Activity,
  Webhook as WebhookIcon,
  RefreshCw,
} from 'lucide-react'
import {
  getAdminTenants,
  getTenantWebhooks,
  createTenantWebhook,
  deleteTenantWebhook,
  getWebhookDeliveries,
  getWebhookEvents,
} from '../../lib/api'

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

/* ── Status Badge ──────────────────────────────────────── */
function WebhookStatusBadge({ isActive, failureCount }) {
  if (!isActive) {
    return <span className="px-2 py-0.5 rounded-full text-xs font-bold ring-1 bg-gray-100 text-gray-600 ring-gray-200">Disabled</span>
  }
  if (failureCount > 3) {
    return <span className="px-2 py-0.5 rounded-full text-xs font-bold ring-1 bg-red-50 text-red-700 ring-red-200">Failing</span>
  }
  return <span className="px-2 py-0.5 rounded-full text-xs font-bold ring-1 bg-green-50 text-green-700 ring-green-200">Active</span>
}

/* ── Create Webhook Modal ──────────────────────────────── */
function CreateWebhookModal({ tenantId, events, onClose, onCreated }) {
  const [url, setUrl] = useState('')
  const [secret, setSecret] = useState('')
  const [autoSecret, setAutoSecret] = useState(true)
  const [selectedEvents, setSelectedEvents] = useState(['*'])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const handleToggleEvent = (event) => {
    setSelectedEvents(prev => {
      if (event === '*') {
        return prev.includes('*') ? [] : ['*']
      }
      const withoutAll = prev.filter(e => e !== '*')
      if (withoutAll.includes(event)) {
        return withoutAll.filter(e => e !== event)
      }
      return [...withoutAll, event]
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!url.trim()) {
      setError('URL is required.')
      return
    }
    if (!url.trim().startsWith('https://')) {
      setError('URL must start with https://')
      return
    }
    if (selectedEvents.length === 0) {
      setError('Select at least one event.')
      return
    }
    setSaving(true)
    setError('')
    try {
      await createTenantWebhook(tenantId, {
        url: url.trim(),
        secret: autoSecret ? '' : secret.trim(),
        events: selectedEvents,
      })
      onCreated()
      onClose()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create webhook')
    } finally {
      setSaving(false)
    }
  }

  const generateSecret = () => {
    const array = new Uint8Array(32)
    crypto.getRandomValues(array)
    return Array.from(array, b => b.toString(16).padStart(2, '0')).join('')
  }

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl ring-1 ring-gray-200 shadow-xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-lg font-bold text-gray-900">Create Webhook</h3>
          <button onClick={onClose} className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 rounded-lg ring-1 ring-red-200 text-sm text-red-700">{error}</div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">URL *</label>
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com/webhooks"
              className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-sm"
              required
            />
            <p className="text-xs text-gray-400 mt-1">Must be an HTTPS URL.</p>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-sm font-semibold text-gray-700">Secret</label>
              <button
                type="button"
                onClick={() => setAutoSecret(v => !v)}
                className="text-xs text-teal-600 hover:text-teal-700 font-medium"
              >
                {autoSecret ? 'Use custom secret' : 'Auto-generate'}
              </button>
            </div>
            {autoSecret ? (
              <p className="text-xs text-gray-500">A secret will be auto-generated for HMAC-SHA256 signing.</p>
            ) : (
              <div className="flex gap-2">
                <input
                  type="text"
                  value={secret}
                  onChange={(e) => setSecret(e.target.value)}
                  placeholder="Enter custom secret..."
                  className="flex-1 px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-sm font-mono"
                />
                <button
                  type="button"
                  onClick={() => setSecret(generateSecret())}
                  className="px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                  title="Generate random secret"
                >
                  <RefreshCw className="w-4 h-4 text-gray-500" />
                </button>
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">Events</label>
            <div className="space-y-2">
              <label className="flex items-center gap-2 p-2 rounded-lg border cursor-pointer transition-all bg-white border-gray-200 hover:bg-gray-50">
                <input
                  type="checkbox"
                  checked={selectedEvents.includes('*')}
                  onChange={() => handleToggleEvent('*')}
                  className="w-4 h-4 text-teal-600 rounded"
                />
                <div>
                  <p className="text-sm font-semibold text-gray-800">All Events</p>
                  <p className="text-xs text-gray-400">Subscribe to every event type</p>
                </div>
              </label>
              {!selectedEvents.includes('*') && events.map(ev => (
                <label
                  key={ev.event}
                  className="flex items-center gap-2 p-2 rounded-lg border cursor-pointer transition-all bg-white border-gray-200 hover:bg-gray-50"
                >
                  <input
                    type="checkbox"
                    checked={selectedEvents.includes(ev.event)}
                    onChange={() => handleToggleEvent(ev.event)}
                    className="w-4 h-4 text-teal-600 rounded"
                  />
                  <div>
                    <p className="text-sm font-medium text-gray-800">{ev.event}</p>
                    <p className="text-xs text-gray-400">{ev.description}</p>
                  </div>
                </label>
              ))}
            </div>
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
              disabled={saving || !url.trim() || selectedEvents.length === 0}
              className="px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-sm font-bold rounded-lg disabled:opacity-50 transition-colors"
            >
              {saving ? 'Creating...' : 'Create Webhook'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

/* ── Delete Confirmation Modal ─────────────────────────── */
function DeleteWebhookModal({ webhook, onClose, onDone }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleDelete = async () => {
    setLoading(true)
    setError('')
    try {
      await deleteTenantWebhook(webhook.tenant_id, webhook.id)
      onDone()
      onClose()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete webhook')
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
            <h3 className="text-lg font-bold text-gray-900">Delete Webhook</h3>
            <p className="text-sm text-gray-500 truncate max-w-[240px]">{webhook.url}</p>
          </div>
        </div>
        <p className="text-sm text-gray-600 mb-4">This webhook will stop receiving events immediately.</p>
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
            {loading ? 'Deleting...' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  )
}

/* ── Delivery History Panel ────────────────────────────── */
function DeliveryHistory({ deliveries, loading }) {
  if (loading) {
    return (
      <div className="p-4 space-y-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-8 bg-gray-100 rounded animate-pulse" />
        ))}
      </div>
    )
  }

  if (deliveries.length === 0) {
    return (
      <div className="p-4 text-center text-sm text-gray-500">
        No delivery history yet.
      </div>
    )
  }

  return (
    <div className="divide-y divide-gray-100">
      {deliveries.map(d => (
        <div key={d.id} className="flex items-center gap-3 px-4 py-2.5">
          {d.success ? (
            <CheckCircle className="w-4 h-4 text-green-500 shrink-0" />
          ) : (
            <XCircle className="w-4 h-4 text-red-500 shrink-0" />
          )}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-800 truncate">{d.event}</p>
            <p className="text-xs text-gray-400">
              {d.created_at ? new Date(d.created_at).toLocaleString() : '—'}
              {d.response_status && ` · HTTP ${d.response_status}`}
              {d.attempt > 1 && ` · Attempt #${d.attempt}`}
            </p>
          </div>
        </div>
      ))}
    </div>
  )
}

/* ── Main WebhooksPage ─────────────────────────────────── */
export default function WebhooksPage() {
  // Data
  const [tenants, setTenants] = useState([])
  const [selectedTenantId, setSelectedTenantId] = useState('')
  const [webhooks, setWebhooks] = useState([])
  const [webhookEvents, setWebhookEvents] = useState([])
  const [loadingTenants, setLoadingTenants] = useState(true)
  const [loadingWebhooks, setLoadingWebhooks] = useState(false)
  const [error, setError] = useState('')
  const [toast, setToast] = useState(null)

  // Delivery history
  const [expandedWebhookId, setExpandedWebhookId] = useState(null)
  const [deliveries, setDeliveries] = useState([])
  const [loadingDeliveries, setLoadingDeliveries] = useState(false)

  // Modals
  const [showCreate, setShowCreate] = useState(false)
  const [deleteWebhook, setDeleteWebhook] = useState(null)

  /* ── Fetch tenants ──────────────────────────────────── */
  const fetchTenants = useCallback(async () => {
    setLoadingTenants(true)
    setError('')
    try {
      const data = await getAdminTenants({ per_page: 200 })
      setTenants(data.tenants || data.items || data || [])
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load tenants')
    } finally {
      setLoadingTenants(false)
    }
  }, [])

  useEffect(() => {
    fetchTenants()
  }, [fetchTenants])

  /* ── Fetch webhook events ───────────────────────────── */
  useEffect(() => {
    getWebhookEvents()
      .then(data => setWebhookEvents(data.events || []))
      .catch(() => {})
  }, [])

  /* ── Fetch webhooks for selected tenant ─────────────── */
  const fetchWebhooks = useCallback(async () => {
    if (!selectedTenantId) {
      setWebhooks([])
      return
    }
    setLoadingWebhooks(true)
    setError('')
    try {
      const data = await getTenantWebhooks(Number(selectedTenantId))
      setWebhooks(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load webhooks')
    } finally {
      setLoadingWebhooks(false)
    }
  }, [selectedTenantId])

  useEffect(() => {
    fetchWebhooks()
    setExpandedWebhookId(null)
  }, [fetchWebhooks])

  /* ── Fetch deliveries ───────────────────────────────── */
  const fetchDeliveries = useCallback(async (webhookId) => {
    setLoadingDeliveries(true)
    try {
      const data = await getWebhookDeliveries(Number(selectedTenantId), webhookId)
      setDeliveries(Array.isArray(data) ? data : [])
    } catch {
      setDeliveries([])
    } finally {
      setLoadingDeliveries(false)
    }
  }, [selectedTenantId])

  const handleToggleDeliveries = (webhookId) => {
    if (expandedWebhookId === webhookId) {
      setExpandedWebhookId(null)
    } else {
      setExpandedWebhookId(webhookId)
      fetchDeliveries(webhookId)
    }
  }

  /* ── Loading skeletons ──────────────────────────────── */
  if (loadingTenants) {
    return (
      <div className="space-y-5">
        <div className="h-8 w-48 bg-gray-200 rounded-lg animate-pulse" />
        <div className="h-64 bg-gray-100 rounded-xl animate-pulse" />
      </div>
    )
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Webhooks</h1>
          <p className="text-sm text-gray-500 mt-0.5">Manage webhook endpoints per tenant</p>
        </div>
        {selectedTenantId && (
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-sm font-bold rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            Create Webhook
          </button>
        )}
      </div>

      {toast && <Toast message={toast.message} type={toast.type} onDone={() => setToast(null)} />}

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-50 rounded-xl ring-1 ring-red-200 text-sm text-red-700 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
          <button onClick={() => selectedTenantId ? fetchWebhooks() : fetchTenants()} className="ml-auto px-3 py-1 text-xs font-bold bg-red-100 hover:bg-red-200 rounded-lg transition-colors">
            Retry
          </button>
        </div>
      )}

      {/* Tenant selector */}
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <label className="block text-sm font-semibold text-gray-700 mb-2">Select Tenant</label>
        <div className="relative max-w-md">
          <select
            value={selectedTenantId}
            onChange={(e) => setSelectedTenantId(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 text-sm appearance-none cursor-pointer"
          >
            <option value="">Choose a tenant...</option>
            {tenants.map(t => (
              <option key={t.id} value={t.id}>{t.name} ({t.slug})</option>
            ))}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
        </div>
      </div>

      {/* Webhooks list */}
      {selectedTenantId && (
        <div className="space-y-4">
          {loadingWebhooks ? (
            <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="flex gap-4">
                  <div className="h-4 w-64 bg-gray-100 rounded animate-pulse" />
                  <div className="h-4 w-20 bg-gray-100 rounded animate-pulse" />
                  <div className="h-4 w-16 bg-gray-100 rounded animate-pulse" />
                </div>
              ))}
            </div>
          ) : webhooks.length === 0 ? (
            <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
              <WebhookIcon className="w-10 h-10 text-gray-300 mx-auto mb-2" />
              <p className="text-sm text-gray-500">No webhooks configured for this tenant.</p>
              <button
                onClick={() => setShowCreate(true)}
                className="mt-3 px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-sm font-bold rounded-lg transition-colors"
              >
                Create your first webhook
              </button>
            </div>
          ) : (
            webhooks.map(wh => (
              <div key={wh.id} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                {/* Webhook header */}
                <div className="p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <Link className="w-4 h-4 text-gray-400 shrink-0" />
                        <p className="text-sm font-semibold text-gray-900 truncate">{wh.url}</p>
                      </div>
                      <div className="flex flex-wrap items-center gap-2 mt-2">
                        <WebhookStatusBadge isActive={wh.is_active} failureCount={wh.failure_count || 0} />
                        <div className="flex flex-wrap gap-1">
                          {(wh.events || []).map(ev => (
                            <span key={ev} className="px-1.5 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
                              {ev}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div className="flex items-center gap-4 mt-2 text-xs text-gray-400">
                        {wh.last_triggered_at && (
                          <span>Last triggered: {new Date(wh.last_triggered_at).toLocaleString()}</span>
                        )}
                        {wh.failure_count > 0 && (
                          <span className="text-red-500">Failures: {wh.failure_count}</span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleToggleDeliveries(wh.id)}
                        className={`p-2 rounded-lg transition-colors ${expandedWebhookId === wh.id ? 'bg-teal-50 text-teal-600' : 'text-gray-400 hover:bg-gray-50 hover:text-gray-600'}`}
                        title="View delivery history"
                      >
                        <Activity className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setDeleteWebhook({ ...wh, tenant_id: Number(selectedTenantId) })}
                        className="p-2 rounded-lg text-gray-400 hover:bg-red-50 hover:text-red-600 transition-colors"
                        title="Delete webhook"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>

                {/* Delivery history (expandable) */}
                {expandedWebhookId === wh.id && (
                  <div className="border-t border-gray-200 bg-gray-50">
                    <div className="px-4 py-2 border-b border-gray-200">
                      <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Recent Deliveries</h4>
                    </div>
                    <DeliveryHistory deliveries={deliveries} loading={loadingDeliveries} />
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {/* No tenant selected */}
      {!selectedTenantId && !loadingTenants && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <WebhookIcon className="w-10 h-10 text-gray-300 mx-auto mb-2" />
          <p className="text-sm text-gray-500">Select a tenant above to manage webhooks.</p>
        </div>
      )}

      {/* Modals */}
      {showCreate && selectedTenantId && (
        <CreateWebhookModal
          tenantId={Number(selectedTenantId)}
          events={webhookEvents}
          onClose={() => setShowCreate(false)}
          onCreated={fetchWebhooks}
        />
      )}
      {deleteWebhook && (
        <DeleteWebhookModal
          webhook={deleteWebhook}
          onClose={() => setDeleteWebhook(null)}
          onDone={() => { setToast({ message: 'Webhook deleted.', type: 'success' }); fetchWebhooks() }}
        />
      )}
    </div>
  )
}
