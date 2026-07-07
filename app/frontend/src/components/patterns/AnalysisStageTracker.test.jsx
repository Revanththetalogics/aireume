import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import AnalysisStageTracker, { StreamStageTracker } from './AnalysisStageTracker'

describe('AnalysisStageTracker', () => {
  it('renders enrichment phases for a processing result', () => {
    render(
      <AnalysisStageTracker
        result={{
          narrative_status: 'processing',
          interview_kit_status: 'pending',
          voice_strategy_status: 'pending',
        }}
      />
    )
    expect(screen.getByText(/AI enrichment/i)).toBeInTheDocument()
    expect(screen.getByText(/AI insights/i)).toBeInTheDocument()
  })

  it('renders stream stages for single-file analyze', () => {
    render(<StreamStageTracker activeStage="scoring" />)
    expect(screen.getByText(/Parsing resume/i)).toBeInTheDocument()
    expect(screen.getByText(/Scoring fit/i)).toBeInTheDocument()
  })
})
