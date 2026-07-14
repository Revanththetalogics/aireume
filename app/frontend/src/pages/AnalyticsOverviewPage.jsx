import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useOutletContext, useSearchParams } from 'react-router-dom'
import { AlertTriangle, Building2, Users } from 'lucide-react'
import { Card, Skeleton, Button } from '../components/ui'
import MetricInfo from '../components/patterns/MetricInfo'
import EmptyState from '../components/EmptyState'
import {
  getAnalyticsOverview,
  listAnalyticsViews,
  createAnalyticsView,
} from '../lib/api'
import usePermissions from '../hooks/usePermissions'
import { ANALYTICS } from '../lib/uxLabels'

const KPI_LABELS = {
  total_analyzed: 'Total analyzed',
  avg_fit_score: 'Avg fit score',
  pipeline_shortlist_rate: 'Pipeline shortlist rate',
  pending_hm_review: 'Pending HM review',
  ats_failure_count: 'ATS sync failures',
  interview_completion_rate: 'Interview completion',
  hm_advance_rate: 'HM advance rate',
  hm_reject_rate: 'HM reject rate',
}

function MiniTrend({ points }) {
  if (!points?.length) {
    return <p className="text-sm text-slate-500">{ANALYTICS.emptyTrend}</p>
  }
  const peak = Math.max(...points.map((p) => p.count || 0), 1)
  return (
    <div className="flex items-end gap-1 h-16">
      {points.map((p) => {
        const h = Math.max(4, Math.round(((p.count || 0) / peak) * 100))
        return (
          <div
            key={p.day || p.date}
            className="flex-1 bg-brand-400 rounded-t"
            style={{ height: `${h}%` }}
            title={`${p.day || p.date}: ${p.count}`}
          />
        )
      })}
    </div>
  )
}

export default function AnalyticsOverviewPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const permissions = usePermissions()
  const { registerRefresh, setGeneratedAt } = useOutletContext() || {}

  const sliceParam = searchParams.get('slice')
  useEffect(() => {
    if (sliceParam) {
      navigate(`/analytics/explore?${searchParams.toString()}`, { replace: true })
    }
  }, [sliceParam, searchParams, navigate])

  const period = searchParams.get('period') || 'last_30_days'
  const startDate = searchParams.get('start_date') || ''
  const endDate = searchParams.get('end_date') || ''
  const compare = searchParams.get('compare') === '1'
  const useCustomRange = Boolean(startDate && endDate)

  const [data, setData] = useState(null)
  const [views, setViews] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = { period, compare }
      if (useCustomRange) {
        params.start_date = startDate
        params.end_date = endDate
      }
      const [overview, viewsRes] = await Promise.all([
        getAnalyticsOverview(params),
        listAnalyticsViews().catch(() => ({ views: [] })),
      ])
      setData(overview)
      setViews(viewsRes.views || [])
      setGeneratedAt?.(overview.generated_at)
    } catch (err) {
      setData(null)
      setError(err?.response?.data?.detail || err.message || ANALYTICS.errorGeneric)
    } finally {
      setLoading(false)
    }
  }, [period, startDate, endDate, compare, useCustomRange, setGeneratedAt])

  useEffect(() => {
    registerRefresh?.(load)
  }, [load, registerRefresh])

  useEffect(() => {
    load()
  }, [load])

  const saveCurrentView = async () => {
    setSaving(true)
    try {
      await createAnalyticsView({
        name: `Overview ${new Date().toLocaleDateString()}`,
        view_type: 'overview',
        filters: {
          period,
          start_date: useCustomRange ? startDate : null,
          end_date: useCustomRange ? endDate : null,
          compare,
        },
      })
      const viewsRes = await listAnalyticsViews()
      setViews(viewsRes.views || [])
    } finally {
      setSaving(false)
    }
  }

  const applyView = (view) => {
    const f = view.filters || {}
    const params = new URLSearchParams(searchParams)
    if (f.period) params.set('period', f.period)
    if (f.start_date) params.set('start_date', f.start_date)
    else params.delete('start_date')
    if (f.end_date) params.set('end_date', f.end_date)
    else params.delete('end_date')
    if (f.compare) params.set('compare', '1')
    else params.delete('compare')
    navigate(`/analytics?${params.toString()}`)
  }

  if (loading) {
    return (
      <div className="grid sm:grid-cols-3 gap-3">
        {[1, 2, 3, 4, 5, 6].map((i) => <Skeleton key={i} className="h-28 rounded-2xl" />)}
      </div>
    )
  }

  if (error) {
    return (
      <EmptyState
        title={ANALYTICS.errorTitle}
        description={error}
        actionLabel={ANALYTICS.retryLabel}
        onAction={load}
      />
    )
  }

  const attention = data?.attention || {}
  const defaultSlice = data?.default_slice || 'screening'

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-slate-600 dark:text-dark-text-secondary">{ANALYTICS.overviewHint}</p>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" disabled={saving} onClick={saveCurrentView}>
            {ANALYTICS.saveViewLabel}
          </Button>
          <Button size="sm" onClick={() => navigate(`/analytics/explore?slice=${defaultSlice}&${searchParams.toString()}`)}>
            {ANALYTICS.exploreCta}
          </Button>
        </div>
      </div>

      {views.length > 0 && (
        <Card className="p-4">
          <p className="text-xs font-bold text-slate-500 uppercase mb-2">{ANALYTICS.savedViewsLabel}</p>
          <div className="flex flex-wrap gap-2">
            {views.map((v) => (
              <button
                key={v.id}
                type="button"
                onClick={() => applyView(v)}
                className="px-3 py-1.5 rounded-lg text-sm border border-slate-200 hover:border-brand-400 hover:text-brand-700"
              >
                {v.name}{v.is_default ? ' ★' : ''}
              </button>
            ))}
          </div>
        </Card>
      )}

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <Card
          hoverable
          className="p-4 cursor-pointer"
          onClick={() => navigate(`/analytics/explore?slice=hm&${searchParams.toString()}`)}
        >
          <div className="flex items-center gap-2 text-amber-600 mb-2">
            <Building2 className="w-4 h-4" />
            <MetricInfo metricKey="pending_hm_review" label={ANALYTICS.attentionHm} />
          </div>
          <p className="text-3xl font-bold text-brand-900">{attention.pending_hm_review || 0}</p>
          <p className="text-xs text-slate-500 mt-1">{ANALYTICS.attentionHmHint}</p>
        </Card>

        <Card
          hoverable
          className="p-4 cursor-pointer"
          onClick={() => navigate(`/analytics/explore?slice=funnel&${searchParams.toString()}`)}
        >
          <div className="flex items-center gap-2 text-orange-600 mb-2">
            <Users className="w-4 h-4" />
            <MetricInfo metricKey="stale_candidates" label={ANALYTICS.attentionStale} />
          </div>
          <p className="text-3xl font-bold text-brand-900">{(attention.stale_candidates || []).length}</p>
          <p className="text-xs text-slate-500 mt-1">{ANALYTICS.attentionStaleHint}</p>
        </Card>

        <Card
          hoverable
          className="p-4 cursor-pointer"
          onClick={() => navigate(`/analytics/explore?slice=leadership&${searchParams.toString()}`)}
        >
          <div className="flex items-center gap-2 text-red-600 mb-2">
            <AlertTriangle className="w-4 h-4" />
            <MetricInfo metricKey="zero_pipeline_requisitions" label={ANALYTICS.attentionEmptyReqs} />
          </div>
          <p className="text-3xl font-bold text-brand-900">{(attention.zero_pipeline_requisitions || []).length}</p>
          <p className="text-xs text-slate-500 mt-1">{ANALYTICS.attentionEmptyReqsHint}</p>
        </Card>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {(data?.role_kpis || []).map((kpi) => (
          <Card key={kpi.key} className="p-4">
            <p className="text-xs font-semibold text-slate-500 uppercase">
              <MetricInfo metricKey={kpi.key} label={KPI_LABELS[kpi.key] || kpi.key} />
            </p>
            <p className="text-2xl font-bold text-brand-900 mt-1 tabular-nums">
              {typeof kpi.value === 'number' && kpi.key.includes('rate')
                ? `${kpi.value}%`
                : kpi.value}
            </p>
          </Card>
        ))}
      </div>

      <Card className="p-4">
        <p className="text-sm font-semibold text-brand-900 mb-3">{ANALYTICS.miniTrendTitle}</p>
        <MiniTrend points={data?.mini_trend} />
      </Card>

      {!permissions.isAdmin && permissions.role === 'viewer' && (
        <p className="text-xs text-slate-500">{ANALYTICS.viewerScopeHint}</p>
      )}
    </div>
  )
}
