import { useState, useCallback, useEffect, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import { 
  Upload, FileText, X, Loader2, AlertCircle, CheckCircle, 
  Sparkles, ChevronRight, BookOpen, LayoutTemplate, Link2, 
  FileUp, Type, Save, Clock, Trophy, Eye, Download, CheckCircle2, ArrowLeft,
  FileCheck, XCircle, Hourglass
} from 'lucide-react'
import { 
  analyzeResumeStream, 
  analyzeBatchStream, 
  extractJdFromUrl, 
  getTemplates, 
  createTemplate,
  createTemplateFromFile,
  getNarrative,
  checkHealth,
} from '../lib/api'
import { useUsageCheck, useSubscription } from '../hooks/useSubscription'
import WeightSuggestionPanel from '../components/WeightSuggestionPanel'
import UniversalWeightsPanel from '../components/UniversalWeightsPanel'
import { FitBadge, RecommendBadge, NarrativeStatusBadge } from '../components/Badges'

const DEFAULT_WEIGHTS = {
  core_competencies: 0.30,
  experience: 0.20,
  domain_fit: 0.20,
  education: 0.10,
  career_trajectory: 0.10,
  role_excellence: 0.10,
  risk: -0.10,
}

// ── IndexedDB helpers for JD file caching ──
const JD_DB_NAME = 'aria_jd_cache'
const JD_STORE_NAME = 'jd_files'
const JD_DB_VERSION = 1

function openJdDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(JD_DB_NAME, JD_DB_VERSION)
    request.onerror = () => reject(request.error)
    request.onsuccess = () => resolve(request.result)
    request.onupgradeneeded = (event) => {
      const db = event.target.result
      if (!db.objectStoreNames.contains(JD_STORE_NAME)) {
        db.createObjectStore(JD_STORE_NAME)
      }
    }
  })
}

async function storeJdFile(file) {
  const db = await openJdDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(JD_STORE_NAME, 'readwrite')
    const store = tx.objectStore(JD_STORE_NAME)
    const req = store.put(file, 'jd_file')
    req.onsuccess = () => resolve()
    req.onerror = () => reject(req.error)
  })
}

async function getJdFile() {
  const db = await openJdDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(JD_STORE_NAME, 'readonly')
    const store = tx.objectStore(JD_STORE_NAME)
    const req = store.get('jd_file')
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

async function clearJdFile() {
  const db = await openJdDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(JD_STORE_NAME, 'readwrite')
    const store = tx.objectStore(JD_STORE_NAME)
    const req = store.delete('jd_file')
    req.onsuccess = () => resolve()
    req.onerror = () => reject(req.error)
  })
}

export default function AnalyzePage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { checkBeforeAnalysis, getRemainingAnalyses } = useUsageCheck()
  const { subscription, refreshAfterAnalysis } = useSubscription()

  // Step 1: Job Description
  const [jdText, setJdText] = useState('')
  const [jdMode, setJdMode] = useState('text')
  const [jdFile, setJdFile] = useState(null)
  const [urlInput, setUrlInput] = useState('')
  const [urlLoading, setUrlLoading] = useState(false)
  const [urlError, setUrlError] = useState('')

  // Step 2: Weights
  const [weights, setWeights] = useState(DEFAULT_WEIGHTS)
  const [roleCategory, setRoleCategory] = useState('general')
  const [showAiSuggestion, setShowAiSuggestion] = useState(false)

  // Step 3: Resume Upload
  const [files, setFiles] = useState([])
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [error, setError] = useState('')

  // Streaming analysis state for batch analysis
  const [streamingResults, setStreamingResults] = useState([])
  const [streamingFailed, setStreamingFailed] = useState([])
  const [analysisProgress, setAnalysisProgress] = useState({ completed: 0, total: 0 })
  const [analysisDone, setAnalysisDone] = useState(false)
  const [fileStatuses, setFileStatuses] = useState([])
  const [batchStartTime, setBatchStartTime] = useState(null)

  // UI State
  const [currentStep, setCurrentStep] = useState(1)
  const [draftSaved, setDraftSaved] = useState(false)
  const [showJdLibrary, setShowJdLibrary] = useState(false)
  const [savedJds, setSavedJds] = useState([])
  const [loadedFromLibrary, setLoadedFromLibrary] = useState(false)
  const [loadedTemplateId, setLoadedTemplateId] = useState(null)
  const jdLibraryRef = useRef(null)

  // Reset analysis state on fresh mount
  useEffect(() => {
    setError('')
    return () => {
      // Cleanup on unmount
      setError('')
    }
  }, [])

  // Lightweight health check on mount
  useEffect(() => {
    checkHealth().catch(() => {
      setError('Backend service may be unavailable. Please try again shortly.')
    })
  }, [])

  // Clean up old report entries in sessionStorage
  useEffect(() => {
    const keysToRemove = []
    for (let i = 0; i < sessionStorage.length; i++) {
      const key = sessionStorage.key(i)
      if (key && key.startsWith('report_')) {
        keysToRemove.push(key)
      }
    }
    // Keep only the 10 most recent
    if (keysToRemove.length > 10) {
      keysToRemove.slice(0, keysToRemove.length - 10).forEach(k => sessionStorage.removeItem(k))
    }
  }, [])

  // Load saved JDs
  useEffect(() => {
    getTemplates()
      .then((res) => {
        const arr = Array.isArray(res) ? res : res?.templates || []
        setSavedJds(arr)
      })
      .catch(() => setSavedJds([]))
  }, [])

  // Auto-save draft to localStorage
  useEffect(() => {
    if (jdText || Object.keys(weights).length > 0) {
      const draft = {
        jd_text: jdText,
        weights: weights,
        role_category: roleCategory,
        timestamp: new Date().toISOString()
      }
      localStorage.setItem('aria_draft_jd', JSON.stringify(draft))
      setDraftSaved(true)
      setTimeout(() => setDraftSaved(false), 2000)
    }
  }, [jdText, weights, roleCategory])

  // Restore draft on mount
  useEffect(() => {
    const draft = localStorage.getItem('aria_draft_jd')
    if (draft) {
      try {
        const { jd_text, weights: savedWeights, role_category } = JSON.parse(draft)
        if (jd_text) setJdText(jd_text)
        if (savedWeights) setWeights(savedWeights)
        if (role_category) setRoleCategory(role_category)
      } catch (e) {
        console.error('Failed to restore draft:', e)
      }
    }
  }, [])

  // Load JD from location state (from JD Library or ReportPage)
  useEffect(() => {
    if (location.state?.jd_text) {
      setJdText(location.state.jd_text)
      if (location.state.weights) {
        setWeights(location.state.weights)
      }
      if (location.state.role_category) {
        setRoleCategory(location.state.role_category)
      }
      // Mark as loaded from library to prevent duplicate JD creation
      if (location.state.template_id) {
        setLoadedFromLibrary(true)
        setLoadedTemplateId(location.state.template_id)
      }
    }
  }, [location.state])

  // Load file JD from IndexedDB and auto-skip when returning from ReportPage
  useEffect(() => {
    if (location.state?.jd_mode === 'file') {
      getJdFile().then(file => {
        if (file) {
          setJdFile(file)
          setJdMode('file')
          if (location.state.weights) {
            setWeights(location.state.weights)
          }
          if (location.state.role_category) {
            setRoleCategory(location.state.role_category)
          }
          setCurrentStep(3)
        }
      }).catch((err) => {
        console.warn('Failed to load from IndexedDB:', err)
        setError('Failed to load saved data. You can continue with a fresh analysis.')
      })
    }
  }, [location.state])

  // Auto-skip to upload when returning with text JD context
  useEffect(() => {
    if (location.state?.jd_text && location.state?.weights) {
      setCurrentStep(3)
    }
  }, [location.state])

  // Close JD library on outside click
  useEffect(() => {
    const handleClick = (e) => {
      if (jdLibraryRef.current && !jdLibraryRef.current.contains(e.target)) {
        setShowJdLibrary(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  // Poll for narrative completion on batch results
  useEffect(() => {
    if (!analysisDone || !streamingResults.length) return

    const pendingIds = streamingResults
      .filter(item => item.screeningResultId && (
        item.result?.narrative_pending === true ||
        item.result?.narrative_status === 'pending' ||
        item.result?.narrative_status === 'processing'
      ))
      .map(item => item.screeningResultId)

    if (!pendingIds.length) return

    let pollCount = 0
    const maxPolls = 120 // 6 minutes max

    const poll = async () => {
      pollCount++
      if (pollCount > maxPolls) return

      const stillPending = []

      for (const id of pendingIds) {
        try {
          const data = await getNarrative(id)
          if (data.status === 'ready' || data.status === 'failed') {
            setStreamingResults(prev => prev.map(item => {
              if (item.screeningResultId !== id) return item
              const updatedResult = {
                ...item.result,
                ...(data.narrative || {}),
                narrative_status: data.status,
                narrative_pending: false,
                ai_enhanced: data.status === 'ready',
              }
              try { sessionStorage.setItem(`report_${id}`, JSON.stringify(updatedResult)) } catch {}
              return { ...item, result: updatedResult }
            }))
          } else {
            stillPending.push(id)
          }
        } catch (e) {
          stillPending.push(id)
        }
      }

      if (stillPending.length && pollCount < maxPolls) {
        setTimeout(poll, 3000)
      }
    }

    const timer = setTimeout(poll, 2000)
    return () => clearTimeout(timer)
  }, [analysisDone])

  // Handle URL extraction
  const handleExtractUrl = async () => {
    if (!urlInput.trim()) return
    setUrlLoading(true)
    setUrlError('')
    try {
      const result = await extractJdFromUrl(urlInput.trim())
      setJdText(result.jd_text)
      setJdMode('text')
      setShowAiSuggestion(true)
    } catch (err) {
      setUrlError(err.response?.data?.detail || 'Failed to extract JD from URL')
    } finally {
      setUrlLoading(false)
    }
  }

  // Handle JD file upload
  const onJdDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      setJdFile(acceptedFiles[0])
      setJdMode('file')
    }
  }, [])

  const { getRootProps: getJdRootProps, getInputProps: getJdInputProps, isDragActive: isJdDragActive } = useDropzone({
    onDrop: onJdDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc'],
      'text/plain': ['.txt'],
    },
    maxFiles: 1,
    maxSize: 5 * 1024 * 1024
  })

  // Handle resume file upload
  const onResumeDrop = useCallback((acceptedFiles) => {
    setFiles(prev => [...prev, ...acceptedFiles])
  }, [])

  const { getRootProps: getResumeRootProps, getInputProps: getResumeInputProps, isDragActive: isResumeDragActive } = useDropzone({
    onDrop: onResumeDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc']
    },
    maxFiles: 50,
    maxSize: 10 * 1024 * 1024
  })

  const removeFile = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  // Handle AI weight acceptance
  const handleWeightsAccepted = (suggestedWeights) => {
    setWeights(suggestedWeights)
    setShowAiSuggestion(false)
  }

  // Load JD from library
  const handleLoadJd = (template) => {
    setJdText(template.jd_text)
    setJdMode('text')
    setShowJdLibrary(false)
    
    // Mark as loaded from library to prevent duplicate save
    setLoadedFromLibrary(true)
    setLoadedTemplateId(template.id)
    
    // Load weights if available
    let hasWeights = false
    if (template.scoring_weights) {
      try {
        const savedWeights = typeof template.scoring_weights === 'string' 
          ? JSON.parse(template.scoring_weights) 
          : template.scoring_weights
        
        // Only set weights if they're valid and not empty
        if (savedWeights && Object.keys(savedWeights).length > 0) {
          setWeights(savedWeights)
          hasWeights = true
        }
      } catch (e) {
        console.error('Failed to parse weights:', e)
      }
    }
    
    // Only trigger AI suggestion if weights are NOT available
    // This prevents unnecessary LLM calls when weights are already saved
    if (!hasWeights) {
      setShowAiSuggestion(true)
    }
  }

  // Handle analysis
  const handleAnalyze = async () => {
    // Validation
    const effectiveJd = jdMode === 'text' ? jdText : jdFile
    if (!effectiveJd) {
      setError('Please provide a job description')
      return
    }
    if (files.length === 0) {
      setError('Please upload at least one resume')
      return
    }

    // Check usage limits
    const check = await checkBeforeAnalysis(files.length)
    if (!check.allowed) {
      setError(check.message || 'Usage limit exceeded. Please upgrade your plan.')
      return
    }

    setError('')

    // Persist JD context so ReportPage can offer "Analyze Another"
    if (jdMode === 'text' && jdText) {
      sessionStorage.setItem('aria_active_jd', JSON.stringify({
        jd_text: jdText,
        weights,
        role_category: roleCategory,
        jd_mode: 'text'
      }))
      clearJdFile().catch(() => {})
    } else if (jdMode === 'file' && jdFile) {
      try {
        await storeJdFile(jdFile)
        sessionStorage.setItem('aria_active_jd', JSON.stringify({
          weights,
          role_category: roleCategory,
          jd_mode: 'file',
          file_name: jdFile.name
        }))
      } catch { /* ignore */ }
    }

    setIsAnalyzing(true)

    try {
      // Only save JD template if it's NEW (not loaded from library)
      // This prevents duplicate JD creation
      if (!loadedFromLibrary) {
        const templateName = `${roleCategory || 'General'} - ${new Date().toLocaleDateString()}`
        if (jdMode === 'text') {
          await createTemplate({
            name: templateName,
            jd_text: jdText,
            scoring_weights: weights,
            tags: roleCategory
          })
        } else {
          await createTemplateFromFile(templateName, jdFile, roleCategory, weights)
        }
      }

      // Run analysis - auto-detect single vs batch
      if (files.length === 1) {
        // Single analysis
        const result = await analyzeResumeStream(
          files[0],
          jdMode === 'text' ? jdText : null,
          jdMode === 'file' ? jdFile : null,
          weights,
          null,  // onStageComplete
          loadedTemplateId,
        )
        navigate('/report', { state: { result } })
      } else {
        // Batch analysis with SSE streaming
        setStreamingResults([])
        setStreamingFailed([])
        setAnalysisDone(false)
        setAnalysisProgress({ completed: 0, total: 0 })
        setBatchStartTime(Date.now())
        // Initialize per-file status tracking
        setFileStatuses(files.map((f, i) => ({
          filename: f.name,
          status: 'queued',
          index: i + 1,
        })))

        await analyzeBatchStream(
          files,
          jdMode === 'text' ? jdText : null,
          jdMode === 'file' ? jdFile : null,
          weights,
          {
            onProcessing: (index, total, filename) => {
              setIsAnalyzing(true)
              setAnalysisProgress(prev => ({ ...prev, total }))
              setFileStatuses(prev => prev.map(fs =>
                fs.filename === filename
                  ? { ...fs, status: 'processing', startTime: Date.now() }
                  : fs.status === 'queued' ? fs : fs
              ))
            },
            onResult: (index, total, filename, result, screeningResultId) => {
              setIsAnalyzing(true)
              setAnalysisProgress({ completed: index, total })
              setStreamingResults(prev => {
                const updated = [...prev, { filename, result, screeningResultId }]
                return updated.sort((a, b) => (b.result?.fit_score || 0) - (a.result?.fit_score || 0))
              })
              setFileStatuses(prev => prev.map(fs =>
                fs.filename === filename
                  ? { ...fs, status: 'completed', result, screeningResultId, endTime: Date.now() }
                  : fs
              ))
              if (screeningResultId) {
                try { sessionStorage.setItem(`report_${screeningResultId}`, JSON.stringify(result)) } catch {}
              }
            },
            onFailed: (index, total, filename, error) => {
              setIsAnalyzing(true)
              setAnalysisProgress(prev => ({ completed: prev.completed, total: total || prev.total }))
              setStreamingFailed(prev => [...prev, { filename, error }])
              setFileStatuses(prev => prev.map(fs =>
                fs.filename === filename
                  ? { ...fs, status: 'failed', error, endTime: Date.now() }
                  : fs
              ))
            },
            onDone: (total, successful, failedCount) => {
              setAnalysisDone(true)
              setIsAnalyzing(false)
              setAnalysisProgress({ completed: total, total })
            }
          },
          loadedTemplateId,
        )
      }

      // Clear draft
      localStorage.removeItem('aria_draft_jd')

      // Refresh subscription usage
      await refreshAfterAnalysis(files.length)

    } catch (err) {
      const detail = err.response?.data?.detail
      setError(
        (Array.isArray(detail) ? 'Validation error — check file types or JD format.' : detail) ||
        err.message ||
        'Analysis failed'
      )
    } finally {
      setIsAnalyzing(false)
    }
  }

  const isStep1Complete = jdMode === 'text' ? jdText.trim().length > 50 : jdFile !== null
  const isStep2Complete = weights && Object.keys(weights).length > 0
  const isStep3Complete = files.length > 0

  const remainingAnalyses = getRemainingAnalyses()

  // Determine if results area should be visible
  const showResults = isAnalyzing || analysisDone || streamingResults.length > 0 || streamingFailed.length > 0

  // Reset for new batch
  const handleNewBatch = () => {
    setStreamingResults([])
    setStreamingFailed([])
    setAnalysisDone(false)
    setIsAnalyzing(false)
    setAnalysisProgress({ completed: 0, total: 0 })
    setFileStatuses([])
    setBatchStartTime(null)
    setFiles([])
    setCurrentStep(3)
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-extrabold text-brand-900 tracking-tight">New Analysis</h1>
        <p className="text-slate-500 text-sm mt-1 font-medium">
          Follow the 3-step process to analyze resumes with AI-powered scoring
          {remainingAnalyses !== undefined && remainingAnalyses !== Infinity && (
            <span className="ml-2 text-brand-600 font-semibold">
              ({remainingAnalyses} analyses remaining)
            </span>
          )}
        </p>
      </div>

      {/* Progress Steps */}
      <div className="mb-8 flex items-center justify-between">
        {[
          { num: 1, label: 'Job Description', complete: isStep1Complete },
          { num: 2, label: 'Scoring Weights', complete: isStep2Complete },
          { num: 3, label: 'Upload Resumes', complete: isStep3Complete }
        ].map((step, idx) => (
          <div key={step.num} className="flex items-center flex-1">
            <button
              onClick={() => setCurrentStep(step.num)}
              className={`flex items-center gap-3 ${currentStep === step.num ? 'opacity-100' : 'opacity-60 hover:opacity-80'} transition-opacity`}
            >
              <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm transition-all ${
                step.complete 
                  ? 'bg-green-500 text-white ring-4 ring-green-100' 
                  : currentStep === step.num
                  ? 'bg-brand-600 text-white ring-4 ring-brand-100'
                  : 'bg-slate-200 text-slate-600'
              }`}>
                {step.complete ? <CheckCircle className="w-5 h-5" /> : step.num}
              </div>
              <span className={`text-sm font-semibold ${currentStep === step.num ? 'text-brand-900' : 'text-slate-600'}`}>
                {step.label}
              </span>
            </button>
            {idx < 2 && (
              <ChevronRight className="w-5 h-5 text-slate-300 mx-2 flex-shrink-0" />
            )}
          </div>
        ))}
      </div>

      {/* Draft saved indicator */}
      {draftSaved && (
        <div className="mb-4 flex items-center gap-2 text-sm text-green-600 bg-green-50 px-4 py-2 rounded-xl ring-1 ring-green-200">
          <Clock className="w-4 h-4" />
          Draft saved locally
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="mb-6 flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-2xl">
          <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-semibold text-red-900">Error</p>
            <p className="text-sm text-red-700 mt-1">{error}</p>
          </div>
          <button
            onClick={() => { setError('') }}
            className="ml-4 px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Step 1: Job Description */}
      {currentStep === 1 && (
        <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand-xl p-6 md:p-8 card-animate">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-brand-900">Step 1: Job Description</h2>
            <div className="relative" ref={jdLibraryRef}>
              <button
                onClick={() => setShowJdLibrary(!showJdLibrary)}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-brand-700 bg-brand-50 hover:bg-brand-100 rounded-xl transition-colors ring-1 ring-brand-200"
              >
                <LayoutTemplate className="w-4 h-4" />
                Load from Library
              </button>
              
              {showJdLibrary && savedJds.length > 0 && (
                <div className="absolute right-0 top-full mt-2 w-80 bg-white rounded-2xl shadow-brand-lg ring-1 ring-brand-100 p-4 z-10 max-h-96 overflow-y-auto">
                  <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide mb-3">Saved Job Descriptions</p>
                  <div className="space-y-2">
                    {savedJds.map(jd => (
                      <button
                        key={jd.id}
                        onClick={() => handleLoadJd(jd)}
                        className="w-full text-left p-3 rounded-xl hover:bg-brand-50 transition-colors ring-1 ring-slate-100 hover:ring-brand-200"
                      >
                        <p className="text-sm font-semibold text-brand-900 truncate">{jd.name}</p>
                        <p className="text-xs text-slate-500 mt-1">
                          {new Date(jd.created_at).toLocaleDateString()}
                        </p>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* JD Mode Tabs */}
          <div className="flex gap-2 mb-4">
            {[
              { mode: 'text', icon: Type, label: 'Paste Text' },
              { mode: 'file', icon: FileUp, label: 'Upload File' },
              { mode: 'url', icon: Link2, label: 'Extract from URL' }
            ].map(({ mode, icon: Icon, label }) => (
              <button
                key={mode}
                onClick={() => setJdMode(mode)}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                  jdMode === mode
                    ? 'bg-brand-600 text-white shadow-brand-sm'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
              </button>
            ))}
          </div>

          {/* JD Input */}
          {jdMode === 'text' && (
            <div>
              <textarea
                value={jdText}
                onChange={(e) => {
                  setJdText(e.target.value)
                  if (e.target.value.length > 100 && !showAiSuggestion) {
                    setShowAiSuggestion(true)
                  }
                }}
                placeholder="Paste the job description here... (minimum 50 characters)"
                className="w-full h-64 px-4 py-3 border border-brand-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none text-sm"
              />
              <p className="text-xs text-slate-500 mt-2">
                {jdText.length} characters • {jdText.split(/\s+/).filter(Boolean).length} words
              </p>
            </div>
          )}

          {jdMode === 'file' && (
            <div
              {...getJdRootProps()}
              className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all ${
                isJdDragActive
                  ? 'border-brand-500 bg-brand-50'
                  : jdFile
                  ? 'border-brand-200 bg-brand-50/40'
                  : 'border-brand-200 hover:border-brand-400 hover:bg-brand-50/40'
              }`}
            >
              <input {...getJdInputProps()} />
              {jdFile ? (
                <div className="flex items-center justify-center gap-3">
                  <FileText className="w-8 h-8 text-brand-600" />
                  <div>
                    <p className="font-semibold text-brand-900">{jdFile.name}</p>
                    <p className="text-xs text-slate-500">{(jdFile.size / 1024).toFixed(1)} KB</p>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      setJdFile(null)
                    }}
                    className="ml-4 p-2 hover:bg-red-50 rounded-lg transition-colors"
                  >
                    <X className="w-4 h-4 text-red-600" />
                  </button>
                </div>
              ) : (
                <div>
                  <FileUp className="w-12 h-12 text-brand-400 mx-auto mb-3" />
                  <p className="text-sm font-medium text-slate-700">Drop JD file here or click to browse</p>
                  <p className="text-xs text-slate-500 mt-1">PDF, DOCX, or TXT (max 5MB)</p>
                </div>
              )}
            </div>
          )}

          {jdMode === 'url' && (
            <div>
              <div className="flex gap-2">
                <input
                  type="url"
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  placeholder="https://example.com/job-posting"
                  className="flex-1 px-4 py-3 border border-brand-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-brand-500 text-sm"
                />
                <button
                  onClick={handleExtractUrl}
                  disabled={urlLoading || !urlInput.trim()}
                  className="px-6 py-3 bg-brand-600 text-white rounded-2xl font-medium hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                >
                  {urlLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Extracting...
                    </>
                  ) : (
                    'Extract'
                  )}
                </button>
              </div>
              {urlError && (
                <p className="text-sm text-red-600 mt-2">{urlError}</p>
              )}
            </div>
          )}

          {/* Next Button */}
          <div className="mt-6 flex justify-end">
            <button
              onClick={() => setCurrentStep(2)}
              disabled={!isStep1Complete}
              className="flex items-center gap-2 px-6 py-3 bg-brand-600 text-white rounded-2xl font-semibold hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-brand-sm"
            >
              Next: Configure Weights
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Scoring Weights */}
      {currentStep === 2 && (
        <div className="space-y-6 card-animate">
          <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand-xl p-6 md:p-8">
            <h2 className="text-xl font-bold text-brand-900 mb-6">Step 2: Scoring Weights</h2>

            {/* AI Suggestion Panel */}
            {showAiSuggestion && jdText && (
              <div className="mb-6">
                <WeightSuggestionPanel
                  jobDescription={jdText}
                  onWeightsAccepted={handleWeightsAccepted}
                  currentWeights={weights}
                />
              </div>
            )}

            {/* Universal Weights Panel */}
            <UniversalWeightsPanel
              weights={weights}
              onChange={setWeights}
              roleCategory={roleCategory}
              onRoleCategoryChange={setRoleCategory}
            />

            {/* Navigation */}
            <div className="mt-6 flex justify-between">
              <button
                onClick={() => setCurrentStep(1)}
                className="flex items-center gap-2 px-6 py-3 bg-slate-100 text-slate-700 rounded-2xl font-semibold hover:bg-slate-200 transition-colors"
              >
                <ChevronRight className="w-4 h-4 rotate-180" />
                Back
              </button>
              <button
                onClick={() => setCurrentStep(3)}
                disabled={!isStep2Complete}
                className="flex items-center gap-2 px-6 py-3 bg-brand-600 text-white rounded-2xl font-semibold hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-brand-sm"
              >
                Next: Upload Resumes
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Step 3: Upload Resumes */}
      {currentStep === 3 && !showResults && (
        <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand-xl p-6 md:p-8 card-animate">
          <h2 className="text-xl font-bold text-brand-900 mb-6">Step 3: Upload Resumes</h2>

          {/* Analysis Type Indicator */}
          <div className="mb-6 p-4 bg-brand-50 rounded-2xl ring-1 ring-brand-200">
            <div className="flex items-center gap-3">
              <Sparkles className="w-5 h-5 text-brand-600" />
              <div>
                <p className="text-sm font-semibold text-brand-900">
                  {files.length === 0 ? 'Ready for Analysis' : files.length === 1 ? 'Single Analysis' : `Batch Analysis (${files.length} resumes)`}
                </p>
                <p className="text-xs text-slate-600 mt-0.5">
                  {files.length === 0 
                    ? 'Upload 1 resume for detailed analysis or multiple for batch processing'
                    : files.length === 1
                    ? 'Detailed report with full analysis and interview questions'
                    : 'Ranked shortlist with comparative scoring'
                  }
                </p>
              </div>
            </div>
          </div>

          {/* Resume Upload */}
          <div
            {...getResumeRootProps()}
            className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all mb-4 ${
              isResumeDragActive
                ? 'border-brand-500 bg-brand-50'
                : files.length > 0
                ? 'border-brand-200 bg-brand-50/40'
                : 'border-brand-200 hover:border-brand-400 hover:bg-brand-50/40'
            }`}
          >
            <input {...getResumeInputProps()} />
            <Upload className="w-12 h-12 text-brand-400 mx-auto mb-3" />
            <p className="text-sm font-medium text-slate-700">
              {files.length > 0 ? 'Drop more resumes or click to add' : 'Drop resumes here or click to browse'}
            </p>
            <p className="text-xs text-slate-500 mt-1">PDF or DOCX (max 10MB each, up to 50 files)</p>
          </div>

          {/* File List */}
          {files.length > 0 && (
            <div className="space-y-2 mb-6">
              <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
                {files.length} Resume{files.length > 1 ? 's' : ''} Ready
              </p>
              <div className="max-h-64 overflow-y-auto space-y-2">
                {files.map((file, idx) => (
                  <div key={idx} className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl ring-1 ring-slate-200">
                    <FileText className="w-5 h-5 text-brand-600 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-900 truncate">{file.name}</p>
                      <p className="text-xs text-slate-500">{(file.size / 1024).toFixed(1)} KB</p>
                    </div>
                    <button
                      onClick={() => removeFile(idx)}
                      className="p-2 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      <X className="w-4 h-4 text-red-600" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Navigation */}
          <div className="flex justify-between">
            <button
              onClick={() => setCurrentStep(2)}
              className="flex items-center gap-2 px-6 py-3 bg-slate-100 text-slate-700 rounded-2xl font-semibold hover:bg-slate-200 transition-colors"
            >
              <ChevronRight className="w-4 h-4 rotate-180" />
              Back
            </button>
            <button
              onClick={handleAnalyze}
              disabled={!isStep3Complete || isAnalyzing}
              className="flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-brand-600 to-brand-500 text-white rounded-2xl font-bold hover:shadow-brand-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-brand-sm"
            >
              {isAnalyzing && files.length === 1 ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5" />
                  Analyze {files.length} Resume{files.length > 1 ? 's' : ''}
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Step 4: Batch Analysis Results */}
      {showResults && (
        <div className="space-y-6 card-animate">
          {/* Header with back button */}
          <div className="flex items-center justify-between">
            <button
              onClick={handleNewBatch}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-brand-700 bg-brand-50 hover:bg-brand-100 rounded-xl transition-colors ring-1 ring-brand-200"
            >
              <ArrowLeft className="w-4 h-4" />
              New Batch
            </button>
            {analysisDone && (
              <button
                onClick={() => navigate('/candidates')}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-xl transition-colors shadow-brand-sm"
              >
                <Eye className="w-4 h-4" />
                View All Candidates
              </button>
            )}
          </div>

          {/* Analysis Progress Section */}
          {(isAnalyzing || analysisDone || streamingResults.length > 0) && (
            <div className="p-4 bg-indigo-50 ring-1 ring-indigo-200 rounded-2xl space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-indigo-900">
                    {analysisDone
                      ? `Analysis Complete: ${streamingResults.length} successful${streamingFailed.length ? `, ${streamingFailed.length} failed` : ''}`
                      : `Analyzing: ${analysisProgress.completed} of ${analysisProgress.total}...`
                    }
                  </h3>
                  {/* Time estimate */}
                  {!analysisDone && batchStartTime && analysisProgress.completed > 0 && (
                    <p className="text-xs text-indigo-600 mt-0.5">
                      {(() => {
                        const elapsed = Date.now() - batchStartTime
                        const avgPerFile = elapsed / analysisProgress.completed
                        const remaining = analysisProgress.total - analysisProgress.completed
                        const etaMs = avgPerFile * remaining
                        if (etaMs < 5000) return 'Almost done...'
                        if (etaMs < 60000) return `~${Math.ceil(etaMs / 1000)}s remaining`
                        return `~${Math.ceil(etaMs / 60000)}min remaining`
                      })()}
                    </p>
                  )}
                </div>
                {!analysisDone && (
                  <Loader2 className="w-5 h-5 text-indigo-500 animate-spin" />
                )}
                {analysisDone && (
                  <CheckCircle2 className="w-5 h-5 text-green-600" />
                )}
              </div>
              {!analysisDone && analysisProgress.total > 0 && (
                <div className="w-full bg-indigo-100 rounded-full h-2 overflow-hidden">
                  <div 
                    className="bg-indigo-500 h-full transition-all duration-500 ease-out"
                    style={{ width: `${analysisProgress.total > 0 ? (analysisProgress.completed / analysisProgress.total) * 100 : 0}%` }}
                  />
                </div>
              )}

              {/* Per-file status cards */}
              {fileStatuses.length > 0 && (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                  {fileStatuses.map((fs) => {
                    const isQueued = fs.status === 'queued'
                    const isProcessing = fs.status === 'processing'
                    const isCompleted = fs.status === 'completed'
                    const isFailed = fs.status === 'failed'
                    return (
                      <div
                        key={fs.filename}
                        className={`flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-xs font-medium transition-all duration-300 ${
                          isQueued ? 'bg-slate-100 text-slate-500 ring-1 ring-slate-200' :
                          isProcessing ? 'bg-indigo-100 text-indigo-700 ring-1 ring-indigo-200 shadow-sm' :
                          isCompleted ? 'bg-green-50 text-green-800 ring-1 ring-green-200' :
                          'bg-red-50 text-red-700 ring-1 ring-red-200'
                        }`}
                      >
                        <div className="shrink-0">
                          {isQueued && <Hourglass className="w-4 h-4" />}
                          {isProcessing && <Loader2 className="w-4 h-4 animate-spin" />}
                          {isCompleted && <FileCheck className="w-4 h-4 text-green-600" />}
                          {isFailed && <XCircle className="w-4 h-4 text-red-600" />}
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="truncate">{fs.filename}</p>
                          {isCompleted && fs.result?.fit_score != null && (
                            <p className="text-[10px] opacity-80">
                              Score: <span className="font-bold">{fs.result.fit_score}</span>
                              {' · '}
                              {fs.result.final_recommendation || '—'}
                            </p>
                          )}
                          {isFailed && fs.error && (
                            <p className="text-[10px] opacity-80 truncate">{fs.error}</p>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )}

          {/* Results header */}
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div>
              <h3 className="text-xl font-extrabold text-brand-900 tracking-tight">Ranked Shortlist</h3>
              <p className="text-sm text-slate-500 font-medium">
                {streamingResults.length} successful{streamingFailed.length ? `, ${streamingFailed.length} failed` : ''} candidates analyzed
              </p>
            </div>
          </div>

          {/* Results Table */}
          {streamingResults.length > 0 && (
            <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-brand-50 border-b border-brand-100">
                  <tr>
                    <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Rank</th>
                    <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">File</th>
                    <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Score</th>
                    <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Recommendation</th>
                    <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Risk</th>
                    <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {streamingResults.map((item, idx) => {
                    const r   = item.result
                    const id  = item.screeningResultId
                    const rank = idx + 1
                    return (
                      <tr key={id || idx} className="border-b border-brand-50 hover:bg-brand-50/40 transition-all duration-300">
                        <td className="px-4 py-3.5">
                          <div className="flex items-center gap-1.5">
                            {rank === 1 && <Trophy className="w-4 h-4 text-amber-500" />}
                            <span className="font-extrabold text-brand-900">#{rank}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3.5 text-brand-900 font-medium max-w-[200px] truncate">{item.filename}</td>
                        <td className="px-4 py-3.5"><FitBadge score={r?.fit_score} /></td>
                        <td className="px-4 py-3.5"><RecommendBadge rec={r?.final_recommendation} /></td>
                        <td className="px-4 py-3.5">
                          <span className={`text-xs font-bold ${
                            !r?.risk_level       ? 'text-slate-400' :
                            r.risk_level === 'Low'  ? 'text-green-700' :
                            r.risk_level === 'High' ? 'text-red-700'   : 'text-amber-700'
                          }`}>{r?.risk_level || '—'}</span>
                        </td>
                        <td className="px-4 py-3.5">
                          <div className="flex items-center gap-2">
                            <NarrativeStatusBadge result={r} />
                            <button
                              onClick={() => navigate(`/report?id=${id}`, { state: { from: '/analyze', result: r } })}
                              className="flex items-center gap-1 text-xs text-brand-600 hover:text-brand-700 font-bold hover:underline"
                            >
                              <Eye className="w-3.5 h-3.5" />
                              View Report
                            </button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Failed Resumes Section */}
          {streamingFailed.length > 0 && (
            <div className="bg-red-50/80 backdrop-blur-md rounded-3xl ring-1 ring-red-200 shadow-sm overflow-hidden">
              <div className="px-5 py-4 border-b border-red-200 bg-red-100/50">
                <div className="flex items-center gap-2.5">
                  <AlertCircle className="w-5 h-5 text-red-600" />
                  <h4 className="text-base font-bold text-red-800">
                    Failed Resumes ({streamingFailed.length})
                  </h4>
                </div>
                <p className="text-sm text-red-600 mt-1 ml-8">
                  The following resumes could not be processed:
                </p>
              </div>
              <div className="divide-y divide-red-100">
                {streamingFailed.map((item, idx) => (
                  <div key={idx} className="px-5 py-3.5 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-xl bg-red-100 flex items-center justify-center shrink-0">
                        <FileText className="w-4 h-4 text-red-600" />
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-red-900">{item.filename}</p>
                        <p className="text-xs text-red-600 mt-0.5">{item.error || 'Unknown error'}</p>
                      </div>
                    </div>
                    <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-red-100 text-red-700 ring-1 ring-red-200">
                      Failed
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
