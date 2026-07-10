import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { AlertTriangle, Users } from 'lucide-react'
import { getPublicHandoff } from '../lib/api'
import HandoffPackage from '../components/HandoffPackage'

/** Public HM handoff page — no login required (magic link). */
export default function PublicHandoffPage() {
  const { token } = useParams()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!token) return
    setLoading(true)
    getPublicHandoff(token)
      .then(setData)
      .catch((err) => {
        const msg = err.response?.data?.detail || 'This link is invalid or has expired.'
        setError(typeof msg === 'string' ? msg : 'This link is invalid or has expired.')
      })
      .finally(() => setLoading(false))
  }, [token])

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-brand-600 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
        <div className="max-w-md w-full text-center bg-white rounded-2xl ring-1 ring-red-100 p-8 shadow-sm">
          <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-4" />
          <h1 className="text-lg font-bold text-slate-800 mb-2">Link unavailable</h1>
          <p className="text-sm text-slate-500">{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center gap-2 text-sm text-slate-500">
          <Users className="w-4 h-4" />
          <span>Hiring Manager Handoff</span>
          {data?.share_link?.label && (
            <span className="text-slate-400">· {data.share_link.label}</span>
          )}
        </div>
      </header>
      <HandoffPackage initialData={data} publicMode />
    </div>
  )
}
