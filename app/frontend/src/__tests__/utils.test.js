import { describe, it, expect } from 'vitest'
import { formatDateTime } from '../lib/utils'

describe('formatDateTime', () => {
  it('returns empty string for falsy input', () => {
    expect(formatDateTime(null)).toBe('')
    expect(formatDateTime(undefined)).toBe('')
    expect(formatDateTime('')).toBe('')
  })

  it('formats a valid ISO date with date and time parts', () => {
    const out = formatDateTime('2026-07-07T13:45:00Z')
    expect(out).not.toBe('')
    // Contains a month abbreviation and a year
    expect(out).toMatch(/2026/)
    expect(out).toMatch(/Jul/)
  })

  it('does not throw for an invalid date', () => {
    expect(() => formatDateTime('not-a-date')).not.toThrow()
    expect(typeof formatDateTime('not-a-date')).toBe('string')
  })

  it('respects option overrides', () => {
    const out = formatDateTime('2026-07-07T13:45:00Z', { timeZoneName: undefined, hour: undefined, minute: undefined })
    expect(out).toMatch(/2026/)
  })
})
