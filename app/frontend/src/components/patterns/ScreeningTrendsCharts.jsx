import {
  BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, AreaChart, Area,
} from 'recharts'
import { TrendingUp } from 'lucide-react'
import { Card } from '../ui'
import SkillTrendChart from '../SkillTrendChart'

const PIE_COLORS = {
  Shortlist: '#22c55e',
  shortlist: '#22c55e',
  Consider: '#f59e0b',
  consider: '#f59e0b',
  Reject: '#ef4444',
  reject: '#ef4444',
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white/95 dark:bg-dark-card backdrop-blur-sm ring-1 ring-slate-200 dark:ring-dark-border rounded-xl shadow-lg px-3 py-2 text-xs">
      <p className="font-bold text-slate-800 dark:text-dark-text mb-1">{label}</p>
      {payload.map((p) => (
        <p key={p.name} className="flex items-center gap-1.5 text-slate-600 dark:text-dark-text-secondary">
          <span className="w-2 h-2 rounded-full inline-block shrink-0" style={{ background: p.color }} />
          <span className="font-semibold">{p.name}:</span> {p.value}
        </p>
      ))}
    </div>
  )
}

function scoreColor(score) {
  if (score >= 70) return 'text-green-600'
  if (score >= 40) return 'text-amber-600'
  return 'text-red-600'
}

function scoreBadgeBg(score) {
  if (score >= 70) return 'bg-green-50 text-green-700 ring-green-200 dark:bg-green-900/30 dark:text-green-300'
  if (score >= 40) return 'bg-amber-50 text-amber-700 ring-amber-200 dark:bg-amber-900/30 dark:text-amber-300'
  return 'bg-red-50 text-red-700 ring-red-200 dark:bg-red-900/30 dark:text-red-300'
}

function JDEffectivenessTable({ data }) {
  if (!data?.length) {
    return (
      <Card className="p-6">
        <h3 className="text-lg font-bold text-slate-800 dark:text-dark-text mb-4">JD effectiveness</h3>
        <p className="text-slate-400 text-sm">No JD data for this period.</p>
      </Card>
    )
  }
  return (
    <Card className="p-6">
      <h3 className="text-lg font-bold text-slate-800 dark:text-dark-text mb-4">JD effectiveness</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 dark:border-dark-border">
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">JD name</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Candidates</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Avg score</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Shortlist rate</th>
            </tr>
          </thead>
          <tbody>
            {data.map((row, i) => (
              <tr key={i} className="border-b border-slate-50 dark:border-dark-border/50">
                <td className="px-4 py-3 font-medium text-slate-800 dark:text-dark-text">{row.jd_name}</td>
                <td className="px-4 py-3 text-slate-600 dark:text-dark-text-secondary">{row.candidates}</td>
                <td className="px-4 py-3">
                  <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-bold ring-1 ${scoreBadgeBg(row.avg_score)}`}>
                    {row.avg_score?.toFixed(1) ?? '—'}
                  </span>
                </td>
                <td className="px-4 py-3 text-slate-600 dark:text-dark-text-secondary">
                  {(row.shortlist_rate * 100).toFixed(1)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  )
}

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
    <Card className="p-6">
      <h3 className="text-lg font-bold text-slate-800 dark:text-dark-text mb-2">Pipeline outcomes funnel</h3>
      <p className="text-xs text-slate-500 mb-4">Based on screening result status (shortlisted → hired), not pipeline stages.</p>
      <div className="space-y-3">
        {stages.map((stage, i) => (
          <div key={stage.label}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-semibold text-slate-700 dark:text-dark-text">{stage.label}</span>
              <span className="text-sm font-bold text-slate-800 dark:text-dark-text">{stage.count}</span>
            </div>
            <div className="w-full bg-slate-100 dark:bg-dark-card-elevated rounded-lg h-8 overflow-hidden">
              <div
                className={`h-8 rounded-lg ${stage.color} flex items-center justify-end pr-3`}
                style={{ width: `${Math.max(stage.pct * 100, 4)}%` }}
                role="progressbar"
                aria-valuenow={Math.round(stage.pct * 100)}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`${stage.label} conversion`}
              >
                {stage.pct > 0 && i > 0 && (
                  <span className="text-xs font-bold text-white">{(stage.pct * 100).toFixed(0)}%</span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  )
}

function exportChartCsv(filename, rows, headers) {
  const lines = [headers.join(',')]
  rows.forEach((row) => {
    lines.push(headers.map((h) => JSON.stringify(row[h] ?? '')).join(','))
  })
  const blob = new Blob([lines.join('\n')], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export default function ScreeningTrendsCharts({
  trends,
  trendData,
  trendLoading,
  trendRoleCategory,
  onRoleCategoryChange,
  onComputeSnapshots,
  computing,
  showAdminCompute = false,
}) {
  if (!trends || (trends.total_analyzed ?? 0) === 0) return null

  const pieData = trends.recommendation_distribution
    ? Object.entries(trends.recommendation_distribution).map(([name, value]) => ({ name, value }))
    : []
  const skillGapsData = [...(trends.top_skill_gaps || [])]
    .sort((a, b) => (b.frequency ?? b.count ?? 0) - (a.frequency ?? a.count ?? 0))
    .slice(0, 10)
    .map((g) => ({ ...g, frequency: g.frequency ?? g.count ?? 0 }))
  const shortlistRate = trends.pass_through_rates?.analyzed_to_shortlisted ?? 0
  const hiredRate = trends.pass_through_rates?.shortlisted_to_hired ?? 0

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-brand-600" />
          <h3 className="text-lg font-bold text-slate-800 dark:text-dark-text">Historical charts</h3>
        </div>
        <button
          type="button"
          className="text-xs font-semibold text-brand-600 hover:text-brand-800"
          onClick={() => exportChartCsv(
            'analyses-trend.csv',
            trends.analyses_by_day || [],
            ['date', 'count'],
          )}
        >
          Export trend CSV
        </button>
      </div>

      {trends.comparison && (
        <Card className="p-4 bg-brand-50/40 dark:bg-brand-900/20">
          <p className="text-xs font-bold text-brand-800 uppercase mb-2">vs prior period</p>
          <div className="flex flex-wrap gap-4 text-sm">
            <span>Analyses: {trends.comparison.deltas.total_analyzed >= 0 ? '+' : ''}{trends.comparison.deltas.total_analyzed}</span>
            <span>Avg score: {trends.comparison.deltas.avg_fit_score >= 0 ? '+' : ''}{trends.comparison.deltas.avg_fit_score}</span>
            <span>Pipeline shortlist: {trends.comparison.deltas.pipeline_shortlist_rate >= 0 ? '+' : ''}{trends.comparison.deltas.pipeline_shortlist_rate}%</span>
          </div>
        </Card>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <Card className="p-4">
          <p className="text-xs font-semibold text-slate-500 uppercase">Pipeline shortlist</p>
          <p className={`text-2xl font-black mt-1 ${scoreColor(trends.pipeline_shortlist_rate)}`}>
            {trends.pipeline_shortlist_rate?.toFixed(1)}%
          </p>
        </Card>
        <Card className="p-4">
          <p className="text-xs font-semibold text-slate-500 uppercase">AI recommend shortlist</p>
          <p className="text-2xl font-black mt-1 text-slate-800 dark:text-dark-text">
            {trends.recommendation_shortlist_rate?.toFixed(1)}%
          </p>
        </Card>
        <Card className="p-4">
          <p className="text-xs font-semibold text-slate-500 uppercase">Hired rate</p>
          <p className={`text-2xl font-black mt-1 ${scoreColor(trends.hired_rate)}`}>
            {trends.hired_rate?.toFixed(1)}%
          </p>
        </Card>
        <Card className="p-4">
          <p className="text-xs font-semibold text-slate-500 uppercase">Pass-through</p>
          <p className="text-2xl font-black mt-1 text-slate-800 dark:text-dark-text">
            {(shortlistRate * 100).toFixed(1)}% → {(hiredRate * 100).toFixed(1)}%
          </p>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card className="p-6">
          <h4 className="font-bold text-slate-800 dark:text-dark-text mb-4">Analyses trend</h4>
          {(trends.analyses_by_day?.length > 0) ? (
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={trends.analyses_by_day}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                <Tooltip content={<ChartTooltip />} />
                <Area type="monotone" dataKey="count" name="Analyses" stroke="#7C3AED" fill="#7C3AED33" />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-slate-400">No daily trend data.</p>
          )}
        </Card>
        <Card className="p-6">
          <h4 className="font-bold text-slate-800 dark:text-dark-text mb-4">Recommendation distribution</h4>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={90} dataKey="value" nameKey="name">
                  {pieData.map((entry) => (
                    <Cell key={entry.name} fill={PIE_COLORS[entry.name] || '#94A3B8'} />
                  ))}
                </Pie>
                <Tooltip content={<ChartTooltip />} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-slate-400">No recommendation data.</p>
          )}
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card className="p-6">
          <h4 className="font-bold text-slate-800 dark:text-dark-text mb-4">Score distribution</h4>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={trends.score_distribution || []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="range" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
              <Tooltip content={<ChartTooltip />} />
              <Bar dataKey="count" name="Candidates" fill="#7C3AED" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
        <Card className="p-6">
          <h4 className="font-bold text-slate-800 dark:text-dark-text mb-4">Top skill gaps</h4>
          {skillGapsData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={skillGapsData} layout="vertical" margin={{ left: 10 }}>
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis dataKey="skill" type="category" width={90} tick={{ fontSize: 11 }} />
                <Tooltip content={<ChartTooltip />} />
                <Bar dataKey="frequency" name="Frequency" fill="#f97316" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-slate-400">No skill gaps recorded.</p>
          )}
        </Card>
      </div>

      <JDEffectivenessTable data={trends.jd_effectiveness} />
      <PassThroughFunnel totalAnalyzed={trends.total_analyzed ?? 0} rates={trends.pass_through_rates} />

      <Card className="p-6">
        <h4 className="font-bold text-slate-800 dark:text-dark-text mb-4">Skill trends (6 months)</h4>
        <SkillTrendChart
          data={trendData}
          loading={trendLoading}
          roleCategory={trendRoleCategory}
          onRoleCategoryChange={onRoleCategoryChange}
          onCompute={showAdminCompute ? onComputeSnapshots : undefined}
          computing={computing}
        />
      </Card>
    </div>
  )
}
