import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

// ─── Skill categorisation ─────────────────────────────────────────────────────
// Covers common tech + domain-specific skills the hybrid pipeline surfaces.

const CATEGORY_MAP = [
  {
    name: 'Programming',
    color: '#7C3AED',
    bg: 'bg-violet-100',
    text: 'text-violet-700',
    keywords: ['python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'c', 'golang',
               'go', 'rust', 'scala', 'kotlin', 'swift', 'ruby', 'php', 'perl', 'r ',
               'matlab', 'assembly', 'vhdl', 'verilog', 'labview', 'lua', 'bash',
               'shell', 'powershell'],
  },
  {
    name: 'Frameworks & Libs',
    color: '#2563EB',
    bg: 'bg-blue-100',
    text: 'text-blue-700',
    keywords: ['react', 'vue', 'angular', 'node', 'express', 'django', 'flask', 'fastapi',
               'spring', 'laravel', 'rails', 'next', 'nuxt', 'svelte', 'tailwind',
               'pytorch', 'tensorflow', 'keras', 'scikit', 'pandas', 'numpy', 'scipy',
               'opencv', 'ros', 'qt', '.net', 'asp.net', 'hibernate', 'junit'],
  },
  {
    name: 'DevOps & Cloud',
    color: '#0891B2',
    bg: 'bg-cyan-100',
    text: 'text-cyan-700',
    keywords: ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'k8s', 'terraform',
               'ansible', 'linux', 'ci/cd', 'jenkins', 'github actions', 'gitlab',
               'nginx', 'prometheus', 'grafana', 'helm', 'devops', 'cloud', 'serverless',
               'iac', 'pulumi'],
  },
  {
    name: 'Data & Databases',
    color: '#059669',
    bg: 'bg-emerald-100',
    text: 'text-emerald-700',
    keywords: ['sql', 'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch',
               'kafka', 'spark', 'hadoop', 'airflow', 'dbt', 'snowflake', 'bigquery',
               'sqlite', 'oracle', 'cassandra', 'dynamodb', 'data pipeline', 'etl',
               'data warehouse', 'bi', 'tableau', 'powerbi'],
  },
  {
    name: 'Embedded & Systems',
    color: '#D97706',
    bg: 'bg-amber-100',
    text: 'text-amber-700',
    keywords: ['embedded', 'rtos', 'freertos', 'can bus', 'can', 'uart', 'spi', 'i2c',
               'modbus', 'profibus', 'profinet', 'ethernet/ip', 'plc', 'scada',
               'microcontroller', 'arm', 'stm32', 'arduino', 'raspberry pi', 'fpga',
               'firmware', 'driver', 'bsp', 'bootloader', 'bare metal', 'real-time',
               'jtag', 'oscilloscope', 'multimeter', 'pcb', 'signal processing',
               'autosar', 'misra', 'functional safety', 'iso 26262', 'iec 61508',
               'railway', 'rail', 'automotive', 'aerospace', 'adas', 'v-model'],
  },
  {
    name: 'Soft Skills',
    color: '#9333EA',
    bg: 'bg-purple-100',
    text: 'text-purple-700',
    keywords: ['leadership', 'management', 'communication', 'agile', 'scrum', 'kanban',
               'mentoring', 'teamwork', 'collaboration', 'problem solving', 'analytical',
               'presentation', 'stakeholder', 'project management', 'pmp', 'prince2',
               'jira', 'confluence'],
  },
]

function categoriseSkill(skill) {
  const s = skill.toLowerCase()
  for (const cat of CATEGORY_MAP) {
    if (cat.keywords.some(k => s === k || s.includes(k))) return cat.name
  }
  return 'Other'
}

const OTHER_CATEGORY = {
  name: 'Other',
  color: '#6B7280',
  bg: 'bg-slate-100',
  text: 'text-slate-600',
}

function getCat(name) {
  return CATEGORY_MAP.find(c => c.name === name) || OTHER_CATEGORY
}

// ─── Custom tooltip ──────────────────────────────────────────────────────────

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white/95 backdrop-blur-sm ring-1 ring-brand-100 rounded-2xl shadow-brand px-4 py-3 text-xs">
      <p className="font-bold text-brand-900 mb-1.5">{label}</p>
      {payload.map(p => (
        <p key={p.name} className="flex items-center gap-1.5 text-slate-600">
          <span className="w-2 h-2 rounded-full inline-block shrink-0" style={{ background: p.fill }} />
          <span className="font-semibold">{p.name}:</span> {p.value} skill{p.value !== 1 ? 's' : ''}
        </p>
      ))}
    </div>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function SkillsRadar({ matchedSkills = [], missingSkills = [] }) {
  if (!matchedSkills.length && !missingSkills.length) return null

  // Tally skills per category
  const tally = {}
  matchedSkills.forEach(s => {
    const c = categoriseSkill(s)
    if (!tally[c]) tally[c] = { matched: 0, missing: 0 }
    tally[c].matched++
  })
  missingSkills.forEach(s => {
    const c = categoriseSkill(s)
    if (!tally[c]) tally[c] = { matched: 0, missing: 0 }
    tally[c].missing++
  })

  // Sort: categories with data first, then by total desc
  const chartData = Object.entries(tally)
    .map(([name, { matched, missing }]) => ({ name, Has: matched, Needs: missing, total: matched + missing }))
    .sort((a, b) => b.total - a.total)

  const totalRequired = matchedSkills.length + missingSkills.length
  const matchPct = totalRequired > 0 ? Math.round((matchedSkills.length / totalRequired) * 100) : 0

  const matchColor = matchPct >= 75 ? '#059669' : matchPct >= 50 ? '#D97706' : '#DC2626'
  const matchBg    = matchPct >= 75 ? 'bg-emerald-50 ring-emerald-200' : matchPct >= 50 ? 'bg-amber-50 ring-amber-200' : 'bg-red-50 ring-red-200'
  const matchText  = matchPct >= 75 ? 'text-emerald-700' : matchPct >= 50 ? 'text-amber-700' : 'text-red-700'

  const barHeight = Math.max(160, chartData.length * 44)

  return (
    <div className="bg-brand-50/60 rounded-2xl p-5 ring-1 ring-brand-100 space-y-5">

      {/* Header + overall match rate */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h3 className="text-sm font-bold text-brand-900 uppercase tracking-wide">
          Skills Gap Analysis
        </h3>
        <div className={`flex items-center gap-3 px-4 py-2 rounded-2xl ring-1 ${matchBg}`}>
          {/* Circular progress indicator */}
          <svg width="44" height="44" className="shrink-0 -rotate-90">
            <circle cx="22" cy="22" r="18" fill="none" stroke="#E5E7EB" strokeWidth="4" />
            <circle
              cx="22" cy="22" r="18" fill="none"
              stroke={matchColor} strokeWidth="4"
              strokeLinecap="round"
              strokeDasharray={`${2 * Math.PI * 18}`}
              strokeDashoffset={`${2 * Math.PI * 18 * (1 - matchPct / 100)}`}
              style={{ transition: 'stroke-dashoffset 0.8s ease' }}
            />
            <text
              x="22" y="22" textAnchor="middle" dominantBaseline="central"
              className="rotate-90"
              style={{ rotate: '90deg', transformOrigin: '22px 22px', fontSize: 11, fontWeight: 700, fill: matchColor }}
            >
              {matchPct}%
            </text>
          </svg>
          <div>
            <p className={`text-lg font-extrabold leading-none ${matchText}`}>
              {matchedSkills.length} / {totalRequired}
            </p>
            <p className="text-xs text-slate-500 mt-0.5">skills matched</p>
          </div>
        </div>
      </div>

      {/* Match rate progress bar */}
      <div>
        <div className="flex justify-between text-xs mb-1.5">
          <span className="font-semibold text-slate-500">Coverage</span>
          <span className="font-bold" style={{ color: matchColor }}>{matchPct}% covered</span>
        </div>
        <div className="w-full bg-slate-200 rounded-full h-3 overflow-hidden">
          <div
            className="h-3 rounded-full transition-all duration-700"
            style={{ width: `${matchPct}%`, background: matchColor }}
          />
        </div>
      </div>

      {/* Category breakdown bar chart */}
      {chartData.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-slate-500 mb-3">Skills by Category</p>
          <ResponsiveContainer width="100%" height={barHeight}>
            <BarChart
              data={chartData}
              layout="vertical"
              margin={{ left: 4, right: 16, top: 0, bottom: 0 }}
              barSize={14}
              barCategoryGap="30%"
            >
              <XAxis type="number" tick={{ fontSize: 10, fill: '#9CA3AF' }} tickLine={false} axisLine={false} />
              <YAxis
                dataKey="name"
                type="category"
                tick={{ fontSize: 11, fill: '#374151', fontWeight: 600 }}
                width={160}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(124,58,237,0.05)' }} />
              <Bar dataKey="Has" name="Matched" radius={[0, 4, 4, 0]}>
                {chartData.map((entry) => (
                  <Cell key={entry.name} fill={getCat(entry.name).color} />
                ))}
              </Bar>
              <Bar dataKey="Needs" name="Missing" radius={[0, 4, 4, 0]} fill="#FCA5A5" />
            </BarChart>
          </ResponsiveContainer>
          {/* Legend */}
          <div className="flex items-center gap-4 mt-2 justify-center">
            <span className="flex items-center gap-1.5 text-xs text-slate-500">
              <span className="w-3 h-3 rounded-sm bg-violet-600 inline-block" /> Matched
            </span>
            <span className="flex items-center gap-1.5 text-xs text-slate-500">
              <span className="w-3 h-3 rounded-sm bg-red-300 inline-block" /> Missing
            </span>
          </div>
        </div>
      )}

      {/* Skill chips per category */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {chartData.map(({ name }) => {
          const cat   = getCat(name)
          const has   = matchedSkills.filter(s => categoriseSkill(s) === name)
          const needs = missingSkills.filter(s => categoriseSkill(s) === name)
          return (
            <div key={name} className={`rounded-xl p-3 ring-1 ${cat.bg} ring-current/10`}>
              <p className={`text-xs font-bold uppercase tracking-wide mb-2 ${cat.text}`}>{name}</p>
              <div className="flex flex-wrap gap-1">
                {has.map((s, i) => (
                  <span key={`h${i}`} className="px-2 py-0.5 bg-white/70 text-slate-700 text-xs rounded-lg font-semibold ring-1 ring-white/50">
                    ✓ {s}
                  </span>
                ))}
                {needs.map((s, i) => (
                  <span key={`n${i}`} className="px-2 py-0.5 bg-red-50 text-red-600 text-xs rounded-lg font-semibold ring-1 ring-red-100">
                    ✗ {s}
                  </span>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
