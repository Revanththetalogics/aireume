import { useState } from 'react'
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { TrendingUp, TrendingDown, Minus, RefreshCw, Loader2 } from 'lucide-react'

const ROLE_CATEGORIES = [
  { value: '', label: 'All Categories' },
  { value: 'Backend Engineering', label: 'Backend Engineering' },
  { value: 'Frontend Engineering', label: 'Frontend Engineering' },
  { value: 'Data Science', label: 'Data Science' },
  { value: 'DevOps', label: 'DevOps' },
  { value: 'Product Management', label: 'Product Management' },
  { value: 'Sales', label: 'Sales' },
  { value: 'Management', label: 'Management' },
]

function trendIcon(direction) {
  if (direction === 'rising') return <TrendingUp className="w-4 h-4 text-green-600" />
  if (direction === 'falling') return <TrendingDown className="w-4 h-4 text-red-500" />
  return <Minus className="w-4 h-4 text-slate-400" />
}

function growthClass(pct) {
  if (pct > 0) return 'text-green-600'
  if (pct < 0) return 'text-red-500'
  return 'text-slate-400'
}

function MiniSparkline({ timeline }) {
  if (!timeline || timeline.length === 0) return null

  const values = timeline.map(t => t.jd_mentions ?? t.value ?? 0)
  const maxVal = Math.max(...values, 1)

  return (
    <div className="flex items-end gap-[3px] h-6">
      {values.map((v, i) => {
        const height = Math.max((v / maxVal) * 100, 6)
        const isLast = i === values.length - 1
        return (
          <div
            key={i}
            className={`w-[6px] rounded-sm ${isLast ? 'bg-violet-500' : 'bg-slate-300'}`}
            style={{ height: `${height}%` }}
            title={`${timeline[i]?.month ?? ''}: ${v}`}
          />
        )
      })}
    </div>
  )
}

function SkillTrendTooltip({ active, payload, label }) {
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

export default function SkillTrendChart({ data, loading, roleCategory, onRoleCategoryChange, onCompute, computing }) {
  const [sortKey, setSortKey] = useState('growth_pct')
  const [sortDir, setSortDir] = useState('desc')

  const skills = data?.skills ?? []
  const rising = skills.filter(s => s.direction === 'rising')
  const falling = skills.filter(s => s.direction === 'falling')
  const timelineMonths = data?.months ?? []

  const sorted = [...skills].sort((a, b) => {
    const av = a[sortKey] ?? 0
    const bv = b[sortKey] ?? 0
    if (typeof av === 'string') return sortDir === 'desc' ? bv.localeCompare(av) : av.localeCompare(bv)
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

  // Build chart data from timelineMonths for the line chart
  const chartData = timelineMonths.map(m => ({
    month: m.month,
    'JD Mentions': m.total_jd_mentions ?? 0,
    'Resume Presence': m.total_resume_presence ?? 0,
  }))

  return (
    <div className="space-y-6">
      {/* ── Controls ──────────────────────────────────────────── */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-3">
          <select
            value={roleCategory ?? ''}
            onChange={e => onRoleCategoryChange?.(e.target.value || null)}
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
          >
            {ROLE_CATEGORIES.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          <span className="text-xs text-slate-400">
            {data?.snapshot_count ?? 0} snapshot{data?.snapshot_count !== 1 ? 's' : ''} &middot; {data?.months_covered ?? 0} month{data?.months_covered !== 1 ? 's' : ''} covered
          </span>
        </div>
        {onCompute && (
          <button
            onClick={onCompute}
            disabled={computing}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-600 text-white text-sm font-semibold shadow-sm hover:bg-brand-700 transition-colors disabled:opacity-50"
          >
            {computing ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
            Compute Snapshots
          </button>
        )}
      </div>

      {/* ── Loading ───────────────────────────────────────────── */}
      {loading && (
        <div className="bg-white rounded-xl shadow-sm border p-6 flex items-center justify-center h-48">
          <Loader2 className="w-6 h-6 text-brand-500 animate-spin" />
          <span className="ml-3 text-sm text-slate-500">Loading skill trends...</span>
        </div>
      )}

      {/* ── Empty state ───────────────────────────────────────── */}
      {!loading && skills.length === 0 && (
        <div className="bg-white rounded-xl shadow-sm border p-8 text-center">
          <p className="text-slate-500 text-sm">
            No trend data yet. Ask your admin to compute monthly snapshots.
          </p>
        </div>
      )}

      {/* ── Data ──────────────────────────────────────────────── */}
      {!loading && skills.length > 0 && (
        <>
          {/* Rising / Falling badges */}
          <div className="space-y-2">
            {rising.length > 0 && (
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-semibold text-slate-600">Rising:</span>
                {rising.slice(0, 10).map(s => (
                  <span key={s.skill} className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold ring-1 bg-green-50 text-green-700 ring-green-200">
                    <TrendingUp className="w-3 h-3" />{s.skill}
                  </span>
                ))}
              </div>
            )}
            {falling.length > 0 && (
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-semibold text-slate-600">Falling:</span>
                {falling.slice(0, 10).map(s => (
                  <span key={s.skill} className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold ring-1 bg-red-50 text-red-700 ring-red-200">
                    <TrendingDown className="w-3 h-3" />{s.skill}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Timeline line chart */}
          {chartData.length > 1 && (
            <div className="bg-white rounded-xl shadow-sm border p-6">
              <h3 className="text-lg font-bold text-slate-800 mb-4">Monthly Trend Overview</h3>
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                  <XAxis
                    dataKey="month"
                    tick={{ fontSize: 11, fill: '#94A3B8' }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis tick={{ fontSize: 11, fill: '#94A3B8' }} tickLine={false} axisLine={false} allowDecimals={false} />
                  <Tooltip content={<SkillTrendTooltip />} />
                  <Line type="monotone" dataKey="JD Mentions" stroke="#7C3AED" strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="Resume Presence" stroke="#22c55e" strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Skills table */}
          <div className="bg-white rounded-xl shadow-sm border p-6">
            <h3 className="text-lg font-bold text-slate-800 mb-4">Skill Breakdown</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100">
                    <SortHeader label="Skill" field="skill" />
                    <SortHeader label="Trend" field="direction" />
                    <SortHeader label="Growth %" field="growth_pct" />
                    <SortHeader label="JD Mentions" field="jd_mentions" />
                    <SortHeader label="Resume %" field="resume_presence" />
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Timeline</th>
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((row, i) => (
                    <tr key={row.skill} className="border-b border-slate-50 hover:bg-slate-50/60 transition-colors">
                      <td className="px-4 py-3 font-medium text-slate-800">{row.skill}</td>
                      <td className="px-4 py-3">{trendIcon(row.direction)}</td>
                      <td className={`px-4 py-3 font-semibold ${growthClass(row.growth_pct)}`}>
                        {row.growth_pct > 0 ? '+' : ''}{row.growth_pct?.toFixed(1) ?? '—'}%
                      </td>
                      <td className="px-4 py-3 text-slate-600">{row.jd_mentions ?? '—'}</td>
                      <td className="px-4 py-3 text-slate-600">{row.resume_presence != null ? `${row.resume_presence.toFixed(1)}%` : '—'}</td>
                      <td className="px-4 py-3">
                        <MiniSparkline timeline={row.timeline} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
