import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Mail, Sparkles, Copy, Check, RefreshCw } from 'lucide-react'
import { resendVerificationEmail } from '../lib/api'

export default function CheckEmailPage() {
  const email = sessionStorage.getItem('aria_pending_verify_email') || ''
  const workspaceSlug = sessionStorage.getItem('aria_workspace_slug') || ''
  const [resending, setResending] = useState(false)
  const [resent, setResent] = useState(false)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState('')

  const handleResend = async () => {
    if (!email) return
    setResending(true)
    setError('')
    try {
      await resendVerificationEmail(email)
      setResent(true)
      setTimeout(() => setResent(false), 5000)
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not resend email. Try again later.')
    } finally {
      setResending(false)
    }
  }

  const handleCopySlug = async () => {
    if (!workspaceSlug) return
    try {
      await navigator.clipboard.writeText(workspaceSlug)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // ignore
    }
  }

  const loginHref = workspaceSlug ? `/login?workspace=${encodeURIComponent(workspaceSlug)}` : '/login'

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center p-4">
      <div className="w-full max-w-md text-center card-animate">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-brand-600 to-brand-500 shadow-brand-lg mb-4">
          <Sparkles className="w-7 h-7 text-white" />
        </div>
        <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand-xl p-8">
          <Mail className="w-12 h-12 text-brand-600 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-brand-900 mb-2">Check your inbox</h1>
          <p className="text-sm text-slate-600 mb-4">
            We sent a verification link to <strong>{email || 'your email'}</strong>.
            Click the link to activate your workspace.
          </p>

          {workspaceSlug && (
            <div className="mb-5 p-4 rounded-xl bg-brand-50 ring-1 ring-brand-100 text-left">
              <p className="text-xs font-semibold text-brand-800 uppercase tracking-wide mb-1">Your workspace slug</p>
              <p className="text-sm text-slate-600 mb-2">Save this — you will need it to sign in.</p>
              <div className="flex items-center gap-2">
                <code className="flex-1 px-3 py-2 rounded-lg bg-white font-mono text-sm text-brand-900 ring-1 ring-brand-200">
                  {workspaceSlug}
                </code>
                <button
                  type="button"
                  onClick={handleCopySlug}
                  className="p-2 rounded-lg text-brand-600 hover:bg-brand-100 transition-colors"
                  aria-label="Copy workspace slug"
                >
                  {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
            </div>
          )}

          {error && (
            <p className="text-sm text-red-600 mb-3">{error}</p>
          )}

          <button
            type="button"
            onClick={handleResend}
            disabled={resending || !email}
            className="inline-flex items-center gap-2 text-sm font-semibold text-brand-600 hover:text-brand-700 disabled:opacity-50 mb-4"
          >
            <RefreshCw className={`w-4 h-4 ${resending ? 'animate-spin' : ''}`} />
            {resent ? 'Verification email sent!' : 'Resend verification email'}
          </button>

          <Link to={loginHref} className="block text-sm font-semibold text-brand-600 hover:text-brand-700">
            Already verified? Sign in
          </Link>
        </div>
      </div>
    </div>
  )
}
