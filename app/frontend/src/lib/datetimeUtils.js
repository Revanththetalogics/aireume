/**
 * Shared datetime utilities — Teams-style: store UTC, display in viewer timezone.
 */

export function getDisplayTimezone() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
  } catch {
    return 'UTC'
  }
}

const pad = (n) => String(n).padStart(2, '0')

/** Default 12-hour parts rounded to next 15 minutes (local). */
export function defaultScheduleParts(baseDate = new Date()) {
  const d = new Date(baseDate)
  d.setSeconds(0, 0)
  const remainder = d.getMinutes() % 15
  if (remainder !== 0) d.setMinutes(d.getMinutes() + (15 - remainder))
  return localDatetimeToParts(localDatetimeFromDate(d))
}

/**
 * Convert datetime-local value (browser local, 24h) to UTC ISO string for API storage.
 */
export function localDatetimeToUtcIso(localValue) {
  if (!localValue) return null
  try {
    const d = new Date(localValue)
    if (Number.isNaN(d.getTime())) return null
    return d.toISOString()
  } catch {
    return null
  }
}

/** Build datetime-local string from a Date in browser local time. */
export function localDatetimeFromDate(date) {
  if (!date || Number.isNaN(date.getTime())) return ''
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

/** Prefill datetime-local input from UTC ISO. */
export function utcIsoToLocalDatetime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return localDatetimeFromDate(d)
}

/** Parse datetime-local (24h) into 12-hour schedule parts. */
export function localDatetimeToParts(localValue) {
  if (!localValue) return defaultScheduleParts()
  const [datePart, timePart] = localValue.split('T')
  if (!datePart || !timePart) return defaultScheduleParts()
  const [hour24Raw, minuteRaw] = timePart.split(':')
  const hour24 = Number(hour24Raw)
  const minute = Number(minuteRaw)
  if (Number.isNaN(hour24) || Number.isNaN(minute)) return defaultScheduleParts()

  const snappedMinute = Math.min(55, Math.round(minute / 5) * 5)

  const meridiem = hour24 >= 12 ? 'PM' : 'AM'
  let hour12 = hour24 % 12
  if (hour12 === 0) hour12 = 12

  return { date: datePart, hour12, minute: snappedMinute, meridiem }
}

/** Build datetime-local string from 12-hour parts. */
export function localDatetimeFromParts({ date, hour12, minute, meridiem }) {
  if (!date) return ''
  const h12 = Number(hour12)
  const mins = Number(minute)
  if (Number.isNaN(h12) || Number.isNaN(mins)) return ''

  let hour24
  if (meridiem === 'AM') {
    hour24 = h12 === 12 ? 0 : h12
  } else {
    hour24 = h12 === 12 ? 12 : h12 + 12
  }

  return `${date}T${pad(hour24)}:${pad(mins)}`
}

export function utcIsoToLocalDatetimeParts(iso) {
  return localDatetimeToParts(utcIsoToLocalDatetime(iso))
}

export function formatSchedulePreview(localValue) {
  if (!localValue) return ''
  const utc = localDatetimeToUtcIso(localValue)
  if (!utc) return ''
  return new Date(utc).toLocaleString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    timeZoneName: 'short',
  })
}

export function formatSchedulePartsPreview(parts) {
  return formatSchedulePreview(localDatetimeFromParts(parts))
}

export function isLocalDatetimeInPast(localValue) {
  if (!localValue) return false
  const d = new Date(localValue)
  if (Number.isNaN(d.getTime())) return false
  return d.getTime() < Date.now() - 60_000
}

export function minScheduleDateString() {
  const d = new Date()
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

export const SCHEDULE_HOUR_OPTIONS = Array.from({ length: 12 }, (_, i) => i + 1)

export const SCHEDULE_MINUTE_OPTIONS = Array.from({ length: 12 }, (_, i) => i * 5)
