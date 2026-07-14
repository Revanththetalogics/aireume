import { NavLink, Outlet, useSearchParams, useLocation } from 'react-router-dom'
import { BarChart3, RefreshCw } from 'lucide-react'
import TimeRangeControl from './TimeRangeControl'
import { ANALYTICS } from '../../lib/uxLabels'

const NAV_ITEMS = [
  { to: '/analytics', label: ANALYTICS.navOverview, end: true },
  { to: '/analytics/explore', label: ANALYTICS.navExplore },
  { to: '/analytics/reports', label: ANALYTICS.navReports },
  { to: '/analytics/docs', label: ANALYTICS.navDocs },
]

export default function AnalyticsShell({ onRefresh, refreshing = false, generatedAt = null, outletContext = {} }) {
  const [searchParams, setSearchParams] = useSearchParams()
  const location = useLocation()

  const period = searchParams.get('period') || 'last_30_days'
  const startDate = searchParams.get('start_date') || ''
  const endDate = searchParams.get('end_date') || ''
  const compare = searchParams.get('compare') === '1'

  const syncUrl = (patch) => {
    setSearchParams((prev) => {
      const params = new URLSearchParams(prev)
      Object.entries(patch).forEach(([key, value]) => {
        if (key === 'mode') return
        if (value === null || value === undefined || value === '') {
          params.delete(key)
        } else if (key === 'compare') {
          if (value) params.set('compare', '1')
          else params.delete('compare')
        } else {
          params.set(key, String(value))
        }
      })
      if (patch.mode === 'preset') {
        params.delete('start_date')
        params.delete('end_date')
      }
      return params
    }, { replace: true })
  }

  const handleTimeChange = (patch) => {
    if (patch.mode === 'custom' && !startDate && !endDate) {
      const today = new Date()
      const prior = new Date(today)
      prior.setDate(prior.getDate() - 30)
      syncUrl({
        start_date: prior.toISOString().slice(0, 10),
        end_date: today.toISOString().slice(0, 10),
        compare: patch.compare ?? compare,
      })
      return
    }
    syncUrl(patch)
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
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
          <TimeRangeControl
            period={period}
            startDate={startDate}
            endDate={endDate}
            compare={compare}
            onChange={handleTimeChange}
          />
          {onRefresh && (
            <button
              type="button"
              onClick={onRefresh}
              disabled={refreshing}
              className="p-2 rounded-lg border border-slate-200 dark:border-dark-border bg-white dark:bg-dark-card text-slate-500 hover:text-brand-600 hover:bg-brand-50 shadow-sm transition-colors disabled:opacity-50"
              aria-label={ANALYTICS.refreshLabel}
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            </button>
          )}
        </div>
      </div>

      <nav className="flex gap-1 overflow-x-auto border-b border-slate-200 dark:border-dark-border pb-px" aria-label={ANALYTICS.sectionNavLabel}>
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={{ pathname: item.to, search: location.search }}
            end={item.end}
            className={({ isActive }) => `
              px-4 py-2 text-sm font-semibold whitespace-nowrap rounded-t-lg transition-colors
              ${isActive
                ? 'text-brand-700 border-b-2 border-brand-600 bg-brand-50/50'
                : 'text-slate-500 hover:text-brand-600'}
            `}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <Outlet context={{
        ...outletContext,
        period,
        startDate,
        endDate,
        compare,
        useCustomRange: Boolean(startDate && endDate),
      }} />
    </div>
  )
}
