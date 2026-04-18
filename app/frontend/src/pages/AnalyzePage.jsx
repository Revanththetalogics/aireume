import { useState, useCallback, useEffect, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import { 
  Upload, FileText, X, Loader2, AlertCircle, CheckCircle, 
  Sparkles, ChevronRight, BookOpen, LayoutTemplate, Link2, 
  FileUp, Type, Save, Clock
} from 'lucide-react'
import { 
  analyzeResumeStream, 
  analyzeBatchChunked, 
  extractJdFromUrl, 
  getTemplates, 
  createTemplate 
} from '../lib/api'
import { useUsageCheck, useSubscription } from '../hooks/useSubscription'
import WeightSuggestionPanel from '../components/WeightSuggestionPanel'
import UniversalWeightsPanel from '../components/UniversalWeightsPanel'

const DEFAULT_WEIGHTS = {
  core_competencies: 0.30,
  experience: 0.20,
  domain_fit: 0.20,
  education: 0.10,
  career_trajectory: 0.10,
  role_excellence: 0.10,
  risk: -0.10,
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

  // UI State
  const [currentStep, setCurrentStep] = useState(1)
  const [draftSaved, setDraftSaved] = useState(false)
  const [showJdLibrary, setShowJdLibrary] = useState(false)
  const [savedJds, setSavedJds] = useState([])
  const jdLibraryRef = useRef(null)

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

  // Load JD from location state (from JD Library)
  useEffect(() => {
    if (location.state?.jd_text) {
      setJdText(location.state.jd_text)
      if (location.state.weights) {
        setWeights(location.state.weights)
      }
      if (location.state.role_category) {
        setRoleCategory(location.state.role_category)
      }
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
    setIsAnalyzing(true)

    try {
      // Save JD + weights to database
      const templateName = `${roleCategory || 'General'} - ${new Date().toLocaleDateString()}`
      await createTemplate({
        name: templateName,
        jd_text: jdMode === 'text' ? jdText : `[File: ${jdFile.name}]`,
        scoring_weights: weights,
        tags: roleCategory
      })

      // Run analysis - auto-detect single vs batch
      if (files.length === 1) {
        // Single analysis
        const result = await analyzeResumeStream(
          files[0],
          jdMode === 'text' ? jdText : null,
          jdMode === 'file' ? jdFile : null,
          weights
        )
        navigate('/report', { state: { result } })
      } else {
        // Batch analysis
        await analyzeBatchChunked(
          files,
          jdMode === 'text' ? jdText : null,
          jdMode === 'file' ? jdFile : null,
          weights
        )
        navigate('/candidates')
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
          <button onClick={() => setError('')} className="text-red-400 hover:text-red-600">
            <X className="w-4 h-4" />
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
      {currentStep === 3 && (
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
              {isAnalyzing ? (
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
    </div>
  )
}
