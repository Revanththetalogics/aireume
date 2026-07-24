import { recordOnboardingEvent } from '../lib/api'

/** Fire-and-forget onboarding funnel event (backend persists for admin metrics). */
export function trackOnboardingEvent(event, properties = {}) {
  recordOnboardingEvent(event, properties).catch(() => {})
}
