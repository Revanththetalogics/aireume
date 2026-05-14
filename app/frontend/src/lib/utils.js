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
