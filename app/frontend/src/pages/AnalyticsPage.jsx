import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { BarChart3, RefreshCw } from 'lucide-react'
import { getSkillTrends, computeSkillTrends } from '../lib/api'
import AnalyticsHub, { VALID_SLICE_IDS } from '../components/patterns/AnalyticsHub'
import usePermissions from '../hooks/usePermissions'
import { ANALYTICS } from '../lib/uxLabels'

const PERIOD_OPTIONS = [
  { value: 'last_7_days', label: 'Last 7 days' },
  { value: 'last_30_days', label: 'Last 30 days' },
  { value: 'last_90_days', label: 'Last 90 days' },
]

function parseSlice(raw) {
  if (!raw || !VALID_SLICE_IDS.has(raw)) return 'screening'
  return raw
}

export default function AnalyticsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const permissions = usePermissions()
  const hubRef = useRef(null)

  const hubSlice = parseSlice(searchParams.get('slice'))
  const [activeSlice, setActiveSlice] = useState(hubSlice)
  const [period, setPeriod] = useState(searchParams.get('period') || 'last_30_days')
  const [startDate, setStartDate] = useState(searchParams.get('start_date') || '')
  const [endDate, setEndDate] = useState(searchParams.get('end_date') || '')
  const [compare, setCompare] = useState(searchParams.get('compare') === '1')
  const [requisitionId, setRequisitionId] = useState(
    searchParams.get('requisition_id') ? Number(searchParams.get('requisition_id')) : null,
  )
  const [recruiterId, setRecruiterId] = useState(
    searchParams.get('recruiter_id') ? Number(searchParams.get('recruiter_id')) : null,
  )
  const [generatedAt, setGeneratedAt] = useState(null)
  const [refreshing, setRefreshing] = useState(false)

  const [trendData, setTrendData] = useState(null)
  const [trendLoading, setTrendLoading] = useState(false)
  const [trendRoleCategory, setTrendRoleCategory] = useState(null)
  const [computing, setComputing] = useState(false)

  const useCustomRange = Boolean(startDate && endDate)

  useEffect(() => {
    setActiveSlice(parseSlice(searchParams.get('slice')))
    setPeriod(searchParams.get('period') || 'last_30_days')
    setStartDate(searchParams.get('start_date') || '')
    setEndDate(searchParams.get('end_date') || '')
    setCompare(searchParams.get('compare') === '1')
    setRequisitionId(searchParams.get('requisition_id') ? Number(searchParams.get('requisition_id')) : null)
    setRecruiterId(searchParams.get('recruiter_id') ? Number(searchParams.get('recruiter_id')) : null)
  }, [searchParams])

  const syncUrl = useCallback((patch) => {
    setSearchParams((prev) => {
      const params = new URLSearchParams(prev)
      Object.entries(patch).forEach(([key, value]) => {
        if (value === null || value === undefined || value === '' || (key === 'slice' && value === 'screening')) {
          params.delete(key)
        } else if (key === 'compare') {
          if (value) params.set('compare', '1')
          else params.delete('compare')
        } else {
          params.set(key, String(value))
        }
      })
      return params
    }, { replace: true })
  }, [setSearchParams])

  const handleSliceChange = (nextSlice) => {
    setActiveSlice(nextSlice)
    syncUrl({ slice: nextSlice })
  }

  const handlePeriodChange = (nextPeriod) => {
    setPeriod(nextPeriod)
    setStartDate('')
    setEndDate('')
    syncUrl({ period: nextPeriod, start_date: null, end_date: null })
  }

  const handleFilterChange = ({ requisitionId: reqId, recruiterId: recId }) => {
    setRequisitionId(reqId)
    setRecruiterId(recId)
    syncUrl({
      requisition_id: reqId,
      recruiter_id: recId,
    })
  }

  const fetchTrends = useCallback(async () => {
    setTrendLoading(true)
    try {
      const params = { months: 6 }
      if (trendRoleCategory) params.role_category = trendRoleCategory
      const result = await getSkillTrends(params)
      setTrendData(result)
    } catch {
      setTrendData(null)
    } finally {
      setTrendLoading(false)
    }
  }, [trendRoleCategory])

  useEffect(() => {
    if (activeSlice === 'screening') fetchTrends()
  }, [activeSlice, fetchTrends])

  const handleComputeSnapshots = async () => {
    if (!permissions.isAdmin) return
    setComputing(true)
    try {
      await computeSkillTrends()
      await fetchTrends()
    } finally {
      setComputing(false)
    }
  }

  const handleRefreshAll = async () => {
    setRefreshing(true)
    try {
      await Promise.all([
        hubRef.current?.reload?.(),
        activeSlice === 'screening' ? fetchTrends() : Promise.resolve(),
      ])
    } finally {
      setRefreshing(false)
    }
  }

  const hubQuery = useMemo(() => ({
    period: useCustomRange ? period : period,
    start_date: useCustomRange ? startDate : undefined,
    end_date: useCustomRange ? endDate : undefined,
    requisition_id: requisitionId,
    recruiter_id: recruiterId,
    compare,
  }), [period, startDate, endDate, useCustomRange, requisitionId, recruiterId, compare])

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand-50 flex items-center justify-center">
              <BarChart3 className="w-5 h-5 text-brand-600" />
            </div>
            <h1 className="text-2xl font-extrabold text-slate-900 dark:text-dark-text tracking-tight">
              {ANALYTICS.pageTitle}
            </h1>
          </div>
          <p className="text-sm text-slate-500 dark:text-dark-text-secondary mt-2 max-w-2xl">
            {ANALYTICS.pageSubtitle}
          </p>
          {generatedAt && (
            <p className="text-xs text-slate-400 mt-1">
              {ANALYTICS.lastUpdated}: {new Date(generatedAt).toLocaleString()}
            </p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={period}
            onChange={(e) => handlePeriodChange(e.target.value)}
            className="rounded-lg border border-slate-200 dark:border-dark-border bg-white dark:bg-dark-card px-3 py-2 text-sm font-medium text-slate-700 dark:text-dark-text shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            aria-label={ANALYTICS.periodLabel}
            disabled={useCustomRange}
          >
            {PERIOD_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          <input
            type="date"
            value={startDate}
            onChange={(e) => {
              setStartDate(e.target.value)
              syncUrl({ start_date: e.target.value || null })
            }}
            className="rounded-lg border border-slate-200 dark:border-dark-border bg-white dark:bg-dark-card px-2 py-2 text-sm"
            aria-label={ANALYTICS.startDateLabel}
          />
          <input
            type="date"
            value={endDate}
            onChange={(e) => {
              setEndDate(e.target.value)
              syncUrl({ end_date: e.target.value || null })
            }}
            className="rounded-lg border border-slate-200 dark:border-dark-border bg-white dark:bg-dark-card px-2 py-2 text-sm"
            aria-label={ANALYTICS.endDateLabel}
          />
          <label className="flex items-center gap-1.5 text-sm text-slate-600 dark:text-dark-text-secondary cursor-pointer">
            <input
              type="checkbox"
              checked={compare}
              onChange={(e) => {
                setCompare(e.target.checked)
                syncUrl({ compare: e.target.checked })
              }}
            />
            {ANALYTICS.compareLabel}
          </label>
          <button
            type="button"
            onClick={handleRefreshAll}
            disabled={refreshing}
            className="p-2 rounded-lg border border-slate-200 dark:border-dark-border bg-white dark:bg-dark-card text-slate-500 hover:text-brand-600 hover:bg-brand-50 shadow-sm transition-colors disabled:opacity-50"
            aria-label={ANALYTICS.refreshLabel}
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <AnalyticsHub
        ref={hubRef}
        period={period}
        startDate={useCustomRange ? startDate : null}
        endDate={useCustomRange ? endDate : null}
        compare={compare}
        requisitionId={requisitionId}
        recruiterId={recruiterId}
        initialSlice={hubSlice}
        activeSlice={activeSlice}
        onSliceChange={handleSliceChange}
        onFilterChange={handleFilterChange}
        onGeneratedAt={setGeneratedAt}
        permissions={permissions}
        trendData={trendData}
        trendLoading={trendLoading}
        trendRoleCategory={trendRoleCategory}
        onTrendRoleCategoryChange={setTrendRoleCategory}
        onComputeSnapshots={handleComputeSnapshots}
      />
    </div>
  )
}
