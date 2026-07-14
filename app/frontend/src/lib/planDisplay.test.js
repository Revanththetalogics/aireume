import { describe, it, expect } from 'vitest'
import { formatPlanPrice, isSalesLedPlan } from './planDisplay'

describe('planDisplay', () => {
  it('shows Contact Sales for enterprise', () => {
    const plan = { name: 'enterprise', price_monthly: 0, display_name: 'Enterprise' }
    expect(isSalesLedPlan(plan)).toBe(true)
    expect(formatPlanPrice(plan)).toBe('Contact Sales')
  })

  it('shows Free for starter', () => {
    const plan = { name: 'starter', price_monthly: 0 }
    expect(formatPlanPrice(plan)).toBe('Free')
  })

  it('shows monthly price for paid plans', () => {
    const plan = { name: 'growth', price_monthly: 4900 }
    expect(formatPlanPrice(plan)).toBe('$49/mo')
  })
})
