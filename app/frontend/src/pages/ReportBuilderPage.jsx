import { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Download, Share2, Calendar, Trash2 } from 'lucide-react'
import { Card, Button, Badge, Skeleton } from '../components/ui'
import EmptyState from '../components/EmptyState'
import {
  getReportFieldCatalog,
  runCustomReport,
  listSavedReports,
  createSavedReport,
  deleteSavedReport,
  shareSavedReport,
  listScheduledReports,
  createScheduledReport,
  deleteScheduledReport,
} from '../lib/api'
import { ANALYTICS } from '../lib/uxLabels'

const STEPS = ['source', 'columns', 'filters', 'run']

function downloadExport(data, format, name) {
  if (format === 'csv' && data.csv) {
    const blob = new Blob([data.csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${name}.csv`
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
    a.download = `${name}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  }
}

export default function ReportBuilderPage() {
  const [searchParams] = useSearchParams()
  const period = searchParams.get('period') || 'last_30_days'
  const startDate = searchParams.get('start_date') || ''
  const endDate = searchParams.get('end_date') || ''
  const useCustomRange = Boolean(startDate && endDate)

  const [catalog, setCatalog] = useState(null)
  const [loading, setLoading] = useState(true)
  const [step, setStep] = useState(0)
  const [entity, setEntity] = useState('requisition_candidates')
  const [columns, setColumns] = useState([])
  const [groupBy, setGroupBy] = useState([])
  const [reportName, setReportName] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [running, setRunning] = useState(false)
  const [savedReports, setSavedReports] = useState([])
  const [schedules, setSchedules] = useState([])
  const [scheduleForm, setScheduleForm] = useState({ saved_report_id: null, schedule: 'weekly', recipients: '' })

  const loadMeta = useCallback(async () => {
    setLoading(true)
    try {
      const [fields, saved, sched] = await Promise.all([
        getReportFieldCatalog(),
        listSavedReports(),
        listScheduledReports(),
      ])
      setCatalog(fields)
      setSavedReports(saved.reports || [])
      setSchedules(sched.schedules || [])
      const firstEntity = Object.keys(fields.entities || {})[0]
      if (firstEntity) {
        setEntity(firstEntity)
        setColumns((fields.entities[firstEntity]?.columns || []).map((c) => c.key))
      }
    } catch (err) {
      setError(err.message || ANALYTICS.errorGeneric)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadMeta()
  }, [loadMeta])

  const entityMeta = catalog?.entities?.[entity]
  const templates = catalog?.templates || []

  const buildDefinition = () => ({
    entity,
    columns,
    group_by: groupBy.length ? groupBy : undefined,
    period: useCustomRange ? period : period,
    start_date: useCustomRange ? startDate : undefined,
    end_date: useCustomRange ? endDate : undefined,
  })

  const runReport = async (format = 'json') => {
    setRunning(true)
    setError(null)
    try {
      const data = await runCustomReport({ definition: buildDefinition(), format })
      setResult(data)
      if (format !== 'json') downloadExport(data, format, reportName || entity)
    } catch (err) {
      setError(err?.response?.data?.detail || err.message || 'Report failed')
    } finally {
      setRunning(false)
    }
  }

  const saveReport = async () => {
    if (!reportName.trim()) {
      setError(ANALYTICS.reportNameRequired)
      return
    }
    await createSavedReport({ name: reportName.trim(), definition: buildDefinition() })
    const saved = await listSavedReports()
    setSavedReports(saved.reports || [])
  }

  const loadSaved = (report) => {
    const def = report.definition || {}
    if (def.entity) setEntity(def.entity)
    if (def.columns) setColumns(def.columns)
    if (def.group_by) setGroupBy(def.group_by)
    setReportName(report.name)
    setStep(3)
  }

  const toggleColumn = (key) => {
    setColumns((prev) => (prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]))
  }

  const toggleGroupBy = (key) => {
    setGroupBy((prev) => (prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]))
  }

  if (loading) {
    return <Skeleton className="h-64 rounded-2xl" />
  }

  return (
    <div className="space-y-6">
      <p className="text-sm text-slate-600">{ANALYTICS.reportsSubtitle}</p>

      <div className="flex flex-wrap gap-2">
        {STEPS.map((s, i) => (
          <button
            key={s}
            type="button"
            onClick={() => setStep(i)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium ${step === i ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-600'}`}
          >
            {i + 1}. {ANALYTICS.reportSteps[s]}
          </button>
        ))}
      </div>

      {error && (
        <Card className="p-3 border-red-200 bg-red-50 text-red-700 text-sm">{error}</Card>
      )}

      {step === 0 && (
        <Card className="p-4 space-y-4">
          <p className="font-semibold text-brand-900">{ANALYTICS.reportPickSource}</p>
          <div className="grid sm:grid-cols-2 gap-3">
            {Object.entries(catalog?.entities || {}).map(([key, meta]) => (
              <button
                key={key}
                type="button"
                onClick={() => {
                  setEntity(key)
                  setColumns((meta.columns || []).map((c) => c.key))
                  setGroupBy([])
                }}
                className={`text-left p-4 rounded-xl border ${entity === key ? 'border-brand-500 bg-brand-50' : 'border-slate-200'}`}
              >
                <p className="font-semibold">{meta.label}</p>
                <p className="text-sm text-slate-500">{meta.description}</p>
              </button>
            ))}
          </div>
          {templates.length > 0 && (
            <div>
              <p className="text-xs font-bold text-slate-500 uppercase mb-2">{ANALYTICS.reportTemplatesLabel}</p>
              <div className="flex flex-wrap gap-2">
                {templates.map((t) => (
                  <Badge key={t.id} color="slate">{t.name}</Badge>
                ))}
              </div>
            </div>
          )}
          <Button onClick={() => setStep(1)}>{ANALYTICS.nextLabel}</Button>
        </Card>
      )}

      {step === 1 && entityMeta && (
        <Card className="p-4 space-y-4">
          <p className="font-semibold text-brand-900">{ANALYTICS.reportPickColumns}</p>
          <div className="grid sm:grid-cols-2 gap-2">
            {entityMeta.columns.map((col) => (
              <label key={col.key} className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" checked={columns.includes(col.key)} onChange={() => toggleColumn(col.key)} />
                {col.label}
              </label>
            ))}
          </div>
          {(entityMeta.group_by_options || []).length > 0 && (
            <div>
              <p className="text-sm font-semibold text-slate-700 mb-2">{ANALYTICS.reportGroupByLabel}</p>
              <div className="flex flex-wrap gap-2">
                {entityMeta.group_by_options.map((g) => (
                  <label key={g} className="flex items-center gap-1 text-sm">
                    <input type="checkbox" checked={groupBy.includes(g)} onChange={() => toggleGroupBy(g)} />
                    {g}
                  </label>
                ))}
              </div>
            </div>
          )}
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => setStep(0)}>{ANALYTICS.backLabel}</Button>
            <Button onClick={() => setStep(2)}>{ANALYTICS.nextLabel}</Button>
          </div>
        </Card>
      )}

      {step === 2 && (
        <Card className="p-4 space-y-4">
          <p className="font-semibold text-brand-900">{ANALYTICS.reportFiltersHint}</p>
          <p className="text-sm text-slate-500">
            {useCustomRange ? `${startDate} – ${endDate}` : period.replace(/_/g, ' ')}
          </p>
          <input
            type="text"
            value={reportName}
            onChange={(e) => setReportName(e.target.value)}
            placeholder={ANALYTICS.reportNamePlaceholder}
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
          />
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => setStep(1)}>{ANALYTICS.backLabel}</Button>
            <Button onClick={() => setStep(3)}>{ANALYTICS.nextLabel}</Button>
          </div>
        </Card>
      )}

      {step === 3 && (
        <Card className="p-4 space-y-4">
          <p className="font-semibold text-brand-900">{ANALYTICS.reportRunTitle}</p>
          <div className="flex flex-wrap gap-2">
            <Button disabled={running} onClick={() => runReport('json')}>{ANALYTICS.previewLabel}</Button>
            <Button disabled={running} onClick={() => runReport('csv')}>
              <Download className="w-4 h-4" /> CSV
            </Button>
            <Button variant="secondary" disabled={running} onClick={() => runReport('xlsx')}>XLSX</Button>
            <Button variant="secondary" disabled={running} onClick={saveReport}>{ANALYTICS.saveReportLabel}</Button>
          </div>
          {result && (
            <div className="overflow-auto max-h-64 rounded-xl bg-slate-50 p-3 text-xs">
              <p className="font-semibold mb-2">{result.row_count} rows</p>
              <table className="w-full text-left">
                <thead>
                  <tr>
                    {(result.columns || Object.keys(result.rows?.[0] || {})).map((h) => (
                      <th key={h} className="pr-3 pb-1">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(result.rows || []).slice(0, 20).map((row, i) => (
                    <tr key={i} className="border-t border-slate-200">
                      {(result.columns || Object.keys(row)).map((h) => (
                        <td key={h} className="pr-3 py-1">{String(row[h] ?? '')}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      <Card className="p-4 space-y-3">
        <p className="font-semibold text-brand-900">{ANALYTICS.savedReportsLabel}</p>
        {!savedReports.length ? (
          <p className="text-sm text-slate-500">{ANALYTICS.emptySavedReports}</p>
        ) : (
          savedReports.map((r) => (
            <div key={r.id} className="flex flex-wrap items-center justify-between gap-2 py-2 border-b border-slate-100">
              <button type="button" className="text-sm font-medium text-brand-700" onClick={() => loadSaved(r)}>
                {r.name}
              </button>
              <div className="flex gap-2">
                {r.shared_with_tenant && <Badge color="green">{ANALYTICS.sharedLabel}</Badge>}
                <Button variant="secondary" size="sm" onClick={() => shareSavedReport(r.id).then(loadMeta)}>
                  <Share2 className="w-3 h-3" />
                </Button>
                <Button variant="secondary" size="sm" onClick={() => deleteSavedReport(r.id).then(loadMeta)}>
                  <Trash2 className="w-3 h-3" />
                </Button>
              </div>
            </div>
          ))
        )}
      </Card>

      <Card className="p-4 space-y-3">
        <p className="font-semibold text-brand-900 flex items-center gap-2">
          <Calendar className="w-4 h-4" />
          {ANALYTICS.scheduledReportsLabel}
        </p>
        <div className="flex flex-wrap gap-2 items-end">
          <select
            value={scheduleForm.saved_report_id || ''}
            onChange={(e) => setScheduleForm((f) => ({ ...f, saved_report_id: Number(e.target.value) }))}
            className="rounded-lg border px-2 py-1.5 text-sm"
          >
            <option value="">{ANALYTICS.pickReportLabel}</option>
            {savedReports.map((r) => (
              <option key={r.id} value={r.id}>{r.name}</option>
            ))}
          </select>
          <select
            value={scheduleForm.schedule}
            onChange={(e) => setScheduleForm((f) => ({ ...f, schedule: e.target.value }))}
            className="rounded-lg border px-2 py-1.5 text-sm"
          >
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
          </select>
          <input
            type="text"
            placeholder={ANALYTICS.recipientsPlaceholder}
            value={scheduleForm.recipients}
            onChange={(e) => setScheduleForm((f) => ({ ...f, recipients: e.target.value }))}
            className="rounded-lg border px-2 py-1.5 text-sm flex-1 min-w-[200px]"
          />
          <Button
            size="sm"
            onClick={async () => {
              if (!scheduleForm.saved_report_id) return
              await createScheduledReport({
                saved_report_id: scheduleForm.saved_report_id,
                schedule: scheduleForm.schedule,
                recipients: scheduleForm.recipients.split(',').map((s) => s.trim()).filter(Boolean),
              })
              loadMeta()
            }}
          >
            {ANALYTICS.scheduleLabel}
          </Button>
        </div>
        {schedules.map((s) => (
          <div key={s.id} className="flex justify-between text-sm py-1">
            <span>Report #{s.saved_report_id} · {s.schedule}</span>
            <button type="button" className="text-red-600" onClick={() => deleteScheduledReport(s.id).then(loadMeta)}>
              Remove
            </button>
          </div>
        ))}
      </Card>
    </div>
  )
}
