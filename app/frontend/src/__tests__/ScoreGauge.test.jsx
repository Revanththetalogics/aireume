import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ScoreGauge from '../components/ScoreGauge'

describe('ScoreGauge', () => {
  it('renders the correct score', () => {
    render(<ScoreGauge score={75} />)
    expect(screen.getByText('75')).toBeInTheDocument()
  })

  it('shows "Strong Fit" for score >= 70', () => {
    render(<ScoreGauge score={75} />)
    expect(screen.getByText('Strong Fit')).toBeInTheDocument()
  })

  it('shows "Moderate Fit" for score 40-69', () => {
    render(<ScoreGauge score={55} />)
    expect(screen.getByText('Moderate Fit')).toBeInTheDocument()
  })

  it('shows "Low Fit" for score < 40', () => {
    render(<ScoreGauge score={30} />)
    expect(screen.getByText('Low Fit')).toBeInTheDocument()
  })
})
