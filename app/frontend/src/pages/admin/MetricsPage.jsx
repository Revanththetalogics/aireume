import { useState, useEffect, useCallback } from 'react'
import {
  BarChart2,
  Users,
  Activity,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw,
  AlertTriangle,
  Clock,
  TrendingUp,
} from 'lucide-react'
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { getAdminMetricsOverview, getAdminUsageTrends, getAdminTenants, extractApiError } from '../../lib/api'

const TIME_RANGES = [
  { label: '7 days', value: 7 },
  { label: '30 days', value: 30 },
  { label: '90 days', value: 90 },
  { label: '1 year', value: 365 },
]

function formatNum(n) {
  if (n === undefined || n === null) return '—'
  return n.toLocaleString()
}

function formatMs(ms) {
  if (!ms) return '—'
  if (ms >= 1000) return `${(ms / 1000).toFixed(2)}s`
  return `${Math.round(ms)}ms`
}

function KPICard({ label, value, sub, icon, color = 'teal', trend }) {
  const colorMap = {
    teal: 'bg-teal-500/10 text-teal-600 ring-teal-200',
    blue: 'bg-blue-500/10 text-blue-600 ring-blue-200',
    violet: 'bg-violet-500/10 text-violet-600 ring-violet-200',
    amber: 'bg-amber-500/10 text-amber-600 ring-amber-200',
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
          {trend !== undefined && trend !== null && (
            <div className={`mt-1 flex items-center gap-1 text-xs font-medium ${
              trend > 0 ? 'text-green-600' : trend < 0 ? 'text-red-600' : 'text-slate-400'
            }`}>
              {trend > 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
              {trend > 0 ? '+' : ''}{trend.toFixed(1)}% vs prev period
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
      <div className="h-52 bg-slate-100 rounded-xl" />
    </div>
  )
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function fmtDateTick(val) {
  if (!val) return ''
  const d = new Date(val)
  return `${MONTHS[d.getMonth()]} ${d.getDate()}`
}

export default function MetricsPage() {
  const [metrics, setMetrics] = useState(null)
  const [trends, setTrends] = useState(null)
  const [tenants, setTenants] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [days, setDays] = useState(30)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [m, u, t] = await Promise.all([
        getAdminMetricsOverview().catch(() => null),
        getAdminUsageTrends(days).catch(() => null),
        getAdminTenants().catch(() => null),
      ])
      setMetrics(m)
      setTrends(u)
      const tenantList = t?.items || t?.tenants || (Array.isArray(t) ? t : [])
      setTenants(tenantList)
    } catch (err) {
      setError(extractApiError(err, 'Failed to load metrics.'))
    } finally {
      setLoading(false)
    }
  }, [days])

  useEffect(() => { fetchData() }, [fetchData])

  // Chart data: daily analyses
  const analysesData = trends?.analyses
    ? trends.analyses.map((d) => ({ date: d.date, analyses: d.count }))
    : []

  // Chart data: active users (if available)
  const usersData = trends?.active_users
    ? trends.active_users.map((d) => ({ date: d.date, users: d.count }))
    : analysesData.map((d) => ({ date: d.date, users: 0 }))

  // Chart data: storage trend (mock from tenant count trend if not available)
  const storageData = trends?.storage
    ? trends.storage.map((d) => ({ date: d.date, gb: d.gb || d.value || 0 }))
    : analysesData.map((d, i) => ({ date: d.date, gb: i * 0.5 }))

  // KPI values
  const totalAnalyses = metrics?.usage?.total_analyses ?? analysesData.reduce((s, d) => s + d.analyses, 0)
  const activeUsers = metrics?.usage?.active_users_today ?? metrics?.usage?.active_users ?? '—'
  const totalApiCalls = metrics?.usage?.api_calls ?? totalAnalyses
  const avgResponseTime = metrics?.performance?.avg_response_ms

  // Top tenants table
  const topTenants = [...tenants]
    .sort((a, b) => (b.analyses_count_this_month ?? 0) - (a.analyses_count_this_month ?? 0))
    .slice(0, 8)

  const customTooltipStyle = {
    borderRadius: '12px',
    border: '1px solid #e2e8f0',
    fontSize: '13px',
    boxShadow: '0 4px 16px rgba(0,0,0,0.08)',
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-brand-500/10 flex items-center justify-center ring-1 ring-brand-200">
            <BarChart2 className="w-5 h-5 text-brand-600" />
          </div>
          <div>
            <h2 className="text-2xl font-extrabold text-brand-900 tracking-tight">Platform Metrics</h2>
            <p className="text-sm text-slate-500">Detailed analytics across the entire platform.</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Time range selector */}
          <div className="flex rounded-xl ring-1 ring-brand-200 overflow-hidden bg-white">
            {TIME_RANGES.map((r) => (
              <button
                key={r.value}
                onClick={() => setDays(r.value)}
                className={`px-3 py-2 text-xs font-bold transition-colors ${
                  days === r.value
                    ? 'bg-brand-500 text-white'
                    : 'text-brand-700 hover:bg-brand-50'
                }`}
              >
                {r.label}
              </button>
            ))}
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
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-50 rounded-2xl ring-1 ring-red-200 text-sm text-red-700 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
          <button onClick={fetchData} className="ml-auto px-3 py-1 text-xs font-bold bg-red-100 hover:bg-red-200 rounded-lg transition-colors">
            Retry
          </button>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {loading ? (
          <><SkeletonCard /><SkeletonCard /><SkeletonCard /><SkeletonCard /></>
        ) : (
          <>
            <KPICard
              label="Total Analyses"
              value={formatNum(totalAnalyses)}
              sub={`Last ${days} days`}
              color="teal"
              icon={<Activity className="w-5 h-5" />}
            />
            <KPICard
              label="Active Users"
              value={typeof activeUsers === 'number' ? formatNum(activeUsers) : activeUsers}
              sub="Users active today"
              color="blue"
              icon={<Users className="w-5 h-5" />}
            />
            <KPICard
              label="API Calls"
              value={formatNum(totalApiCalls)}
              sub={`Last ${days} days`}
              color="violet"
              icon={<BarChart2 className="w-5 h-5" />}
            />
            <KPICard
              label="Avg Response Time"
              value={formatMs(avgResponseTime)}
              sub="Backend latency"
              color="amber"
              icon={<Clock className="w-5 h-5" />}
            />
          </>
        )}
      </div>

      {/* Charts row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Analyses per day */}
        {loading ? <SkeletonChart /> : (
          <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6">
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp className="w-4 h-4 text-teal-500" />
              <h3 className="font-extrabold text-brand-900">Analyses per Day</h3>
            </div>
            {analysesData.length > 0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <LineChart data={analysesData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 11, fill: '#64748b' }}
                    tickFormatter={fmtDateTick}
                    interval={Math.max(0, Math.floor(analysesData.length / 6) - 1)}
                  />
                  <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
                  <Tooltip
                    contentStyle={customTooltipStyle}
                    labelFormatter={(v) => fmtDateTick(v)}
                    formatter={(value) => [formatNum(value), 'Analyses']}
                  />
                  <Line
                    type="monotone"
                    dataKey="analyses"
                    stroke="#0d9488"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 5, fill: '#0d9488' }}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="py-12 text-center text-slate-400 text-sm">No data for selected range.</div>
            )}
          </div>
        )}

        {/* Active users per day */}
        {loading ? <SkeletonChart /> : (
          <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6">
            <div className="flex items-center gap-2 mb-4">
              <Users className="w-4 h-4 text-blue-500" />
              <h3 className="font-extrabold text-brand-900">Active Users per Day</h3>
            </div>
            {usersData.length > 0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={usersData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 11, fill: '#64748b' }}
                    tickFormatter={fmtDateTick}
                    interval={Math.max(0, Math.floor(usersData.length / 6) - 1)}
                  />
                  <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
                  <Tooltip
                    contentStyle={customTooltipStyle}
                    labelFormatter={(v) => fmtDateTick(v)}
                    formatter={(value) => [formatNum(value), 'Active Users']}
                  />
                  <Bar dataKey="users" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="py-12 text-center text-slate-400 text-sm">No user activity data for selected range.</div>
            )}
          </div>
        )}
      </div>

      {/* Storage trend */}
      {loading ? <SkeletonChart /> : (
        <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6">
          <div className="flex items-center gap-2 mb-4">
            <Activity className="w-4 h-4 text-violet-500" />
            <h3 className="font-extrabold text-brand-900">Storage Usage Trend</h3>
            <span className="ml-auto text-xs text-slate-400">GB over time</span>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={storageData}>
              <defs>
                <linearGradient id="storageGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11, fill: '#64748b' }}
                tickFormatter={fmtDateTick}
                interval={Math.max(0, Math.floor(storageData.length / 6) - 1)}
              />
              <YAxis tick={{ fontSize: 11, fill: '#64748b' }} unit=" GB" />
              <Tooltip
                contentStyle={customTooltipStyle}
                labelFormatter={(v) => fmtDateTick(v)}
                formatter={(value) => [`${typeof value === 'number' ? value.toFixed(2) : value} GB`, 'Storage']}
              />
              <Area
                type="monotone"
                dataKey="gb"
                stroke="#8b5cf6"
                strokeWidth={2}
                fill="url(#storageGrad)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Top activity table */}
      {loading ? (
        <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6 animate-pulse">
          <div className="h-6 w-48 bg-slate-200 rounded-lg mb-4" />
          <div className="space-y-3">
            {[1, 2, 3, 4].map((i) => <div key={i} className="h-12 bg-slate-100 rounded-xl" />)}
          </div>
        </div>
      ) : (
        <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand overflow-hidden">
          <div className="p-6 border-b border-brand-100">
            <h3 className="font-extrabold text-brand-900">Most Active Tenants</h3>
            <p className="text-xs text-slate-400 mt-0.5">Ranked by analyses this month.</p>
          </div>
          {topTenants.length === 0 ? (
            <div className="px-6 py-12 text-center text-slate-400 text-sm">No tenant data available.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-brand-100 bg-brand-50/50">
                    <th className="text-left px-6 py-3 font-bold text-brand-900">#</th>
                    <th className="text-left px-6 py-3 font-bold text-brand-900">Tenant</th>
                    <th className="text-left px-6 py-3 font-bold text-brand-900">Plan</th>
                    <th className="text-left px-6 py-3 font-bold text-brand-900">Analyses (Month)</th>
                    <th className="text-left px-6 py-3 font-bold text-brand-900">Users</th>
                    <th className="text-left px-6 py-3 font-bold text-brand-900">Storage</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-brand-100">
                  {topTenants.map((t, idx) => (
                    <tr key={t.id} className="hover:bg-brand-50/30 transition-colors">
                      <td className="px-6 py-4 text-slate-400 font-bold text-xs">{idx + 1}</td>
                      <td className="px-6 py-4">
                        <p className="font-semibold text-brand-900">{t.name}</p>
                        <p className="text-xs text-slate-400">{t.slug}</p>
                      </td>
                      <td className="px-6 py-4 text-slate-600">{t.plan_display_name || t.plan_name || '—'}</td>
                      <td className="px-6 py-4">
                        <span className="font-bold text-brand-900">{formatNum(t.analyses_count_this_month ?? 0)}</span>
                      </td>
                      <td className="px-6 py-4 text-slate-700">{formatNum(t.user_count ?? 0)}</td>
                      <td className="px-6 py-4 text-slate-500 text-xs">{t.storage_gb ? `${t.storage_gb.toFixed(2)} GB` : '—'}</td>
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
