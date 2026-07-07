import { Link } from 'react-router-dom'
import { Mail, Sparkles } from 'lucide-react'

export default function CheckEmailPage() {
  const email = sessionStorage.getItem('aria_pending_verify_email') || 'your email'

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center p-4">
      <div className="w-full max-w-md text-center card-animate">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-brand-600 to-brand-500 shadow-brand-lg mb-4">
          <Sparkles className="w-7 h-7 text-white" />
        </div>
        <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand-xl p-8">
          <Mail className="w-12 h-12 text-brand-600 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-brand-900 mb-2">Check your inbox</h1>
          <p className="text-sm text-slate-600 mb-6">
            We sent a verification link to <strong>{email}</strong>. Click the link to activate your workspace.
          </p>
          <Link to="/login" className="text-sm font-semibold text-brand-600 hover:text-brand-700">
            Already verified? Sign in
          </Link>
        </div>
      </div>
    </div>
  )
}
