import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || '/api'

const api = axios.create({
  baseURL: API_URL,
})

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Auto-refresh on 401
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        try {
          const res = await axios.post(`${API_URL}/auth/refresh`, { refresh_token: refreshToken })
          localStorage.setItem('access_token', res.data.access_token)
          original.headers.Authorization = `Bearer ${res.data.access_token}`
          return api(original)
        } catch {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/login'
        }
      } else {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

// ─── Resume Analysis ──────────────────────────────────────────────────────────

export async function analyzeResume(file, jobDescription, jobFile = null, scoringWeights = null) {
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
  const response = await api.post('/analyze', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 90000,
  })
  return response.data
}

export async function analyzeBatch(files, jobDescription, jobFile = null, scoringWeights = null) {
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
  const response = await api.post('/analyze/batch', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000,
  })
  return response.data
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

// ─── Templates ───────────────────────────────────────────────────────────────

export async function getTemplates() {
  const res = await api.get('/templates')
  return res.data
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

export async function getTranscriptAnalyses() {
  const res = await api.get('/transcript/analyses')
  return res.data
}

export async function getTranscriptAnalysis(id) {
  const res = await api.get(`/transcript/analyses/${id}`)
  return res.data
}

// ─── Health ───────────────────────────────────────────────────────────────────

export async function checkHealth() {
  const response = await api.get('/health')
  return response.data
}

export default api
