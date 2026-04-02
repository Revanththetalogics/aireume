import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ResultCard from '../components/ResultCard'

const mockResult = {
  fit_score: 85,
  strengths: ['Strong Python skills', 'Leadership experience'],
  weaknesses: ['Limited cloud experience'],
  education_analysis: 'Good educational background',
  risk_signals: [],
  final_recommendation: 'Shortlist'
}

describe('ResultCard', () => {
  it('renders the recommendation badge', () => {
    render(<ResultCard result={mockResult} />)
    expect(screen.getByText('Shortlist')).toBeInTheDocument()
  })

  it('displays strengths', () => {
    render(<ResultCard result={mockResult} />)
    expect(screen.getByText('Strong Python skills')).toBeInTheDocument()
  })

  it('displays weaknesses', () => {
    render(<ResultCard result={mockResult} />)
    expect(screen.getByText('Limited cloud experience')).toBeInTheDocument()
  })

  it('toggles education analysis on click', () => {
    render(<ResultCard result={mockResult} />)
    const button = screen.getByText('Education Analysis')
    fireEvent.click(button)
    expect(screen.getByText('Good educational background')).toBeInTheDocument()
  })

  it('shows correct colors for different recommendations', () => {
    const { rerender } = render(<ResultCard result={{ ...mockResult, final_recommendation: 'Reject' }} />)
    expect(screen.getByText('Reject')).toBeInTheDocument()

    rerender(<ResultCard result={{ ...mockResult, final_recommendation: 'Consider' }} />)
    expect(screen.getByText('Consider')).toBeInTheDocument()
  })
})
