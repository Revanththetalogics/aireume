import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import axios from 'axios'

// Mock axios entirely
vi.mock('axios', async () => {
  const mockAxiosInstance = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  }
  return {
    default: {
      create: vi.fn(() => mockAxiosInstance),
      post: vi.fn(),
    },
    ...mockAxiosInstance,
  }
})

// Mock DOM APIs used by export functions
const mockCreateObjectURL = vi.fn(() => 'blob:mock-url')
const mockRevokeObjectURL = vi.fn()
const mockClick = vi.fn()

global.URL.createObjectURL = mockCreateObjectURL
global.URL.revokeObjectURL = mockRevokeObjectURL

// Mock document.createElement to intercept anchor clicks
const originalCreateElement = document.createElement.bind(document)
vi.spyOn(document, 'createElement').mockImplementation((tag) => {
  if (tag === 'a') {
    const el = { href: '', download: '', click: mockClick, style: {} }
    return el
  }
  return originalCreateElement(tag)
})

// localStorage mock
const localStorageMock = (() => {
  let store = {}
  return {
    getItem: vi.fn((key) => store[key] || null),
    setItem: vi.fn((key, value) => { store[key] = String(value) }),
    removeItem: vi.fn((key) => { delete store[key] }),
    clear: vi.fn(() => { store = {} }),
  }
})()
Object.defineProperty(global, 'localStorage', { value: localStorageMock })

// Import after mocks are set up
import api, {
  exportCsv,
  exportExcel,
  analyzeVideoFromUrl,
  analyzeResume,
  getHistory,
  compareResults,
  getTemplates,
  createTemplate,
  getCandidates,
} from '../lib/api'

describe('api.js', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorageMock.clear()
  })

  // ─── exportCsv ─────────────────────────────────────────────────────────

  describe('exportCsv', () => {
    it('calls GET /export/csv with responseType blob', async () => {
      const mockBlob = new Blob(['id,name'], { type: 'text/csv' })
      api.get.mockResolvedValue({ data: mockBlob })

      await exportCsv([])

      expect(api.get).toHaveBeenCalledWith(
        expect.stringContaining('/export/csv'),
        expect.objectContaining({ responseType: 'blob' })
      )
    })

    it('includes ids in query string when provided', async () => {
      api.get.mockResolvedValue({ data: new Blob(['csv data']) })

      await exportCsv([1, 2, 3])

      expect(api.get).toHaveBeenCalledWith(
        expect.stringContaining('ids=1,2,3'),
        expect.any(Object)
      )
    })

    it('does not use window.open (auth header must be sent)', async () => {
      const windowOpenSpy = vi.spyOn(window, 'open').mockImplementation(() => {})
      api.get.mockResolvedValue({ data: new Blob(['csv']) })

      await exportCsv([])

      expect(windowOpenSpy).not.toHaveBeenCalled()
      windowOpenSpy.mockRestore()
    })

    it('triggers anchor download programmatically', async () => {
      api.get.mockResolvedValue({ data: new Blob(['csv data']) })

      await exportCsv([])

      expect(mockCreateObjectURL).toHaveBeenCalled()
      expect(mockClick).toHaveBeenCalled()
    })

    it('generates csv filename with timestamp', async () => {
      api.get.mockResolvedValue({ data: new Blob(['csv']) })

      await exportCsv([])

      const calls = document.createElement.mock.calls.filter(c => c[0] === 'a')
      expect(calls.length).toBeGreaterThan(0)
    })
  })

  // ─── exportExcel ───────────────────────────────────────────────────────

  describe('exportExcel', () => {
    it('calls GET /export/excel with responseType blob', async () => {
      api.get.mockResolvedValue({ data: new Blob(['xlsx data']) })

      await exportExcel([])

      expect(api.get).toHaveBeenCalledWith(
        expect.stringContaining('/export/excel'),
        expect.objectContaining({ responseType: 'blob' })
      )
    })

    it('includes ids when provided', async () => {
      api.get.mockResolvedValue({ data: new Blob(['xlsx']) })

      await exportExcel([5, 10])

      expect(api.get).toHaveBeenCalledWith(
        expect.stringContaining('ids=5,10'),
        expect.any(Object)
      )
    })

    it('does not use window.open', async () => {
      const windowOpenSpy = vi.spyOn(window, 'open').mockImplementation(() => {})
      api.get.mockResolvedValue({ data: new Blob(['xlsx']) })

      await exportExcel([])

      expect(windowOpenSpy).not.toHaveBeenCalled()
      windowOpenSpy.mockRestore()
    })
  })

  // ─── analyzeVideoFromUrl ───────────────────────────────────────────────

  describe('analyzeVideoFromUrl', () => {
    it('calls POST /analyze/video-url with url and candidate_id', async () => {
      api.post.mockResolvedValue({ data: { communication_score: 80 } })

      await analyzeVideoFromUrl('https://zoom.us/rec/share/abc', 42)

      expect(api.post).toHaveBeenCalledWith(
        '/analyze/video-url',
        { url: 'https://zoom.us/rec/share/abc', candidate_id: 42 },
        expect.objectContaining({ timeout: expect.any(Number) })
      )
    })

    it('sends null candidate_id when not provided', async () => {
      api.post.mockResolvedValue({ data: { communication_score: 70 } })

      await analyzeVideoFromUrl('https://loom.com/share/abc')

      expect(api.post).toHaveBeenCalledWith(
        '/analyze/video-url',
        { url: 'https://loom.com/share/abc', candidate_id: null },
        expect.any(Object)
      )
    })

    it('uses a generous timeout (at least 5 minutes) for video downloads', async () => {
      api.post.mockResolvedValue({ data: {} })

      await analyzeVideoFromUrl('https://example.com/video.mp4')

      const callArgs = api.post.mock.calls[0]
      expect(callArgs[2].timeout).toBeGreaterThanOrEqual(300000)
    })
  })

  // ─── analyzeResume ─────────────────────────────────────────────────────

  describe('analyzeResume', () => {
    it('calls POST /analyze with multipart form', async () => {
      api.post.mockResolvedValue({ data: { fit_score: 75 } })

      const mockFile = new File(['resume content'], 'resume.pdf', { type: 'application/pdf' })
      await analyzeResume(mockFile, 'Python developer needed')

      expect(api.post).toHaveBeenCalledWith(
        '/analyze',
        expect.any(FormData),
        expect.objectContaining({ headers: { 'Content-Type': 'multipart/form-data' } })
      )
    })
  })

  // ─── getHistory ────────────────────────────────────────────────────────

  describe('getHistory', () => {
    it('calls GET /history', async () => {
      api.get.mockResolvedValue({ data: [] })
      await getHistory()
      expect(api.get).toHaveBeenCalledWith('/history')
    })
  })

  // ─── compareResults ────────────────────────────────────────────────────

  describe('compareResults', () => {
    it('calls POST /compare with candidate_ids array', async () => {
      api.post.mockResolvedValue({ data: { comparisons: [] } })
      await compareResults([1, 2, 3])
      expect(api.post).toHaveBeenCalledWith('/compare', { candidate_ids: [1, 2, 3] })
    })
  })

  // ─── Templates ────────────────────────────────────────────────────────

  describe('templates', () => {
    it('getTemplates calls GET /templates', async () => {
      api.get.mockResolvedValue({ data: [] })
      await getTemplates()
      expect(api.get).toHaveBeenCalledWith('/templates')
    })

    it('createTemplate calls POST /templates', async () => {
      api.post.mockResolvedValue({ data: { id: 1 } })
      await createTemplate({ name: 'Test', jd_text: 'JD', tags: '' })
      expect(api.post).toHaveBeenCalledWith('/templates', { name: 'Test', jd_text: 'JD', tags: '' })
    })
  })

  // ─── Candidates ───────────────────────────────────────────────────────

  describe('getCandidates', () => {
    it('calls GET /candidates with params', async () => {
      api.get.mockResolvedValue({ data: { candidates: [] } })
      await getCandidates({ page: 1, page_size: 20 })
      expect(api.get).toHaveBeenCalledWith('/candidates', { params: { page: 1, page_size: 20 } })
    })
  })
})
