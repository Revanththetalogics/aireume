import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, AlertCircle, FileUp, Type, Link2, SlidersHorizontal, ChevronDown, ChevronUp, Loader2 } from 'lucide-react'
import { extractJdFromUrl } from '../lib/api'

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
    <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-blue-800 uppercase tracking-wide">Scoring Weights</p>
        <div className="flex gap-1 flex-wrap">
          {Object.keys(WEIGHT_PRESETS).map(name => (
            <button
              key={name}
              onClick={() => applyPreset(name)}
              className={`px-2 py-1 text-xs rounded-md font-medium transition-colors ${
                preset === name ? 'bg-blue-600 text-white' : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
              }`}
            >
              {name}
            </button>
          ))}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {Object.entries(labels).map(([key, label]) => (
          <div key={key}>
            <div className="flex justify-between text-xs text-slate-600 mb-1">
              <span>{label}</span>
              <span className="font-bold">{Math.round((weights[key] || 0) * 100)}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              step="5"
              value={Math.round((weights[key] || 0) * 100)}
              onChange={(e) => updateWeight(key, e.target.value)}
              className="w-full accent-blue-600"
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
  const localWeights = scoringWeights || { skills: 0.40, experience: 0.35, stability: 0.15, education: 0.10 }

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
      'application/msword': ['.doc']
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
    <div className="w-full max-w-3xl mx-auto">
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 md:p-8">
        <h2 className="text-2xl font-semibold text-slate-800 mb-6">Upload Resume & Job Description</h2>

        {/* Resume Upload */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-slate-700 mb-2">Resume (PDF or DOCX)</label>
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors duration-200 ${
              isDragActive ? 'border-blue-500 bg-blue-50' : 'border-slate-300 hover:border-slate-400'
            } ${selectedFile ? 'bg-slate-50' : ''}`}
          >
            <input {...getInputProps()} />
            {selectedFile ? (
              <div className="flex items-center justify-center gap-3">
                <FileText className="w-8 h-8 text-blue-500" />
                <div className="text-left">
                  <p className="font-medium text-slate-800">{selectedFile.name}</p>
                  <p className="text-sm text-slate-500">{(selectedFile.size / 1024).toFixed(1)} KB</p>
                </div>
              </div>
            ) : (
              <>
                <Upload className="w-10 h-10 text-slate-400 mx-auto mb-3" />
                <p className="text-slate-600 mb-1">{isDragActive ? 'Drop the file here...' : 'Drag & drop your resume here'}</p>
                <p className="text-sm text-slate-400">or click to browse (PDF, DOCX up to 10MB)</p>
              </>
            )}
          </div>
        </div>

        {/* Job Description */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-slate-700">Job Description</label>
            <div className="flex bg-slate-100 rounded-lg p-1">
              {[
                { mode: 'text', Icon: Type,     label: 'Text' },
                { mode: 'file', Icon: FileUp,   label: 'File' },
                { mode: 'url',  Icon: Link2,    label: 'URL'  },
              ].map(({ mode, Icon, label }) => (
                <button
                  key={mode}
                  onClick={() => {
                    // Clear stale job file when leaving file-upload mode
                    if (jdMode === 'file' && mode !== 'file') {
                      onJobFileSelect(null)
                    }
                    setJdMode(mode)
                  }}
                  className={`flex items-center gap-1 px-3 py-1 rounded-md text-sm transition-all ${
                    jdMode === mode ? 'bg-white shadow-sm text-blue-600' : 'text-slate-600'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </button>
              ))}
            </div>
          </div>

          {jdMode === 'text' && (
            <textarea
              value={jobDescription}
              onChange={(e) => onJobDescriptionChange(e.target.value)}
              placeholder="Paste the job description here..."
              rows={6}
              className="w-full px-4 py-3 rounded-lg border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none text-slate-700 placeholder-slate-400"
            />
          )}

          {jdMode === 'file' && (
            <div
              {...getJdRootProps()}
              className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors duration-200 ${
                isJdDragActive ? 'border-blue-500 bg-blue-50' : 'border-slate-300 hover:border-slate-400'
              } ${selectedJobFile ? 'bg-slate-50' : ''}`}
            >
              <input {...getJdInputProps()} />
              {selectedJobFile ? (
                <div className="flex items-center justify-center gap-3">
                  <FileText className="w-6 h-6 text-green-500" />
                  <div className="text-left">
                    <p className="font-medium text-slate-800">{selectedJobFile.name}</p>
                    <p className="text-sm text-slate-500">{(selectedJobFile.size / 1024).toFixed(1)} KB</p>
                  </div>
                </div>
              ) : (
                <>
                  <FileUp className="w-8 h-8 text-slate-400 mx-auto mb-2" />
                  <p className="text-slate-600 text-sm">{isJdDragActive ? 'Drop JD file here...' : 'Upload JD — PDF, DOCX, DOC, TXT, RTF, HTML, ODT'}</p>
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
                  className="flex-1 px-4 py-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-blue-500 text-sm"
                />
                <button
                  onClick={handleExtractUrl}
                  disabled={urlLoading || !urlInput.trim()}
                  className="px-4 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-60 flex items-center gap-2 transition-colors"
                >
                  {urlLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Link2 className="w-4 h-4" />}
                  Extract
                </button>
              </div>
              {urlError && <p className="text-xs text-red-600 mt-1">{urlError}</p>}
              {jobDescription && jdMode === 'url' && (
                <p className="text-xs text-green-600 mt-1">JD extracted successfully — switched to Text mode for review.</p>
              )}
            </div>
          )}
        </div>

        {/* Scoring Weights */}
        <div className="mb-6">
          <button
            onClick={() => setShowWeights(!showWeights)}
            className="flex items-center gap-2 text-sm text-slate-600 hover:text-slate-800 transition-colors"
          >
            <SlidersHorizontal className="w-4 h-4" />
            Scoring Weights
            {showWeights ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
          {showWeights && (
            <WeightsPanel
              weights={localWeights}
              onChange={(w) => onScoringWeightsChange && onScoringWeightsChange(w)}
            />
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Submit */}
        <button
          onClick={onSubmit}
          disabled={isSubmitDisabled}
          className={`w-full py-3 px-6 rounded-lg font-semibold text-white transition-all duration-200 ${
            isSubmitDisabled ? 'bg-slate-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 active:scale-[0.98]'
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
