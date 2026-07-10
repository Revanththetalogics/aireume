import { describe, it, expect } from 'vitest'
import {
  localDatetimeToParts,
  localDatetimeFromParts,
  localDatetimeToUtcIso,
  utcIsoToLocalDatetime,
  isLocalDatetimeInPast,
} from './datetimeUtils'

describe('localDatetimeToParts / localDatetimeFromParts', () => {
  it('parses morning 24h to 12h parts', () => {
    expect(localDatetimeToParts('2026-07-11T09:30')).toEqual({
      date: '2026-07-11',
      hour12: 9,
      minute: 30,
      meridiem: 'AM',
    })
  })

  it('parses afternoon 24h to 12h parts', () => {
    expect(localDatetimeToParts('2026-07-11T14:05')).toEqual({
      date: '2026-07-11',
      hour12: 2,
      minute: 5,
      meridiem: 'PM',
    })
  })

  it('handles noon and midnight', () => {
    expect(localDatetimeToParts('2026-07-11T12:00').meridiem).toBe('PM')
    expect(localDatetimeToParts('2026-07-11T00:00').hour12).toBe(12)
    expect(localDatetimeToParts('2026-07-11T00:00').meridiem).toBe('AM')
  })

  it('round-trips 12h parts to local datetime string', () => {
    const cases = [
      { date: '2026-07-11', hour12: 9, minute: 30, meridiem: 'AM', expected: '2026-07-11T09:30' },
      { date: '2026-07-11', hour12: 2, minute: 15, meridiem: 'PM', expected: '2026-07-11T14:15' },
      { date: '2026-07-11', hour12: 12, minute: 0, meridiem: 'PM', expected: '2026-07-11T12:00' },
      { date: '2026-07-11', hour12: 12, minute: 0, meridiem: 'AM', expected: '2026-07-11T00:00' },
    ]
    for (const c of cases) {
      expect(localDatetimeFromParts(c)).toBe(c.expected)
      expect(localDatetimeToParts(c.expected)).toMatchObject({
        date: c.date,
        hour12: c.hour12,
        minute: c.minute,
        meridiem: c.meridiem,
      })
    }
  })
})

describe('utc conversion', () => {
  it('converts local datetime to UTC ISO', () => {
    const iso = localDatetimeToUtcIso('2026-07-11T14:30')
    expect(iso).toBeTruthy()
    expect(new Date(iso).toISOString()).toBe(iso)
  })

  it('round-trips UTC ISO through local datetime', () => {
    const original = '2026-07-11T10:45:00.000Z'
    const local = utcIsoToLocalDatetime(original)
    const back = localDatetimeToUtcIso(local)
    expect(new Date(back).getTime()).toBe(new Date(original).getTime())
  })
})

describe('isLocalDatetimeInPast', () => {
  it('returns true for dates far in the past', () => {
    expect(isLocalDatetimeInPast('2020-01-01T10:00')).toBe(true)
  })

  it('returns false for empty value', () => {
    expect(isLocalDatetimeInPast('')).toBe(false)
  })
})
