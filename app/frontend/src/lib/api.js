import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || '/api'

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'multipart/form-data'
  }
})

export async function analyzeResume(file, jobDescription, jobFile = null) {
  const formData = new FormData()
  formData.append('resume', file)
  
  if (jobFile) {
    formData.append('job_file', jobFile)
  } else {
    formData.append('job_description', jobDescription)
  }

  const response = await api.post('/analyze', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    },
    timeout: 90000 // 90 seconds for LLM processing
  })

  return response.data
}

export async function getHistory() {
  const response = await api.get('/history')
  return response.data
}

export async function checkHealth() {
  const response = await api.get('/health')
  return response.data
}

export default api
