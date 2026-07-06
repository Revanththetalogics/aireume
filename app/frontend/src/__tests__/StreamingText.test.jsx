import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import StreamingText from '../components/StreamingText'

describe('StreamingText accessibility', () => {
  it('hides the animated visual span from assistive tech', () => {
    const { container } = render(
      <StreamingText text="Hello world" isStreaming immediate />
    )
    const hidden = container.querySelector('[aria-hidden="true"]')
    expect(hidden).toBeInTheDocument()
  })

  it('does not announce partial text while streaming', () => {
    const { container } = render(
      <StreamingText text="Analyzing candidate strengths" isStreaming />
    )
    const live = container.querySelector('.sr-only[aria-live="polite"]')
    expect(live).toBeInTheDocument()
    // While streaming, the sr-only live region is empty (no chatty announcements)
    expect(live.textContent).toBe('')
  })

  it('announces the full text once streaming completes', () => {
    const { container } = render(
      <StreamingText text="Final narrative summary" isStreaming={false} immediate />
    )
    const live = container.querySelector('.sr-only[aria-live="polite"]')
    expect(live.textContent).toBe('Final narrative summary')
  })
})
