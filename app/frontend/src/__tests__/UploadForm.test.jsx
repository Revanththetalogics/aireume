import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import UploadForm from '../components/UploadForm'

describe('UploadForm', () => {
  const defaultProps = {
    onFileSelect: vi.fn(),
    jobDescription: '',
    onJobDescriptionChange: vi.fn(),
    onSubmit: vi.fn(),
    isLoading: false,
    selectedFile: null,
    error: null
  }

  it('renders upload area', () => {
    render(<UploadForm {...defaultProps} />)
    expect(screen.getByText(/drag & drop your resume here/i)).toBeInTheDocument()
  })

  it('renders job description textarea', () => {
    render(<UploadForm {...defaultProps} />)
    expect(screen.getByPlaceholderText(/paste the job description here/i)).toBeInTheDocument()
  })

  it('disables submit when no file selected', () => {
    render(<UploadForm {...defaultProps} />)
    const button = screen.getByRole('button', { name: /analyze resume/i })
    expect(button).toBeDisabled()
  })

  it('shows loading state', () => {
    render(<UploadForm {...defaultProps} isLoading={true} />)
    expect(screen.getByText(/analyzing/i)).toBeInTheDocument()
  })

  it('displays error message', () => {
    render(<UploadForm {...defaultProps} error="Test error message" />)
    expect(screen.getByText('Test error message')).toBeInTheDocument()
  })

  it('disables submit when skills not confirmed', () => {
    const onSubmit = vi.fn()
    const mockFile = new File(['test'], 'resume.pdf', { type: 'application/pdf' })

    render(
      <UploadForm
        {...defaultProps}
        selectedFile={mockFile}
        jobDescription="Test job description with enough words to be valid for parsing"
        onSubmit={onSubmit}
      />
    )

    const button = screen.getByRole('button', { name: /analyze resume/i })
    // Button should be disabled because skills haven't been confirmed yet
    expect(button).toBeDisabled()
    fireEvent.click(button)
    expect(onSubmit).not.toHaveBeenCalled()
  })
})
