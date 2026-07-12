import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { HeartPulse, AlertTriangle, TrendingDown, MessageSquare, Loader2 } from 'lucide-react'
import { getCrmHealthOverview, getAdminTenants } from '../../lib/api'

function RiskBadge({ risk }) {
  const map = {
    low: 'bg-green-50 text-green-700 ring-green-200',
    medium: 'bg-amber-50 text-amber-700 ring-amber-200',
    high: 'bg-red-50 text-red-700 ring-red-200',
  }
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-bold ring-1 ${map[risk] || 'bg-slate-100 text-slate-600'}`}>
      {risk || '—'}
    </span>
  )
}

function HealthBar({ score }) {
  const color = score >= 70 ? 'bg-green-500' : score >= 40 ? 'bg-amber-500' : 'bg-red-500'
  return (
    <div className="flex items-center gap-2 min-w-[120px]">
      <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${score ?? 0}%` }} />
      </div>
      <span className="text-xs font-mono text-slate-600 w-8">{score ?? '—'}</span>
    </div>
  )
}

export default function CrmPage() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const overview = await getCrmHealthOverview()
      setData(overview)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load CRM data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <HeartPulse className="w-7 h-7 text-teal-600" /> Customer Success CRM
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Health scores, churn risk, and account intelligence across all tenants.
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">{error}</div>
      )}

      {loading ? (
        <div className="flex justify-center py-16"><Loader2 className="w-8 h-8 animate-spin text-teal-600" /></div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <p className="text-xs font-medium text-gray-500 uppercase">Total Accounts</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{data?.tenants?.length ?? 0}</p>
            </div>
            <div className="bg-white rounded-xl border border-red-200 p-5">
              <p className="text-xs font-medium text-red-600 uppercase flex items-center gap-1">
                <AlertTriangle className="w-3.5 h-3.5" /> At Risk
              </p>
              <p className="text-2xl font-bold text-red-700 mt-1">{data?.at_risk_count ?? 0}</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <p className="text-xs font-medium text-gray-500 uppercase flex items-center gap-1">
                <TrendingDown className="w-3.5 h-3.5" /> Trialing
              </p>
              <p className="text-2xl font-bold text-amber-600 mt-1">
                {data?.tenants?.filter((t) => t.subscription_status === 'trialing').length ?? 0}
              </p>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-100">
              <h2 className="font-semibold text-gray-800">Account Health</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-left text-xs text-gray-500 uppercase">
                  <tr>
                    <th className="px-5 py-3">Tenant</th>
                    <th className="px-5 py-3">Health</th>
                    <th className="px-5 py-3">Churn Risk</th>
                    <th className="px-5 py-3">Status</th>
                    <th className="px-5 py-3">Trial Ends</th>
                    <th className="px-5 py-3"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {(data?.tenants || []).map((t) => (
                    <tr key={t.tenant_id} className="hover:bg-gray-50">
                      <td className="px-5 py-3">
                        <p className="font-medium text-gray-900">{t.name}</p>
                        <p className="text-xs text-gray-400 font-mono">{t.slug}</p>
                      </td>
                      <td className="px-5 py-3"><HealthBar score={t.health_score} /></td>
                      <td className="px-5 py-3"><RiskBadge risk={t.churn_risk} /></td>
                      <td className="px-5 py-3 capitalize text-gray-600">{t.subscription_status}</td>
                      <td className="px-5 py-3 text-gray-500 text-xs">
                        {t.trial_ends_at ? new Date(t.trial_ends_at).toLocaleDateString() : '—'}
                      </td>
                      <td className="px-5 py-3 text-right">
                        <Link
                          to={`/admin/tenants/${t.tenant_id}`}
                          className="text-teal-600 hover:text-teal-700 font-medium text-xs"
                        >
                          View →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {data?.at_risk?.length > 0 && (
            <div className="bg-red-50 rounded-xl border border-red-200 p-5">
              <h3 className="font-semibold text-red-800 flex items-center gap-2 mb-3">
                <MessageSquare className="w-4 h-4" /> High churn risk — needs outreach
              </h3>
              <ul className="space-y-2">
                {data.at_risk.map((t) => (
                  <li key={t.tenant_id} className="flex items-center justify-between text-sm">
                    <span className="text-red-900 font-medium">{t.name}</span>
                    <Link to={`/admin/tenants/${t.tenant_id}`} className="text-red-700 underline text-xs">
                      Review account
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </div>
  )
}
