import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import AnalyticsHub, { VALID_SLICE_IDS } from '../components/patterns/AnalyticsHub'

vi.mock('../components/patterns/ScreeningTrendsCharts', () => ({
  default: () => null,
}))

vi.mock('../lib/api', () => ({
  getAnalyticsHub: vi.fn(() => Promise.resolve({
    generated_at: new Date().toISOString(),
    filter_options: { requisitions: [], recruiters: [] },
    attention: { stale_candidates: [], zero_pipeline_requisitions: [], pending_hm_review: 0 },
    slices: {
      screening: {
        kpis: { total_analyzed: 0, avg_fit_score: 0, recommendation_shortlist_rate: 0, pipeline_shortlist_rate: 0 },
        recommendation_distribution: {},
        score_distribution: {},
        top_skill_gaps: [],
        drill_down: [],
        drill_down_pagination: { total_count: 0, limit: 50, offset: 0, has_more: false },
        trends: { total_analyzed: 0 },
      },
    },
  })),
  getReportTemplates: vi.fn(() => Promise.resolve({ templates: [] })),
  runAnalyticsReport: vi.fn(),
  getBiExportManifest: vi.fn(() => Promise.resolve({ endpoints: { hub: '/api/analytics/hub' } })),
}))

describe('AnalyticsHub', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('exports valid slice ids including reports', () => {
    expect(VALID_SLICE_IDS.has('screening')).toBe(true)
    expect(VALID_SLICE_IDS.has('reports')).toBe(true)
    expect(VALID_SLICE_IDS.has('foo')).toBe(false)
  })

  it('renders screening slice by default', async () => {
    render(
      <MemoryRouter>
        <AnalyticsHub
          period="last_30_days"
          activeSlice="screening"
          permissions={{ role: 'admin', isAdmin: true }}
        />
      </MemoryRouter>,
    )
    expect(await screen.findByText(/Total analyzed/i)).toBeInTheDocument()
  })

  it('renders explore slices without reports tab when hidden', async () => {
    render(
      <MemoryRouter>
        <AnalyticsHub
          period="last_30_days"
          activeSlice="screening"
          permissions={{ role: 'admin', isAdmin: true }}
          hideReportsTab
        />
      </MemoryRouter>,
    )
    expect(await screen.findByText(/Total analyzed/i)).toBeInTheDocument()
    expect(screen.queryByText(/^Reports$/)).not.toBeInTheDocument()
  })
})
