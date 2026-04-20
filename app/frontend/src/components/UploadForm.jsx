import { useCallback, useState, useEffect, useRef } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, AlertCircle, FileUp, Type, Link2, SlidersHorizontal, ChevronDown, ChevronUp, Loader2, X, BookOpen, BookmarkPlus, Check, LayoutTemplate, Sparkles } from 'lucide-react'
import { extractJdFromUrl, getTemplates, createTemplate } from '../lib/api'
import WeightSuggestionPanel from './WeightSuggestionPanel'
import UniversalWeightsPanel from './UniversalWeightsPanel'

const WEIGHT_PRESETS = {
  Balanced:        { skills: 0.40, experience: 0.35, stability: 0.15, education: 0.10 },
  'Skill-Heavy':   { skills: 0.60, experience: 0.25, stability: 0.10, education: 0.05 },
  'Exp-Heavy':     { skills: 0.25, experience: 0.55, stability: 0.15, education: 0.05 },
  'Edu-Heavy':     { skills: 0.30, experience: 0.30, stability: 0.15, education: 0.25 },
}

function WeightsPanel({ weights, onChange }) {
  const [preset, setPreset] = useState('Balanced')

  const applyPreset = (name) => {
    setPreset(name)
    onChange(WEIGHT_PRESETS[name])
  }

  const updateWeight = (key, value) => {
    const val = parseFloat(value) / 100
    onChange({ ...weights, [key]: val })
    setPreset('Custom')
  }

  const labels = {
    skills:     'Skills Match',
    experience: 'Experience',
    stability:  'Stability',
    education:  'Education',
  }

  return (
    <div className="mt-4 p-4 bg-brand-50 border border-brand-100 rounded-2xl space-y-3">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <p className="text-xs font-semibold text-brand-800 uppercase tracking-wide">Scoring Weights</p>
        <div className="flex gap-1 flex-wrap">
          {Object.keys(WEIGHT_PRESETS).map(name => (
            <button
              key={name}
              onClick={() => applyPreset(name)}
              className={`px-2.5 py-1 text-xs rounded-lg font-medium transition-all ${
                preset === name
                  ? 'bg-brand-600 text-white shadow-brand-sm'
                  : 'bg-white text-slate-600 ring-1 ring-slate-200 hover:ring-brand-200 hover:text-brand-700'
              }`}
            >
              {name}
            </button>
          ))}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        {Object.entries(labels).map(([key, label]) => (
          <div key={key}>
            <div className="flex justify-between text-xs text-slate-600 mb-1.5">
              <span className="font-medium">{label}</span>
              <span className="font-bold text-brand-700">{Math.round((weights[key] || 0) * 100)}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              step="5"
              value={Math.round((weights[key] || 0) * 100)}
              onChange={(e) => updateWeight(key, e.target.value)}
              className="w-full"
            />
          </div>
        ))}
      </div>
    </div>
  )
}

export default function UploadForm({
  onFileSelect,
  jobDescription,
  onJobDescriptionChange,
  onJobFileSelect,
  onSubmit,
  isLoading,
  selectedFile,
  selectedJobFile,
  error,
  scoringWeights,
  onScoringWeightsChange,
}) {
  const [jdMode, setJdMode]               = useState('text')
  const [urlInput, setUrlInput]           = useState('')
  const [urlLoading, setUrlLoading]       = useState(false)
  const [urlError, setUrlError]           = useState('')
  const [showWeights, setShowWeights]     = useState(false)
  const [showAiSuggestion, setShowAiSuggestion] = useState(false)
  const [useNewWeights, setUseNewWeights] = useState(true)
  const [weightMetadata, setWeightMetadata] = useState(null)
  
  // Default to new 7-weight schema
  const defaultNewWeights = {
    core_competencies: 0.30,
    experience: 0.20,
    domain_fit: 0.20,
    education: 0.10,
    career_trajectory: 0.10,
    role_excellence: 0.10,
    risk: -0.10,
  }
  
  const defaultOldWeights = { 
    skills: 0.40, 
    experience: 0.35, 
    stability: 0.15, 
    education: 0.10 
  }
  
  const localWeights = scoringWeights || (useNewWeights ? defaultNewWeights : defaultOldWeights)

  // Saved JD library
  const [savedJds, setSavedJds]           = useState([])
  const [showJdPicker, setShowJdPicker]   = useState(false)
  const [saveLoading, setSaveLoading]     = useState(false)
  const [savedNotice, setSavedNotice]     = useState(false)
  const pickerRef = useRef(null)

  useEffect(() => {
    getTemplates()
      .then((res) => {
        const arr = Array.isArray(res) ? res : res?.templates || []
        setSavedJds(arr)
      })
      .catch(() => setSavedJds([]))
  }, [])

  useEffect(() => {
    const handleClick = (e) => {
      if (pickerRef.current && !pickerRef.current.contains(e.target)) setShowJdPicker(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const handleSaveJd = async () => {
    if (!jobDescription.trim()) return
    const name = window.prompt('Save JD as (enter a name):', `JD ${new Date().toLocaleDateString()}`)
    if (!name) return
    setSaveLoading(true)
    try {
      const saved = await createTemplate({ name: name.trim(), jd_text: jobDescription })
      setSavedJds((prev) => [saved, ...prev])
      setSavedNotice(true)
      setTimeout(() => setSavedNotice(false), 2000)
    } catch { /* ignore */ } finally {
      setSaveLoading(false)
    }
  }

  const handleLoadJd = (template) => {
    onJobDescriptionChange(template.jd_text)
    setJdMode('text')
    setShowJdPicker(false)
  }

  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) onFileSelect(acceptedFiles[0])
  }, [onFileSelect])

  const onJdDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      onJobFileSelect(acceptedFiles[0])
      setJdMode('file')
    }
  }, [onJobFileSelect])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc'],
      'text/plain': ['.txt'],
      'application/rtf': ['.rtf'],
      'text/rtf': ['.rtf'],
      'application/vnd.oasis.opendocument.text': ['.odt'],
    },
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024
  })

  const { getRootProps: getJdRootProps, getInputProps: getJdInputProps, isDragActive: isJdDragActive } = useDropzone({
    onDrop: onJdDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc'],
      'text/plain': ['.txt', '.md'],
      'application/rtf': ['.rtf'],
      'text/rtf': ['.rtf'],
      'text/html': ['.html', '.htm'],
      'application/vnd.oasis.opendocument.text': ['.odt'],
    },
    maxFiles: 1,
    maxSize: 5 * 1024 * 1024
  })

  const handleExtractUrl = async () => {
    if (!urlInput.trim()) return
    setUrlLoading(true)
    setUrlError('')
    try {
      const result = await extractJdFromUrl(urlInput.trim())
      onJobDescriptionChange(result.jd_text)
      setJdMode('text')
    } catch (err) {
      setUrlError(err.response?.data?.detail || 'Failed to extract JD from URL')
    } finally {
      setUrlLoading(false)
    }
  }

  const isSubmitDisabled = isLoading || !selectedFile || (
    jdMode === 'text' ? !jobDescription.trim() :
    jdMode === 'file' ? !selectedJobFile :
    !urlInput.trim()
  )

  return (
    <div className="w-full max-w-3xl mx-auto card-animate">
      <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand-xl p-6 md:p-8">
        <h2 className="text-xl font-bold text-brand-900 mb-6 tracking-tight">Upload Resume & Job Description</h2>

        {/* Resume Upload */}
        <div className="mb-6">
          <label className="block text-sm font-semibold text-slate-700 mb-2">Resume (PDF, DOCX, DOC, TXT, RTF, ODT)</label>
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all duration-200 ${
              isDragActive
                ? 'border-brand-500 bg-brand-50 shadow-brand-sm'
                : selectedFile
                ? 'border-brand-200 bg-brand-50/40'
                : 'border-brand-200 hover:border-brand-400 hover:bg-brand-50/40'
            }`}
          >
            <input {...getInputProps()} />
            {selectedFile ? (
              <div className="flex items-center justify-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-brand-100 flex items-center justify-center">
                  <FileText className="w-5 h-5 text-brand-600" />
                </div>
                <div className="text-left flex-1 min-w-0">
                  <p className="font-semibold text-slate-800 truncate">{selectedFile.name}</p>
                  <p className="text-sm text-slate-400">{(selectedFile.size / 1024).toFixed(1)} KB</p>
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); onFileSelect(null) }}
                  className="p-1.5 rounded-lg hover:bg-brand-100 text-slate-400 hover:text-brand-600 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <>
                <div className="w-12 h-12 rounded-2xl bg-brand-50 ring-1 ring-brand-100 flex items-center justify-center mx-auto mb-3">
                  <Upload className="w-6 h-6 text-brand-500" />
                </div>
                <p className="text-slate-600 font-medium mb-1">
                  {isDragActive ? 'Drop the file here...' : 'Drag & drop your resume here'}
                </p>
                <p className="text-sm text-slate-400">or click to browse (PDF, DOCX, DOC, TXT, RTF, ODT up to 10MB)</p>
              </>
            )}
          </div>
        </div>

        {/* Job Description */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <label className="block text-sm font-semibold text-slate-700">Job Description</label>

              {/* Load from saved JDs - now more prominent */}
              <div className="relative" ref={pickerRef}>
                <button
                  type="button"
                  onClick={() => setShowJdPicker((v) => !v)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-brand-700 bg-brand-50 hover:bg-brand-100 transition-colors border border-brand-200"
                >
                  <BookOpen className="w-3.5 h-3.5" />
                  Saved JDs
                  {savedJds.length > 0 && (
                    <span className="ml-0.5 bg-brand-200 text-brand-800 rounded-full px-1.5 py-0.5 text-[10px] font-bold">
                      {savedJds.length}
                    </span>
                  )}
                </button>
                {showJdPicker && (
                  <div className="absolute left-0 top-full mt-1.5 w-72 bg-white border border-brand-100 rounded-2xl shadow-brand-lg z-30 max-h-64 overflow-y-auto py-1">
                    {savedJds.length === 0 ? (
                      <div className="px-4 py-3">
                        <p className="text-xs text-slate-400">No saved JDs yet.</p>
                        <p className="text-[10px] text-slate-400 mt-1">Paste a JD and click "Save to Library" below.</p>
                      </div>
                    ) : (
                      <>
                        <p className="text-[10px] uppercase tracking-wide text-slate-400 font-semibold px-3 py-1.5 sticky top-0 bg-white/95 border-b border-brand-50">
                          Select a Template
                        </p>
                        {savedJds.map((t) => (
                          <button
                            key={t.id}
                            type="button"
                            onClick={() => handleLoadJd(t)}
                            className="w-full text-left px-4 py-3 hover:bg-brand-50 transition-colors border-b border-brand-50 last:border-b-0"
                          >
                            <p className="font-semibold text-slate-800 text-sm truncate">{t.name}</p>
                            <p className="text-xs text-slate-400 truncate mt-0.5">{t.jd_text.slice(0, 80)}…</p>
                          </button>
                        ))}
                        <div className="px-3 py-2 bg-brand-50/50 border-t border-brand-100">
                          <a href="/templates" className="text-xs text-brand-700 font-medium hover:text-brand-800 flex items-center gap-1">
                            <LayoutTemplate className="w-3 h-3" />
                            Manage all templates →
                          </a>
                        </div>
                      </>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Pill tab switcher */}
            <div className="flex bg-brand-50 ring-1 ring-brand-100 rounded-xl p-1">
              {[
                { mode: 'text', Icon: Type,   label: 'Text' },
                { mode: 'file', Icon: FileUp, label: 'File' },
                { mode: 'url',  Icon: Link2,  label: 'URL'  },
              ].map(({ mode, Icon, label }) => (
                <button
                  key={mode}
                  onClick={() => {
                    if (jdMode === 'file' && mode !== 'file') onJobFileSelect(null)
                    setJdMode(mode)
                  }}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                    jdMode === mode
                      ? 'bg-brand-600 text-white shadow-brand-sm'
                      : 'text-slate-500 hover:text-brand-700'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {label}
                </button>
              ))}
            </div>
          </div>

          {jdMode === 'text' && (
            <div className="relative">
              <textarea
                value={jobDescription}
                onChange={(e) => onJobDescriptionChange(e.target.value)}
                placeholder="Paste the job description here..."
                rows={6}
                className="w-full px-4 py-3 rounded-2xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 bg-white resize-none text-slate-700 placeholder-slate-400 text-sm transition-shadow"
              />
              {/* Save JD button - prominently placed below textarea */}
              <div className="flex justify-between items-center mt-2">
                <span className="text-xs text-slate-400">
                  {jobDescription.length > 0 && `${jobDescription.length.toLocaleString()} characters`}
                </span>
                <button
                  type="button"
                  onClick={handleSaveJd}
                  disabled={saveLoading || !jobDescription.trim()}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-semibold transition-all disabled:opacity-40
                    bg-white border border-brand-200 text-brand-700 hover:bg-brand-50 hover:border-brand-300"
                >
                  {savedNotice ? (
                    <>
                      <Check className="w-4 h-4 text-green-600" />
                      <span className="text-green-600">Saved to Library!</span>
                    </>
                  ) : saveLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <BookmarkPlus className="w-4 h-4" />
                      Save to Library
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {jdMode === 'file' && (
            <div
              {...getJdRootProps()}
              className={`border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition-all duration-200 ${
                isJdDragActive
                  ? 'border-brand-500 bg-brand-50'
                  : selectedJobFile
                  ? 'border-brand-200 bg-brand-50/40'
                  : 'border-brand-200 hover:border-brand-400 hover:bg-brand-50/40'
              }`}
            >
              <input {...getJdInputProps()} />
              {selectedJobFile ? (
                <div className="flex items-center justify-center gap-3">
                  <div className="w-8 h-8 rounded-xl bg-brand-100 flex items-center justify-center">
                    <FileText className="w-4 h-4 text-brand-600" />
                  </div>
                  <div className="text-left flex-1 min-w-0">
                    <p className="font-semibold text-slate-800 truncate">{selectedJobFile.name}</p>
                    <p className="text-sm text-slate-400">{(selectedJobFile.size / 1024).toFixed(1)} KB</p>
                  </div>
                </div>
              ) : (
                <>
                  <div className="w-10 h-10 rounded-2xl bg-brand-50 ring-1 ring-brand-100 flex items-center justify-center mx-auto mb-2">
                    <FileUp className="w-5 h-5 text-brand-500" />
                  </div>
                  <p className="text-slate-600 text-sm font-medium">
                    {isJdDragActive ? 'Drop JD file here...' : 'Upload JD — PDF, DOCX, DOC, TXT, RTF, HTML, ODT'}
                  </p>
                </>
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
                  placeholder="https://linkedin.com/jobs/view/... or indeed.com/..."
                  className="flex-1 px-4 py-2.5 rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm bg-white"
                />
                <button
                  onClick={handleExtractUrl}
                  disabled={urlLoading || !urlInput.trim()}
                  className="px-4 py-2.5 bg-brand-600 text-white text-sm font-semibold rounded-xl hover:bg-brand-700 disabled:opacity-60 flex items-center gap-2 transition-colors shadow-brand-sm"
                >
                  {urlLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Link2 className="w-4 h-4" />}
                  Extract
                </button>
              </div>
              {urlError && <p className="text-xs text-red-600 mt-1.5">{urlError}</p>}
              {jobDescription && jdMode === 'url' && (
                <p className="text-xs text-green-600 mt-1.5">JD extracted — switched to Text mode for review.</p>
              )}
            </div>
          )}
        </div>

        {/* AI Weight Suggestion */}
        {jobDescription && jobDescription.trim().length > 100 && (
          <div className="mb-6">
            <button
              onClick={() => setShowAiSuggestion(!showAiSuggestion)}
              className="flex items-center gap-2 text-sm font-semibold text-indigo-600 hover:text-indigo-700 transition-colors mb-3"
            >
              <Sparkles className="w-4 h-4" />
              AI Weight Suggestions
              {showAiSuggestion ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
            {showAiSuggestion && (
              <WeightSuggestionPanel
                jobDescription={jobDescription}
                currentWeights={localWeights}
                onWeightsAccepted={(weights) => {
                  setUseNewWeights(true)
                  onScoringWeightsChange && onScoringWeightsChange(weights)
                  setShowWeights(true)
                }}
              />
            )}
          </div>
        )}

        {/* Scoring Weights */}
        <div className="mb-6">
          <button
            onClick={() => setShowWeights(!showWeights)}
            className="flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-brand-700 transition-colors"
          >
            <SlidersHorizontal className="w-4 h-4" />
            Scoring Weights {useNewWeights && '(7-Factor Universal)'}
            {showWeights ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
          {showWeights && (
            <div className="mt-4">
              {useNewWeights ? (
                <UniversalWeightsPanel
                  weights={localWeights}
                  onChange={(w) => onScoringWeightsChange && onScoringWeightsChange(w)}
                  roleCategory={weightMetadata?.role_category}
                  roleExcellenceLabel={weightMetadata?.role_excellence_label}
                />
              ) : (
                <WeightsPanel
                  weights={localWeights}
                  onChange={(w) => onScoringWeightsChange && onScoringWeightsChange(w)}
                />
              )}
              <div className="mt-3 flex items-center justify-between">
                <button
                  onClick={() => {
                    setUseNewWeights(!useNewWeights)
                    onScoringWeightsChange && onScoringWeightsChange(
                      useNewWeights ? defaultOldWeights : defaultNewWeights
                    )
                  }}
                  className="text-xs text-slate-500 hover:text-indigo-600 transition-colors"
                >
                  Switch to {useNewWeights ? 'Legacy (4-weight)' : 'Universal (7-weight)'} mode
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="mb-5 p-4 bg-red-50 ring-1 ring-red-200 rounded-2xl flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Submit */}
        <button
          onClick={onSubmit}
          disabled={isSubmitDisabled}
          className={`w-full py-3.5 px-6 rounded-2xl font-bold text-white transition-all duration-200 text-sm tracking-wide ${
            isSubmitDisabled
              ? 'bg-slate-300 cursor-not-allowed text-slate-400'
              : 'btn-brand shadow-brand'
          }`}
        >
          {isLoading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Analyzing...
            </span>
          ) : (
            'Analyze Resume'
          )}
        </button>
      </div>
    </div>
  )
}
