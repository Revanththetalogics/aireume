import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  BarChart3, Users, Columns3, Phone, Building2, AlertTriangle, Plug, FileSpreadsheet, Download,
} from 'lucide-react'
import { Card, Button, SegmentedControl, Badge, Skeleton } from '../ui'
import { getAnalyticsHub, getReportTemplates, runAnalyticsReport } from '../../lib/api'
import EmptyState from '../EmptyState'

const SLICES = [
  { id: 'screening', label: 'Screening', icon: BarChart3 },
  { id: 'funnel', label: 'Funnel', icon: Columns3 },
  { id: 'interviews', label: 'Interviews', icon: Phone },
  { id: 'team', label: 'Team', icon: Users },
  { id: 'hm', label: 'HM', icon: Building2 },
  { id: 'leadership', label: 'Executive', icon: AlertTriangle },
  { id: 'ats', label: 'ATS', icon: Plug },
  { id: 'reports', label: 'Reports', icon: FileSpreadsheet },
]

const SLICE_META = {
  screening: {
    title: 'Resume screening',
    description: 'Who was screened, how they scored, and which reports to open.',
  },
  funnel: {
    title: 'Pipeline funnel',
    description: 'Stage movement, conversion rates, and requisitions with stalled candidates.',
  },
  interviews: {
    title: 'AI interviews',
    description: 'Voice session completion and how call scores compare to resume scores.',
  },
  team: {
    title: 'Team productivity',
    description: 'Which recruiters are running analyses and relative workload.',
  },
  hm: {
    title: 'Hiring manager workflow',
    description: 'HM submissions, pending reviews, and outcome turnaround.',
  },
  leadership: {
    title: 'Executive health',
    description: 'Open requisitions at risk — empty pipelines or calibrated roles with no screens.',
  },
  ats: {
    title: 'ATS integrations',
    description: 'Sync success rates, provider activity, and recent integration failures.',
  },
  reports: {
    title: 'Exports',
    description: 'Download CSV/XLSX report templates for offline analysis.',
  },
}

function SliceHeader({ sliceId }) {
  const meta = SLICE_META[sliceId]
  if (!meta) return null
  return (
    <div className="mb-1">
      <h3 className="text-base font-bold text-brand-900">{meta.title}</h3>
      <p className="text-sm text-slate-500">{meta.description}</p>
    </div>
  )
}

function DistributionBars({ items, valueKey = 'count', labelKey = 'label', maxItems = 8 }) {
  const rows = (items || []).slice(0, maxItems)
  if (!rows.length) return <p className="text-sm text-slate-500">No data for this period.</p>
  const peak = Math.max(...rows.map((r) => Number(r[valueKey]) || 0), 1)
  return (
    <div className="space-y-2">
      {rows.map((row) => {
        const value = Number(row[valueKey]) || 0
        const pct = Math.max(4, Math.round((value / peak) * 100))
        return (
          <div key={row[labelKey] || row.skill || row.name}>
            <div className="flex justify-between text-xs mb-1">
              <span className="font-medium text-slate-700 capitalize truncate pr-2">{row[labelKey] || row.skill || row.name}</span>
              <span className="text-slate-500 tabular-nums shrink-0">{value}</span>
            </div>
            <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
              <div className="h-full rounded-full bg-brand-500" style={{ width: `${pct}%` }} />
            </div>
          </div>
        )
      })}
    </div>
  )
}

const REC_COLORS = {
  shortlist: 'green',
  consider: 'amber',
  reject: 'red',
  hold: 'brand',
  unscored: 'slate',
}

function formatRelativeTime(iso) {
  if (!iso) return '—'
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return '—'
  const diffMs = Date.now() - then
  const mins = Math.floor(diffMs / 60000)
  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 14) return `${days}d ago`
  return new Date(iso).toLocaleDateString()
}

function recommendationColor(label) {
  if (!label) return REC_COLORS.unscored
  const key = String(label).toLowerCase()
  if (key.includes('shortlist') || key.includes('hire') || key.includes('proceed')) return REC_COLORS.shortlist
  if (key.includes('consider') || key.includes('review')) return REC_COLORS.consider
  if (key.includes('reject') || key.includes('pass')) return REC_COLORS.reject
  return REC_COLORS.hold
}

function scoreColorClass(score) {
  if (score == null || score === '') return 'text-slate-500'
  const n = Number(score)
  if (Number.isNaN(n)) return 'text-slate-500'
  if (n >= 70) return 'text-green-700 font-semibold'
  if (n >= 40) return 'text-amber-700 font-semibold'
  return 'text-red-700 font-semibold'
}

function KpiTile({ label, value, suffix = '' }) {
  return (
    <Card className="p-4">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-black text-brand-800 mt-1 tabular-nums">{value}{suffix}</p>
    </Card>
  )
}

function DrillTable({ rows, columns, onRowClick, emptyMessage = 'No rows to display.' }) {
  if (!rows?.length) return <p className="text-sm text-slate-500 py-4">{emptyMessage}</p>
  return (
    <div className="overflow-x-auto rounded-xl ring-1 ring-brand-100">
      <table className="w-full text-sm">
        <thead className="bg-brand-50/80">
          <tr>
            {columns.map((c) => (
              <th key={c.key} className="text-left px-3 py-2 font-semibold text-slate-600">{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={row.id || row.result_id || `${row.candidate_id}-${row.requisition_id}-${i}`}
              className={onRowClick ? 'cursor-pointer hover:bg-brand-50/50 border-t border-brand-50' : 'border-t border-brand-50'}
              onClick={() => onRowClick?.(row)}
            >
              {columns.map((c) => (
                <td key={c.key} className="px-3 py-2 text-slate-700 align-top">
                  {c.render ? c.render(row) : (row[c.key] ?? '—')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function AttentionPanels({ attention, onDrill }) {
  const stale = attention?.stale_candidates || []
  const zeroPipeline = attention?.zero_pipeline_requisitions || []
  const pendingHm = attention?.pending_hm_review ?? 0
  const hasItems = stale.length > 0 || zeroPipeline.length > 0 || pendingHm > 0
  if (!hasItems) return null

  return (
    <div className="grid gap-3 md:grid-cols-3">
      {stale.length > 0 && (
        <Card className="p-4 border-amber-100 bg-amber-50/40">
          <p className="text-xs font-bold text-amber-800 uppercase mb-2">Stale pipeline</p>
          <p className="text-sm text-amber-900 mb-2">{stale.length} candidate{stale.length !== 1 ? 's' : ''} idle 7+ days</p>
          <ul className="space-y-1">
            {stale.slice(0, 3).map((row) => (
              <li key={`${row.candidate_id}-${row.requisition_id}`}>
                <button
                  type="button"
                  className="text-sm text-amber-900 hover:underline text-left"
                  onClick={() => onDrill?.('candidate', row)}
                >
                  {row.candidate_name || `Candidate #${row.candidate_id}`}
                  {row.requisition_title ? ` · ${row.requisition_title}` : ''}
                </button>
              </li>
            ))}
          </ul>
        </Card>
      )}
      {zeroPipeline.length > 0 && (
        <Card className="p-4 border-red-100 bg-red-50/30">
          <p className="text-xs font-bold text-red-800 uppercase mb-2">Open reqs at risk</p>
          <p className="text-sm text-red-900 mb-2">{zeroPipeline.length} requisition{zeroPipeline.length !== 1 ? 's' : ''} with no candidates</p>
          <ul className="space-y-1">
            {zeroPipeline.slice(0, 3).map((row) => (
              <li key={row.id}>
                <button
                  type="button"
                  className="text-sm text-red-900 hover:underline text-left"
                  onClick={() => onDrill?.('requisition', row)}
                >
                  {row.title}
                </button>
              </li>
            ))}
          </ul>
        </Card>
      )}
      {pendingHm > 0 && (
        <Card className="p-4 border-brand-100 bg-brand-50/50">
          <p className="text-xs font-bold text-brand-800 uppercase mb-2">HM review</p>
          <p className="text-2xl font-black text-brand-900 tabular-nums">{pendingHm}</p>
          <p className="text-sm text-slate-600 mt-1">submissions awaiting hiring manager outcome</p>
        </Card>
      )}
    </div>
  )
}

function HubFilters({ options, requisitionId, recruiterId, onRequisitionChange, onRecruiterChange }) {
  const reqs = options?.requisitions || []
  const recruiters = options?.recruiters || []
  if (!reqs.length && !recruiters.length) return null

  return (
    <div className="flex flex-wrap gap-3">
      {reqs.length > 0 && (
        <select
          value={requisitionId ?? ''}
          onChange={(e) => onRequisitionChange(e.target.value ? Number(e.target.value) : null)}
          className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          aria-label="Filter by requisition"
        >
          <option value="">All requisitions</option>
          {reqs.map((r) => (
            <option key={r.id} value={r.id}>{r.title}</option>
          ))}
        </select>
      )}
      {recruiters.length > 0 && (
        <select
          value={recruiterId ?? ''}
          onChange={(e) => onRecruiterChange(e.target.value ? Number(e.target.value) : null)}
          className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          aria-label="Filter by recruiter"
        >
          <option value="">All recruiters</option>
          {recruiters.map((u) => (
            <option key={u.id} value={u.id}>{u.email}</option>
          ))}
        </select>
      )}
    </div>
  )
}

const SCREENING_COLUMNS = [
  {
    key: 'candidate_name',
    label: 'Candidate',
    render: (row) => (
      <div>
        <p className="font-semibold text-slate-900">{row.candidate_name || '—'}</p>
        {row.candidate_email && (
          <p className="text-xs text-slate-500 truncate max-w-[200px]">{row.candidate_email}</p>
        )}
      </div>
    ),
  },
  {
    key: 'role_title',
    label: 'Role',
    render: (row) => (
      <span className="text-slate-700">{row.requisition_title || row.role_title || '—'}</span>
    ),
  },
  {
    key: 'fit_score',
    label: 'Score',
    render: (row) => (
      <span className={scoreColorClass(row.fit_score)}>
        {row.fit_score != null && row.fit_score !== '' ? row.fit_score : 'Unscored'}
      </span>
    ),
  },
  {
    key: 'recommendation',
    label: 'Recommendation',
    render: (row) => (
      row.recommendation
        ? <Badge color={recommendationColor(row.recommendation)} className="capitalize">{row.recommendation}</Badge>
        : <span className="text-slate-400 text-xs">No recommendation</span>
    ),
  },
  {
    key: 'timestamp',
    label: 'Screened',
    render: (row) => <span className="text-slate-500 text-xs whitespace-nowrap">{formatRelativeTime(row.timestamp)}</span>,
  },
]

const INTERVIEW_COLUMNS = [
  {
    key: 'candidate_name',
    label: 'Candidate',
    render: (row) => (
      <div>
        <p className="font-semibold text-slate-900">{row.candidate_name || `Candidate #${row.candidate_id}`}</p>
        {row.candidate_email && <p className="text-xs text-slate-500">{row.candidate_email}</p>}
      </div>
    ),
  },
  { key: 'resume_score', label: 'Resume' },
  { key: 'call_score', label: 'Call' },
  {
    key: 'delta',
    label: 'Delta',
    render: (row) => {
      const d = row.delta
      if (d == null) return '—'
      const cls = d > 0 ? 'text-green-700' : d < 0 ? 'text-red-700' : 'text-slate-600'
      return <span className={`font-semibold tabular-nums ${cls}`}>{d > 0 ? `+${d}` : d}</span>
    },
  },
]

function ScreeningSlice({ data, onDrill }) {
  const kpis = data?.kpis || {}
  const recDist = Object.entries(data?.recommendation_distribution || {}).map(([name, count]) => ({
    label: name,
    count,
  }))
  const scoreDist = Object.entries(data?.score_distribution || {}).map(([range, count]) => ({
    label: range,
    count,
  }))

  return (
    <div className="space-y-4">
      <SliceHeader sliceId="screening" />
      <div className="grid sm:grid-cols-3 gap-3">
        <KpiTile label="Total analyzed" value={kpis.total_analyzed ?? 0} />
        <KpiTile label="Avg fit score" value={kpis.avg_fit_score ?? 0} />
        <KpiTile label="Shortlist rate" value={kpis.shortlist_rate ?? 0} suffix="%" />
      </div>
      <div className="grid lg:grid-cols-2 gap-3">
        <Card className="p-4">
          <p className="text-xs font-bold text-slate-500 uppercase mb-3">Recommendation mix</p>
          <DistributionBars items={recDist} labelKey="label" />
        </Card>
        <Card className="p-4">
          <p className="text-xs font-bold text-slate-500 uppercase mb-3">Score distribution</p>
          <DistributionBars items={scoreDist} labelKey="label" />
        </Card>
      </div>
      <Card className="p-4">
        <p className="text-xs font-bold text-slate-500 uppercase mb-3">Top skill gaps</p>
        <div className="flex flex-wrap gap-2">
          {(data?.top_skill_gaps || []).map((g) => (
            <Badge key={g.skill} color="amber">{g.skill} ({g.count})</Badge>
          ))}
          {!(data?.top_skill_gaps || []).length && (
            <p className="text-sm text-slate-500">No skill gaps recorded for this period.</p>
          )}
        </div>
      </Card>
      <Card className="p-4">
        <p className="text-xs font-bold text-slate-500 uppercase mb-3">Recent screenings — click row to open report</p>
        <DrillTable
          rows={data?.drill_down || []}
          columns={SCREENING_COLUMNS}
          onRowClick={(row) => onDrill?.('screening', row)}
          emptyMessage="No screenings in this period. Run an analysis to populate this table."
        />
      </Card>
    </div>
  )
}

function FunnelSlice({ data, onDrill }) {
  const conversion = data?.conversion || {}
  const stageRows = Object.entries(data?.stage_totals || {}).map(([stage, count]) => ({
    label: stage,
    count,
  }))

  return (
    <div className="space-y-4">
      <SliceHeader sliceId="funnel" />
      <div className="grid sm:grid-cols-2 gap-3">
        <KpiTile label="Shortlist conversion" value={conversion.to_shortlist ?? 0} suffix="%" />
        <KpiTile label="Hired conversion" value={conversion.to_hired ?? 0} suffix="%" />
      </div>
      <Card className="p-4">
        <p className="text-xs font-bold text-slate-500 uppercase mb-3">Candidates by pipeline stage</p>
        <DistributionBars items={stageRows} labelKey="label" />
      </Card>
      {(data?.stale_candidates || []).length > 0 && (
        <Card className="p-4">
          <p className="text-xs font-bold text-slate-500 uppercase mb-3">Stale candidates (7+ days)</p>
          <DrillTable
            rows={data.stale_candidates}
            columns={[
              {
                key: 'candidate_name',
                label: 'Candidate',
                render: (row) => row.candidate_name || `Candidate #${row.candidate_id}`,
              },
              { key: 'requisition_title', label: 'Requisition' },
              { key: 'pipeline_status', label: 'Status' },
              {
                key: 'updated_at',
                label: 'Last update',
                render: (row) => formatRelativeTime(row.updated_at),
              },
            ]}
            onRowClick={(row) => onDrill?.('candidate', row)}
          />
        </Card>
      )}
      <Card className="p-4">
        <p className="text-xs font-bold text-slate-500 uppercase mb-3">Pipeline volume by requisition</p>
        <DrillTable
          rows={(data?.by_requisition || []).map((r) => ({
            ...r,
            id: r.requisition_id,
          }))}
          columns={[
            { key: 'title', label: 'Requisition' },
            { key: 'total', label: 'Candidates' },
            { key: 'shortlist_rate', label: 'Shortlist %' },
          ]}
          onRowClick={(row) => onDrill?.('requisition', row)}
        />
      </Card>
    </div>
  )
}

function InterviewsSlice({ data, onDrill }) {
  const statusRows = Object.entries(data?.status_breakdown || {}).map(([status, count]) => ({
    label: status,
    count,
  }))

  return (
    <div className="space-y-4">
      <SliceHeader sliceId="interviews" />
      <div className="grid sm:grid-cols-3 gap-3">
        <KpiTile label="Sessions" value={data?.kpis?.total_sessions ?? 0} />
        <KpiTile label="Completion" value={data?.kpis?.completion_rate ?? 0} suffix="%" />
        <KpiTile label="Avg duration" value={data?.kpis?.avg_duration_min ?? 0} suffix="m" />
      </div>
      <Card className="p-4">
        <p className="text-xs font-bold text-slate-500 uppercase mb-3">Session status breakdown</p>
        <DistributionBars items={statusRows} labelKey="label" />
      </Card>
      <Card className="p-4">
        <p className="text-xs font-bold text-slate-500 uppercase mb-3">Resume vs call score delta</p>
        <DrillTable
          rows={data?.resume_vs_call_delta || []}
          columns={INTERVIEW_COLUMNS}
          onRowClick={(row) => onDrill('candidate', row)}
          emptyMessage="No completed interviews with both resume and call scores yet."
        />
      </Card>
    </div>
  )
}

function TeamSlice({ data }) {
  const rows = data?.recruiter_activity || []
  const peak = Math.max(...rows.map((r) => r.analyses || 0), 1)

  return (
    <div className="space-y-4">
      <SliceHeader sliceId="team" />
      <Card className="p-4">
        <p className="text-xs font-bold text-slate-500 uppercase mb-3">Recruiter activity leaderboard</p>
        {!rows.length ? (
          <p className="text-sm text-slate-500">No analysis activity recorded for this period.</p>
        ) : (
          <div className="space-y-3">
            {rows.map((row) => (
              <div key={row.user_id || row.email}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="font-medium text-slate-800">{row.email}</span>
                  <span className="text-slate-500 tabular-nums">{row.analyses} analyses</span>
                </div>
                <div className="h-2.5 rounded-full bg-slate-100 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-violet-500"
                    style={{ width: `${Math.max(6, Math.round(((row.analyses || 0) / peak) * 100))}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}

function HmSlice({ data, onDrill }) {
  const outcomeRows = Object.entries(data?.outcome_distribution || {}).map(([outcome, count]) => ({
    label: outcome,
    count,
  }))

  return (
    <div className="space-y-4">
      <SliceHeader sliceId="hm" />
      <div className="grid sm:grid-cols-3 gap-3">
        <KpiTile label="Submissions" value={data?.submissions_sent ?? 0} />
        <KpiTile label="Pending HM" value={data?.pending_hm_review ?? 0} />
        <KpiTile label="Avg turnaround" value={data?.avg_turnaround_hours ?? '—'} suffix="h" />
      </div>
      <Card className="p-4">
        <p className="text-xs font-bold text-slate-500 uppercase mb-3">HM outcome distribution</p>
        <DistributionBars items={outcomeRows} labelKey="label" />
      </Card>
      <Card className="p-4">
        <p className="text-xs font-bold text-slate-500 uppercase mb-3">Awaiting HM decision</p>
        <DrillTable
          rows={data?.pending_submissions || []}
          columns={[
            {
              key: 'candidate_name',
              label: 'Candidate',
              render: (row) => (
                <div>
                  <p className="font-semibold text-slate-900">{row.candidate_name || '—'}</p>
                  {row.candidate_email && <p className="text-xs text-slate-500">{row.candidate_email}</p>}
                </div>
              ),
            },
            { key: 'requisition_title', label: 'Requisition' },
            {
              key: 'submitted_at',
              label: 'Submitted',
              render: (row) => formatRelativeTime(row.submitted_at),
            },
          ]}
          onRowClick={(row) => onDrill?.('requisition', row)}
          emptyMessage="No submissions waiting on hiring manager review."
        />
      </Card>
    </div>
  )
}

function LeadershipSlice({ data, navigate }) {
  const zeroPipeline = data?.risk_flags?.zero_pipeline || []
  const calibratedIdle = data?.risk_flags?.calibrated_no_candidates || []

  return (
    <div className="space-y-4">
      <SliceHeader sliceId="leadership" />
      <KpiTile label="Open requisitions" value={data?.open_requisitions ?? 0} />
      <div className="grid md:grid-cols-2 gap-3">
        <Card className="p-4 border-amber-100">
          <p className="text-xs font-bold text-amber-800 uppercase mb-3">Zero pipeline</p>
          {zeroPipeline.length ? zeroPipeline.map((r) => (
            <button
              key={r.id}
              type="button"
              className="block text-sm text-amber-800 hover:underline mb-1 text-left"
              onClick={() => navigate(`/requisitions/${r.id}`)}
            >
              {r.title}
            </button>
          )) : <p className="text-sm text-slate-500">No open reqs without candidates.</p>}
        </Card>
        <Card className="p-4 border-red-100">
          <p className="text-xs font-bold text-red-800 uppercase mb-3">Calibrated, no screens</p>
          {calibratedIdle.length ? calibratedIdle.map((r) => (
            <button
              key={r.id}
              type="button"
              className="block text-sm text-red-800 hover:underline mb-1 text-left"
              onClick={() => navigate(`/requisitions/${r.id}`)}
            >
              {r.title}
            </button>
          )) : <p className="text-sm text-slate-500">All calibrated reqs have screening activity.</p>}
        </Card>
      </div>
    </div>
  )
}

function AtsSlice({ data }) {
  const providerRows = Object.entries(data?.by_provider || {}).map(([provider, count]) => ({
    label: provider,
    count,
  }))

  return (
    <div className="space-y-4">
      <SliceHeader sliceId="ats" />
      <div className="grid sm:grid-cols-3 gap-3">
        <KpiTile label="Sync success" value={data?.sync_success_rate ?? 0} suffix="%" />
        <KpiTile label="Failed syncs" value={data?.sync_failed ?? 0} />
        <KpiTile label="Active connections" value={data?.active_connections ?? 0} />
      </div>
      <Card className="p-4">
        <p className="text-xs font-bold text-slate-500 uppercase mb-3">Sync activity by provider</p>
        <DistributionBars items={providerRows} labelKey="label" />
      </Card>
      <Card className="p-4">
        <p className="text-xs font-bold text-slate-500 uppercase mb-3">Recent sync failures</p>
        <DrillTable
          rows={data?.recent_failures || []}
          columns={[
            { key: 'entity_type', label: 'Entity' },
            {
              key: 'created_at',
              label: 'When',
              render: (row) => formatRelativeTime(row.created_at),
            },
            { key: 'error_message', label: 'Error' },
          ]}
          emptyMessage="No ATS sync failures in this period."
        />
      </Card>
    </div>
  )
}

function ReportsSlice({ period }) {
  const [templates, setTemplates] = useState([])
  const [running, setRunning] = useState(null)
  const [result, setResult] = useState(null)

  useEffect(() => {
    getReportTemplates().then((d) => setTemplates(d.templates || [])).catch(() => setTemplates([]))
  }, [])

  const run = async (templateId, format = 'json') => {
    setRunning(templateId)
    try {
      const data = await runAnalyticsReport({ template_id: templateId, period, format })
      setResult(data)
      if (format === 'csv' && data.csv) {
        const blob = new Blob([data.csv], { type: 'text/csv' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${templateId}-${period}.csv`
        a.click()
        URL.revokeObjectURL(url)
      }
      if (format === 'xlsx' && data.xlsx_base64) {
        const binary = atob(data.xlsx_base64)
        const bytes = new Uint8Array(binary.length)
        for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i)
        const blob = new Blob([bytes], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${templateId}-${period}.xlsx`
        a.click()
        URL.revokeObjectURL(url)
      }
    } finally {
      setRunning(null)
    }
  }

  return (
    <div className="space-y-3">
      <SliceHeader sliceId="reports" />
      {templates.map((t) => (
        <Card key={t.id} className="p-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="font-semibold text-brand-900">{t.name}</p>
            <p className="text-sm text-slate-500">{t.description}</p>
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" disabled={running === t.id} onClick={() => run(t.id, 'json')}>
              Preview
            </Button>
            <Button size="sm" disabled={running === t.id} onClick={() => run(t.id, 'csv')}>
              <Download className="w-4 h-4" />
              Export CSV
            </Button>
            <Button variant="secondary" size="sm" disabled={running === t.id} onClick={() => run(t.id, 'xlsx')}>
              Export XLSX
            </Button>
          </div>
        </Card>
      ))}
      {result && (
        <Card className="p-4">
          <p className="text-xs font-bold text-slate-500 uppercase mb-2">Last report preview</p>
          <pre className="text-xs overflow-auto max-h-48 bg-brand-50/50 p-3 rounded-xl">
            {JSON.stringify(result.data || result.rows || result, null, 2)}
          </pre>
        </Card>
      )}
    </div>
  )
}

export default function AnalyticsHub({
  period = 'last_30_days',
  initialSlice = 'screening',
  activeSlice: controlledSlice,
  onSliceChange,
}) {
  const navigate = useNavigate()
  const [internalSlice, setInternalSlice] = useState(initialSlice)
  const slice = controlledSlice ?? internalSlice

  const setSlice = (next) => {
    if (controlledSlice === undefined) {
      setInternalSlice(next)
    }
    onSliceChange?.(next)
  }
  const [hub, setHub] = useState(null)
  const [loading, setLoading] = useState(true)
  const [requisitionId, setRequisitionId] = useState(null)
  const [recruiterId, setRecruiterId] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params = { period }
      if (requisitionId) params.requisition_id = requisitionId
      if (recruiterId) params.recruiter_id = recruiterId
      const data = await getAnalyticsHub(params)
      setHub(data)
    } catch {
      setHub(null)
    } finally {
      setLoading(false)
    }
  }, [period, requisitionId, recruiterId])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    if (controlledSlice !== undefined) return
    if (initialSlice && SLICES.some((s) => s.id === initialSlice)) {
      setInternalSlice(initialSlice)
    }
  }, [initialSlice, controlledSlice])

  const onDrill = (type, row) => {
    if (type === 'screening' && (row.result_id || row.id)) {
      navigate(`/report?id=${row.result_id || row.id}`)
      return
    }
    if (type === 'candidate' && row.candidate_id) {
      navigate(`/candidates/${row.candidate_id}`)
      return
    }
    if (type === 'requisition' && row.requisition_id) {
      navigate(`/requisitions/${row.requisition_id}?tab=pipeline`)
    }
  }

  const slices = hub?.slices || {}

  return (
    <div className="space-y-6">
      <SegmentedControl
        options={SLICES.map((s) => ({ value: s.id, label: s.label }))}
        value={slice}
        onChange={setSlice}
      />

      {loading ? (
        <div className="grid sm:grid-cols-3 gap-3">
          {[1, 2, 3].map((i) => <Skeleton key={i} className="h-24 rounded-2xl" />)}
        </div>
      ) : !hub ? (
        <EmptyState title="Analytics unavailable" description="Could not load hub data." />
      ) : (
        <>
          <HubFilters
            options={hub.filter_options}
            requisitionId={requisitionId}
            recruiterId={recruiterId}
            onRequisitionChange={setRequisitionId}
            onRecruiterChange={setRecruiterId}
          />
          {slice === 'screening' && (
            <AttentionPanels attention={hub.attention} onDrill={onDrill} />
          )}
          {slice === 'screening' ? (
            <ScreeningSlice data={slices.screening} onDrill={onDrill} />
          ) : slice === 'funnel' ? (
            <FunnelSlice data={slices.funnel} onDrill={onDrill} />
          ) : slice === 'interviews' ? (
            <InterviewsSlice data={slices.interviews} onDrill={onDrill} />
          ) : slice === 'team' ? (
            <TeamSlice data={slices.team} />
          ) : slice === 'hm' ? (
            <HmSlice data={slices.hm} onDrill={onDrill} />
          ) : slice === 'leadership' ? (
            <LeadershipSlice data={slices.leadership} navigate={navigate} />
          ) : slice === 'ats' ? (
            <AtsSlice data={slices.ats} />
          ) : (
            <ReportsSlice period={period} />
          )}
        </>
      )}
    </div>
  )
}
