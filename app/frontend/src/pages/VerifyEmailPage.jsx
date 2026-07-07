import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Sparkles, CheckCircle2, XCircle, Loader2 } from 'lucide-react'
import { verifyEmail } from '../lib/api'

export default function VerifyEmailPage() {
  const { token } = useParams()
  const [status, setStatus] = useState('loading')
  const [message, setMessage] = useState('')

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
      })
      .catch((err) => {
        setStatus('error')
        setMessage(err.response?.data?.detail || 'Verification failed. The link may have expired.')
      })
  }, [token])

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
              <Link
                to="/login"
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
