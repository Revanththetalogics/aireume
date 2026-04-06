import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ResultCard from '../components/ResultCard'

const mockResult = {
  fit_score: 85,
  strengths: ['Strong Python skills', 'Leadership experience'],
  concerns: ['Limited cloud experience'],
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

  it('displays concerns', () => {
    render(<ResultCard result={mockResult} />)
    expect(screen.getByText('Limited cloud experience')).toBeInTheDocument()
  })

  it('displays concerns section heading', () => {
    render(<ResultCard result={mockResult} />)
    expect(screen.getByText('Concerns')).toBeInTheDocument()
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

  it('displays fit_summary banner when provided', () => {
    const resultWithSummary = {
      ...mockResult,
      fit_summary: 'Strong candidate with excellent technical skills and leadership experience.'
    }
    render(<ResultCard result={resultWithSummary} />)
    expect(screen.getByText('Executive Summary')).toBeInTheDocument()
    expect(screen.getByText('Strong candidate with excellent technical skills and leadership experience.')).toBeInTheDocument()
  })

  it('displays risk flags when provided', () => {
    const resultWithRiskFlags = {
      ...mockResult,
      risk_summary: {
        risk_flags: [
          { flag: 'Frequent job changes', detail: '3 jobs in 2 years', severity: 'medium' },
          { flag: 'Employment gap', detail: '6 months gap', severity: 'low' }
        ]
      }
    }
    render(<ResultCard result={resultWithRiskFlags} />)
    expect(screen.getByText('Risk Flags')).toBeInTheDocument()
    expect(screen.getByText('Frequent job changes')).toBeInTheDocument()
    expect(screen.getByText('Employment gap')).toBeInTheDocument()
  })

  it('displays seniority alignment when provided', () => {
    const resultWithSeniority = {
      ...mockResult,
      score_breakdown: {
        skill_match: 85,
        experience_match: 80,
        education: 75,
        timeline: 90
      },
      risk_summary: {
        seniority_alignment: 'Well-aligned for Senior Engineer role'
      }
    }
    render(<ResultCard result={resultWithSeniority} />)
    expect(screen.getByText('Seniority Alignment:')).toBeInTheDocument()
    expect(screen.getByText('Well-aligned for Senior Engineer role')).toBeInTheDocument()
  })

  it('displays skill depth counts when provided', () => {
    const resultWithSkillDepth = {
      ...mockResult,
      matched_skills: ['Python', 'React'],
      skill_depth: { 'Python': 8, 'React': 3 }
    }
    render(<ResultCard result={resultWithSkillDepth} />)
    expect(screen.getByText('(8x)')).toBeInTheDocument()
    expect(screen.getByText('(3x)')).toBeInTheDocument()
  })

  it('uses score_rationales when explainability is missing', () => {
    const resultWithRationales = {
      ...mockResult,
      score_rationales: {
        skill_rationale: 'Strong technical skills match',
        experience_rationale: 'Relevant industry experience',
        overall_rationale: 'Good overall fit'
      }
    }
    render(<ResultCard result={resultWithRationales} />)
    expect(screen.getByText('Score Rationales — Why this score?')).toBeInTheDocument()
    // Click to expand the collapsible section
    const button = screen.getByText('Score Rationales — Why this score?')
    fireEvent.click(button)
    expect(screen.getByText('Strong technical skills match')).toBeInTheDocument()
    expect(screen.getByText('Relevant industry experience')).toBeInTheDocument()
  })

  it('falls back to weaknesses when concerns is not provided', () => {
    const resultWithWeaknesses = {
      ...mockResult,
      concerns: undefined,
      weaknesses: ['Old weakness format']
    }
    render(<ResultCard result={resultWithWeaknesses} />)
    expect(screen.getByText('Old weakness format')).toBeInTheDocument()
  })
})
