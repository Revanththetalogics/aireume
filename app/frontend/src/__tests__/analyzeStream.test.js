import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { analyzeResumeStream } from '../lib/api'

/**
 * Real-world scenario: the analysis SSE stream drops mid-flight (Wi-Fi loss,
 * proxy timeout). The client must surface a clear, retryable error rather than
 * a cryptic network failure — so the UI can offer a "Retry" affordance.
 */

function makeResponse(reader) {
  return {
    ok: true,
    status: 200,
    body: { getReader: () => reader },
  }
}

describe('analyzeResumeStream error handling', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
    // getCsrfToken reads document.cookie; jsdom provides it. No token is fine.
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('throws a retryable error when the connection drops mid-stream', async () => {
    const reader = {
      read: vi.fn().mockRejectedValueOnce(new TypeError('network error')),
    }
    fetch.mockResolvedValueOnce(makeResponse(reader))

    const file = new File(['résumé'], 'resume.txt', { type: 'text/plain' })
    await expect(analyzeResumeStream(file, 'a'.repeat(200)))
      .rejects.toMatchObject({ retryable: true })
  })

  it('throws a retryable error when the stream ends without a final result', async () => {
    const reader = {
      read: vi.fn().mockResolvedValueOnce({ done: true, value: undefined }),
    }
    fetch.mockResolvedValueOnce(makeResponse(reader))

    const file = new File(['résumé'], 'resume.txt', { type: 'text/plain' })
    await expect(analyzeResumeStream(file, 'a'.repeat(200)))
      .rejects.toMatchObject({ retryable: true })
  })

  it('propagates a server error detail on non-ok response', async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 402,
      json: async () => ({ detail: 'Usage limit reached' }),
    })

    const file = new File(['résumé'], 'resume.txt', { type: 'text/plain' })
    await expect(analyzeResumeStream(file, 'a'.repeat(200)))
      .rejects.toThrow(/usage limit reached/i)
  })
})
