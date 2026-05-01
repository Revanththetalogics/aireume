import { useState, useEffect } from 'react'
import {
  Mail,
  Loader2,
  Check,
  AlertTriangle,
  Save,
  TestTube,
  Trash2,
  ShieldCheck,
  Info,
  X
} from 'lucide-react'
import {
  getEmailConfig,
  saveEmailConfig,
  testEmailConfig,
  deleteEmailConfig,
} from '../../lib/api'

function Toast({ message, type = 'success', onDone }) {
  useEffect(() => {
    const t = setTimeout(onDone, 3000)
    return () => clearTimeout(t)
  }, [onDone])

  const bg = type === 'success' ? 'bg-brand-900' : 'bg-red-600'
  return (
    <div className={`fixed bottom-6 right-6 z-50 ${bg} text-white px-5 py-3 rounded-2xl shadow-brand-lg text-sm font-semibold card-animate flex items-center gap-2`}>
      {type === 'success' ? <Check className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
      {message}
    </div>
  )
}

function ConfirmDialog({ title, message, onConfirm, onCancel, confirmText = 'Confirm', destructive = false }) {
  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white/95 backdrop-blur-xl rounded-3xl ring-1 ring-brand-100 shadow-brand-xl w-full max-w-md p-6 card-animate">
        <div className="flex items-start gap-4">
          <div className={`w-10 h-10 rounded-2xl flex items-center justify-center shrink-0 ${destructive ? 'bg-red-50 ring-1 ring-red-100' : 'bg-brand-50 ring-1 ring-brand-100'}`}>
            <AlertTriangle className={`w-5 h-5 ${destructive ? 'text-red-600' : 'text-brand-600'}`} />
          </div>
          <div>
            <h3 className="font-extrabold text-brand-900 tracking-tight">{title}</h3>
            <p className="text-sm text-slate-500 mt-1">{message}</p>
          </div>
        </div>
        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onCancel}
            className="px-4 py-2 ring-1 ring-brand-200 text-sm font-semibold text-brand-700 rounded-xl hover:bg-brand-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className={`px-4 py-2 text-white text-sm font-bold rounded-xl transition-colors ${
              destructive ? 'bg-red-600 hover:bg-red-700' : 'btn-brand shadow-brand-sm'
            }`}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function EmailSettings() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [config, setConfig] = useState(null)
  const [form, setForm] = useState({
    smtp_host: '',
    smtp_port: 587,
    smtp_user: '',
    smtp_password: '',
    smtp_from: '',
    from_name: '',
    reply_to: '',
    encryption_type: 'TLS',
  })
  const [originalPassword, setOriginalPassword] = useState('')
  const [toast, setToast] = useState(null)
  const [testResult, setTestResult] = useState(null)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  const encryptionOptions = ['TLS', 'SSL', 'None']

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getEmailConfig()
      .then((data) => {
        if (cancelled) return
        setConfig(data)
        const loaded = {
          smtp_host: data.smtp_host || '',
          smtp_port: data.smtp_port || 587,
          smtp_user: data.smtp_user || '',
          smtp_password: data.smtp_password || '',
          smtp_from: data.smtp_from || '',
          from_name: data.from_name || '',
          reply_to: data.reply_to || '',
          encryption_type: data.encryption_type || 'TLS',
        }
        setForm(loaded)
        setOriginalPassword(data.smtp_password || '')
      })
      .catch((err) => {
        if (cancelled) return
        const detail = err.response?.data?.detail || err.message
        if (err.response?.status === 404) {
          // No config yet — that's okay
          setConfig(null)
        } else {
          setToast({ message: `Failed to load email config: ${detail}`, type: 'error' })
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  function handleChange(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }))
    setTestResult(null)
  }

  function handlePasswordFocus() {
    if (form.smtp_password === originalPassword && originalPassword) {
      setForm((prev) => ({ ...prev, smtp_password: '' }))
    }
  }

  async function handleSave() {
    setSaving(true)
    setTestResult(null)
    try {
      const payload = { ...form }
      const res = await saveEmailConfig(payload)
      setConfig(res)
      if (res.smtp_password) {
        setOriginalPassword(res.smtp_password)
        setForm((prev) => ({ ...prev, smtp_password: res.smtp_password }))
      }
      setToast({ message: 'Email configuration saved successfully', type: 'success' })
    } catch (err) {
      const detail = err.response?.data?.detail || err.message
      setToast({ message: `Failed to save: ${detail}`, type: 'error' })
    } finally {
      setSaving(false)
    }
  }

  async function handleTest() {
    setTesting(true)
    setTestResult(null)
    try {
      const res = await testEmailConfig()
      setTestResult({ success: true, message: res.message || 'Test email sent successfully' })
      // Refresh config to update last_test info
      const refreshed = await getEmailConfig()
      setConfig(refreshed)
    } catch (err) {
      const detail = err.response?.data?.detail || err.message
      setTestResult({ success: false, message: detail || 'Test failed' })
    } finally {
      setTesting(false)
    }
  }

  async function handleDelete() {
    setDeleting(true)
    setShowDeleteConfirm(false)
    try {
      await deleteEmailConfig()
      setConfig(null)
      setForm({
        smtp_host: '',
        smtp_port: 587,
        smtp_user: '',
        smtp_password: '',
        smtp_from: '',
        from_name: '',
        reply_to: '',
        encryption_type: 'TLS',
      })
      setOriginalPassword('')
      setTestResult(null)
      setToast({ message: 'Email configuration removed', type: 'success' })
    } catch (err) {
      const detail = err.response?.data?.detail || err.message
      setToast({ message: `Failed to remove: ${detail}`, type: 'error' })
    } finally {
      setDeleting(false)
    }
  }

  const isConfigured = Boolean(config?.smtp_host && config?.smtp_from)

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-brand-600" />
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8 card-animate">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-2xl bg-brand-50 ring-1 ring-brand-100 flex items-center justify-center">
            <Mail className="w-5 h-5 text-brand-600" />
          </div>
          <div>
            <h1 className="text-3xl font-extrabold text-brand-900 tracking-tight">Email Settings</h1>
            <p className="text-slate-500 text-sm font-medium">Configure your organization&apos;s email delivery</p>
          </div>
        </div>
      </div>

      <div className="space-y-6">
        {/* Status Card */}
        <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6 card-animate">
          <h3 className="font-extrabold text-brand-900 tracking-tight mb-4">Configuration Status</h3>
          <div className="flex flex-col sm:flex-row sm:items-center gap-4">
            <div className={`flex items-center gap-3 p-3 rounded-xl ring-1 flex-1 ${
              isConfigured
                ? 'bg-green-50/50 ring-green-200'
                : 'bg-slate-50 ring-slate-200'
            }`}>
              {isConfigured ? (
                <ShieldCheck className="w-5 h-5 text-green-600 shrink-0" />
              ) : (
                <Info className="w-5 h-5 text-slate-500 shrink-0" />
              )}
              <div>
                <p className="text-xs text-slate-500 font-medium">Status</p>
                <p className={`text-sm font-bold ${isConfigured ? 'text-green-700' : 'text-slate-600'}`}>
                  {isConfigured ? 'Configured' : 'Not configured — using default'}
                </p>
              </div>
            </div>

            {isConfigured && config?.last_tested_at && (
              <div className="flex items-center gap-3 p-3 rounded-xl ring-1 bg-brand-50/50 ring-brand-100 flex-1">
                <TestTube className={`w-5 h-5 shrink-0 ${config.last_test_success ? 'text-green-600' : 'text-red-600'}`} />
                <div>
                  <p className="text-xs text-slate-500 font-medium">Last Test</p>
                  <p className={`text-sm font-bold ${config.last_test_success ? 'text-green-700' : 'text-red-700'}`}>
                    {new Date(config.last_tested_at).toLocaleString()} — {config.last_test_success ? 'Passed' : 'Failed'}
                  </p>
                </div>
              </div>
            )}
          </div>

          {!isConfigured && (
            <div className="mt-4 p-3 bg-blue-50/50 rounded-xl ring-1 ring-blue-100 flex items-start gap-2.5">
              <Info className="w-4 h-4 text-blue-600 mt-0.5 shrink-0" />
              <p className="text-sm text-blue-700">
                No custom email configuration is set. ARIA will use the default system sender for all outgoing emails.
              </p>
            </div>
          )}
        </div>

        {/* SMTP Configuration Form */}
        <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6 card-animate">
          <h3 className="font-extrabold text-brand-900 tracking-tight mb-5">SMTP Configuration</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="md:col-span-2">
              <label className="block text-sm font-bold text-slate-700 mb-1.5">
                SMTP Host <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={form.smtp_host}
                onChange={(e) => handleChange('smtp_host', e.target.value)}
                placeholder="smtp.example.com"
                className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white outline-none transition-all"
              />
            </div>

            <div>
              <label className="block text-sm font-bold text-slate-700 mb-1.5">
                SMTP Port <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                value={form.smtp_port}
                onChange={(e) => handleChange('smtp_port', parseInt(e.target.value, 10) || 0)}
                placeholder="587"
                className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white outline-none transition-all"
              />
            </div>

            <div>
              <label className="block text-sm font-bold text-slate-700 mb-1.5">Encryption Type</label>
              <select
                value={form.encryption_type}
                onChange={(e) => handleChange('encryption_type', e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white outline-none transition-all"
              >
                {encryptionOptions.map((opt) => (
                  <option key={opt} value={opt}>{opt}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-bold text-slate-700 mb-1.5">Username</label>
              <input
                type="text"
                value={form.smtp_user}
                onChange={(e) => handleChange('smtp_user', e.target.value)}
                placeholder="user@example.com"
                className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white outline-none transition-all"
              />
            </div>

            <div>
              <label className="block text-sm font-bold text-slate-700 mb-1.5">Password</label>
              <input
                type="password"
                value={form.smtp_password}
                onChange={(e) => handleChange('smtp_password', e.target.value)}
                onFocus={handlePasswordFocus}
                placeholder={originalPassword ? '••••••••' : ''}
                className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white outline-none transition-all"
              />
              {originalPassword && (
                <p className="text-xs text-slate-400 mt-1">Focus the field to change the saved password.</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-bold text-slate-700 mb-1.5">
                From Email <span className="text-red-500">*</span>
              </label>
              <input
                type="email"
                value={form.smtp_from}
                onChange={(e) => handleChange('smtp_from', e.target.value)}
                placeholder="noreply@example.com"
                className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white outline-none transition-all"
              />
            </div>

            <div>
              <label className="block text-sm font-bold text-slate-700 mb-1.5">From Name</label>
              <input
                type="text"
                value={form.from_name}
                onChange={(e) => handleChange('from_name', e.target.value)}
                placeholder="ARIA Recruiting"
                className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white outline-none transition-all"
              />
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-bold text-slate-700 mb-1.5">Reply-To Email</label>
              <input
                type="email"
                value={form.reply_to}
                onChange={(e) => handleChange('reply_to', e.target.value)}
                placeholder="recruiting@example.com"
                className="w-full px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white outline-none transition-all"
              />
            </div>
          </div>

          {/* Actions */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 mt-8 pt-6 border-t border-brand-50">
            <button
              onClick={handleSave}
              disabled={saving || !form.smtp_host || !form.smtp_from}
              className="flex items-center gap-2 px-5 py-2.5 btn-brand text-white text-sm font-bold rounded-xl shadow-brand-sm disabled:opacity-60 transition-all"
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              {saving ? 'Saving...' : 'Save Configuration'}
            </button>

            <button
              onClick={handleTest}
              disabled={testing || !isConfigured}
              className="flex items-center gap-2 px-5 py-2.5 ring-1 ring-brand-200 text-sm font-semibold text-brand-700 rounded-xl hover:bg-brand-50 transition-colors disabled:opacity-60"
            >
              {testing ? <Loader2 className="w-4 h-4 animate-spin" /> : <TestTube className="w-4 h-4" />}
              {testing ? 'Testing...' : 'Test Connection'}
            </button>

            <button
              onClick={() => setShowDeleteConfirm(true)}
              disabled={deleting || !isConfigured}
              className="flex items-center gap-2 px-5 py-2.5 bg-red-600 text-white text-sm font-bold rounded-xl hover:bg-red-700 transition-colors disabled:opacity-60 sm:ml-auto"
            >
              {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
              {deleting ? 'Removing...' : 'Remove Configuration'}
            </button>
          </div>

          {/* Test Result */}
          {testResult && (
            <div className={`mt-4 p-3 rounded-xl ring-1 flex items-start gap-2.5 ${
              testResult.success
                ? 'bg-green-50 ring-green-200 text-green-700'
                : 'bg-red-50 ring-red-200 text-red-700'
            }`}>
              {testResult.success ? <Check className="w-4 h-4 mt-0.5 shrink-0" /> : <X className="w-4 h-4 mt-0.5 shrink-0" />}
              <p className="text-sm font-medium">{testResult.message}</p>
            </div>
          )}
        </div>
      </div>

      {/* Delete Confirmation */}
      {showDeleteConfirm && (
        <ConfirmDialog
          title="Remove Email Configuration?"
          message="This will delete your custom SMTP settings and revert to the default ARIA sender. This action cannot be undone."
          onConfirm={handleDelete}
          onCancel={() => setShowDeleteConfirm(false)}
          confirmText="Remove"
          destructive
        />
      )}

      {/* Toast */}
      {toast && <Toast message={toast.message} type={toast.type} onDone={() => setToast(null)} />}
    </div>
  )
}
