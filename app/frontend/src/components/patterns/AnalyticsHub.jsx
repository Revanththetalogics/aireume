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

function KpiTile({ label, value, suffix = '' }) {
  return (
    <Card className="p-4">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-black text-brand-800 mt-1 tabular-nums">{value}{suffix}</p>
    </Card>
  )
}

function DrillTable({ rows, columns, onRowClick }) {
  if (!rows?.length) return <p className="text-sm text-slate-500 py-4">No rows to display.</p>
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
              key={row.id || row.candidate_id || i}
              className={onRowClick ? 'cursor-pointer hover:bg-brand-50/50 border-t border-brand-50' : 'border-t border-brand-50'}
              onClick={() => onRowClick?.(row)}
            >
              {columns.map((c) => (
                <td key={c.key} className="px-3 py-2 text-slate-700">{row[c.key] ?? '—'}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ScreeningSlice({ data, onDrill }) {
  const kpis = data?.kpis || {}
  return (
    <div className="space-y-4">
      <div className="grid sm:grid-cols-3 gap-3">
        <KpiTile label="Total analyzed" value={kpis.total_analyzed ?? 0} />
        <KpiTile label="Avg fit score" value={kpis.avg_fit_score ?? 0} />
        <KpiTile label="Shortlist rate" value={kpis.shortlist_rate ?? 0} suffix="%" />
      </div>
      <Card className="p-4">
        <p className="text-xs font-bold text-slate-500 uppercase mb-3">Top skill gaps</p>
        <div className="flex flex-wrap gap-2">
          {(data?.top_skill_gaps || []).map((g) => (
            <Badge key={g.skill} color="amber">{g.skill} ({g.count})</Badge>
          ))}
        </div>
      </Card>
      <Card className="p-4">
        <p className="text-xs font-bold text-slate-500 uppercase mb-3">Drill-down — click row to open report</p>
        <DrillTable
          rows={data?.drill_down || []}
          columns={[
            { key: 'candidate_id', label: 'Candidate' },
            { key: 'fit_score', label: 'Score' },
            { key: 'recommendation', label: 'Rec' },
          ]}
          onRowClick={(row) => onDrill?.('candidate', row)}
        />
      </Card>
    </div>
  )
}

function FunnelSlice({ data, onDrill }) {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {Object.entries(data?.stage_totals || {}).map(([stage, count]) => (
          <Badge key={stage} color="brand" className="capitalize">{stage}: {count}</Badge>
        ))}
      </div>
      <Card className="p-4">
        <p className="text-xs font-bold text-slate-500 uppercase mb-3">By requisition</p>
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

export default function AnalyticsHub({ period = 'last_30_days', initialSlice = 'screening' }) {
  const navigate = useNavigate()
  const [slice, setSlice] = useState(initialSlice)
  const [hub, setHub] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getAnalyticsHub({ period })
      setHub(data)
    } catch {
      setHub(null)
    } finally {
      setLoading(false)
    }
  }, [period])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    if (initialSlice && SLICES.some((s) => s.id === initialSlice)) {
      setSlice(initialSlice)
    }
  }, [initialSlice])

  const onDrill = (type, row) => {
    if (type === 'candidate' && row.candidate_id) {
      navigate(`/candidates/${row.candidate_id}`)
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
      ) : slice === 'screening' ? (
        <ScreeningSlice data={slices.screening} onDrill={onDrill} />
      ) : slice === 'funnel' ? (
        <FunnelSlice data={slices.funnel} onDrill={onDrill} />
      ) : slice === 'interviews' ? (
        <div className="space-y-4">
          <div className="grid sm:grid-cols-3 gap-3">
            <KpiTile label="Sessions" value={slices.interviews?.kpis?.total_sessions ?? 0} />
            <KpiTile label="Completion" value={slices.interviews?.kpis?.completion_rate ?? 0} suffix="%" />
            <KpiTile label="Avg duration" value={slices.interviews?.kpis?.avg_duration_min ?? 0} suffix="m" />
          </div>
          <Card className="p-4">
            <p className="text-xs font-bold text-slate-500 uppercase mb-3">Resume vs call score delta</p>
            <DrillTable
              rows={slices.interviews?.resume_vs_call_delta || []}
              columns={[
                { key: 'candidate_id', label: 'Candidate' },
                { key: 'resume_score', label: 'Resume' },
                { key: 'call_score', label: 'Call' },
                { key: 'delta', label: 'Delta' },
              ]}
              onRowClick={(row) => onDrill('candidate', row)}
            />
          </Card>
        </div>
      ) : slice === 'team' ? (
        <DrillTable
          rows={slices.team?.recruiter_activity || []}
          columns={[
            { key: 'name', label: 'Recruiter' },
            { key: 'analyses', label: 'Analyses' },
          ]}
        />
      ) : slice === 'hm' ? (
        <div className="grid sm:grid-cols-3 gap-3">
          <KpiTile label="Submissions" value={slices.hm?.submissions_sent ?? 0} />
          <KpiTile label="Pending HM" value={slices.hm?.pending_hm_review ?? 0} />
          <KpiTile label="Avg turnaround" value={slices.hm?.avg_turnaround_hours ?? '—'} suffix="h" />
        </div>
      ) : slice === 'leadership' ? (
        <Card className="p-4 space-y-2">
          <p className="text-sm font-semibold">Open requisitions: {slices.leadership?.open_requisitions ?? 0}</p>
          {(slices.leadership?.risk_flags?.zero_pipeline || []).map((r) => (
            <button
              key={r.id}
              type="button"
              className="block text-sm text-amber-700 hover:underline"
              onClick={() => navigate(`/requisitions/${r.id}`)}
            >
              {r.title} — zero pipeline
            </button>
          ))}
        </Card>
      ) : slice === 'ats' ? (
        <div className="space-y-4">
          <div className="grid sm:grid-cols-3 gap-3">
            <KpiTile label="Sync success" value={slices.ats?.sync_success_rate ?? 0} suffix="%" />
            <KpiTile label="Failed syncs" value={slices.ats?.sync_failed ?? 0} />
            <KpiTile label="Connections" value={slices.ats?.active_connections ?? 0} />
          </div>
          <DrillTable
            rows={slices.ats?.recent_failures || []}
            columns={[
              { key: 'entity_type', label: 'Entity' },
              { key: 'error_message', label: 'Error' },
            ]}
          />
        </div>
      ) : (
        <ReportsSlice period={period} />
      )}
    </div>
  )
}
