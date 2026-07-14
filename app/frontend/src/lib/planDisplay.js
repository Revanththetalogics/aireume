/** Plan pricing display helpers — sales-led tiers vs self-serve. */

export function isSalesLedPlan(plan) {
  if (!plan) return false
  return plan.name === 'enterprise'
}

export function formatPlanPrice(plan, { suffix = true } = {}) {
  if (!plan) return '—'
  if (isSalesLedPlan(plan)) return 'Contact Sales'
  if ((plan.price_monthly || 0) === 0) return 'Free'
  const amount = `$${(plan.price_monthly / 100).toFixed(0)}`
  return suffix ? `${amount}/mo` : amount
}

export const SALES_CONTACT_EMAIL = 'sales@thetalogics.com'
