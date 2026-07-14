import { useMemo } from 'react'
import { ANALYTICS } from '../../lib/uxLabels'

const PRESETS = [
  { value: 'last_7_days', label: 'Last 7 days' },
  { value: 'last_30_days', label: 'Last 30 days' },
  { value: 'last_90_days', label: 'Last 90 days' },
]

function formatRangeLabel(period, startDate, endDate) {
  if (startDate && endDate) {
    const start = new Date(startDate)
    const end = new Date(endDate)
    if (!Number.isNaN(start.getTime()) && !Number.isNaN(end.getTime())) {
      return `${start.toLocaleDateString()} – ${end.toLocaleDateString()}`
    }
    return ANALYTICS.customRangeLabel
  }
  const preset = PRESETS.find((p) => p.value === period)
  return preset?.label || period
}

export default function TimeRangeControl({
  period = 'last_30_days',
  startDate = '',
  endDate = '',
  compare = false,
  onChange,
  className = '',
}) {
  const mode = startDate && endDate ? 'custom' : 'preset'
  const rangeLabel = useMemo(
    () => formatRangeLabel(period, startDate, endDate),
    [period, startDate, endDate],
  )

  const emit = (patch) => onChange?.(patch)

  return (
    <div className={`flex flex-wrap items-center gap-2 ${className}`}>
      <div className="flex rounded-lg border border-slate-200 dark:border-dark-border overflow-hidden bg-white dark:bg-dark-card shadow-sm">
        <button
          type="button"
          onClick={() => emit({ mode: 'preset', start_date: null, end_date: null })}
          className={`px-3 py-2 text-sm font-medium ${mode === 'preset' ? 'bg-brand-50 text-brand-700' : 'text-slate-600'}`}
        >
          {ANALYTICS.presetLabel}
        </button>
        <button
          type="button"
          onClick={() => emit({ mode: 'custom' })}
          className={`px-3 py-2 text-sm font-medium border-l border-slate-200 dark:border-dark-border ${mode === 'custom' ? 'bg-brand-50 text-brand-700' : 'text-slate-600'}`}
        >
          {ANALYTICS.customRangeLabel}
        </button>
      </div>

      {mode === 'preset' ? (
        <select
          value={period}
          onChange={(e) => emit({ period: e.target.value, start_date: null, end_date: null })}
          className="rounded-lg border border-slate-200 dark:border-dark-border bg-white dark:bg-dark-card px-3 py-2 text-sm font-medium text-slate-700 dark:text-dark-text shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          aria-label={ANALYTICS.periodLabel}
        >
          {PRESETS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      ) : (
        <>
          <input
            type="date"
            value={startDate}
            onChange={(e) => emit({ start_date: e.target.value })}
            className="rounded-lg border border-slate-200 dark:border-dark-border bg-white dark:bg-dark-card px-2 py-2 text-sm"
            aria-label={ANALYTICS.startDateLabel}
          />
          <span className="text-slate-400 text-sm">–</span>
          <input
            type="date"
            value={endDate}
            onChange={(e) => emit({ end_date: e.target.value })}
            className="rounded-lg border border-slate-200 dark:border-dark-border bg-white dark:bg-dark-card px-2 py-2 text-sm"
            aria-label={ANALYTICS.endDateLabel}
          />
        </>
      )}

      <label className="flex items-center gap-1.5 text-sm text-slate-600 dark:text-dark-text-secondary cursor-pointer">
        <input
          type="checkbox"
          checked={compare}
          onChange={(e) => emit({ compare: e.target.checked })}
        />
        {ANALYTICS.compareLabel}
      </label>

      <span className="text-xs text-slate-500 dark:text-dark-text-secondary px-2 py-1 rounded-md bg-slate-50 dark:bg-dark-card">
        {rangeLabel}
        {compare ? ` · ${ANALYTICS.compareActiveHint}` : ''}
      </span>
    </div>
  )
}
