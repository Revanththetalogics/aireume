import { useState, useEffect, useCallback } from 'react'
import {
  DollarSign,
  Users,
  TrendingUp,
  AlertTriangle,
  Loader2,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw,
} from 'lucide-react'
import {
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  XAxis,
  YAxis,
  CartesianGrid,
} from 'recharts'
import { getAdminMetricsOverview, getAdminTenants, getAdminUsageTrends } from '../../lib/api'

const COLORS = ['#0d9488', '#0f766e', '#14b8a6', '#2dd4bf', '#5eead4', '#99f6e4', '#f59e0b', '#ef4444', '#8b5cf6', '#3b82f6']

function formatCurrency(cents) {
  if (cents === undefined || cents === null) return '—'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(cents / 100)
}

function formatPercent(val) {
  if (val === undefined || val === null) return '—'
  return `${val.toFixed(1)}%`
}

function KPICard({ label, value, sub, icon, color = 'teal', trend, trendLabel }) {
  const colorMap = {
    teal: 'bg-teal-500/10 text-teal-600 ring-teal-200',
    blue: 'bg-blue-500/10 text-blue-600 ring-blue-200',
    violet: 'bg-violet-500/10 text-violet-600 ring-violet-200',
    amber: 'bg-amber-500/10 text-amber-600 ring-amber-200',
    red: 'bg-red-500/10 text-red-600 ring-red-200',
  }
  return (
    <div className="bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 shadow-brand p-5">
      <div className="flex items-start gap-4">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ring-1 ${colorMap[color]}`}>
          {icon}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">{label}</p>
          <p className="mt-0.5 text-2xl font-bold text-brand-900">{value}</p>
          {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
          {trend && (
            <div className={`mt-1 flex items-center gap-1 text-xs font-medium ${
              trend > 0 ? 'text-green-600' : trend < 0 ? 'text-red-600' : 'text-slate-400'
            }`}>
              {trend > 0 ? <ArrowUpRight className="w-3 h-3" /> : trend < 0 ? <ArrowDownRight className="w-3 h-3" /> : null}
              {trendLabel || `${trend > 0 ? '+' : ''}${trend.toFixed(1)}%`}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function SkeletonCard() {
  return (
    <div className="bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 p-5 animate-pulse">
      <div className="flex items-start gap-4">
        <div className="w-10 h-10 rounded-xl bg-slate-200" />
        <div className="flex-1 space-y-2">
          <div className="h-3 w-20 bg-slate-200 rounded" />
          <div className="h-6 w-32 bg-slate-200 rounded" />
          <div className="h-3 w-16 bg-slate-100 rounded" />
        </div>
      </div>
    </div>
  )
}

function SkeletonChart() {
  return (
    <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6 animate-pulse">
      <div className="h-6 w-40 bg-slate-200 rounded-lg mb-4" />
      <div className="h-48 bg-slate-100 rounded-xl" />
    </div>
  )
}

export default function RevenuePage() {
  const [metrics, setMetrics] = useState(null)
  const [tenants, setTenants] = useState([])
  const [trends, setTrends] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [m, t, u] = await Promise.all([
        getAdminMetricsOverview().catch(() => null),
        getAdminTenants().catch(() => null),
        getAdminUsageTrends(365).catch(() => null),
      ])
      setMetrics(m)
      const tenantItems = t?.items || t?.tenants || t || []
      setTenants(tenantItems)
      setTrends(u)
    } catch (err) {
      console.error('Failed to load revenue data:', err)
      setError(err.response?.data?.detail || 'Failed to load revenue data.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  // Computed revenue data
  const activeTenants = tenants.filter((t) => t.subscription_status === 'active')
  const mrr = metrics?.revenue?.mrr_cents ?? 0
  const arr = metrics?.revenue?.arr_estimate_cents ?? mrr * 12
  const activeSubscribers = metrics?.tenants?.active ?? activeTenants.length

  // Churn calculation
  const cancelled = metrics?.tenants?.cancelled ?? 0
  const totalTenants = metrics?.tenants?.total ?? tenants.length
  const churnRate = totalTenants > 0 ? (cancelled / totalTenants) * 100 : 0

  // Plan distribution from metrics
  const planDistribution = metrics?.plans || {}
  const planPieData = Object.entries(planDistribution)
    .filter(([, count]) => count > 0)
    .map(([name, count], i) => ({
      name,
      value: count,
      color: COLORS[i % COLORS.length],
    }))

  // Revenue trend (from usage trends, compute monthly buckets)
  const revenueChartData = (() => {
    if (!trends?.analyses) return []
    // Group analyses by month for the trend chart
    const monthlyMap = {}
    trends.analyses.forEach((entry) => {
      const monthKey = entry.date.substring(0, 7) // YYYY-MM
      if (!monthlyMap[monthKey]) monthlyMap[monthKey] = { month: monthKey, analyses: 0 }
      monthlyMap[monthKey].analyses += entry.count
    })
    // Sort and take last 12 months
    const sorted = Object.values(monthlyMap).sort((a, b) => a.month.localeCompare(b.month))
    const last12 = sorted.slice(-12)
    // Map month to readable label
    return last12.map((entry) => ({
      ...entry,
      label: entry.month,
    }))
  })()

  // Top tenants by revenue (we only have plan info, not individual revenue)
  const topTenants = activeTenants
    .slice(0, 10)
    .map((t) => ({
      ...t,
      plan_display_name: t.plan_display_name || t.plan_name || '—',
    }))

  const formatTooltipValue = (value) => {
    if (typeof value === 'number') return value.toLocaleString()
    return value
  }

  // ── Render ──
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-brand-500/10 flex items-center justify-center ring-1 ring-brand-200">
            <TrendingUp className="w-5 h-5 text-brand-600" />
          </div>
          <div>
            <h2 className="text-2xl font-extrabold text-brand-900 tracking-tight">Revenue Dashboard</h2>
            <p className="text-sm text-slate-500">Track MRR, ARR, churn, and subscriber distribution.</p>
          </div>
        </div>
        {!loading && (
          <button
            onClick={fetchData}
            className="flex items-center gap-2 px-4 py-2 ring-1 ring-brand-200 text-sm font-semibold text-brand-700 rounded-xl hover:bg-brand-50 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        )}
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 bg-red-50 rounded-2xl ring-1 ring-red-200 text-sm text-red-700 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          {error}
          <button
            onClick={fetchData}
            className="ml-auto px-3 py-1 text-xs font-bold bg-red-100 hover:bg-red-200 rounded-lg transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {loading ? (
          <>
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </>
        ) : (
          <>
            <KPICard
              label="MRR"
              value={formatCurrency(mrr)}
              sub="Monthly recurring revenue"
              color="teal"
              icon={<DollarSign className="w-5 h-5" />}
            />
            <KPICard
              label="ARR"
              value={formatCurrency(arr)}
              sub="Annual recurring revenue (estimate)"
              color="blue"
              icon={<TrendingUp className="w-5 h-5" />}
            />
            <KPICard
              label="Active Subscribers"
              value={activeSubscribers}
              sub={`${totalTenants} total tenants`}
              color="violet"
              icon={<Users className="w-5 h-5" />}
            />
            <KPICard
              label="Churn Rate"
              value={formatPercent(churnRate)}
              sub={`${cancelled} cancelled tenants`}
              color={churnRate > 5 ? 'red' : 'amber'}
              trend={churnRate > 5 ? -churnRate : undefined}
              trendLabel={churnRate > 5 ? `High churn` : undefined}
              icon={<AlertTriangle className="w-5 h-5" />}
            />
          </>
        )}
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Revenue Trend Chart */}
        {loading ? (
          <SkeletonChart />
        ) : (
          <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6">
            <h3 className="font-extrabold text-brand-900 mb-4">Usage Trend (Last 12 Months)</h3>
            {revenueChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={revenueChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis
                    dataKey="label"
                    tick={{ fontSize: 11, fill: '#64748b' }}
                    tickFormatter={(v) => {
                      const [y, m] = v.split('-')
                      const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                      return months[parseInt(m, 10) - 1] || v
                    }}
                  />
                  <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
                  <Tooltip
                    contentStyle={{ borderRadius: '12px', ring: '1px solid #e2e8f0', fontSize: '13px' }}
                    formatter={(value) => [formatTooltipValue(value), 'Analyses']}
                    labelFormatter={(label) => {
                      const [y, m] = label.split('-')
                      const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                      return `${months[parseInt(m, 10) - 1]} ${y}`
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="analyses"
                    stroke="#0d9488"
                    strokeWidth={2}
                    dot={{ fill: '#0d9488', r: 3 }}
                    activeDot={{ r: 5 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="py-12 text-center text-slate-400 text-sm">
                No usage data available yet.
              </div>
            )}
          </div>
        )}

        {/* Plan Distribution Pie Chart */}
        {loading ? (
          <SkeletonChart />
        ) : (
          <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6">
            <h3 className="font-extrabold text-brand-900 mb-4">Plan Distribution</h3>
            {planPieData.length > 0 ? (
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                  <Pie
                    data={planPieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={2}
                    dataKey="value"
                    nameKey="name"
                    stroke="none"
                  >
                    {planPieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ borderRadius: '12px', ring: '1px solid #e2e8f0', fontSize: '13px' }}
                    formatter={(value, name) => [`${value} tenant(s)`, name]}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="py-12 text-center text-slate-400 text-sm">
                No plan distribution data available.
              </div>
            )}
            {/* Legend */}
            {planPieData.length > 0 && (
              <div className="flex flex-wrap gap-3 mt-4 justify-center">
                {planPieData.map((entry) => (
                  <div key={entry.name} className="flex items-center gap-1.5 text-xs">
                    <span className={`w-3 h-3 rounded-full`} style={{ backgroundColor: entry.color }} />
                    <span className="font-medium text-slate-700">{entry.name}</span>
                    <span className="text-slate-400">({entry.value})</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Top Tenants Table */}
      {loading ? (
        <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6 animate-pulse">
          <div className="h-6 w-40 bg-slate-200 rounded-lg mb-4" />
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-12 bg-slate-100 rounded-xl" />
            ))}
          </div>
        </div>
      ) : (
        <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand overflow-hidden">
          <div className="p-6 border-b border-brand-100">
            <h3 className="font-extrabold text-brand-900">Top Tenants by Plan</h3>
            <p className="text-xs text-slate-400 mt-0.5">Active tenants with their current subscription plan.</p>
          </div>
          {topTenants.length === 0 ? (
            <div className="px-6 py-12 text-center text-slate-400 text-sm">
              No active tenants found.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-brand-100 bg-brand-50/50">
                    <th className="text-left px-6 py-3 font-bold text-brand-900">Name</th>
                    <th className="text-left px-6 py-3 font-bold text-brand-900">Slug</th>
                    <th className="text-left px-6 py-3 font-bold text-brand-900">Plan</th>
                    <th className="text-left px-6 py-3 font-bold text-brand-900">Status</th>
                    <th className="text-left px-6 py-3 font-bold text-brand-900">Users</th>
                    <th className="text-left px-6 py-3 font-bold text-brand-900">Analyses (This Month)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-brand-100">
                  {topTenants.map((t) => (
                    <tr key={t.id} className="hover:bg-brand-50/30 transition-colors">
                      <td className="px-6 py-4 font-semibold text-brand-900">{t.name}</td>
                      <td className="px-6 py-4 text-slate-500 text-xs">{t.slug}</td>
                      <td className="px-6 py-4 text-slate-700">{t.plan_display_name}</td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-bold ${
                          t.subscription_status === 'active'
                            ? 'bg-green-50 text-green-700 ring-1 ring-green-200'
                            : t.subscription_status === 'trialing'
                            ? 'bg-blue-50 text-blue-700 ring-1 ring-blue-200'
                            : 'bg-slate-100 text-slate-600 ring-1 ring-slate-200'
                        }`}>
                          {t.subscription_status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-slate-700">{t.user_count ?? 0}</td>
                      <td className="px-6 py-4 text-slate-700">{t.analyses_count_this_month ?? 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}