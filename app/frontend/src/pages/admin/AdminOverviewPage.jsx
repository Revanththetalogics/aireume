import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getAdminMetricsOverview, getAdminTenants } from '../../lib/api'

function StatCard({ label, value, sub, color = 'teal', icon }) {
  const colors = {
    teal:   'bg-teal-500/10 text-teal-600',
    blue:   'bg-blue-500/10 text-blue-600',
    violet: 'bg-violet-500/10 text-violet-600',
    amber:  'bg-amber-500/10 text-amber-600',
  }
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 flex items-start gap-4 shadow-sm">
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${colors[color]}`}>
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
        <p className="mt-0.5 text-2xl font-bold text-gray-900">
          {value ?? <span className="text-gray-300">—</span>}
        </p>
        {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  )
}

function QuickLink({ to, label, desc }) {
  return (
    <Link
      to={to}
      className="block bg-white rounded-xl border border-gray-200 p-4 hover:border-teal-300 hover:shadow-md transition-all group"
    >
      <p className="font-semibold text-gray-800 group-hover:text-teal-700">{label}</p>
      <p className="text-xs text-gray-400 mt-0.5">{desc}</p>
    </Link>
  )
}

export default function AdminOverviewPage() {
  const [metrics, setMetrics] = useState(null)
  const [tenantCount, setTenantCount] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([
      getAdminMetricsOverview().catch(() => null),
      getAdminTenants({ page: 1, per_page: 1 }).catch(() => null),
    ]).then(([m, t]) => {
      setMetrics(m)
      setTenantCount(t?.total ?? t?.tenants?.length ?? null)
    }).catch(e => setError(e.message)).finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-6">
      {/* Page title */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Platform Overview</h1>
        <p className="mt-1 text-sm text-gray-500">Real-time platform health and key metrics.</p>
      </div>

      {error && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 text-sm rounded-lg px-4 py-3">
          Could not load metrics: {error}
        </div>
      )}

      {/* Stats grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          label="Total Tenants"
          value={loading ? null : tenantCount}
          sub="Registered organizations"
          color="teal"
          icon={
            <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
              <path fillRule="evenodd" d="M4 4a2 2 0 012-2h8a2 2 0 012 2v12a1 1 0 110 2H4a1 1 0 110-2V4zm3 1h2v2H7V5zm2 4H7v2h2V9zm2-4h2v2h-2V5zm2 4h-2v2h2V9z" clipRule="evenodd"/>
            </svg>
          }
        />
        <StatCard
          label="Active Users"
          value={loading ? null : (metrics?.active_users ?? metrics?.total_users ?? '—')}
          sub="Across all tenants"
          color="blue"
          icon={
            <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
              <path d="M9 6a3 3 0 11-6 0 3 3 0 016 0zM17 6a3 3 0 11-6 0 3 3 0 016 0zM12.93 17c.046-.327.07-.66.07-1a6.97 6.97 0 00-1.5-4.33A5 5 0 0119 16v1h-6.07zM6 11a5 5 0 015 5v1H1v-1a5 5 0 015-5z"/>
            </svg>
          }
        />
        <StatCard
          label="Analyses Run"
          value={loading ? null : (metrics?.total_analyses ?? '—')}
          sub="All time"
          color="violet"
          icon={
            <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
              <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z"/>
            </svg>
          }
        />
        <StatCard
          label="MRR"
          value={loading ? null : (metrics?.mrr ? `$${metrics.mrr.toLocaleString()}` : '—')}
          sub="Monthly recurring revenue"
          color="amber"
          icon={
            <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
              <path d="M8.433 7.418c.155-.103.346-.196.567-.267v1.698a2.305 2.305 0 01-.567-.267C8.07 8.34 8 8.114 8 8c0-.114.07-.34.433-.582zM11 12.849v-1.698c.22.071.412.164.567.267.364.243.433.468.433.582 0 .114-.07.34-.433.582a2.305 2.305 0 01-.567.267z"/>
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-13a1 1 0 10-2 0v.092a4.535 4.535 0 00-1.676.662C6.602 6.234 6 7.009 6 8c0 .99.602 1.765 1.324 2.246.48.32 1.054.545 1.676.662v1.941c-.391-.127-.68-.317-.843-.504a1 1 0 10-1.51 1.31c.562.649 1.413 1.076 2.353 1.253V15a1 1 0 102 0v-.092a4.535 4.535 0 001.676-.662C13.398 13.766 14 12.991 14 12c0-.99-.602-1.765-1.324-2.246A4.535 4.535 0 0011 9.092V7.151c.391.127.68.317.843.504a1 1 0 101.511-1.31c-.563-.649-1.413-1.076-2.354-1.253V5z" clipRule="evenodd"/>
            </svg>
          }
        />
      </div>

      {/* Quick links */}
      <div>
        <h2 className="text-sm font-semibold text-gray-700 mb-3">Quick Access</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <QuickLink to="/admin/tenants"   label="Manage Tenants"   desc="View, suspend, or configure tenants" />
          <QuickLink to="/admin/plans"     label="Subscription Plans" desc="Edit plan limits and pricing" />
          <QuickLink to="/admin/features"  label="Feature Flags"    desc="Toggle features per tenant or globally" />
          <QuickLink to="/admin/audit"     label="Audit Log"        desc="Review platform activity" />
          <QuickLink to="/admin/security"  label="Security Events"  desc="Monitor authentication anomalies" />
          <QuickLink to="/admin/billing"   label="Revenue"          desc="Track MRR, churn, and invoices" />
        </div>
      </div>
    </div>
  )
}
