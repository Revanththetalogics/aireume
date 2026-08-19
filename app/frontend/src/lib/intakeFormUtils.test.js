import { describe, it, expect } from 'vitest'
import {
  splitIntakeListInput,
  normalizeIntakeShape,
  normalizeTranscriptItems,
  formatIntakeStatus,
} from './intakeFormUtils'

describe('intakeFormUtils', () => {
  it('splits comma-separated list input into separate items', () => {
    expect(splitIntakeListInput('sourcing, screening, interviewing')).toEqual([
      'sourcing',
      'screening',
      'interviewing',
    ])
  })

  it('normalizes legacy string intake fields', () => {
    const out = normalizeIntakeShape({
      must_haves: 'Python, FastAPI, PostgreSQL',
    })
    expect(out.must_haves).toEqual(['Python', 'FastAPI', 'PostgreSQL'])
  })

  it('maps recruiter question fields for transcript UI', () => {
    const items = normalizeTranscriptItems([
      { question_text: 'Tell me about X', candidate_response: 'I built Y', category: 'technical' },
    ])
    expect(items[0].question).toBe('Tell me about X')
    expect(items[0].response).toBe('I built Y')
  })

  it('formats intake status labels', () => {
    expect(formatIntakeStatus('pending_hm')).toBe('Pending HM')
  })
})
