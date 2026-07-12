import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Sparkles, CheckCircle2, XCircle, Loader2, Copy, Check } from 'lucide-react'
import { verifyEmail } from '../lib/api'

export default function VerifyEmailPage() {
  const { token } = useParams()
  const [status, setStatus] = useState('loading')
  const [message, setMessage] = useState('')
  const [workspaceSlug, setWorkspaceSlug] = useState('')
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!token) {
      setStatus('error')
      setMessage('Invalid verification link.')
      return
    }
    verifyEmail(token)
      .then((data) => {
        setStatus('success')
        setMessage(data.message || 'Your email has been verified. You can now sign in.')
        if (data.tenant?.slug) {
          setWorkspaceSlug(data.tenant.slug)
          sessionStorage.setItem('aria_workspace_slug', data.tenant.slug)
        }
      })
      .catch((err) => {
        setStatus('error')
        setMessage(err.response?.data?.detail || 'Verification failed. The link may have expired.')
      })
  }, [token])

  const loginHref = workspaceSlug
    ? `/login?workspace=${encodeURIComponent(workspaceSlug)}`
    : '/login'

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

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center p-4">
      <div className="w-full max-w-md text-center card-animate">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-brand-600 to-brand-500 shadow-brand-lg mb-4">
          <Sparkles className="w-7 h-7 text-white" />
        </div>
        <h1 className="text-2xl font-extrabold text-brand-900 mb-6">
          <span className="text-gradient">Email Verification</span>
        </h1>

        <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand-xl p-8">
          {status === 'loading' && (
            <div className="flex flex-col items-center gap-3 text-brand-700">
              <Loader2 className="w-8 h-8 animate-spin" />
              <p className="text-sm font-medium">Verifying your email…</p>
            </div>
          )}
          {status === 'success' && (
            <div className="flex flex-col items-center gap-3">
              <CheckCircle2 className="w-12 h-12 text-emerald-500" />
              <p className="text-sm text-slate-600">{message}</p>
              {workspaceSlug && (
                <div className="w-full mt-2 p-4 rounded-xl bg-brand-50 ring-1 ring-brand-100 text-left">
                  <p className="text-xs font-semibold text-brand-800 uppercase tracking-wide mb-1">Workspace slug</p>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 px-3 py-2 rounded-lg bg-white font-mono text-sm text-brand-900 ring-1 ring-brand-200">
                      {workspaceSlug}
                    </code>
                    <button
                      type="button"
                      onClick={handleCopySlug}
                      className="p-2 rounded-lg text-brand-600 hover:bg-brand-100"
                      aria-label="Copy workspace slug"
                    >
                      {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
              )}
              <Link
                to={loginHref}
                className="mt-4 inline-flex px-6 py-2.5 btn-brand text-white font-bold rounded-xl shadow-brand-sm"
              >
                Sign in to ARIA
              </Link>
            </div>
          )}
          {status === 'error' && (
            <div className="flex flex-col items-center gap-3">
              <XCircle className="w-12 h-12 text-red-500" />
              <p className="text-sm text-slate-600">{message}</p>
              <Link to="/login" className="mt-4 text-sm font-semibold text-brand-600 hover:text-brand-700">
                Back to login
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
