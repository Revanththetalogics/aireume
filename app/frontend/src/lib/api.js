import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || '/api'

const api = axios.create({
  baseURL: API_URL,
  withCredentials: true,  // Send httpOnly cookies with every request
})

// Attach JWT token to every request (for backward compatibility with API clients)
// Browser clients will use httpOnly cookies automatically
api.interceptors.request.use((config) => {
  // Token storage is now handled via httpOnly cookies only
  // No localStorage token handling for security
  return config
})

// Add CSRF token to all non-GET requests for browser clients
api.interceptors.request.use((config) => {
  if (config.method !== 'get') {
    // Read CSRF token from cookie
    const csrfToken = document.cookie
      .split('; ')
      .find(row => row.startsWith('csrf_token='))
      ?.split('=')[1]
    if (csrfToken) {
      config.headers['X-CSRF-Token'] = csrfToken
    }
  }
  return config
})

// Auto-refresh on 401 - uses httpOnly cookies only
// Skip refresh logic for auth endpoints to prevent login loops
const AUTH_PATHS = ['/auth/me', '/auth/login', '/auth/register', '/auth/refresh', '/auth/logout']

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    const reqPath = original?.url || ''
    const isAuthEndpoint = AUTH_PATHS.some(p => reqPath.includes(p))

    if (error.response?.status === 401 && !original._retry && !isAuthEndpoint) {
      original._retry = true
      try {
        // Refresh endpoint reads from cookie - browser sends cookie automatically
        await axios.post(`${API_URL}/auth/refresh`, {}, { withCredentials: true })
        // Retry the original request - cookies are sent automatically
        return api(original)
      } catch {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

// Retry configuration for transient errors
const MAX_RETRIES = 3
const RETRY_DELAYS = [1000, 2000, 4000] // Exponential backoff

// Add retry interceptor (must be after 401 refresh interceptor)
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config

    // Only retry on 5xx errors and network errors (not 4xx)
    const isRetryable = !error.response || (error.response.status >= 500)

    // Don't retry POST requests that might not be idempotent (except specific ones)
    const isIdempotent = config.method === 'get' || config._isRetryable

    if (!isRetryable || !isIdempotent) {
      return Promise.reject(error)
    }

    config._retryCount = config._retryCount || 0
    if (config._retryCount >= MAX_RETRIES) {
      return Promise.reject(error)
    }

    config._retryCount++
    const delay = RETRY_DELAYS[config._retryCount - 1] || 4000

    await new Promise(resolve => setTimeout(resolve, delay))
    return api(config)
  }
)

// ─── Queue-Based Analysis (Async) ────────────────────────────────────────────

/**
 * Submit a resume analysis job to the queue (returns immediately with job_id)
 */
export async function submitAnalysisJob(file, jobDescription, jobFile = null, scoringWeights = null, priority = 5, templateId = null) {
  const formData = new FormData()
  formData.append('resume_file', file)
  if (jobFile) {
    formData.append('jd_file', jobFile)
  } else {
    formData.append('jd_text', jobDescription)
  }
  if (scoringWeights) {
    formData.append('scoring_weights', JSON.stringify(scoringWeights))
  }
  formData.append('priority', priority.toString())
  if (templateId) {
    formData.append('template_id', templateId)
  }
  
  const response = await api.post('/queue/submit', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data // { job_id, status, queued_at }
}

/**
 * Check the status of a queued analysis job
 */
export async function getJobStatus(jobId) {
  const response = await api.get(`/queue/status/${jobId}`)
  return response.data // { job_id, status, progress_percent, processing_stage, ... }
}

/**
 * Get the completed analysis result for a job
 */
export async function getJobResult(jobId) {
  const response = await api.get(`/queue/result/${jobId}`)
  return response.data // { analysis: {...}, metadata: {...} }
}

/**
 * Poll a job until completion (helper function)
 * @param {string} jobId - Job ID to poll
 * @param {function} onProgress - Callback for progress updates (status, progress_percent)
 * @param {number} pollInterval - Milliseconds between polls (default 2000)
 * @param {number} timeout - Max wait time in ms (default 120000 = 2 min)
 * @returns {Promise<object>} - Completed analysis result
 */
export async function pollJobUntilComplete(jobId, onProgress = null, pollInterval = 2000, timeout = 120000) {
  const startTime = Date.now()
  
  while (true) {
    if (Date.now() - startTime > timeout) {
      throw new Error('Job polling timeout - analysis taking too long')
    }
    
    const status = await getJobStatus(jobId)
    
    if (onProgress) {
      onProgress(status)
    }
    
    if (status.status === 'completed') {
      return await getJobResult(jobId)
    }
    
    if (status.status === 'failed') {
      throw new Error(status.error_message || 'Analysis failed')
    }
    
    if (status.status === 'cancelled') {
      throw new Error('Job was cancelled')
    }
    
    // Wait before next poll
    await new Promise(resolve => setTimeout(resolve, pollInterval))
  }
}

/**
 * Submit job and wait for completion (convenience wrapper)
 */
export async function analyzeResumeAsync(file, jobDescription, jobFile = null, scoringWeights = null, onProgress = null) {
  const { job_id } = await submitAnalysisJob(file, jobDescription, jobFile, scoringWeights)
  const result = await pollJobUntilComplete(job_id, onProgress)
  return result.analysis
}

// ─── Resume Analysis (Legacy Synchronous) ─────────────────────────────────────

export async function analyzeResume(file, jobDescription, jobFile = null, scoringWeights = null, templateId = null) {
  const formData = new FormData()
  formData.append('resume', file)
  if (jobFile) {
    formData.append('job_file', jobFile)
  } else {
    formData.append('job_description', jobDescription)
  }
  if (scoringWeights) {
    formData.append('scoring_weights', JSON.stringify(scoringWeights))
  }
  if (templateId) {
    formData.append('template_id', templateId)
  }
  const response = await api.post('/analyze', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
  return response.data
}

/**
 * Streaming version of analyzeResume — uses /api/analyze/stream (SSE).
 *
 * @param {File} file  - Resume file
 * @param {string} jobDescription  - JD text (or empty if jobFile provided)
 * @param {File|null} jobFile  - JD file upload
 * @param {object|null} scoringWeights  - Custom weight map
 * @param {function} onStageComplete  - Called with ({stage, result}) after each node
 * @returns {Promise<object>}  - Resolves with the complete assembled result
 */
export async function analyzeResumeStream(
  file,
  jobDescription,
  jobFile = null,
  scoringWeights = null,
  onStageComplete = null,
  templateId = null,
) {
  const formData = new FormData()
  formData.append('resume', file)
  if (jobFile) {
    formData.append('job_file', jobFile)
  } else {
    formData.append('job_description', jobDescription)
  }
  if (scoringWeights) {
    formData.append('scoring_weights', JSON.stringify(scoringWeights))
  }
  if (templateId) {
    formData.append('template_id', templateId)
  }

  const baseURL = import.meta.env.VITE_API_URL || '/api'

  // Get CSRF token from cookie for the fetch call
  const csrfToken = document.cookie
    .split('; ')
    .find(row => row.startsWith('csrf_token='))
    ?.split('=')[1]

  const headers = {}
  if (csrfToken) {
    headers['X-CSRF-Token'] = csrfToken
  }

  const response = await fetch(`${baseURL}/analyze/stream`, {
    method: 'POST',
    headers,
    body: formData,
    credentials: 'include',  // Send httpOnly cookies
  })

  if (!response.ok) {
    let detail = `HTTP ${response.status}`
    try {
      const err = await response.json()
      detail = err.detail || detail
    } catch { /* ignore */ }
    throw new Error(detail)
  }

  const reader  = response.body.getReader()
  const decoder = new TextDecoder()
  let   buffer  = ''
  let   finalResult = null
  let   streamDone = false

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    // SSE lines are separated by \n\n
    const parts = buffer.split('\n\n')
    buffer = parts.pop() ?? ''   // last fragment (possibly incomplete)

    for (const part of parts) {
      const line = part.trim()
      if (!line.startsWith('data: ')) continue
      const raw = line.slice(6).trim()
      if (raw === '[DONE]') {
        streamDone = true
        break
      }

      try {
        const event = JSON.parse(raw)
        console.log('[SSE] Received event:', event.stage, event)
        
        if (event.stage === 'complete') {
          finalResult = event.result
          console.log('[SSE] Final result captured:', finalResult?.fit_score)
        } else if (event.stage === 'parsing') {
          // Parsing stage also contains the result - use as fallback
          if (!finalResult && event.result) {
            console.log('[SSE] Storing parsing result as fallback')
            finalResult = event.result
          }
          if (onStageComplete) {
            onStageComplete(event)
          }
        } else if (event.stage === 'error') {
          throw new Error(event.result?.message || 'Analysis failed')
        } else if (onStageComplete) {
          onStageComplete(event)
        }
      } catch (parseError) {
        console.error('[SSE] Failed to parse event:', raw, parseError)
        // Don't throw - continue processing other events
      }
    }
    
    if (streamDone) break
  }

  if (!finalResult) {
    console.error('[SSE] Stream ended without final result')
    throw new Error('Stream ended without a complete result.')
  }
  console.log('[SSE] Returning final result:', finalResult?.fit_score)
  return finalResult
}

export async function analyzeBatch(files, jobDescription, jobFile = null, scoringWeights = null, templateId = null) {
  const formData = new FormData()
  files.forEach((f) => formData.append('resumes', f))
  if (jobFile) {
    formData.append('job_file', jobFile)
  } else {
    formData.append('job_description', jobDescription)
  }
  if (scoringWeights) {
    formData.append('scoring_weights', JSON.stringify(scoringWeights))
  }
  if (templateId) {
    formData.append('template_id', templateId)
  }
  const response = await api.post('/analyze/batch', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000,
  })
  return response.data
}

/**
 * Analyze batch of resumes using chunked upload for large files.
 * This bypasses CDN/proxy upload limits by splitting files into chunks.
 *
 * @param {File[]} files - Array of resume files to analyze
 * @param {string} jobDescription - Job description text
 * @param {File|null} jobFile - Optional job description file
 * @param {Object|null} scoringWeights - Optional custom scoring weights
 * @param {Object} callbacks - Progress callbacks
 * @param {Function} callbacks.onFileProgress - Called with (filename, progress) for each file
 * @param {Function} callbacks.onOverallProgress - Called with overall upload progress
 * @returns {Promise} Analysis results
 */
export async function analyzeBatchChunked(files, jobDescription, jobFile = null, scoringWeights = null, callbacks = {}, templateId = null) {
  const { uploadMultipleFiles } = await import('./uploadChunked')

  // Upload all files using chunked upload
  const uploadResults = await uploadMultipleFiles(files, {
    onFileProgress: callbacks.onFileProgress || (() => {}),
    onOverallProgress: callbacks.onOverallProgress || (() => {}),
    onFileComplete: callbacks.onFileComplete || (() => {}),
    onFileError: callbacks.onFileError || (() => {}),
  })

  // Check if any uploads failed
  if (uploadResults.failed.length > 0) {
    throw new Error(`Failed to upload ${uploadResults.failed.length} file(s): ${uploadResults.failed.map(f => f.file).join(', ')}`)
  }

  // Now call a new backend endpoint that processes the assembled files
  const formData = new FormData()

  // Send upload IDs instead of files - backend will read from assembled directory
  uploadResults.successful.forEach(({ file: filename, result }) => {
    formData.append('upload_ids', result.upload_id)
    formData.append('filenames', filename)
  })

  if (jobFile) {
    formData.append('job_file', jobFile)
  } else {
    formData.append('job_description', jobDescription)
  }

  if (scoringWeights) {
    formData.append('scoring_weights', JSON.stringify(scoringWeights))
  }
  if (templateId) {
    formData.append('template_id', templateId)
  }

  const response = await api.post('/analyze/batch-chunked', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 600000, // 10 minutes - longer than Cloudflare's 100s timeout
  })

  return response.data
}

/**
 * Batch analyze resumes with progressive SSE streaming.
 * Uploads files first (reusing uploadMultipleFiles), then opens SSE stream
 * to /api/analyze/batch-stream for progressive results.
 *
 * @param {File[]} files - Array of resume files to analyze
 * @param {string} jobDescription - Job description text
 * @param {File|null} jdFile - Optional job description file
 * @param {Object|null} scoringWeights - Optional custom scoring weights
 * @param {Object} callbacks - Callbacks for upload and streaming events
 * @param {Function} callbacks.onFileProgress - Called with (filename, progress) during upload
 * @param {Function} callbacks.onOverallProgress - Called with overall upload progress
 * @param {Function} callbacks.onFileComplete - Called when a file upload completes
 * @param {Function} callbacks.onFileError - Called when a file upload fails
 * @param {Function} callbacks.onProcessing - Called with (index, total, filename) when a file starts processing
 * @param {Function} callbacks.onResult - Called with (index, total, filename, result, screeningResultId) for each successful analysis
 * @param {Function} callbacks.onFailed - Called with (index, total, filename, error) for each failed analysis
 * @param {Function} callbacks.onDone - Called with (total, successful, failedCount) when complete
 * @returns {Promise<void>}
 */
export async function analyzeBatchStream(files, jobDescription, jdFile = null, scoringWeights = null, callbacks = {}, templateId = null) {
  const {
    onFileProgress, onOverallProgress, onFileComplete, onFileError,  // upload callbacks
    onProcessing, // (index, total, filename) => void
    onResult,    // (index, total, filename, result, screeningResultId) => void
    onFailed,    // (index, total, filename, error) => void
    onDone,      // (total, successful, failedCount) => void
  } = callbacks || {}

  const { uploadMultipleFiles } = await import('./uploadChunked')

  // Phase 1: Upload files (reuse existing)
  const uploadResults = await uploadMultipleFiles(files, {
    onFileProgress: onFileProgress || (() => {}),
    onOverallProgress: onOverallProgress || (() => {}),
    onFileComplete: onFileComplete || (() => {}),
    onFileError: onFileError || (() => {}),
  })

  // Report upload failures
  if (uploadResults.failed?.length) {
    uploadResults.failed.forEach(({ file: filename, error }) => {
      if (onFailed) onFailed(0, files.length, filename, `Upload failed: ${error}`)
    })
  }

  if (!uploadResults.successful.length) {
    throw new Error('No files uploaded successfully')
  }

  // Phase 2: Build FormData (same as analyzeBatchChunked)
  const formData = new FormData()
  uploadResults.successful.forEach(({ file: filename, result }) => {
    formData.append('upload_ids', result.upload_id)
    formData.append('filenames', filename)
  })
  if (jobDescription) formData.append('job_description', jobDescription)
  if (jdFile) formData.append('job_file', jdFile)
  if (scoringWeights) formData.append('scoring_weights', JSON.stringify(scoringWeights))
  if (templateId) formData.append('template_id', templateId)

  // Phase 3: Open SSE stream
  const baseURL = import.meta.env.VITE_API_URL || '/api'

  // Get CSRF token from cookie for the fetch call
  const csrfToken = document.cookie
    .split('; ')
    .find(row => row.startsWith('csrf_token='))
    ?.split('=')[1]

  const headers = {}
  if (csrfToken) {
    headers['X-CSRF-Token'] = csrfToken
  }

  const response = await fetch(`${baseURL}/analyze/batch-stream`, {
    method: 'POST',
    body: formData,
    headers,
    credentials: 'include',  // Send httpOnly cookies
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || `Analysis failed: ${response.status}`)
  }

  // Phase 4: Parse SSE stream
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    // SSE lines are separated by \n\n
    const parts = buffer.split('\n\n')
    buffer = parts.pop() ?? ''   // last fragment (possibly incomplete)

    for (const part of parts) {
      const line = part.trim()
      if (!line.startsWith('data: ')) continue
      const data = line.slice(6).trim()

      if (data === '[DONE]') return

      try {
        const evt = JSON.parse(data)

        if (evt.event === 'processing' && onProcessing) {
          onProcessing(evt.index, evt.total, evt.filename)
        } else if (evt.event === 'result' && onResult) {
          onResult(evt.index, evt.total, evt.filename, evt.result, evt.screening_result_id)
        } else if (evt.event === 'failed' && onFailed) {
          onFailed(evt.index, evt.total, evt.filename, evt.error)
        } else if (evt.event === 'done' && onDone) {
          onDone(evt.total, evt.successful, evt.failed_count)
        }
      } catch (e) {
        console.warn('Failed to parse SSE event:', data, e)
      }
    }
  }
}

// ─── History ──────────────────────────────────────────────────────────────────

export async function getHistory() {
  const response = await api.get('/history')
  return response.data
}

// ─── Compare ─────────────────────────────────────────────────────────────────

export async function compareResults(ids) {
  const response = await api.post('/compare', { candidate_ids: ids })
  return response.data
}

// ─── Export ──────────────────────────────────────────────────────────────────

export async function exportCsv(ids = []) {
  const idsParam = ids.length ? `?ids=${ids.join(',')}` : ''
  const res = await api.get(`/export/csv${idsParam}`, { responseType: 'blob' })
  _triggerDownload(res.data, `aria_export_${_ts()}.csv`, 'text/csv')
}

export async function exportExcel(ids = []) {
  const idsParam = ids.length ? `?ids=${ids.join(',')}` : ''
  const res = await api.get(`/export/excel${idsParam}`, { responseType: 'blob' })
  _triggerDownload(res.data, `aria_export_${_ts()}.xlsx`, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
}

function _triggerDownload(blob, filename, type) {
  const url = URL.createObjectURL(new Blob([blob], { type }))
  const a = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  setTimeout(() => URL.revokeObjectURL(url), 100)
}

function _ts() {
  return new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
}

// ─── Resume File Download / View ─────────────────────────────────────────────

export async function downloadCandidateResume(candidateId, filename) {
  const res = await api.get(`/candidates/${candidateId}/resume`, { responseType: 'blob' })
  const type = res.headers['content-type'] || 'application/octet-stream'
  // If server converted .doc to PDF, ensure downloaded file has .pdf extension
  if (type === 'application/pdf' && filename && !filename.toLowerCase().endsWith('.pdf')) {
    filename = filename.replace(/\.[^.]+$/, '') + '.pdf'
  }
  _triggerDownload(res.data, filename, type)
}

export async function viewCandidateResume(candidateId) {
  const res = await api.get(`/candidates/${candidateId}/resume`, { responseType: 'blob' })
  const type = res.headers['content-type'] || 'application/octet-stream'
  const url = URL.createObjectURL(new Blob([res.data], { type }))
  window.open(url, '_blank')
  setTimeout(() => URL.revokeObjectURL(url), 30000)
}

// ─── Templates ───────────────────────────────────────────────────────────────

export async function getTemplates() {
  const res = await api.get('/templates')
  return res.data.templates || res.data
}

export async function createTemplate(data) {
  const res = await api.post('/templates', data)
  return res.data
}

export async function updateTemplate(id, data) {
  const res = await api.put(`/templates/${id}`, data)
  return res.data
}

export async function deleteTemplate(id) {
  await api.delete(`/templates/${id}`)
}

// ─── Candidates ───────────────────────────────────────────────────────────────

export async function getCandidates(params = {}) {
  const res = await api.get('/candidates', { params })
  return res.data
}

export async function getCandidate(id) {
  const res = await api.get(`/candidates/${id}`)
  return res.data
}

export async function getCandidateTimeline(id) {
  const res = await api.get(`/candidates/${id}/timeline`)
  return res.data
}

export async function getCandidatePipeline(jdId = null) {
  const params = {}
  if (jdId) params.jd_id = jdId
  const res = await api.get('/candidates/pipeline', { params })
  return res.data
}

export async function updateCandidateName(candidateId, name) {
  const response = await api.put(`/candidates/${candidateId}/name`, { name })
  return response.data
}

// ─── Candidate Notes ─────────────────────────────────────────────────────────

export async function getCandidateNotes(candidateId) {
  const res = await api.get(`/candidates/${candidateId}/notes`)
  return res.data
}

export async function addCandidateNote(candidateId, text) {
  const res = await api.post(`/candidates/${candidateId}/notes`, { text })
  return res.data
}

export async function deleteCandidateNote(candidateId, noteId) {
  const res = await api.delete(`/candidates/${candidateId}/notes/${noteId}`)
  return res.data
}

// ─── Email Generation ─────────────────────────────────────────────────────────

export async function generateEmail(candidateId, type) {
  const res = await api.post('/email/generate', { candidate_id: candidateId, type })
  return res.data
}

// ─── JD URL Extraction ────────────────────────────────────────────────────────

export async function extractJdFromUrl(url) {
  const res = await api.post('/jd/extract-url', { url })
  return res.data
}

// ─── Team ────────────────────────────────────────────────────────────────────

export async function getTeamMembers() {
  const res = await api.get('/team')
  return res.data
}

export async function inviteTeamMember(email, role) {
  const res = await api.post('/invites', { email, role })
  return res.data
}

export async function addComment(resultId, text) {
  const res = await api.post(`/results/${resultId}/comments`, { text })
  return res.data
}

export async function updateResultStatus(resultId, status) {
  const res = await api.put(`/results/${resultId}/status`, { status })
  return res.data
}

// ─── Training ────────────────────────────────────────────────────────────────

export async function labelTrainingExample(resultId, outcome, feedback = '') {
  const res = await api.post('/training/label', { screening_result_id: resultId, outcome, feedback })
  return res.data
}

export async function startTraining() {
  const res = await api.post('/training/train')
  return res.data
}

export async function getTrainingStatus() {
  const res = await api.get('/training/status')
  return res.data
}

// ─── Video Analysis ──────────────────────────────────────────────────────────

export async function analyzeVideo(videoFile, candidateId = null) {
  const formData = new FormData()
  formData.append('video', videoFile)
  if (candidateId) formData.append('candidate_id', candidateId)
  const res = await api.post('/analyze/video', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000,
  })
  return res.data
}

export async function analyzeVideoFromUrl(url, candidateId = null) {
  const res = await api.post('/analyze/video-url', { url, candidate_id: candidateId }, {
    timeout: 600000,  // 10 min — download + analysis
  })
  return res.data
}

// ─── Transcript Analysis ─────────────────────────────────────────────────────

export async function analyzeTranscript(
  transcriptFile,
  transcriptText,
  candidateId,
  roleTemplateId,
  sourcePlatform
) {
  const formData = new FormData()
  if (transcriptFile) {
    formData.append('transcript_file', transcriptFile)
  } else if (transcriptText) {
    formData.append('transcript_text', transcriptText)
  }
  if (candidateId)    formData.append('candidate_id', candidateId)
  if (roleTemplateId) formData.append('role_template_id', roleTemplateId)
  if (sourcePlatform) formData.append('source_platform', sourcePlatform)

  const res = await api.post('/transcript/analyze', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
  return res.data
}

// ─── Queue Management & Monitoring ────────────────────────────────────────────

/**
 * Get queue statistics (job counts by status, avg processing time, etc.)
 */
export async function getQueueStats() {
  const response = await api.get('/queue/stats')
  return response.data
}

/**
 * List jobs with optional filters
 */
export async function listJobs(status = null, limit = 50, offset = 0) {
  const params = { limit, offset }
  if (status) params.status = status
  const response = await api.get('/queue/jobs', { params })
  return response.data
}

/**
 * Retry a failed job
 */
export async function retryJob(jobId) {
  const response = await api.post(`/queue/retry/${jobId}`)
  return response.data
}

/**
 * Cancel a queued or processing job
 */
export async function cancelJob(jobId) {
  const response = await api.delete(`/queue/cancel/${jobId}`)
  return response.data
}

/**
 * Get performance metrics
 */
export async function getQueueMetrics() {
  const response = await api.get('/queue/metrics/performance')
  return response.data
}

// ─── Transcript Analysis ──────────────────────────────────────────────────────

export async function getTranscriptAnalyses() {
  const res = await api.get('/transcript/analyses')
  return res.data
}

export async function getTranscriptAnalysis(id) {
  const res = await api.get(`/transcript/analyses/${id}`)
  return res.data
}

// ─── Narrative Polling ────────────────────────────────────────────────────────

export async function getNarrative(analysisId) {
  const response = await api.get(`/analysis/${analysisId}/narrative`)
  return response.data
}

// ─── Health ───────────────────────────────────────────────────────────────────

export async function checkHealth() {
  const response = await api.get('/health')
  return response.data
}

// ─── Subscription ───────────────────────────────────────────────────────────

export async function getSubscription() {
  const response = await api.get('/subscription')
  return response.data
}

export async function getAvailablePlans() {
  const response = await api.get('/subscription/plans')
  return response.data
}

export async function checkUsage(action, quantity = 1) {
  const response = await api.get(`/subscription/check/${action}?quantity=${quantity}`)
  return response.data
}

export async function getUsageHistory(limit = 100) {
  const response = await api.get(`/subscription/usage-history?limit=${limit}`)
  return response.data
}

// ─── Admin (for testing/plan management) ──────────────────────────────────────

export async function adminResetUsage() {
  const response = await api.post('/subscription/admin/reset-usage')
  return response.data
}

export async function adminChangePlan(planId) {
  const response = await api.post(`/subscription/admin/change-plan/${planId}`)
  return response.data
}

// ─── User-friendly Error Messages ─────────────────────────────────────────────

export function getUserFriendlyError(error) {
  if (!error.response) {
    return "Network error. Please check your connection and try again."
  }
  const status = error.response.status
  const detail = error.response.data?.detail

  const errorMap = {
    400: detail || "Invalid request. Please check your input.",
    401: "Session expired. Please log in again.",
    403: detail === "CSRF token missing or invalid"
      ? "Session expired, please refresh the page."
      : "You don't have permission for this action.",
    404: "The requested resource was not found.",
    413: "File is too large. Please upload a smaller file.",
    429: detail || "Too many requests. Please wait a moment.",
    500: "Server error. Our team has been notified.",
    502: "Service temporarily unavailable. Please try again.",
    503: "Service is under maintenance. Please try again later.",
  }

  return errorMap[status] || detail || "An unexpected error occurred."
}

// ─── Platform Admin API ─────────────────────────────────────

export async function getAdminTenants(params = {}) {
  const response = await api.get('/admin/tenants', { params })
  return response.data
}

export async function getAdminTenantDetail(tenantId) {
  const response = await api.get(`/admin/tenants/${tenantId}`)
  return response.data
}

export async function suspendTenant(tenantId, reason) {
  const response = await api.post(`/admin/tenants/${tenantId}/suspend`, { reason })
  return response.data
}

export async function reactivateTenant(tenantId) {
  const response = await api.post(`/admin/tenants/${tenantId}/reactivate`)
  return response.data
}

export async function adminChangeTenantPlan(tenantId, planId) {
  const response = await api.post(`/admin/tenants/${tenantId}/change-plan`, { plan_id: planId })
  return response.data
}

export async function adminAdjustUsage(tenantId, data) {
  const response = await api.post(`/admin/tenants/${tenantId}/adjust-usage`, data)
  return response.data
}

export async function getAdminTenantUsageHistory(tenantId, limit = 100) {
  const response = await api.get(`/admin/tenants/${tenantId}/usage-history`, { params: { limit } })
  return response.data
}

export async function getAdminAuditLogs(params = {}) {
  const response = await api.get('/admin/audit-logs', { params })
  return response.data
}

// ─── Platform Admin API — Phase 2 ──────────────────────────

export async function getAdminFeatureFlags() {
  const response = await api.get('/admin/feature-flags')
  return response.data
}

export async function toggleFeatureFlag(flagId, enabledGlobally) {
  const response = await api.put(`/admin/feature-flags/${flagId}`, { enabled_globally: enabledGlobally })
  return response.data
}

export async function getTenantFeatureOverrides(tenantId) {
  const response = await api.get(`/admin/tenants/${tenantId}/features`)
  return response.data
}

export async function setTenantFeatureOverride(tenantId, flagId, enabled) {
  const response = await api.put(`/admin/tenants/${tenantId}/features/${flagId}`, { enabled })
  return response.data
}

export async function deleteTenantFeatureOverride(tenantId, flagId) {
  const response = await api.delete(`/admin/tenants/${tenantId}/features/${flagId}`)
  return response.data
}

export async function getTenantWebhooks(tenantId) {
  const response = await api.get(`/admin/tenants/${tenantId}/webhooks`)
  return response.data
}

export async function createTenantWebhook(tenantId, data) {
  const response = await api.post(`/admin/tenants/${tenantId}/webhooks`, data)
  return response.data
}

export async function deleteTenantWebhook(tenantId, webhookId) {
  const response = await api.delete(`/admin/tenants/${tenantId}/webhooks/${webhookId}`)
  return response.data
}

export async function getWebhookDeliveries(tenantId, webhookId, limit = 50) {
  const response = await api.get(`/admin/tenants/${tenantId}/webhooks/${webhookId}/deliveries`, { params: { limit } })
  return response.data
}

export async function getAdminMetricsOverview() {
  const response = await api.get('/admin/metrics/overview')
  return response.data
}

export async function getAdminUsageTrends(days = 30) {
  const response = await api.get('/admin/metrics/usage-trends', { params: { days } })
  return response.data
}

// ─── Billing Admin API ──────────────────────────────────────────

export async function getBillingConfig() {
  const response = await api.get('/admin/billing/config')
  return response.data
}

export async function updateBillingConfig(data) {
  const response = await api.put('/admin/billing/config', data)
  return response.data
}

export async function getBillingProviders() {
  const response = await api.get('/admin/billing/providers')
  return response.data
}

// ─── Interview Evaluation & Scorecard ─────────────────────────────────────────

export async function getEvaluations(resultId) {
  const res = await api.get(`/results/${resultId}/evaluations`)
  return res.data
}

export async function saveEvaluation(resultId, { question_category, question_index, rating, notes }) {
  const res = await api.put(`/results/${resultId}/evaluations`, {
    question_category,
    question_index,
    rating: rating || null,
    notes: notes || null,
  })
  return res.data
}

export async function saveOverallAssessment(resultId, { overall_assessment, recruiter_recommendation }) {
  const res = await api.put(`/results/${resultId}/evaluations/overall`, {
    overall_assessment,
    recruiter_recommendation: recruiter_recommendation || null,
  })
  return res.data
}

export async function getScorecard(resultId) {
  const res = await api.get(`/results/${resultId}/scorecard`)
  return res.data
}

// ─── Dashboard ────────────────────────────────────────────────────────────────

export async function getDashboardSummary() {
  const res = await api.get('/dashboard/summary')
  return res.data
}

export async function getDashboardActivity() {
  const res = await api.get('/dashboard/activity')
  return res.data
}

// ─── JD Skill Tags ──────────────────────────────────────────────────────────

export async function getJDSkillTags(jdId) {
  const res = await api.get(`/jd/${jdId}/skill-tags`)
  return res.data
}

// ─── JD Candidates & Shortlisting ──────────────────────────────────────────

export async function getJDCandidates(jdId, { sortBy = 'fit_score', sortOrder = 'desc', status = '' } = {}) {
  const params = { sort_by: sortBy, sort_order: sortOrder }
  if (status) params.status = status
  const res = await api.get(`/jd/${jdId}/candidates`, { params })
  return res.data
}

export async function bulkUpdateStatus(jdId, resultIds, status) {
  const res = await api.post(`/jd/${jdId}/shortlist`, { result_ids: resultIds, status })
  return res.data
}

export async function getAllJDStats() {
  const res = await api.get('/jd/stats/batch')
  return res.data
}

// ─── Screening Analytics ────────────────────────────────────────────────────

export async function getScreeningAnalytics(period = 'last_30_days') {
  const response = await api.get('/analytics/screening', { params: { period } })
  return response.data
}

// ─── HM Handoff Package ──────────────────────────────────────────────────────

export async function getHandoffPackage(jdId) {
  const response = await api.get(`/jd/${jdId}/handoff-package`)
  return response.data
}

// ─── Notification Admin API ──────────────────────────────────────

export async function getNotificationConfig() {
  const response = await api.get('/admin/notifications/config')
  return response.data
}

export async function sendTestEmail(email) {
  const response = await api.post('/admin/notifications/test', { email })
  return response.data
}

// ─── Tenant Email Configuration ───────────────────────────────────────────────

export async function getEmailConfig() {
  const response = await api.get('/admin/email-config')
  return response.data
}

export async function saveEmailConfig(data) {
  const response = await api.post('/admin/email-config', data)
  return response.data
}

export async function testEmailConfig() {
  const response = await api.post('/admin/email-config/test')
  return response.data
}

export async function deleteEmailConfig() {
  const response = await api.delete('/admin/email-config')
  return response.data
}

// ─── Enterprise Platform Admin API (Phase 1-4) ────────────────────────────────

export async function getSecurityEvents(params = {}) {
  const response = await api.get('/admin/security-events', { params })
  return response.data
}

export async function impersonateUser(userId) {
  const response = await api.post(`/admin/impersonate/${userId}`)
  return response.data
}

export async function listImpersonationSessions() {
  const response = await api.get('/admin/impersonate/sessions')
  return response.data
}

export async function revokeImpersonationSession(sessionId) {
  const response = await api.delete(`/admin/impersonate/sessions/${sessionId}`)
  return response.data
}

export async function requestErasure(tenantId) {
  const response = await api.post(`/admin/tenants/${tenantId}/anonymize`, { confirm: true })
  return response.data
}

export async function getErasureLogs(tenantId) {
  const response = await api.get(`/admin/tenants/${tenantId}/anonymize`)
  return response.data
}

export async function getAdminPlanFeatures(planId) {
  const response = await api.get(`/admin/plans/${planId}/features`)
  return response.data
}

export async function updatePlanFeature(planId, featureFlagId, enabled) {
  const response = await api.put(`/admin/plans/${planId}/features/${featureFlagId}`, { enabled })
  return response.data
}

export async function deletePlanFeature(planId, featureFlagId) {
  const response = await api.delete(`/admin/plans/${planId}/features/${featureFlagId}`)
  return response.data
}

export default api
