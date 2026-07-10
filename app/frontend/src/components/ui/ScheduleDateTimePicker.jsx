import { useMemo } from 'react'
import { Calendar, Clock, Globe, AlertTriangle } from 'lucide-react'
import SegmentedControl from './SegmentedControl'
import {
  localDatetimeToParts,
  localDatetimeFromParts,
  formatSchedulePreview,
  isLocalDatetimeInPast,
  minScheduleDateString,
  getDisplayTimezone,
  SCHEDULE_HOUR_OPTIONS,
  SCHEDULE_MINUTE_OPTIONS,
} from '../../lib/datetimeUtils'

const selectClass = `
  w-full px-3 py-3 rounded-xl ring-1 ring-slate-200 dark:ring-white/10
  bg-white dark:bg-dark-card text-sm text-slate-800 dark:text-dark-text-primary
  outline-none focus:ring-2 focus:ring-brand-500 appearance-none cursor-pointer
`

/**
 * Custom 12-hour date + time picker with live preview.
 * Value/onChange use datetime-local string (browser local, 24h internally).
 */
export default function ScheduleDateTimePicker({
  value,
  onChange,
  required = false,
  allowClear = false,
  showPreview = true,
  className = '',
}) {
  const parts = useMemo(() => {
    if (!value && allowClear) {
      return { date: '', hour12: 9, minute: 0, meridiem: 'AM' }
    }
    return localDatetimeToParts(value)
  }, [value, allowClear])
  const inPast = value ? isLocalDatetimeInPast(value) : false
  const minDate = minScheduleDateString()

  function update(patch) {
    const merged = { ...parts, ...patch }
    if (!merged.date) merged.date = minDate
    const next = localDatetimeFromParts(merged)
    onChange(next)
  }

  function handleDateChange(date) {
    if (!date && allowClear) {
      onChange('')
      return
    }
    update({ date: date || parts.date })
  }

  return (
    <div className={`space-y-3 ${className}`}>
      <div>
        <label className="flex items-center gap-1.5 text-xs font-semibold text-slate-600 dark:text-dark-text-secondary mb-1.5">
          <Calendar className="w-3.5 h-3.5" />
          Date
        </label>
        <input
          type="date"
          value={parts.date}
          min={minDate}
          required={required}
          onChange={(e) => handleDateChange(e.target.value)}
          className={`${selectClass} [color-scheme:light] dark:[color-scheme:dark]`}
        />
      </div>

      <div>
        <label className="flex items-center gap-1.5 text-xs font-semibold text-slate-600 dark:text-dark-text-secondary mb-1.5">
          <Clock className="w-3.5 h-3.5" />
          Time (12-hour)
        </label>
        <div className="grid grid-cols-3 gap-2">
          <select
            aria-label="Hour"
            value={parts.hour12}
            onChange={(e) => update({ hour12: Number(e.target.value) })}
            className={selectClass}
          >
            {SCHEDULE_HOUR_OPTIONS.map((h) => (
              <option key={h} value={h}>{h}</option>
            ))}
          </select>

          <select
            aria-label="Minute"
            value={parts.minute}
            onChange={(e) => update({ minute: Number(e.target.value) })}
            className={selectClass}
          >
            {SCHEDULE_MINUTE_OPTIONS.map((m) => (
              <option key={m} value={m}>{String(m).padStart(2, '0')}</option>
            ))}
          </select>

          <SegmentedControl
            options={[
              { label: 'AM', value: 'AM' },
              { label: 'PM', value: 'PM' },
            ]}
            value={parts.meridiem}
            onChange={(meridiem) => update({ meridiem })}
            className="w-full flex"
          />
        </div>
      </div>

      {showPreview && value && (
        <p className="text-xs text-slate-500 flex items-start gap-1.5">
          <Globe className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          <span>
            {formatSchedulePreview(value)}
            <span className="text-slate-400"> · {getDisplayTimezone()}</span>
          </span>
        </p>
      )}

      {inPast && (
        <p className="text-xs text-amber-700 flex items-center gap-1.5 bg-amber-50 ring-1 ring-amber-200 rounded-lg px-3 py-2">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
          Choose a future date and time.
        </p>
      )}

      {allowClear && value && (
        <button
          type="button"
          onClick={() => onChange('')}
          className="text-xs font-semibold text-slate-500 hover:text-brand-700"
        >
          Clear schedule (call ASAP)
        </button>
      )}
    </div>
  )
}
