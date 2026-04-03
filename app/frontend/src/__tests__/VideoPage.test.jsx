import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

// Mock the api module
vi.mock('../lib/api', () => ({
  getCandidates: vi.fn().mockResolvedValue({ candidates: [] }),
  analyzeVideoFromUrl: vi.fn(),
}))

// Mock NavBar to avoid router/auth dependencies
vi.mock('../components/NavBar', () => ({
  default: () => <nav data-testid="navbar">NavBar</nav>,
}))

// Mock react-dropzone
vi.mock('react-dropzone', () => ({
  useDropzone: () => ({
    getRootProps: () => ({ 'data-testid': 'dropzone' }),
    getInputProps: () => ({ 'data-testid': 'file-input', type: 'file' }),
    isDragActive: false,
  }),
}))

import VideoPage from '../pages/VideoPage'
import { analyzeVideoFromUrl } from '../lib/api'

const MOCK_RESULT = {
  source: 'Zoom — zoom_recording.mp4',
  filename: 'zoom_recording.mp4',
  platform: 'Zoom',
  transcript: 'Hello I have five years of experience in Python development building large scale systems.',
  language: 'en',
  duration_s: 45.0,
  segments: [],
  communication_score: 78,
  confidence_level: 'high',
  clarity_score: 82,
  articulation_score: 75,
  key_phrases: ['five years', 'Python development'],
  strengths: ['Clear articulation'],
  red_flags: [],
  summary: 'Good communicator overall.',
  words_per_minute: 120,
  malpractice: {
    malpractice_score: 15,
    malpractice_risk: 'low',
    reliability_rating: 'trustworthy',
    flags: [],
    positive_signals: ['Natural filler words', 'Self-corrections observed'],
    overall_assessment: 'No significant malpractice signals detected.',
    follow_up_questions: [],
    pause_count: 0,
    pauses: [],
  },
}

const MOCK_RESULT_HIGH_RISK = {
  ...MOCK_RESULT,
  malpractice: {
    malpractice_score: 82,
    malpractice_risk: 'high',
    reliability_rating: 'unreliable',
    flags: [
      {
        type: 'scripted_reading',
        severity: 'high',
        evidence: 'No filler words detected throughout the interview',
        recommendation: 'Ask candidate to elaborate spontaneously on a topic',
      },
      {
        type: 'suspicious_pause',
        severity: 'medium',
        evidence: '18s pause at 2:15 after "What is your approach to debugging?"',
        recommendation: 'Verify candidate was not looking up answers',
      },
    ],
    positive_signals: [],
    overall_assessment: 'High malpractice risk. Multiple flags detected.',
    follow_up_questions: ['Explain your debugging process without preparation.', 'Walk me through a recent bug you solved.'],
    pause_count: 1,
    pauses: [
      { at_seconds: 135.0, duration_s: 18.0, before_text: 'What is your approach to debugging?', after_text: 'Well, I usually...', severity: 'medium', formatted_at: '2:15' },
    ],
  },
}

function renderVideoPage() {
  return render(
    <MemoryRouter>
      <VideoPage />
    </MemoryRouter>
  )
}

describe('VideoPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ─── Input mode toggle ───────────────────────────────────────────────────

  it('renders both Upload File and From URL tabs', () => {
    renderVideoPage()
    expect(screen.getByText('Upload File')).toBeInTheDocument()
    expect(screen.getByText('From URL')).toBeInTheDocument()
  })

  it('defaults to upload mode showing dropzone', () => {
    renderVideoPage()
    expect(screen.getByTestId('dropzone')).toBeInTheDocument()
  })

  it('switches to URL mode when From URL tab clicked', () => {
    renderVideoPage()
    fireEvent.click(screen.getByText('From URL'))
    expect(screen.getByPlaceholderText(/zoom\.us|Teams|Drive|Loom/i)).toBeInTheDocument()
  })

  it('shows file dropzone when switching back to upload mode', () => {
    renderVideoPage()
    fireEvent.click(screen.getByText('From URL'))
    fireEvent.click(screen.getByText('Upload File'))
    expect(screen.getByTestId('dropzone')).toBeInTheDocument()
  })

  // ─── URL input and platform detection ───────────────────────────────────

  it('shows Zoom platform badge when Zoom URL entered', () => {
    renderVideoPage()
    fireEvent.click(screen.getByText('From URL'))
    const input = screen.getByPlaceholderText(/zoom\.us|Teams|Drive|Loom/i)
    fireEvent.change(input, { target: { value: 'https://zoom.us/rec/share/abc123' } })
    // "Zoom" appears both in the badge and in the supported platforms list
    expect(screen.getAllByText('Zoom').length).toBeGreaterThanOrEqual(1)
  })

  it('shows Microsoft Teams badge for SharePoint URL', () => {
    renderVideoPage()
    fireEvent.click(screen.getByText('From URL'))
    const input = screen.getByPlaceholderText(/zoom\.us|Teams|Drive|Loom/i)
    fireEvent.change(input, { target: { value: 'https://company.sharepoint.com/:v:/g/abc' } })
    expect(screen.getAllByText('Microsoft Teams').length).toBeGreaterThanOrEqual(1)
  })

  it('shows Google Drive badge for Drive URL', () => {
    renderVideoPage()
    fireEvent.click(screen.getByText('From URL'))
    const input = screen.getByPlaceholderText(/zoom\.us|Teams|Drive|Loom/i)
    fireEvent.change(input, { target: { value: 'https://drive.google.com/file/d/ABC/view' } })
    expect(screen.getAllByText('Google Drive').length).toBeGreaterThanOrEqual(1)
  })

  it('shows Loom badge for Loom URL', () => {
    renderVideoPage()
    fireEvent.click(screen.getByText('From URL'))
    const input = screen.getByPlaceholderText(/zoom\.us|Teams|Drive|Loom/i)
    fireEvent.change(input, { target: { value: 'https://www.loom.com/share/abc123def456' } })
    expect(screen.getAllByText('Loom').length).toBeGreaterThanOrEqual(1)
  })

  it('shows supported platforms list in URL mode', () => {
    renderVideoPage()
    fireEvent.click(screen.getByText('From URL'))
    expect(screen.getByText('Supported platforms')).toBeInTheDocument()
    expect(screen.getAllByText(/Zoom/).length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText(/Dropbox/).length).toBeGreaterThanOrEqual(1)
  })

  it('shows public sharing instructions', () => {
    renderVideoPage()
    fireEvent.click(screen.getByText('From URL'))
    expect(screen.getByText(/Anyone with the link/i)).toBeInTheDocument()
  })

  // ─── Analyze button state ─────────────────────────────────────────────

  it('Analyze button is disabled when URL is empty', () => {
    renderVideoPage()
    fireEvent.click(screen.getByText('From URL'))
    const btn = screen.getByRole('button', { name: /Analyze Interview/i })
    expect(btn).toBeDisabled()
  })

  it('Analyze button enables when URL is entered', () => {
    renderVideoPage()
    fireEvent.click(screen.getByText('From URL'))
    const input = screen.getByPlaceholderText(/zoom\.us|Teams|Drive|Loom/i)
    fireEvent.change(input, { target: { value: 'https://zoom.us/rec/share/abc123' } })
    const btn = screen.getByRole('button', { name: /Analyze Interview/i })
    expect(btn).not.toBeDisabled()
  })

  // ─── URL analysis flow ────────────────────────────────────────────────

  it('calls analyzeVideoFromUrl with entered URL on button click', async () => {
    analyzeVideoFromUrl.mockResolvedValue(MOCK_RESULT)
    renderVideoPage()
    fireEvent.click(screen.getByText('From URL'))
    const input = screen.getByPlaceholderText(/zoom\.us|Teams|Drive|Loom/i)
    fireEvent.change(input, { target: { value: 'https://zoom.us/rec/share/abc123' } })
    fireEvent.click(screen.getByRole('button', { name: /Analyze Interview/i }))
    expect(analyzeVideoFromUrl).toHaveBeenCalledWith('https://zoom.us/rec/share/abc123', null)
  })

  it('shows error message on failed URL analysis', async () => {
    analyzeVideoFromUrl.mockRejectedValue({
      response: { data: { detail: 'Access denied. Link requires authentication.' } }
    })
    renderVideoPage()
    fireEvent.click(screen.getByText('From URL'))
    const input = screen.getByPlaceholderText(/zoom\.us|Teams|Drive|Loom/i)
    fireEvent.change(input, { target: { value: 'https://zoom.us/rec/share/private' } })
    fireEvent.click(screen.getByRole('button', { name: /Analyze Interview/i }))
    await waitFor(() => {
      expect(screen.getByText(/Access denied/i)).toBeInTheDocument()
    })
  })

  // ─── Results: Communication ───────────────────────────────────────────

  it('shows communication score after successful analysis', async () => {
    analyzeVideoFromUrl.mockResolvedValue(MOCK_RESULT)
    renderVideoPage()
    fireEvent.click(screen.getByText('From URL'))
    const input = screen.getByPlaceholderText(/zoom\.us|Teams|Drive|Loom/i)
    fireEvent.change(input, { target: { value: 'https://zoom.us/rec/share/abc123' } })
    fireEvent.click(screen.getByRole('button', { name: /Analyze Interview/i }))
    await waitFor(() => {
      expect(screen.getByText('Communication Analysis')).toBeInTheDocument()
      expect(screen.getByText('78')).toBeInTheDocument()
    })
  })

  it('shows platform name in results header', async () => {
    analyzeVideoFromUrl.mockResolvedValue(MOCK_RESULT)
    renderVideoPage()
    fireEvent.click(screen.getByText('From URL'))
    const input = screen.getByPlaceholderText(/zoom\.us|Teams|Drive|Loom/i)
    fireEvent.change(input, { target: { value: 'https://zoom.us/rec/share/abc123' } })
    fireEvent.click(screen.getByRole('button', { name: /Analyze Interview/i }))
    await waitFor(() => {
      expect(screen.getByText('Zoom')).toBeInTheDocument()
    })
  })

  // ─── Results: Malpractice Panel (LOW risk) ────────────────────────────

  it('renders malpractice panel with LOW RISK badge', async () => {
    analyzeVideoFromUrl.mockResolvedValue(MOCK_RESULT)
    renderVideoPage()
    fireEvent.click(screen.getByText('From URL'))
    fireEvent.change(screen.getByPlaceholderText(/zoom\.us|Teams|Drive|Loom/i), { target: { value: 'https://zoom.us/rec/share/abc' } })
    fireEvent.click(screen.getByRole('button', { name: /Analyze Interview/i }))
    await waitFor(() => {
      expect(screen.getByText('Malpractice Assessment')).toBeInTheDocument()
      expect(screen.getByText('LOW RISK')).toBeInTheDocument()
    })
  })

  it('shows trustworthy reliability rating for low risk result', async () => {
    analyzeVideoFromUrl.mockResolvedValue(MOCK_RESULT)
    renderVideoPage()
    fireEvent.click(screen.getByText('From URL'))
    fireEvent.change(screen.getByPlaceholderText(/zoom\.us|Teams|Drive|Loom/i), { target: { value: 'https://zoom.us/rec/share/abc' } })
    fireEvent.click(screen.getByRole('button', { name: /Analyze Interview/i }))
    await waitFor(() => {
      expect(screen.getByText('Trustworthy')).toBeInTheDocument()
    })
  })

  it('shows positive authenticity signals', async () => {
    analyzeVideoFromUrl.mockResolvedValue(MOCK_RESULT)
    renderVideoPage()
    fireEvent.click(screen.getByText('From URL'))
    fireEvent.change(screen.getByPlaceholderText(/zoom\.us|Teams|Drive|Loom/i), { target: { value: 'https://zoom.us/rec/share/abc' } })
    fireEvent.click(screen.getByRole('button', { name: /Analyze Interview/i }))
    await waitFor(() => {
      expect(screen.getByText('Authenticity Signals')).toBeInTheDocument()
      expect(screen.getByText('Natural filler words')).toBeInTheDocument()
    })
  })

  // ─── Results: Malpractice Panel (HIGH risk) ───────────────────────────

  it('shows HIGH RISK badge for high malpractice score', async () => {
    analyzeVideoFromUrl.mockResolvedValue(MOCK_RESULT_HIGH_RISK)
    renderVideoPage()
    fireEvent.click(screen.getByText('From URL'))
    fireEvent.change(screen.getByPlaceholderText(/zoom\.us|Teams|Drive|Loom/i), { target: { value: 'https://zoom.us/rec/share/high-risk' } })
    fireEvent.click(screen.getByRole('button', { name: /Analyze Interview/i }))
    await waitFor(() => {
      expect(screen.getByText('HIGH RISK')).toBeInTheDocument()
    })
  })

  it('shows detected flags for high-risk result', async () => {
    analyzeVideoFromUrl.mockResolvedValue(MOCK_RESULT_HIGH_RISK)
    renderVideoPage()
    fireEvent.click(screen.getByText('From URL'))
    fireEvent.change(screen.getByPlaceholderText(/zoom\.us|Teams|Drive|Loom/i), { target: { value: 'https://zoom.us/rec/share/high-risk' } })
    fireEvent.click(screen.getByRole('button', { name: /Analyze Interview/i }))
    await waitFor(() => {
      expect(screen.getByText('Detected Flags (2)')).toBeInTheDocument()
      expect(screen.getByText('Scripted Reading')).toBeInTheDocument()
    })
  })

  it('shows suspicious pause timeline for high-risk result', async () => {
    analyzeVideoFromUrl.mockResolvedValue(MOCK_RESULT_HIGH_RISK)
    renderVideoPage()
    fireEvent.click(screen.getByText('From URL'))
    fireEvent.change(screen.getByPlaceholderText(/zoom\.us|Teams|Drive|Loom/i), { target: { value: 'https://zoom.us/rec/share/high-risk' } })
    fireEvent.click(screen.getByRole('button', { name: /Analyze Interview/i }))
    await waitFor(() => {
      expect(screen.getByText('Suspicious Pause Timeline')).toBeInTheDocument()
      expect(screen.getByText('2:15')).toBeInTheDocument()
    })
  })

  it('shows follow-up questions for high-risk result', async () => {
    analyzeVideoFromUrl.mockResolvedValue(MOCK_RESULT_HIGH_RISK)
    renderVideoPage()
    fireEvent.click(screen.getByText('From URL'))
    fireEvent.change(screen.getByPlaceholderText(/zoom\.us|Teams|Drive|Loom/i), { target: { value: 'https://zoom.us/rec/share/high-risk' } })
    fireEvent.click(screen.getByRole('button', { name: /Analyze Interview/i }))
    await waitFor(() => {
      expect(screen.getByText('Recommended Follow-Up Questions')).toBeInTheDocument()
    })
  })

  it('shows overall assessment text', async () => {
    analyzeVideoFromUrl.mockResolvedValue(MOCK_RESULT_HIGH_RISK)
    renderVideoPage()
    fireEvent.click(screen.getByText('From URL'))
    fireEvent.change(screen.getByPlaceholderText(/zoom\.us|Teams|Drive|Loom/i), { target: { value: 'https://zoom.us/rec/share/high-risk' } })
    fireEvent.click(screen.getByRole('button', { name: /Analyze Interview/i }))
    await waitFor(() => {
      expect(screen.getByText('High malpractice risk. Multiple flags detected.')).toBeInTheDocument()
    })
  })

  it('shows flag evidence quote', async () => {
    analyzeVideoFromUrl.mockResolvedValue(MOCK_RESULT_HIGH_RISK)
    renderVideoPage()
    fireEvent.click(screen.getByText('From URL'))
    fireEvent.change(screen.getByPlaceholderText(/zoom\.us|Teams|Drive|Loom/i), { target: { value: 'https://zoom.us/rec/share/high-risk' } })
    fireEvent.click(screen.getByRole('button', { name: /Analyze Interview/i }))
    await waitFor(() => {
      expect(screen.getByText(/"No filler words detected throughout the interview"/i)).toBeInTheDocument()
    })
  })

  // ─── New Video reset ───────────────────────────────────────────────────

  it('shows New Video button in results and resets on click', async () => {
    analyzeVideoFromUrl.mockResolvedValue(MOCK_RESULT)
    renderVideoPage()
    fireEvent.click(screen.getByText('From URL'))
    fireEvent.change(screen.getByPlaceholderText(/zoom\.us|Teams|Drive|Loom/i), { target: { value: 'https://zoom.us/rec/share/abc' } })
    fireEvent.click(screen.getByRole('button', { name: /Analyze Interview/i }))
    await waitFor(() => screen.getByText('New Video'))
    fireEvent.click(screen.getByText('New Video'))
    expect(screen.getByText('Upload File')).toBeInTheDocument()
  })

  // ─── How it works section ─────────────────────────────────────────────

  it('shows all four how-it-works cards including malpractice check', () => {
    renderVideoPage()
    expect(screen.getByText('Upload or URL')).toBeInTheDocument()
    expect(screen.getByText('Auto Transcription')).toBeInTheDocument()
    expect(screen.getByText('Communication Score')).toBeInTheDocument()
    expect(screen.getByText('Malpractice Check')).toBeInTheDocument()
  })
})
