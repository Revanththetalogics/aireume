/**
 * Shared utility functions for the ARIA frontend application.
 */

/**
 * Coerce any value to a render-safe string.
 * Objects become JSON; null/undefined → ''
 */
export function safeStr(val) {
  if (val === null || val === undefined) return ''
  if (typeof val === 'object') return JSON.stringify(val)
  return String(val)
}

/**
 * Generate a deterministic color class from a string.
 * Returns one of 8 predefined color combinations.
 */
export function stringToColor(str) {
  let hash = 0
  for (let i = 0; i < str.length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash)
  const colors = [
    'bg-blue-100 text-blue-700',
    'bg-indigo-100 text-indigo-700',
    'bg-purple-100 text-purple-700',
    'bg-pink-100 text-pink-700',
    'bg-rose-100 text-rose-700',
    'bg-amber-100 text-amber-700',
    'bg-teal-100 text-teal-700',
    'bg-cyan-100 text-cyan-700'
  ]
  return colors[Math.abs(hash) % colors.length]
}

/**
 * Compute duration string from start/end dates.
 * Returns format like "2y 3m" or "6m"
 */
export function computeDuration(startDate, endDate) {
  if (!startDate) return null
  try {
    const start = new Date(startDate)
    if (isNaN(start.getTime())) return null
    const isPresent = !endDate || endDate.toLowerCase() === 'present'
    const end = isPresent ? new Date() : new Date(endDate)
    if (!isPresent && isNaN(end.getTime())) return null
    let months = (end.getFullYear() - start.getFullYear()) * 12 + (end.getMonth() - start.getMonth())
    if (months < 0) return null
    const y = Math.floor(months / 12), m = months % 12
    if (y > 0 && m > 0) return `${y}y ${m}m`
    if (y > 0) return `${y}y`
    return `${months}m`
  } catch { return null }
}

/**
 * Compute gap months between two date strings.
 * Returns null if gap is less than 3 months.
 */
export function computeGapMonths(prevEnd, nextStart) {
  if (!prevEnd || !nextStart) return null
  try {
    const end = new Date(prevEnd), start = new Date(nextStart)
    if (isNaN(end.getTime()) || isNaN(start.getTime())) return null
    const months = (start.getFullYear() - end.getFullYear()) * 12 + (start.getMonth() - end.getMonth())
    return months > 3 ? months : null
  } catch { return null }
}

/**
 * Format date to locale string.
 */
export function formatDate(date, options = {}) {
  if (!date) return ''
  try {
    return new Date(date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      ...options
    })
  } catch { return '' }
}

/**
 * Format a date+time including the viewer's timezone abbreviation, e.g.
 * "Jul 7, 2026, 12:30 PM PDT". Use this for schedules, audit logs, and history
 * timestamps where the exact time (and zone) matters.
 */
export function formatDateTime(date, options = {}) {
  if (!date) return ''
  try {
    return new Date(date).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      timeZoneName: 'short',
      ...options,
    })
  } catch { return '' }
}

/**
 * Format number with thousands separator.
 */
export function formatNumber(num) {
  if (num === null || num === undefined) return ''
  return Number(num).toLocaleString('en-US')
}

/**
 * Truncate text to specified length with ellipsis.
 */
export function truncate(text, maxLength = 100) {
  if (!text || text.length <= maxLength) return text
  return text.slice(0, maxLength).trim() + '...'
}

/**
 * Debounce function execution.
 */
export function debounce(fn, delay = 300) {
  let timeoutId
  return (...args) => {
    clearTimeout(timeoutId)
    timeoutId = setTimeout(() => fn(...args), delay)
  }
}

/**
 * Generate initials from email or name.
 */
export function getInitials(emailOrName) {
  if (!emailOrName) return '?'
  const str = emailOrName.includes('@') ? emailOrName.split('@')[0] : emailOrName
  return str.charAt(0).toUpperCase()
}
