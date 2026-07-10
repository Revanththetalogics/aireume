import { useState, useCallback, useEffect, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import { 
  Upload, FileText, X, Loader2, AlertCircle, CheckCircle, 
  Sparkles, ChevronRight, BookOpen, LayoutTemplate, Link2, 
  FileUp, Type, Save, Clock, Trophy, Eye, Download, CheckCircle2, ArrowLeft,
  XCircle, RefreshCw, ShieldCheck, Settings, ChevronDown
} from 'lucide-react'
import { 
  analyzeResumeStream, 
  analyzeBatchStream, 
  submitBatchToQueue,
  extractJdFromUrl, 
  getTemplates, 
  createTemplate,
  createTemplateFromFile,
  updateTemplate,
  getNarrative,
  checkHealth,
  parseJdPreview,
  parseJdPreviewFromFile,
} from '../lib/api'
import { useUsageCheck, useSubscription } from '../hooks/useSubscription'
import { useNotification } from '../contexts/NotificationContext'
import { useOnboarding } from '../contexts/OnboardingContext'
import WeightSuggestionPanel from '../components/WeightSuggestionPanel'
import UniversalWeightsPanel, { isValidWeightTotal } from '../components/UniversalWeightsPanel'
import SkillClassificationEditor from '../components/SkillClassificationEditor'
import { FitBadge, RecommendBadge, EnrichmentStatusBadges } from '../components/Badges'
import {
  StreamStageTracker,
  BatchAnalysisProgress,
  AnalysisSetupSummary,
  PageHeader,
} from '../components/patterns'
import EmptyState from '../components/EmptyState'
import { Button, Badge, Card } from '../components/ui'
import { showSuccess } from '../lib/toast'
import { mergeNarrativePollResult, isNarrativePending, isKitPending, isReportCacheable } from '../lib/enrichmentUtils'
import {
  ANALYZE_STEPS,
  buildSetupSummary,
  buildRoleTemplateName,
  buildRoleTemplateTags,
  extractRoleTitle,
  getActiveAnalyzeStep,
  isAnalyzeStepComplete,
  canNavigateToAnalyzeStep,
  getEffectiveBatchTotal,
} from '../lib/analyzeBatchUtils'

const DEFAULT_WEIGHTS = {
  core_competencies: 0.30,
  experience: 0.20,
  domain_fit: 0.20,
  education: 0.10,
  career_trajectory: 0.10,
  role_excellence: 0.10,
  risk: -0.10,
}

const WEIGHT_PRESETS = {
  balanced: { core_competencies: 0.30, experience: 0.20, domain_fit: 0.20, education: 0.10, career_trajectory: 0.10, role_excellence: 0.10, risk: -0.10 },
  'skill-heavy': { core_competencies: 0.40, experience: 0.20, domain_fit: 0.15, education: 0.05, career_trajectory: 0.10, role_excellence: 0.10, risk: -0.10 },
  'experience-heavy': { core_competencies: 0.25, experience: 0.35, domain_fit: 0.15, education: 0.05, career_trajectory: 0.10, role_excellence: 0.10, risk: -0.10 },
  'domain-focused': { core_competencies: 0.25, experience: 0.20, domain_fit: 0.30, education: 0.05, career_trajectory: 0.10, role_excellence: 0.10, risk: -0.10 },
}

const PRESET_LABELS = {
  balanced: 'Balanced',
  'skill-heavy': 'Skill-Heavy',
  'experience-heavy': 'Experience-Heavy',
  'domain-focused': 'Domain-Focused',
}

const BACKGROUND_BATCH_MIN = 20
const BACKGROUND_BATCH_AUTO = 50

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
  const {
    startBatchAnalysis,
    updateProgress,
    completeBatchAnalysis,
    trackEnrichmentJob,
    updateEnrichmentJob,
    completeEnrichmentJob,
    addNotification,
    trackQueueBatch,
  } = useNotification()
  const { completeChecklistItem } = useOnboarding()

  // Step 1: Job Description
  const [jdText, setJdText] = useState('')
  const [jdMode, setJdMode] = useState('text')
  const [jdFile, setJdFile] = useState(null)
  const [urlInput, setUrlInput] = useState('')
  const [urlLoading, setUrlLoading] = useState(false)
  const [urlError, setUrlError] = useState('')

  // Weights (now optional, inside collapsible Advanced section in Step 2)
  const [weights, setWeights] = useState(DEFAULT_WEIGHTS)
  const [roleCategory, setRoleCategory] = useState('general')
  const [showAiSuggestion, setShowAiSuggestion] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [weightsManuallySet, setWeightsManuallySet] = useState(false)
  const [weightPreset, setWeightPreset] = useState('balanced')

  // Step 2: Resume Upload & Analyze
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
  const [runInBackground, setRunInBackground] = useState(false)
  const [batchStuckError, setBatchStuckError] = useState(null)
  const [setupSummaryExpanded, setSetupSummaryExpanded] = useState(false)
  const [queuedBatchInfo, setQueuedBatchInfo] = useState(null)

  useEffect(() => {
    if (files.length >= BACKGROUND_BATCH_AUTO) {
      setRunInBackground(true)
    }
  }, [files.length])
  const [currentStep, setCurrentStep] = useState(1)
  const [draftSaved, setDraftSaved] = useState(false)
  const [showJdLibrary, setShowJdLibrary] = useState(false)
  const [savedJds, setSavedJds] = useState([])
  const [loadedFromLibrary, setLoadedFromLibrary] = useState(false)
  const [loadedTemplateId, setLoadedTemplateId] = useState(null)
  const jdLibraryRef = useRef(null)

  // Skill Classification state (mandatory review before analysis)
  const [jdParseResult, setJdParseResult]     = useState(null)
  const [skillOverrides, setSkillOverrides]    = useState(null)
  const [parsingJd, setParsingJd]             = useState(false)
  const [skillsConfirmed, setSkillsConfirmed] = useState(false)
  const [parseError, setParseError]           = useState(null)
  const [roleName, setRoleName]               = useState('')
  const [streamStage, setStreamStage]         = useState(null)
  const [singleFileName, setSingleFileName]   = useState(null)
  const debounceRef = useRef(null)
  const skipAutoParseRef = useRef(false)
  const roleNameTouchedRef = useRef(false)
  const streamingResultsRef = useRef([])
  const streamingFailedRef = useRef([])
  const sessionRestoredRef = useRef(false)

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

  // Restore active session from sessionStorage on fresh mount
  // ONLY auto-advance when coming from "Analyze Another Resume" (flag set in ReportPage)
  useEffect(() => {
    if (location.state?.jd_text || location.state?.jd_mode) return

    const params = new URLSearchParams(location.search)
    const returningFromReport = params.get('restored') === 'true' || location.state?.from === '/analyze'

    if (returningFromReport && !sessionRestoredRef.current) {
      sessionRestoredRef.current = true
      const savedBatch = sessionStorage.getItem('aria_batch_results')
      if (savedBatch) {
        try {
          const batch = JSON.parse(savedBatch)
          // Only restore if less than 30 minutes old
          if (batch.timestamp && (Date.now() - batch.timestamp) < 30 * 60 * 1000) {
            const results = batch.results || []
            const failed = batch.failed || []
            if (results.length === 0 && failed.length === 0) {
              sessionStorage.removeItem('aria_batch_results')
              return
            }
            setStreamingResults(results)
            setStreamingFailed(failed)
            setAnalysisProgress(batch.progress || { completed: results.length + failed.length, total: results.length + failed.length })
            setAnalysisDone(true)
            setCurrentStep(3)
            // Also restore batch context (JD text, skill overrides, etc.)
            const savedContext = sessionStorage.getItem('aria_batch_context')
            if (savedContext) {
              try {
                const ctx = JSON.parse(savedContext)
                if (ctx.jdText) setJdText(ctx.jdText)
                if (ctx.skillOverrides) setSkillOverrides(ctx.skillOverrides)
                if (ctx.skillsConfirmed !== undefined) setSkillsConfirmed(ctx.skillsConfirmed)
                if (ctx.jdParseResult) setJdParseResult(ctx.jdParseResult)
                if (ctx.jdMode) setJdMode(ctx.jdMode)
                if (ctx.weights) setWeights(ctx.weights)
                if (ctx.roleCategory) setRoleCategory(ctx.roleCategory)
                // Skip auto-parse so it doesn't clobber restored jdParseResult
                skipAutoParseRef.current = true
              } catch {}
            }
            // Clean URL param without triggering navigation
            window.history.replaceState({}, '', '/analyze')
            return  // Skip the rest of session restoration logic
          }
        } catch {}
      }
    }

    if (sessionRestoredRef.current) return

    const isAnalyzeAnother = sessionStorage.getItem('aria_analyze_another')

    if (!isAnalyzeAnother && !returningFromReport) {
      // Fresh navigation (Dashboard, nav menu, etc.) — clear stale session data
      sessionStorage.removeItem('aria_active_jd')
      sessionStorage.removeItem('aria_batch_results')  // Also clear batch results
      sessionRestoredRef.current = true
      return
    }

    // Clear the one-time flag immediately
    sessionStorage.removeItem('aria_analyze_another')

    const savedSession = sessionStorage.getItem('aria_active_jd')
    if (!savedSession) {
      sessionRestoredRef.current = true
      return
    }
    try {
      const ctx = JSON.parse(savedSession)
      if (ctx.jd_text) setJdText(ctx.jd_text)
      if (ctx.weights) setWeights(ctx.weights)
      if (ctx.role_category) setRoleCategory(ctx.role_category)
      if (ctx.jd_mode) setJdMode(ctx.jd_mode)
      if (ctx.skillOverrides) setSkillOverrides(ctx.skillOverrides)
      if (ctx.jdParseResult) setJdParseResult(ctx.jdParseResult)
      if (ctx.skillsConfirmed) setSkillsConfirmed(ctx.skillsConfirmed)
      // Auto-skip to upload if JD context is complete
      if ((ctx.jd_text || ctx.jd_mode === 'file') && ctx.weights) {
        setCurrentStep(2)
      }
    } catch (e) {
      console.error('Failed to restore session:', e)
    }
    sessionRestoredRef.current = true
  }, [location.search])

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
      // Restore skill overrides if available
      if (location.state.skillOverrides) {
        setSkillOverrides(location.state.skillOverrides)
        setSkillsConfirmed(location.state.skillsConfirmed ?? false)
      }
      if (location.state.jdParseResult) {
        setJdParseResult(location.state.jdParseResult)
      }
      // Mark as loaded from library to prevent duplicate JD creation
      if (location.state.template_id) {
        setLoadedFromLibrary(true)
        setLoadedTemplateId(location.state.template_id)
      }
      if (location.state.template_name) {
        setRoleName(location.state.template_name)
        roleNameTouchedRef.current = true
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
          // Restore skill overrides if available
          if (location.state.skillOverrides) {
            setSkillOverrides(location.state.skillOverrides)
            setSkillsConfirmed(location.state.skillsConfirmed ?? false)
          }
          if (location.state.jdParseResult) {
            setJdParseResult(location.state.jdParseResult)
          }
          setCurrentStep(2)
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
      setCurrentStep(2)
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

  // ── Auto-parse JD text with debounce (1.5s after user stops typing) ──
  useEffect(() => {
    if (jdMode !== 'text') return

    // Skip auto-parse when we just restored overrides from a template —
    // the restored jdParseResult should not be clobbered by a fresh parse.
    if (skipAutoParseRef.current) {
      skipAutoParseRef.current = false
      return
    }

    if (debounceRef.current) clearTimeout(debounceRef.current)

    const words = (jdText || '').trim().split(/\s+/).filter(Boolean).length
    if (words < 80) {
      setJdParseResult(null)
      setParseError(null)
      return
    }

    debounceRef.current = setTimeout(async () => {
      setParsingJd(true)
      setParseError(null)
      try {
        const data = await parseJdPreview(jdText)
        setJdParseResult(data)
      } catch (err) {
        console.warn('JD auto-parse failed:', err)
        setParseError(err.message || 'Failed to parse job description')
      } finally {
        setParsingJd(false)
      }
    }, 1500)

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [jdText, jdMode])

  // Auto-fill role name from parsed JD title until recruiter edits it
  useEffect(() => {
    if (roleNameTouchedRef.current) return
    const extracted = extractRoleTitle(jdParseResult, roleCategory, '')
    if (extracted) setRoleName(extracted)
  }, [jdParseResult, roleCategory])

  // ── Auto-parse JD file on upload ──
  useEffect(() => {
    if (jdMode !== 'file' || !jdFile) return

    let cancelled = false
    const parseFile = async () => {
      setParsingJd(true)
      setParseError(null)
      setSkillsConfirmed(false)
      try {
        const data = await parseJdPreviewFromFile(jdFile)
        if (!cancelled) setJdParseResult(data)
      } catch (err) {
        if (!cancelled) {
          console.warn('JD file auto-parse failed:', err)
          setParseError(err.message || 'Failed to parse job description file')
        }
      } finally {
        if (!cancelled) setParsingJd(false)
      }
    }

    parseFile()
    return () => { cancelled = true }
  }, [jdMode, jdFile])

  // ── Auto-select weight preset based on JD role detection ──
  useEffect(() => {
    if (jdParseResult && !weightsManuallySet) {
      const seniority = jdParseResult.seniority || ''
      const jobFunction = jdParseResult.job_function || ''

      if (seniority.toLowerCase().includes('senior') || seniority.toLowerCase().includes('lead') || seniority.toLowerCase().includes('principal')) {
        setWeightPreset('skill-heavy')
        setWeights(WEIGHT_PRESETS['skill-heavy'])
      } else if (seniority.toLowerCase().includes('manager') || seniority.toLowerCase().includes('director') || seniority.toLowerCase().includes('vp')) {
        setWeightPreset('experience-heavy')
        setWeights(WEIGHT_PRESETS['experience-heavy'])
      } else if (jobFunction.toLowerCase().includes('research') || jobFunction.toLowerCase().includes('data')) {
        setWeightPreset('domain-focused')
        setWeights(WEIGHT_PRESETS['domain-focused'])
      } else {
        setWeightPreset('balanced')
        setWeights(WEIGHT_PRESETS['balanced'])
      }
    }
  }, [jdParseResult])

  // ── Auto-advance from Step 1 to Step 2 when skills are confirmed ──
  useEffect(() => {
    if (skillsConfirmed && currentStep === 1) {
      setCurrentStep(2)
    }
  }, [skillsConfirmed])

  // Handle weights change — marks as manually set
  const handleWeightsChange = (newWeights) => {
    setWeights(newWeights)
    setWeightsManuallySet(true)
  }

// Poll for narrative completion on batch results
  useEffect(() => {
    if (!analysisDone || !streamingResults.length) return

    const pendingIds = streamingResults
      .filter(item => item.screeningResultId && (
        isNarrativePending(item.result) || isKitPending(item.result)
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
        const labelFor = (rid) =>
          streamingResultsRef.current.find((r) => r.screeningResultId === rid)?.filename || `Report #${rid}`

        try {
          const data = await getNarrative(id)
          if (data.status === 'ready' || data.status === 'fallback' || data.status === 'failed') {
            const kitStatus = data.interview_kit_status
            const kitPending = kitStatus === 'pending' || kitStatus === 'processing'
            setStreamingResults(prev => prev.map(item => {
              if (item.screeningResultId !== id) return item
              const updatedResult = mergeNarrativePollResult(item.result, data)
              try {
                if (isReportCacheable(updatedResult)) {
                  sessionStorage.setItem(`report_${id}`, JSON.stringify(updatedResult))
                }
              } catch {}
              try {
                const currentResults = JSON.parse(sessionStorage.getItem('aria_batch_results') || '{}')
                if (currentResults.results) {
                  currentResults.results = currentResults.results.map(batchItem =>
                    batchItem.screeningResultId === id ? { ...batchItem, result: updatedResult } : batchItem
                  )
                  sessionStorage.setItem('aria_batch_results', JSON.stringify(currentResults))
                }
              } catch {}
              return { ...item, result: updatedResult }
            }))
            if (kitPending) {
              stillPending.push(id)
              updateEnrichmentJob(`enrich-${id}`, {
                phase: kitStatus === 'processing' ? 'Interview kit generating' : 'AI insights ready, kit pending',
                status: 'processing',
              })
            } else {
              completeEnrichmentJob(`enrich-${id}`, {
                phase: 'Complete',
                status: data.status === 'ready' ? 'ready' : 'fallback',
              })
              addNotification({
                type: 'success',
                title: 'Report enrichment complete',
                message: `${labelFor(id)} — interview kit ready`,
                href: `/report?id=${id}`,
              })
            }
          } else if (data.interview_kit_status === 'ready' || data.interview_kit_status === 'fallback') {
            setStreamingResults(prev => prev.map(item => {
              if (item.screeningResultId !== id) return item
              const updatedResult = mergeNarrativePollResult(item.result, data)
              return { ...item, result: updatedResult }
            }))
            completeEnrichmentJob(`enrich-${id}`, { phase: 'Complete', status: 'ready' })
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
      // Reset skill confirmation since JD changed
      setSkillsConfirmed(false)
      setSkillOverrides(null)
      setJdParseResult(null)
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
      // Reset skill confirmation since JD source changed
      setSkillsConfirmed(false)
      setSkillOverrides(null)
      setJdParseResult(null)
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
    setWeightsManuallySet(true)
    setShowAiSuggestion(false)
  }

  // Load JD from library
  const handleLoadJd = (template) => {
    setJdText(template.jd_text)
    setJdMode('text')
    setShowJdLibrary(false)
    setRoleName(template.name || '')
    roleNameTouchedRef.current = Boolean(template.name)
    
    // Robust override parser — handles null, "", "null", "[]", JSON strings, arrays
    const parseOverride = (val) => {
      if (!val) return []
      if (Array.isArray(val)) return val
      if (typeof val === 'string') {
        try {
          const parsed = JSON.parse(val)
          return Array.isArray(parsed) ? parsed : []
        } catch { return [] }
      }
      return []
    }

    const reqOverride = parseOverride(template.required_skills_override)
    const niceOverride = parseOverride(template.nice_to_have_skills_override)
    const hasOverrides = reqOverride.length > 0 || niceOverride.length > 0

    if (hasOverrides) {
      const restoredOverrides = {
        required_skills: reqOverride,
        nice_to_have_skills: niceOverride
      }
      setSkillOverrides(restoredOverrides)
      setSkillsConfirmed(true)
      setJdParseResult({
        required_skills: reqOverride,
        nice_to_have_skills: niceOverride,
        restored_from_template: true
      })
      // Skip the auto-parse effect so it doesn't clobber restored state
      skipAutoParseRef.current = true
    } else {
      // Reset skill confirmation since JD changed
      setSkillsConfirmed(false)
      setSkillOverrides(null)
      setJdParseResult(null)
    }
    
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
    if (!isValidWeightTotal(weights)) {
      setError('Scoring weights must sum to 100% (98–102% allowed). Adjust weights in Advanced settings.')
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
        jd_mode: 'text',
        skillOverrides,
        jdParseResult,
        skillsConfirmed
      }))
      clearJdFile().catch(() => {})
    } else if (jdMode === 'file' && jdFile) {
      try {
        await storeJdFile(jdFile)
        sessionStorage.setItem('aria_active_jd', JSON.stringify({
          weights,
          role_category: roleCategory,
          jd_mode: 'file',
          file_name: jdFile.name,
          skillOverrides,
          jdParseResult,
          skillsConfirmed
        }))
      } catch { /* ignore */ }
    }

    sessionStorage.removeItem('aria_batch_results')
    // Save full batch context for back-navigation restoration
    try {
      sessionStorage.setItem('aria_batch_context', JSON.stringify({
        jdText,
        skillOverrides,
        skillsConfirmed,
        jdParseResult,
        jdMode,
        weights,
        roleCategory,
        fileNames: files.map(f => f.name),
        timestamp: Date.now()
      }))
    } catch {}
    setIsAnalyzing(true)

    try {
      // Only save JD template if it's NEW (not loaded from library)
      // This prevents duplicate JD creation
      if (!loadedFromLibrary) {
        const templateName = buildRoleTemplateName(roleName, jdParseResult, roleCategory)
        const templateTags = buildRoleTemplateTags(jdParseResult, roleCategory)
        if (jdMode === 'text') {
          await createTemplate({
            name: templateName,
            jd_text: jdText,
            scoring_weights: weights,
            tags: templateTags,
            required_skills_override: skillOverrides ? JSON.stringify(skillOverrides.required_skills) : null,
            nice_to_have_skills_override: skillOverrides ? JSON.stringify(skillOverrides.nice_to_have_skills) : null,
          })
        } else {
          await createTemplateFromFile(templateName, jdFile, templateTags, weights)
        }
      } else if (loadedTemplateId && skillOverrides) {
        // Template already exists — update it with the latest skill overrides
        try {
          await updateTemplate(loadedTemplateId, {
            required_skills_override: JSON.stringify(skillOverrides.required_skills),
            nice_to_have_skills_override: JSON.stringify(skillOverrides.nice_to_have_skills),
          })
        } catch (err) {
          console.warn('Failed to update template overrides before analysis:', err)
        }
      }

      // Run analysis - auto-detect single vs batch
      if (files.length === 1) {
        setStreamStage('parsing')
        setSingleFileName(files[0].name)
        const result = await analyzeResumeStream(
          files[0],
          jdMode === 'text' ? jdText : null,
          jdMode === 'file' ? jdFile : null,
          weights,
          (event) => {
            if (event.stage === 'parsing') setStreamStage('parsing')
            else if (event.stage === 'scoring') setStreamStage('scoring')
            else if (event.stage === 'complete') setStreamStage('complete')
          },
          loadedTemplateId,
          skillOverrides,
        )
        setStreamStage(null)
        setSingleFileName(null)
        const resultId = result?.result_id || result?.analysis_id
        if (resultId) {
          trackEnrichmentJob({
            id: `enrich-${resultId}`,
            label: files[0].name,
            status: 'processing',
            phase: 'AI enrichment',
            href: `/report?id=${resultId}`,
          })
        }
        navigate('/report', { state: { result } })
        completeChecklistItem('analyzedResume')
      } else if (runInBackground && files.length >= BACKGROUND_BATCH_MIN) {
        const batch = await submitBatchToQueue(
          files,
          jdMode === 'text' ? jdText : null,
          jdMode === 'file' ? jdFile : null,
          weights,
          loadedTemplateId,
          skillOverrides,
        )
        trackQueueBatch(batch)
        showSuccess(`Queued ${batch.queued} resume${batch.queued !== 1 ? 's' : ''} for background analysis`)
        addNotification({
          type: 'success',
          title: 'Batch queued',
          message: `${batch.queued} resume${batch.queued !== 1 ? 's' : ''} scoring in the background. Open Activity in the nav to track progress.`,
        })
        if (batch.failed > 0) {
          addNotification({
            type: 'warning',
            title: 'Some files could not be queued',
            message: `${batch.failed} file(s) failed to enqueue. Check file sizes and formats.`,
          })
        }
        setQueuedBatchInfo({ count: batch.queued || files.length })
        setFiles([])
        setCurrentStep(2)
        await refreshAfterAnalysis(batch.queued || files.length)
      } else {
        // Batch analysis with SSE streaming
        setBatchStuckError(null)
        setCurrentStep(3)
        startBatchAnalysis(files.length)
        setStreamingResults([])
        setStreamingFailed([])
        setAnalysisDone(false)
        setAnalysisProgress({ completed: 0, total: files.length })
        setBatchStartTime(Date.now())
        // Initialize per-file status tracking immediately
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
              updateProgress(filename, 'processing')
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
                updated.sort((a, b) => (b.result?.fit_score || 0) - (a.result?.fit_score || 0))
                streamingResultsRef.current = updated
                return updated
              })
              setFileStatuses(prev => prev.map(fs =>
                fs.filename === filename
                  ? { ...fs, status: 'completed', result, screeningResultId, endTime: Date.now() }
                  : fs
              ))
              if (screeningResultId) {
                try {
                  if (isReportCacheable(result)) {
                    sessionStorage.setItem(`report_${screeningResultId}`, JSON.stringify(result))
                  }
                } catch {}
                trackEnrichmentJob({
                  id: `enrich-${screeningResultId}`,
                  label: filename,
                  status: 'processing',
                  phase: 'AI insights generating',
                  href: `/report?id=${screeningResultId}`,
                })
              }
              updateProgress(filename, 'completed')
              // Safety net: persist batch results on every new result
              try {
                const currentResults = streamingResultsRef.current
                const currentFailed = streamingFailedRef.current
                if (currentResults.length > 0) {
                  sessionStorage.setItem('aria_batch_results', JSON.stringify({
                    results: currentResults,
                    failed: currentFailed || [],
                    progress: { completed: index, total },
                    timestamp: Date.now()
                  }))
                }
              } catch {}
            },
            onFailed: (index, total, filename, error) => {
              setIsAnalyzing(true)
              setAnalysisProgress(prev => ({ completed: prev.completed, total: total || prev.total }))
              setStreamingFailed(prev => {
                const updated = [...prev, { filename, error }]
                streamingFailedRef.current = updated
                return updated
              })
              setFileStatuses(prev => prev.map(fs =>
                fs.filename === filename
                  ? { ...fs, status: 'failed', error, endTime: Date.now() }
                  : fs
              ))
              updateProgress(filename, 'error')
              try {
                const currentResults = streamingResultsRef.current
                const currentFailed = streamingFailedRef.current
                sessionStorage.setItem('aria_batch_results', JSON.stringify({
                  results: currentResults,
                  failed: currentFailed || [],
                  progress: { completed: index, total: total || 0 },
                  timestamp: Date.now()
                }))
              } catch {}
            },
            onDone: (total, successful, failedCount) => {
              setAnalysisDone(true)
              completeChecklistItem('analyzedResume')
              // Persist batch results for back-navigation (use refs to avoid stale closure)
              try {
                sessionStorage.setItem('aria_batch_results', JSON.stringify({
                  results: streamingResultsRef.current,
                  failed: streamingFailedRef.current,
                  progress: { completed: total, total },
                  timestamp: Date.now()
                }))
              } catch {}
              setIsAnalyzing(false)
              setAnalysisProgress({ completed: total, total })
              completeBatchAnalysis()
              showSuccess(`${successful} of ${total} resumes analyzed`)
            },
          },
          loadedTemplateId,
          skillOverrides,
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
      if (files.length > 1) {
        setBatchStuckError('Analysis failed before completing. You can retry or start a new batch.')
      }
    } finally {
      setIsAnalyzing(false)
    }
  }

  const handleRetryBatch = () => {
    setBatchStuckError(null)
    setError('')
    if (files.length > 0 && skillsConfirmed) {
      handleAnalyze()
      return
    }
    handleNewBatch()
  }

  const isStep1Complete = (jdMode === 'text' ? jdText.trim().length > 50 : jdFile !== null) && skillsConfirmed
  const isStep2Complete = files.length > 0

  const remainingAnalyses = getRemainingAnalyses()

  // Detect batch start stuck state (no SSE progress after 5s)
  useEffect(() => {
    if (!isAnalyzing || analysisProgress.total > 0) {
      return undefined
    }
    const timer = setTimeout(() => {
      setBatchStuckError('The analysis service did not respond. Check your connection and try again.')
      setIsAnalyzing(false)
    }, 5000)
    return () => clearTimeout(timer)
  }, [isAnalyzing, analysisProgress.total])

  // Determine if results area should be visible
  const showResults = isAnalyzing || analysisDone || streamingResults.length > 0 || streamingFailed.length > 0 || Boolean(batchStuckError)

  const activeStep = getActiveAnalyzeStep(showResults, currentStep)
  const setupSummary = buildSetupSummary({
    roleCategory,
    roleName,
    jdParseResult,
    skillOverrides,
    fileCount: getEffectiveBatchTotal(analysisProgress, fileStatuses),
    jdMode,
    jdFile,
  })
  const topCandidate = streamingResults[0]
  const batchPreparing = isAnalyzing && analysisProgress.total <= 0 && fileStatuses.length === 0

  // Reset for new batch
  const handleNewBatch = () => {
    setStreamingResults([])
    setStreamingFailed([])
    setAnalysisDone(false)
    setIsAnalyzing(false)
    setAnalysisProgress({ completed: 0, total: 0 })
    setFileStatuses([])
    setBatchStartTime(null)
    setBatchStuckError(null)
    setSetupSummaryExpanded(false)
    setFiles([])
    setCurrentStep(2)
    sessionStorage.removeItem('aria_batch_context')
    sessionStorage.removeItem('aria_batch_results')
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader
        className="mb-8"
        title="New Analysis"
        subtitle="Score resumes against a role in three steps — job description, upload, then ranked results."
        icon={Sparkles}
        actions={
          remainingAnalyses !== undefined && remainingAnalyses !== Infinity ? (
            <Badge color="brand">{remainingAnalyses} analyses left</Badge>
          ) : null
        }
      />

      {/* Progress Steps */}
      <div className="mb-8 flex items-center justify-between gap-2">
        {ANALYZE_STEPS.map((step, idx) => {
          const isComplete = isAnalyzeStepComplete(step.num, {
            isStep1Complete,
            isStep2Complete,
            showResults,
            analysisDone,
          })
          const isActive = activeStep === step.num
          const canNavigate = canNavigateToAnalyzeStep(step.num, { isAnalyzing, showResults })

          return (
            <div key={step.num} className="flex items-center flex-1 min-w-0">
              <button
                type="button"
                disabled={!canNavigate}
                onClick={() => {
                  if (!canNavigate) return
                  if (step.num === 3) return
                  setCurrentStep(step.num)
                }}
                className={`flex items-center gap-2 sm:gap-3 min-w-0 ${
                  isActive ? 'opacity-100' : 'opacity-60 hover:opacity-80'
                } ${canNavigate ? '' : 'cursor-default'} transition-opacity`}
              >
                <div className={`w-9 h-9 sm:w-10 sm:h-10 rounded-full flex items-center justify-center font-bold text-sm transition-all shrink-0 ${
                  isComplete
                    ? 'bg-emerald-500 text-white ring-4 ring-emerald-100'
                    : isActive
                    ? 'bg-brand-600 text-white ring-4 ring-brand-100'
                    : 'bg-slate-200 text-slate-600'
                }`}>
                  {isComplete && step.num !== 3 ? (
                    <CheckCircle className="w-5 h-5" />
                  ) : isActive && step.num === 3 && !analysisDone ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : isComplete && step.num === 3 ? (
                    <CheckCircle className="w-5 h-5" />
                  ) : (
                    step.num
                  )}
                </div>
                <span className={`text-xs sm:text-sm font-semibold truncate ${isActive ? 'text-brand-900' : 'text-slate-600'}`}>
                  {step.label}
                </span>
              </button>
              {idx < ANALYZE_STEPS.length - 1 && (
                <ChevronRight className="w-4 h-4 sm:w-5 sm:h-5 text-slate-300 mx-1 sm:mx-2 flex-shrink-0" />
              )}
            </div>
          )
        })}
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
      {currentStep === 1 && !showResults && (
        <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand-xl p-6 md:p-8 card-animate">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-brand-900">Step 1: Job Description & Skill Review</h2>
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

          {/* Role name — used when saving to library */}
          {!loadedFromLibrary && (jdMode === 'text' ? jdText.trim().length > 50 : jdFile) && (
            <div className="mb-4">
              <label htmlFor="role-name" className="block text-sm font-semibold text-brand-900 mb-1.5">
                Role name
              </label>
              <input
                id="role-name"
                type="text"
                value={roleName}
                onChange={(e) => {
                  roleNameTouchedRef.current = true
                  setRoleName(e.target.value)
                }}
                placeholder={extractRoleTitle(jdParseResult, roleCategory, '') || 'e.g. Talent Acquisition Specialist'}
                className="w-full px-4 py-3 border border-brand-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-brand-500 text-sm"
              />
              <p className="text-xs text-slate-500 mt-1.5">
                {parsingJd
                  ? 'Detecting role title from job description…'
                  : 'Saved to your Roles library when you analyze. Edit if the detected title is wrong.'}
              </p>
            </div>
          )}

          {/* JD Input */}
          {jdMode === 'text' && (
            <div>
              <textarea
                value={jdText}
                onChange={(e) => {
                  setJdText(e.target.value)
                  // Reset skill confirmation when JD text changes
                  if (skillsConfirmed) {
                    setSkillsConfirmed(false)
                    setSkillOverrides(null)
                    setJdParseResult(null)
                  }
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

              {/* Short JD hint */}
              {jdText.trim() && jdText.split(/\s+/).filter(Boolean).length < 80 && (
                <div className="mt-3 flex items-center gap-2 p-3 bg-amber-50 border border-amber-200 rounded-xl">
                  <AlertCircle className="w-4 h-4 text-amber-500 shrink-0" />
                  <p className="text-xs text-amber-700">
                    Add more detail to the job description for better skill extraction ({jdText.split(/\s+/).filter(Boolean).length}/80 words minimum)
                  </p>
                </div>
              )}

              {/* Parsing indicator */}
              {parsingJd && jdMode === 'text' && (
                <div className="mt-3 flex items-center gap-2 p-3 bg-brand-50 border border-brand-200 rounded-xl">
                  <Loader2 className="w-4 h-4 animate-spin text-brand-600" />
                  <p className="text-xs text-brand-700 font-medium">Parsing job description…</p>
                </div>
              )}

              {/* Parse error with retry */}
              {parseError && !parsingJd && jdMode === 'text' && (
                <div className="mt-3 flex items-center justify-between gap-2 p-3 bg-red-50 border border-red-200 rounded-xl">
                  <p className="text-xs text-red-700">{parseError}</p>
                  <button
                    type="button"
                    onClick={async () => {
                      setParseError(null)
                      setParsingJd(true)
                      try {
                        if (jdMode === 'file' && jdFile) {
                          const data = await parseJdPreviewFromFile(jdFile)
                          setJdParseResult(data)
                        } else {
                          const data = await parseJdPreview(jdText)
                          setJdParseResult(data)
                        }
                      } catch (err) {
                        setParseError(err.message || 'Failed to parse job description')
                      } finally {
                        setParsingJd(false)
                      }
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white text-red-700 ring-1 ring-red-200 hover:bg-red-50 transition-all shrink-0"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    Retry
                  </button>
                </div>
              )}
            </div>
          )}

          {jdMode === 'file' && (
            <div>
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
                        setSkillsConfirmed(false)
                        setSkillOverrides(null)
                        setJdParseResult(null)
                      }}
                      aria-label="Remove job description file"
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
              {/* File mode parsing indicator */}
              {parsingJd && jdMode === 'file' && (
                <div className="mt-3 flex items-center gap-2 p-3 bg-brand-50 border border-brand-200 rounded-xl">
                  <Loader2 className="w-4 h-4 animate-spin text-brand-600" />
                  <p className="text-xs text-brand-700 font-medium">Parsing job description file…</p>
                </div>
              )}
              {/* File mode parse error */}
              {parseError && !parsingJd && jdMode === 'file' && (
                <div className="mt-3 flex items-center justify-between gap-2 p-3 bg-red-50 border border-red-200 rounded-xl">
                  <p className="text-xs text-red-700">{parseError}</p>
                  <button
                    type="button"
                    onClick={async () => {
                      setParseError(null)
                      setParsingJd(true)
                      try {
                        const data = await parseJdPreviewFromFile(jdFile)
                        setJdParseResult(data)
                      } catch (err) {
                        setParseError(err.message || 'Failed to parse job description file')
                      } finally {
                        setParsingJd(false)
                      }
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white text-red-700 ring-1 ring-red-200 hover:bg-red-50 transition-all shrink-0"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    Retry
                  </button>
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

          {/* ── Inline Skill Classification Editor (shown after JD is parsed, before confirmation) ── */}
          {jdParseResult && !skillsConfirmed && (
            <div className="mt-6">
              <SkillClassificationEditor
                data={jdParseResult}
                onConfirm={async (overrides) => {
                  setSkillOverrides(overrides)
                  setSkillsConfirmed(true)
                  // Persist overrides to the template so they are restored on next load
                  if (loadedTemplateId) {
                    try {
                      await updateTemplate(loadedTemplateId, {
                        required_skills_override: JSON.stringify(overrides.required_skills),
                        nice_to_have_skills_override: JSON.stringify(overrides.nice_to_have_skills),
                      })
                    } catch (err) {
                      console.warn('Failed to persist skill overrides to template:', err)
                    }
                  }
                }}
                onSkip={() => {
                  setSkillOverrides(null)
                  setSkillsConfirmed(true)
                }}
                loading={false}
              />
            </div>
          )}

          {/* ── Skills Confirmed Badge ── */}
          {skillsConfirmed && (
            <div className="mt-6 flex items-center gap-3 flex-wrap p-3 bg-green-50 border border-green-200 rounded-2xl">
              <ShieldCheck className="w-4 h-4 text-green-600 shrink-0" />
              <span className="text-sm font-medium text-green-700">
                {jdParseResult?.restored_from_template
                  ? 'Skills restored from saved template'
                  : 'Skills confirmed'}
                {skillOverrides && !jdParseResult?.restored_from_template
                  ? ` — ${Array.isArray(skillOverrides.required_skills) ? skillOverrides.required_skills.length : 0} must-have, ${Array.isArray(skillOverrides.nice_to_have_skills) ? skillOverrides.nice_to_have_skills.length : 0} good-to-have`
                  : skillOverrides && jdParseResult?.restored_from_template
                  ? ` — ${Array.isArray(skillOverrides.required_skills) ? skillOverrides.required_skills.length : 0} must-have, ${Array.isArray(skillOverrides.nice_to_have_skills) ? skillOverrides.nice_to_have_skills.length : 0} good-to-have`
                  : ' — using AI defaults'}
              </span>
              {jdParseResult?.jd_quality && (
                <span className="text-sm font-medium text-emerald-700">
                  JD Quality: {jdParseResult.jd_quality.grade} ({jdParseResult.jd_quality.overall_score}/100)
                </span>
              )}
              <button
                type="button"
                onClick={() => {
                  setSkillsConfirmed(false)
                  // Clear restored flag so user can re-edit from fresh parse
                  if (jdParseResult?.restored_from_template) {
                    setJdParseResult(null)
                    setSkillOverrides(null)
                  }
                }}
                className="ml-auto text-xs text-green-500 hover:text-green-700 underline"
              >
                Re-edit
              </button>
            </div>
          )}
        </div>
      )}

      {/* Step 2: Upload & Analyze */}
      {currentStep === 2 && !showResults && (
        <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand-xl p-6 md:p-8 card-animate">
          <h2 className="text-xl font-bold text-brand-900 mb-6">Step 2: Upload & Analyze</h2>

          {queuedBatchInfo && (
            <Card className="mb-6 p-6 ring-emerald-100 bg-emerald-50/40">
              <EmptyState
                icon={CheckCircle2}
                title={`${queuedBatchInfo.count} resume${queuedBatchInfo.count !== 1 ? 's' : ''} queued`}
                description="Scoring runs in the background. Open Activity in the top navigation to track progress."
                actionLabel="Upload another batch"
                onAction={() => setQueuedBatchInfo(null)}
              />
            </Card>
          )}

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
                      aria-label="Remove file"
                      className="p-2 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      <X className="w-4 h-4 text-red-600" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Weight preset indicator */}
          <p className="text-xs text-slate-400 mt-1 mb-4">
            Scoring: {PRESET_LABELS[weightPreset] || 'Balanced'} weights
            {!weightsManuallySet && ' (auto-detected)'}
          </p>

          {/* Advanced: Scoring Weights (collapsible) */}
          <div className="mt-6">
            <button 
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-700 transition-colors"
            >
              <Settings className="w-4 h-4" />
              <span>Advanced: Scoring Weights</span>
              <ChevronDown className={`w-4 h-4 transition-transform ${showAdvanced ? 'rotate-180' : ''}`} />
            </button>
            
            {showAdvanced && (
              <div className="mt-4 p-4 bg-slate-50 rounded-xl border border-slate-200">
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
                  onChange={handleWeightsChange}
                  roleCategory={roleCategory}
                />
              </div>
            )}
          </div>

          {/* Skill confirmation required message */}
          {!skillsConfirmed && files.length > 0 && (
            <div className="mb-6 p-4 bg-amber-50 ring-1 ring-amber-200 rounded-2xl flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
              <p className="text-sm text-amber-700">Please go back to Step 1 and confirm the extracted skills before analysis</p>
            </div>
          )}

          {streamStage && singleFileName && (
            <div className="mb-6">
              <p className="text-xs text-slate-500 mb-2 font-medium">Analyzing {singleFileName}</p>
              <StreamStageTracker activeStage={streamStage} />
            </div>
          )}

          {files.length > 1 && files.length >= BACKGROUND_BATCH_MIN && (
            <label className="mb-4 flex items-start gap-3 p-4 bg-indigo-50 ring-1 ring-indigo-200 rounded-2xl cursor-pointer">
              <input
                type="checkbox"
                checked={runInBackground}
                onChange={(e) => setRunInBackground(e.target.checked)}
                className="mt-1 rounded border-indigo-300 text-indigo-600 focus:ring-indigo-500"
              />
              <div>
                <p className="text-sm font-semibold text-indigo-900">Run in background</p>
                <p className="text-xs text-indigo-700 mt-0.5">
                  Queue {files.length} resumes for server-side processing. Track progress in Activity Center.
                  {files.length >= BACKGROUND_BATCH_AUTO && ' (Recommended for 50+ files)'}
                </p>
              </div>
            </label>
          )}

          {/* Navigation */}
          <div className="flex justify-between">
            <button
              onClick={() => setCurrentStep(1)}
              className="flex items-center gap-2 px-6 py-3 bg-slate-100 text-slate-700 rounded-2xl font-semibold hover:bg-slate-200 transition-colors"
            >
              <ChevronRight className="w-4 h-4 rotate-180" />
              Back
            </button>
            <button
              onClick={handleAnalyze}
              disabled={!isStep2Complete || isAnalyzing || !skillsConfirmed}
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

      {/* Step 3: Batch Analysis Results */}
      {showResults && (
        <div className="space-y-5 card-animate">
          <AnalysisSetupSummary
            roleTitle={setupSummary.roleTitle}
            requiredCount={setupSummary.requiredCount}
            fileCount={setupSummary.fileCount}
            sourceLabel={setupSummary.sourceLabel}
            jdText={jdMode === 'text' ? jdText : ''}
            expanded={setupSummaryExpanded}
            onToggle={() => setSetupSummaryExpanded((v) => !v)}
          />

          {/* Results toolbar */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <Button variant="secondary" size="sm" onClick={handleNewBatch}>
                <ArrowLeft className="w-4 h-4" />
                New batch
              </Button>
            </div>
            {analysisDone && topCandidate && (
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  size="sm"
                  onClick={() => {
                    const id = topCandidate.screeningResultId
                    const r = topCandidate.result
                    if (!id) return
                    try {
                      sessionStorage.setItem('aria_batch_results', JSON.stringify({
                        results: streamingResults,
                        failed: streamingFailed,
                        progress: analysisProgress,
                        timestamp: Date.now(),
                      }))
                    } catch {}
                    navigate(`/report?id=${id}&from=analyze`, { state: { from: '/analyze', result: r } })
                  }}
                >
                  <Trophy className="w-4 h-4" />
                  View top candidate
                </Button>
                <Button variant="secondary" size="sm" onClick={() => navigate('/candidates')}>
                  <Eye className="w-4 h-4" />
                  All candidates
                </Button>
              </div>
            )}
          </div>

          {/* Analysis Progress */}
          {(isAnalyzing || analysisDone || fileStatuses.length > 0 || batchStuckError) && (
            <BatchAnalysisProgress
              analysisDone={analysisDone}
              analysisProgress={analysisProgress}
              batchStartTime={batchStartTime}
              fileStatuses={fileStatuses}
              successfulCount={streamingResults.length}
              failedCount={streamingFailed.length}
              preparing={batchPreparing}
              stuck={Boolean(batchStuckError)}
              stuckMessage={batchStuckError}
              onRetry={handleRetryBatch}
            />
          )}

          {/* Waiting for first result */}
          {!analysisDone && streamingResults.length === 0 && !batchStuckError && (
            <Card className="p-8">
              <div className="flex flex-col items-center text-center py-4">
                <Loader2 className="w-10 h-10 text-brand-600 animate-spin mb-4" />
                <h3 className="text-lg font-bold text-brand-900 mb-1">Waiting for first result</h3>
                <p className="text-sm text-slate-500 max-w-sm">
                  {analysisProgress.total > 0
                    ? `Scoring ${analysisProgress.total} resume${analysisProgress.total !== 1 ? 's' : ''}. Results will appear here as each completes.`
                    : 'Connecting to the analysis service…'}
                </p>
              </div>
            </Card>
          )}

          {/* Results header + table */}
          {streamingResults.length > 0 && (
            <>
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div>
                  <h3 className="text-xl font-extrabold text-brand-900 tracking-tight">Ranked Shortlist</h3>
                  <p className="text-sm text-slate-500 font-medium">
                    {streamingResults.length} scored
                    {!analysisDone && analysisProgress.total > streamingResults.length
                      ? ` · ${analysisProgress.total - streamingResults.length} still processing`
                      : ''}
                    {streamingFailed.length ? ` · ${streamingFailed.length} failed` : ''}
                  </p>
                </div>
              </div>
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
                            <EnrichmentStatusBadges result={r} />
                            <button
                              onClick={() => {
                                // Persist batch results before navigating to report
                                try {
                                  sessionStorage.setItem('aria_batch_results', JSON.stringify({
                                    results: streamingResultsRef.current,
                                    failed: streamingFailedRef.current,
                                    progress: analysisProgress,
                                    timestamp: Date.now()
                                  }))
                                  // Also persist batch context for back-navigation
                                  sessionStorage.setItem('aria_batch_context', JSON.stringify({
                                    jdText,
                                    skillOverrides,
                                    skillsConfirmed,
                                    jdParseResult,
                                    jdMode,
                                    weights,
                                    roleCategory,
                                    fileNames: streamingResults.map(r => r.filename),
                                    timestamp: Date.now()
                                  }))
                                } catch {}
                                navigate(`/report?id=${id}&from=analyze`, { state: { from: '/analyze', result: r } })
                              }}
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
            </>
          )}

          {/* All failed / zero scored */}
          {analysisDone && streamingResults.length === 0 && !batchStuckError && (
            <Card className="p-8">
              <EmptyState
                icon={AlertCircle}
                title="No resumes were scored"
                description={
                  streamingFailed.length > 0
                    ? `${streamingFailed.length} file${streamingFailed.length !== 1 ? 's' : ''} could not be processed. Review errors below or upload again.`
                    : 'The batch finished without any successful results. Try uploading again or check your job description.'
                }
                actionLabel="Start new batch"
                onAction={handleNewBatch}
              />
            </Card>
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
