import { useState, useEffect, useCallback } from 'react'
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, AreaChart, Area,
} from 'recharts'
import { BarChart3, RefreshCw } from 'lucide-react'
import { getScreeningAnalytics } from '../lib/api'

const PERIOD_OPTIONS = [
  { value: 'last_7_days', label: 'Last 7 Days' },
  { value: 'last_30_days', label: 'Last 30 Days' },
  { value: 'last_90_days', label: 'Last 90 Days' },
]

const PIE_COLORS = { Shortlist: '#22c55e', Consider: '#f59e0b', Reject: '#ef4444' }

function scoreColor(score) {
  if (score >= 70) return 'text-green-600'
  if (score >= 40) return 'text-amber-600'
  return 'text-red-600'
}

function scoreBadgeBg(score) {
  if (score >= 70) return 'bg-green-50 text-green-700 ring-green-200'
  if (score >= 40) return 'bg-amber-50 text-amber-700 ring-amber-200'
  return 'bg-red-50 text-red-700 ring-red-200'
}

// ─── Custom Tooltip ──────────────────────────────────────────────────────────

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white/95 backdrop-blur-sm ring-1 ring-slate-200 rounded-xl shadow-lg px-3 py-2 text-xs">
      <p className="font-bold text-slate-800 mb-1">{label}</p>
      {payload.map(p => (
        <p key={p.name} className="flex items-center gap-1.5 text-slate-600">
          <span className="w-2 h-2 rounded-full inline-block shrink-0" style={{ background: p.color }} />
          <span className="font-semibold">{p.name}:</span> {p.value}
        </p>
      ))}
    </div>
  )
}

// ─── KPI Card ────────────────────────────────────────────────────────────────

function KpiCard({ label, value, suffix = '', colorClass = '' }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border p-6">
      <p className="text-sm font-medium text-slate-500 mb-1">{label}</p>
      <p className={`text-3xl font-extrabold tracking-tight ${colorClass}`}>
        {value}{suffix}
      </p>
    </div>
  )
}

// ─── JD Effectiveness Table ──────────────────────────────────────────────────

function JDEffectivenessTable({ data }) {
  const [sortKey, setSortKey] = useState('avg_score')
  const [sortDir, setSortDir] = useState('desc')

  const sorted = [...(data || [])].sort((a, b) => {
    const av = a[sortKey] ?? 0
    const bv = b[sortKey] ?? 0
    return sortDir === 'desc' ? bv - av : av - bv
  })

  function toggleSort(key) {
    if (sortKey === key) {
      setSortDir(d => (d === 'desc' ? 'asc' : 'desc'))
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  function SortHeader({ label, field }) {
    const active = sortKey === field
    return (
      <th
        className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider cursor-pointer hover:text-brand-700 select-none"
        onClick={() => toggleSort(field)}
      >
        {label}
        {active && <span className="ml-1">{sortDir === 'desc' ? '↓' : '↑'}</span>}
      </th>
    )
  }

  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm border p-6">
        <h3 className="text-lg font-bold text-slate-800 mb-4">JD Effectiveness</h3>
        <p className="text-slate-400 text-sm">No JD data available for this period</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border p-6">
      <h3 className="text-lg font-bold text-slate-800 mb-4">JD Effectiveness</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100">
              <SortHeader label="JD Name" field="jd_name" />
              <SortHeader label="Candidates" field="candidates" />
              <SortHeader label="Avg Score" field="avg_score" />
              <SortHeader label="Shortlist Rate" field="shortlist_rate" />
            </tr>
          </thead>
          <tbody>
            {sorted.map((row, i) => (
              <tr key={i} className="border-b border-slate-50 hover:bg-slate-50/60 transition-colors">
                <td className="px-4 py-3 font-medium text-slate-800">{row.jd_name}</td>
                <td className="px-4 py-3 text-slate-600">{row.candidates}</td>
                <td className="px-4 py-3">
                  <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-bold ring-1 ${scoreBadgeBg(row.avg_score)}`}>
                    {row.avg_score?.toFixed(1) ?? '—'}
                  </span>
                </td>
                <td className="px-4 py-3 text-slate-600">{(row.shortlist_rate * 100).toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ─── Pass-Through Funnel ─────────────────────────────────────────────────────

function PassThroughFunnel({ totalAnalyzed, rates }) {
  const analyzedToShortlisted = rates?.analyzed_to_shortlisted ?? 0
  const shortlistedToHired = rates?.shortlisted_to_hired ?? 0

  const shortlisted = Math.round(totalAnalyzed * analyzedToShortlisted)
  const hired = Math.round(shortlisted * shortlistedToHired)

  const stages = [
    { label: 'Analyzed', count: totalAnalyzed, pct: 1, color: 'bg-violet-500' },
    { label: 'Shortlisted', count: shortlisted, pct: analyzedToShortlisted || 0, color: 'bg-amber-500' },
    { label: 'Hired', count: hired, pct: shortlistedToHired || 0, color: 'bg-green-500' },
  ]

  return (
    <div className="bg-white rounded-xl shadow-sm border p-6">
      <h3 className="text-lg font-bold text-slate-800 mb-5">Pass-Through Funnel</h3>
      <div className="space-y-3">
        {stages.map((stage, i) => (
          <div key={stage.label}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-semibold text-slate-700">{stage.label}</span>
              <span className="text-sm font-bold text-slate-800">{stage.count}</span>
            </div>
            <div className="w-full bg-slate-100 rounded-lg h-8 overflow-hidden">
              <div
                className={`h-8 rounded-lg ${stage.color} flex items-center justify-end pr-3 transition-all duration-700`}
                style={{ width: `${Math.max(stage.pct * 100, 4)}%` }}
              >
                {stage.pct > 0 && (
                  <span className="text-xs font-bold text-white">
                    {i === 0 ? '' : `${(stage.pct * 100).toFixed(0)}%`}
                  </span>
                )}
              </div>
            </div>
            {i < stages.length - 1 && (
              <div className="flex justify-center my-1">
                <span className="text-xs text-slate-400">
                  ↓ {(i === 0 ? analyzedToShortlisted : shortlistedToHired) * 100}% conversion
                </span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Main Analytics Page ─────────────────────────────────────────────────────

export default function AnalyticsPage() {
  const [period, setPeriod] = useState('last_30_days')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await getScreeningAnalytics(period)
      setData(result)
    } catch (err) {
      setError(err.message || 'Failed to load analytics')
    } finally {
      setLoading(false)
    }
  }, [period])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  // Prepare pie chart data from recommendation_distribution
  const pieData = data?.recommendation_distribution
    ? Object.entries(data.recommendation_distribution).map(([name, value]) => ({ name, value }))
    : []

  // Prepare skill gaps data (top 10, sorted by frequency desc)
  const skillGapsData = (data?.top_skill_gaps || [])
    .sort((a, b) => b.frequency - a.frequency)
    .slice(0, 10)

  // Shortlist / hired rates
  const shortlistRate = data?.pass_through_rates?.analyzed_to_shortlisted ?? 0
  const hiredRate = data?.pass_through_rates?.shortlisted_to_hired ?? 0

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* ── Header ──────────────────────────────────────────── */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-brand-50 flex items-center justify-center">
            <BarChart3 className="w-5 h-5 text-brand-600" />
          </div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Screening Analytics</h1>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={period}
            onChange={e => setPeriod(e.target.value)}
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
          >
            {PERIOD_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          <button
            onClick={fetchData}
            disabled={loading}
            className="p-2 rounded-lg border border-slate-200 bg-white text-slate-500 hover:text-brand-600 hover:bg-brand-50 shadow-sm transition-colors disabled:opacity-50"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* ── Loading ─────────────────────────────────────────── */}
      {loading && !data && (
        <div className="flex items-center justify-center py-20">
          <div className="w-8 h-8 border-4 border-brand-600 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {/* ── Error ───────────────────────────────────────────── */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <p className="text-red-700 font-medium mb-2">{error}</p>
          <button
            onClick={fetchData}
            className="text-sm font-semibold text-red-600 hover:text-red-800 underline"
          >
            Retry
          </button>
        </div>
      )}

      {/* ── Data ────────────────────────────────────────────── */}
      {data && !error && (
        <>
          {/* Row 1 — KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <KpiCard
              label="Total Analyzed"
              value={data.total_analyzed ?? 0}
            />
            <KpiCard
              label="Avg Fit Score"
              value={data.avg_fit_score?.toFixed(1) ?? '—'}
              colorClass={scoreColor(data.avg_fit_score ?? 0)}
            />
            <KpiCard
              label="Shortlist Rate"
              value={`${(shortlistRate * 100).toFixed(1)}%`}
              colorClass={shortlistRate >= 0.3 ? 'text-green-600' : shortlistRate >= 0.15 ? 'text-amber-600' : 'text-red-600'}
            />
            <KpiCard
              label="Hired Rate"
              value={`${(hiredRate * 100).toFixed(1)}%`}
              colorClass={hiredRate >= 0.2 ? 'text-green-600' : hiredRate >= 0.05 ? 'text-amber-600' : 'text-red-600'}
            />
          </div>

          {/* Row 2 — Trend + Pie */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Analyses Trend */}
            <div className="bg-white rounded-xl shadow-sm border p-6">
              <h3 className="text-lg font-bold text-slate-800 mb-4">Analyses Trend</h3>
              {(data.analyses_by_day?.length > 0) ? (
                <ResponsiveContainer width="100%" height={280}>
                  <AreaChart data={data.analyses_by_day} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                    <defs>
                      <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#7C3AED" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#7C3AED" stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 11, fill: '#94A3B8' }}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={v => {
                        const d = new Date(v + 'T00:00:00')
                        return `${d.getMonth() + 1}/${d.getDate()}`
                      }}
                    />
                    <YAxis tick={{ fontSize: 11, fill: '#94A3B8' }} tickLine={false} axisLine={false} allowDecimals={false} />
                    <Tooltip content={<ChartTooltip />} />
                    <Area
                      type="monotone"
                      dataKey="count"
                      name="Analyses"
                      stroke="#7C3AED"
                      strokeWidth={2.5}
                      fill="url(#areaGradient)"
                      dot={false}
                      activeDot={{ r: 5, fill: '#7C3AED', stroke: '#fff', strokeWidth: 2 }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-slate-400 text-sm">No data for this period</p>
              )}
            </div>

            {/* Recommendation Distribution */}
            <div className="bg-white rounded-xl shadow-sm border p-6">
              <h3 className="text-lg font-bold text-slate-800 mb-4">Recommendation Distribution</h3>
              {pieData.length > 0 ? (
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={3}
                      dataKey="value"
                      nameKey="name"
                      stroke="none"
                    >
                      {pieData.map(entry => (
                        <Cell key={entry.name} fill={PIE_COLORS[entry.name] || '#94A3B8'} />
                      ))}
                    </Pie>
                    <Tooltip content={<ChartTooltip />} />
                    <Legend
                      verticalAlign="bottom"
                      iconType="circle"
                      iconSize={10}
                      formatter={(value) => <span className="text-sm text-slate-600 font-medium">{value}</span>}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-slate-400 text-sm">No data for this period</p>
              )}
            </div>
          </div>

          {/* Row 3 — Score Distribution + Skill Gaps */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Score Distribution */}
            <div className="bg-white rounded-xl shadow-sm border p-6">
              <h3 className="text-lg font-bold text-slate-800 mb-4">Score Distribution</h3>
              {(data.score_distribution?.length > 0) ? (
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={data.score_distribution} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                    <XAxis dataKey="range" tick={{ fontSize: 11, fill: '#94A3B8' }} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: '#94A3B8' }} tickLine={false} axisLine={false} allowDecimals={false} />
                    <Tooltip content={<ChartTooltip />} />
                    <Bar dataKey="count" name="Candidates" fill="#7C3AED" radius={[6, 6, 0, 0]} barSize={36} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-slate-400 text-sm">No data for this period</p>
              )}
            </div>

            {/* Top Skill Gaps */}
            <div className="bg-white rounded-xl shadow-sm border p-6">
              <h3 className="text-lg font-bold text-slate-800 mb-4">Top Skill Gaps</h3>
              {skillGapsData.length > 0 ? (
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart
                    data={skillGapsData}
                    layout="vertical"
                    margin={{ left: 10, right: 20, top: 5, bottom: 5 }}
                    barSize={18}
                    barCategoryGap="25%"
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" horizontal={false} />
                    <XAxis type="number" tick={{ fontSize: 11, fill: '#94A3B8' }} tickLine={false} axisLine={false} allowDecimals={false} />
                    <YAxis
                      dataKey="skill"
                      type="category"
                      tick={{ fontSize: 11, fill: '#374151', fontWeight: 600 }}
                      width={100}
                      tickLine={false}
                      axisLine={false}
                    />
                    <Tooltip content={<ChartTooltip />} />
                    <Bar dataKey="frequency" name="Frequency" radius={[0, 6, 6, 0]}>
                      {skillGapsData.map((_, i) => (
                        <Cell key={i} fill={i < 3 ? '#ef4444' : '#f97316'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-slate-400 text-sm">No data for this period</p>
              )}
            </div>
          </div>

          {/* Row 4 — JD Effectiveness Table */}
          <JDEffectivenessTable data={data.jd_effectiveness} />

          {/* Row 5 — Pass-Through Funnel */}
          <PassThroughFunnel
            totalAnalyzed={data.total_analyzed ?? 0}
            rates={data.pass_through_rates}
          />
        </>
      )}
    </div>
  )
}
