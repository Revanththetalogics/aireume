import { useState, useEffect, useCallback } from 'react'
import { Loader2, Shield, UserCheck, XCircle, Clock, Copy, Check } from 'lucide-react'
import { impersonateUser, listImpersonationSessions, revokeImpersonationSession } from '../../lib/api'

export default function ImpersonationPage() {
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(false)
  const [userId, setUserId] = useState('')
  const [actionLoading, setActionLoading] = useState(false)
  const [token, setToken] = useState(null)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const fetchSessions = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listImpersonationSessions()
      setSessions(data || [])
    } catch (err) {
      console.error('Failed to fetch sessions:', err)
      setError('Failed to load impersonation sessions.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchSessions()
  }, [fetchSessions])

  const handleImpersonate = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setToken(null)
    if (!userId.trim()) return
    setActionLoading(true)
    try {
      const id = parseInt(userId.trim(), 10)
      if (isNaN(id)) throw new Error('User ID must be a number')
      const data = await impersonateUser(id)
      setToken(data.impersonation_token)
      setSuccess(`Impersonation session created for ${data.target_user?.email || 'user'}. Token expires in ${data.expires_in_minutes} minutes.`)
      setUserId('')
      fetchSessions()
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to create session.')
    } finally {
      setActionLoading(false)
    }
  }

  const handleRevoke = async (sessionId) => {
    setError('')
    setSuccess('')
    setActionLoading(true)
    try {
      await revokeImpersonationSession(sessionId)
      setSuccess('Session revoked successfully.')
      fetchSessions()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to revoke session.')
    } finally {
      setActionLoading(false)
    }
  }

  const copyToken = () => {
    if (!token) return
    navigator.clipboard.writeText(token)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-extrabold text-brand-900 tracking-tight flex items-center gap-2">
          <Shield className="w-6 h-6 text-brand-600" />
          Impersonation
        </h2>
      </div>

      {/* Create Session Card */}
      <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6">
        <h3 className="text-lg font-bold text-brand-900 mb-4 flex items-center gap-2">
          <UserCheck className="w-5 h-5 text-brand-600" />
          Start Impersonation Session
        </h3>
        <form onSubmit={handleImpersonate} className="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            inputMode="numeric"
            placeholder="Target User ID"
            className="flex-1 px-4 py-2.5 rounded-xl ring-1 ring-brand-200 bg-white text-sm"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
          />
          <button
            type="submit"
            disabled={actionLoading || !userId.trim()}
            className="px-6 py-2.5 rounded-xl bg-brand-600 text-white text-sm font-bold hover:bg-brand-700 disabled:opacity-50 transition-colors"
          >
            {actionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Create Session'}
          </button>
        </form>

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
        {token && (
          <div className="mt-4 p-4 bg-amber-50 rounded-xl ring-1 ring-amber-200">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-bold text-amber-800">Impersonation Token</span>
              <button
                onClick={copyToken}
                className="flex items-center gap-1 text-xs font-bold text-amber-700 hover:text-amber-900"
              >
                {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>
            <code className="block text-xs font-mono text-amber-900 break-all bg-white/60 rounded-lg p-3">
              {token}
            </code>
            <p className="mt-2 text-xs text-amber-700">
              Pass this token in the <code className="font-mono">X-Impersonation-Token</code> header to authenticate as the target user.
            </p>
          </div>
        )}
      </div>

      {/* Active Sessions */}
      <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand overflow-hidden">
        <div className="px-6 py-4 border-b border-brand-100 flex items-center justify-between">
          <h3 className="text-lg font-bold text-brand-900 flex items-center gap-2">
            <Clock className="w-5 h-5 text-brand-600" />
            Active Sessions
          </h3>
          <button
            onClick={fetchSessions}
            className="text-sm font-bold text-brand-600 hover:text-brand-700"
          >
            Refresh
          </button>
        </div>

        {loading && !sessions.length ? (
          <div className="flex justify-center py-16">
            <Loader2 className="w-8 h-8 animate-spin text-brand-600" />
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-brand-50/50">
              <tr>
                <th className="text-left px-4 py-3 font-bold text-brand-900">Admin</th>
                <th className="text-left px-4 py-3 font-bold text-brand-900">Target User</th>
                <th className="text-left px-4 py-3 font-bold text-brand-900">Created</th>
                <th className="text-left px-4 py-3 font-bold text-brand-900">Expires</th>
                <th className="text-left px-4 py-3 font-bold text-brand-900">IP</th>
                <th className="text-right px-4 py-3 font-bold text-brand-900">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-brand-100">
              {sessions.map((s) => (
                <tr key={s.id} className="hover:bg-brand-50/30">
                  <td className="px-4 py-3 text-slate-700">{s.admin_email || s.admin_user_id}</td>
                  <td className="px-4 py-3 text-slate-700">{s.target_email || s.target_user_id}</td>
                  <td className="px-4 py-3 text-slate-500 text-xs">{s.created_at}</td>
                  <td className="px-4 py-3 text-slate-500 text-xs">{s.expires_at}</td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-600">{s.ip_address || '—'}</td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => handleRevoke(s.id)}
                      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-red-50 text-red-700 text-xs font-bold hover:bg-red-100 ring-1 ring-red-200 transition-colors"
                    >
                      <XCircle className="w-3 h-3" />
                      Revoke
                    </button>
                  </td>
                </tr>
              ))}
              {!sessions.length && (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-slate-400">
                    No active impersonation sessions.
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
