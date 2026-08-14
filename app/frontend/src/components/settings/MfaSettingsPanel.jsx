import { useState } from 'react'
import { Shield } from 'lucide-react'
import { setupMfa, enableMfa, disableMfa } from '../../lib/api'
import { showError, showSuccess } from '../../lib/toast'
import { useAuth } from '../../contexts/AuthContext'
import { Toggle } from '../ui'

export default function MfaSettingsPanel() {
  const { user, loadUser } = useAuth()
  const [secret, setSecret] = useState('')
  const [otpauth, setOtpauth] = useState('')
  const [code, setCode] = useState('')
  const [busy, setBusy] = useState(false)

  const enrolled = Boolean(user?.mfa_enabled)

  const startSetup = async () => {
    setBusy(true)
    try {
      const data = await setupMfa()
      setSecret(data.secret)
      setOtpauth(data.otpauth_url)
    } catch (err) {
      showError(err.response?.data?.detail || 'Could not start MFA setup')
    } finally {
      setBusy(false)
    }
  }

  const confirmEnable = async () => {
    setBusy(true)
    try {
      await enableMfa(code)
      showSuccess('Authenticator app enabled')
      setCode('')
      setSecret('')
      await loadUser?.()
    } catch (err) {
      showError(err.response?.data?.detail || 'Invalid code')
    } finally {
      setBusy(false)
    }
  }

  const confirmDisable = async () => {
    setBusy(true)
    try {
      await disableMfa(code)
      showSuccess('MFA disabled')
      setCode('')
      await loadUser?.()
    } catch (err) {
      showError(err.response?.data?.detail || 'Invalid code')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-brand-600" />
          <p className="text-sm font-semibold text-slate-800 dark:text-dark-text-primary">Authenticator app (TOTP)</p>
        </div>
        <Toggle
          checked={enrolled}
          onChange={() => {
            if (enrolled) return
            startSetup()
          }}
          label={enrolled ? 'Enabled' : 'Off'}
          disabled={busy || enrolled}
        />
      </div>
      {user?.mfa_required && !enrolled && (
        <p role="alert" className="text-sm text-amber-700">
          MFA is required for admin and platform roles. Enroll an authenticator app to continue.
        </p>
      )}
      {secret && (
        <div className="p-3 rounded-xl bg-brand-50 ring-1 ring-brand-100 text-sm space-y-2">
          <p className="font-medium text-brand-900">Scan this secret in your authenticator app</p>
          <code className="block break-all text-xs">{secret}</code>
          {otpauth && <p className="text-xs text-slate-500 break-all">{otpauth}</p>}
        </div>
      )}
      <div>
        <label htmlFor="mfa-code" className="block text-sm font-medium text-slate-700 mb-1.5">
          Authenticator code
        </label>
        <input
          id="mfa-code"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          inputMode="numeric"
          autoComplete="one-time-code"
          className="w-full px-4 py-2.5 rounded-xl text-sm ring-1 ring-slate-200 dark:bg-dark-card dark:text-dark-text-primary"
          placeholder="123456"
        />
      </div>
      <div className="flex gap-2">
        {!enrolled ? (
          <button
            type="button"
            disabled={busy || !code}
            onClick={confirmEnable}
            className="px-4 py-2.5 bg-brand-600 text-white text-sm font-semibold rounded-xl disabled:opacity-50"
          >
            Verify and enable
          </button>
        ) : (
          <button
            type="button"
            disabled={busy || !code || user?.mfa_required}
            onClick={confirmDisable}
            className="px-4 py-2.5 bg-red-100 text-red-700 text-sm font-semibold rounded-xl disabled:opacity-50"
          >
            Disable MFA
          </button>
        )}
      </div>
    </div>
  )
}
