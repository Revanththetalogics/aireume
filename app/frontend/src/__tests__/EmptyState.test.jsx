import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { FileText } from 'lucide-react'
import EmptyState from '../components/EmptyState'

const renderWithRouter = (ui) => render(<MemoryRouter>{ui}</MemoryRouter>)

describe('EmptyState', () => {
  it('renders title and description', () => {
    renderWithRouter(
      <EmptyState icon={FileText} title="No analyses yet" description="Analyze a resume to get started." />
    )
    expect(screen.getByText('No analyses yet')).toBeInTheDocument()
    expect(screen.getByText('Analyze a resume to get started.')).toBeInTheDocument()
  })

  it('renders a link CTA when actionHref is provided', () => {
    renderWithRouter(
      <EmptyState title="Empty" actionLabel="Analyze a resume" actionHref="/analyze" />
    )
    const link = screen.getByRole('link', { name: /analyze a resume/i })
    expect(link).toHaveAttribute('href', '/analyze')
  })

  it('fires onAction when the button CTA is clicked', () => {
    const onAction = vi.fn()
    renderWithRouter(
      <EmptyState title="Empty" actionLabel="Do it" onAction={onAction} />
    )
    fireEvent.click(screen.getByRole('button', { name: /do it/i }))
    expect(onAction).toHaveBeenCalledTimes(1)
  })

  it('does not render a CTA without a label', () => {
    renderWithRouter(<EmptyState title="Empty" />)
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})
