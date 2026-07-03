import { describe, it, expect } from 'vitest'
import { safeStr, stringToColor, computeDuration, computeGapMonths, formatDate, formatNumber, truncate, debounce, getInitials } from './utils'

describe('safeStr', () => {
  it('returns empty string for null', () => {
    expect(safeStr(null)).toBe('')
  })

  it('returns empty string for undefined', () => {
    expect(safeStr(undefined)).toBe('')
  })

  it('returns string for string input', () => {
    expect(safeStr('hello')).toBe('hello')
  })

  it('returns JSON string for object', () => {
    expect(safeStr({ a: 1 })).toBe('{"a":1}')
  })

  it('returns string for number', () => {
    expect(safeStr(123)).toBe('123')
  })
})

describe('stringToColor', () => {
  it('returns consistent color for same input', () => {
    expect(stringToColor('test')).toBe(stringToColor('test'))
  })

  it('returns different colors for different inputs', () => {
    expect(stringToColor('test1')).not.toBe(stringToColor('test2'))
  })

  it('returns valid color class', () => {
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
    expect(colors).toContain(stringToColor('any'))
  })
})

describe('computeDuration', () => {
  it('returns null for null start date', () => {
    expect(computeDuration(null, '2020-01-01')).toBeNull()
  })

  it('computes years and months', () => {
    expect(computeDuration('2020-01-01', '2022-06-01')).toBe('2y 5m')
  })

  it('computes only years', () => {
    expect(computeDuration('2020-01-01', '2022-01-01')).toBe('2y')
  })

  it('computes only months', () => {
    expect(computeDuration('2020-01-01', '2020-06-01')).toBe('5m')
  })

  it('handles present as end date', () => {
    const result = computeDuration('2020-01-01', 'present')
    expect(result).toMatch(/\d+y/)
  })
})

describe('computeGapMonths', () => {
  it('returns null for null inputs', () => {
    expect(computeGapMonths(null, '2020-01-01')).toBeNull()
    expect(computeGapMonths('2020-01-01', null)).toBeNull()
  })

  it('returns null for gaps less than 3 months', () => {
    expect(computeGapMonths('2020-01-01', '2020-03-01')).toBeNull()
  })

  it('returns months for gaps more than 3 months', () => {
    expect(computeGapMonths('2020-01-01', '2020-06-01')).toBe(5)
  })
})

describe('formatDate', () => {
  it('returns empty string for null', () => {
    expect(formatDate(null)).toBe('')
  })

  it('formats date correctly', () => {
    const result = formatDate('2020-06-15')
    expect(result).toContain('Jun')
    expect(result).toContain('2020')
  })
})

describe('formatNumber', () => {
  it('returns empty string for null', () => {
    expect(formatNumber(null)).toBe('')
  })

  it('formats number with thousands separator', () => {
    expect(formatNumber(1000)).toBe('1,000')
    expect(formatNumber(1000000)).toBe('1,000,000')
  })
})

describe('truncate', () => {
  it('returns original text if shorter than maxLength', () => {
    expect(truncate('hello', 10)).toBe('hello')
  })

  it('truncates text longer than maxLength', () => {
    expect(truncate('hello world', 5)).toBe('hello...')
  })
})

describe('debounce', () => {
  it('delays function execution', async () => {
    vi.useFakeTimers()
    const fn = vi.fn()
    const debouncedFn = debounce(fn, 100)

    debouncedFn()
    expect(fn).not.toHaveBeenCalled()

    vi.advanceTimersByTime(100)
    expect(fn).toHaveBeenCalledTimes(1)

    vi.useRealTimers()
  })
})

describe('getInitials', () => {
  it('returns ? for null', () => {
    expect(getInitials(null)).toBe('?')
  })

  it('returns first letter of email', () => {
    expect(getInitials('test@example.com')).toBe('T')
  })

  it('returns first letter of name', () => {
    expect(getInitials('john')).toBe('J')
  })
})
