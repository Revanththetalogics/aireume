import { useState, useCallback, useEffect, useRef } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, X, Loader2, Trophy, AlertTriangle, Download, BookOpen, LayoutTemplate, BookmarkPlus, Check, Sparkles } from 'lucide-react'
import { analyzeBatch, analyzeBatchChunked, exportCsv, exportExcel, getTemplates, createTemplate } from '../lib/api'
import { useUsageCheck, useSubscription } from '../hooks/useSubscription'

function FitBadge({ score }) {
  if (score == null)
    return <span className="px-2.5 py-0.5 rounded-full text-xs font-bold ring-1 bg-slate-50 text-slate-500 ring-slate-200">—</span>
  let color = 'bg-red-50 text-red-700 ring-red-200'
  if (score >= 72) color = 'bg-green-50 text-green-700 ring-green-200'
  else if (score >= 45) color = 'bg-amber-50 text-amber-700 ring-amber-200'
  return <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ring-1 ${color}`}>{score}</span>
}

function RecommendBadge({ rec }) {
  const styles = {
    Shortlist: 'bg-green-50 text-green-700 ring-green-200',
    Consider:  'bg-amber-50 text-amber-700 ring-amber-200',
    Reject:    'bg-red-50 text-red-700 ring-red-200',
    Pending:   'bg-slate-50 text-slate-600 ring-slate-200',
  }
  return <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ring-1 ${styles[rec] || 'bg-slate-50 text-slate-600 ring-slate-200'}`}>{rec || '—'}</span>
}

export default function BatchPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [files, setFiles]         = useState([])
  const [jdText, setJdText]       = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [results, setResults]     = useState(location.state?.results || null)
  const [error, setError]         = useState('')
  const [selected, setSelected]   = useState([])

  // Saved JD / Templates
  const [savedJds, setSavedJds]   = useState([])
  const [showJdPicker, setShowJdPicker] = useState(false)
  const [saveLoading, setSaveLoading]   = useState(false)
  const [savedNotice, setSavedNotice]   = useState(false)
  const pickerRef = useRef(null)

  // Subscription & Usage
  const { checkBeforeAnalysis, getRemainingAnalyses } = useUsageCheck()
  const { subscription, isFeatureAvailable, refreshAfterAnalysis } = useSubscription()
  const [usageCheck, setUsageCheck] = useState(null)

  // Upload progress tracking for chunked uploads
  const [uploadProgress, setUploadProgress] = useState({})
  const [overallProgress, setOverallProgress] = useState(null)
  const [isUploading, setIsUploading] = useState(false)

  // Restore results from navigation state (when coming back from report page)
  useEffect(() => {
    if (location.state?.results) {
      setResults(location.state.results)
    }
  }, [location.state])

  useEffect(() => {
    getTemplates().then(setSavedJds).catch(() => {})
  }, [])

  useEffect(() => {
    const handleClick = (e) => {
      if (pickerRef.current && !pickerRef.current.contains(e.target)) setShowJdPicker(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  // Check usage when files change
  useEffect(() => {
    if (files.length > 0) {
      checkBeforeAnalysis(files.length).then(setUsageCheck)
    } else {
      setUsageCheck(null)
    }
  }, [files.length, checkBeforeAnalysis])

  const onDrop = useCallback((accepted) => {
    setFiles(prev => [...prev, ...accepted].slice(0, 50))
  }, [])

  // Get batch limit from subscription
  const maxBatchSize = subscription?.current_plan?.plan?.limits?.batch_size || 50

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc'],
    },
    maxFiles: maxBatchSize,
    // No maxSize limit - chunked upload handles large files
  })

  const removeFile = (idx) => setFiles(prev => prev.filter((_, i) => i !== idx))

  const handleAnalyze = async () => {
    if (!files.length || !jdText.trim()) {
      setError('Add at least one resume and a job description')
      return
    }

    // Check usage before analyzing
    const check = await checkBeforeAnalysis(files.length)
    if (!check.allowed) {
      setError(check.message || 'Usage limit exceeded. Please upgrade your plan.')
      return
    }

    setError('')
    setIsLoading(true)
    setResults(null)
    setUploadProgress({})
    setOverallProgress(null)
    
    try {
      // Always use chunked upload to bypass Cloudflare 100MB limit
      // Cloudflare blocks at proxy level, so we can't rely on total size check
      setIsUploading(true)
      
      const data = await analyzeBatchChunked(files, jdText, null, null, {
        onFileProgress: (filename, progress) => {
          setUploadProgress(prev => ({
            ...prev,
            [filename]: progress
          }))
        },
        onOverallProgress: (progress) => {
          setOverallProgress(progress)
        },
        onFileComplete: (filename) => {
          console.log(`Upload complete: ${filename}`)
        },
        onFileError: (filename, error) => {
          console.error(`Upload failed for ${filename}:`, error)
        },
      })
      
      setIsUploading(false)
      
      setResults(data)
      setSelected([])
      // Refresh subscription to show updated usage
      await refreshAfterAnalysis(files.length)
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(
        (Array.isArray(detail) ? 'Validation error — check file types or JD format.' : detail) ||
        err.message ||
        'Batch analysis failed'
      )
    } finally {
      setIsLoading(false)
      setIsUploading(false)
      setUploadProgress({})
      setOverallProgress(null)
    }
  }

  const toggleSelect = (id) => {
    setSelected(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])
  }

  const handleLoadJd = (template) => {
    setJdText(template.jd_text)
    setShowJdPicker(false)
    
    // Load weights if available
    if (template.scoring_weights) {
      try {
        const savedWeights = typeof template.scoring_weights === 'string' 
          ? JSON.parse(template.scoring_weights) 
          : template.scoring_weights
        
        // Only set weights if they're valid and not empty
        if (savedWeights && Object.keys(savedWeights).length > 0) {
          setWeights(savedWeights)
        }
      } catch (e) {
        console.error('Failed to parse weights from template:', e)
      }
    }
  }

  const handleSaveJd = async () => {
    if (!jdText.trim()) return
    const name = window.prompt('Save JD as (enter a name):', `JD ${new Date().toLocaleDateString()}`)
    if (!name) return
    setSaveLoading(true)
    try {
      const saved = await createTemplate({ name: name.trim(), jd_text: jdText })
      setSavedJds((prev) => [saved, ...prev])
      setSavedNotice(true)
      setTimeout(() => setSavedNotice(false), 2000)
    } catch { /* ignore */ } finally {
      setSaveLoading(false)
    }
  }

  const allIds = results?.results?.map(r => r.result?.result_id).filter(Boolean) || []

  return (
    <div>
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
          <div className="card-animate">
          <h2 className="text-3xl font-extrabold text-brand-900 tracking-tight">Batch Resume Screening</h2>
          <p className="text-slate-500 text-sm mt-1 font-medium">
            Upload up to {maxBatchSize} resumes against one JD — get a ranked shortlist instantly.
            {usageCheck?.remaining !== undefined && usageCheck.remaining !== Infinity && (
              <span className="ml-2 text-brand-600 font-semibold">({usageCheck.remaining} analyses remaining)</span>
            )}
          </p>
        </div>

        {!results && (
          <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6 space-y-5 card-animate">
            {/* Multi-file dropzone */}
            <div>
              <label className="block text-sm font-bold text-slate-700 mb-2">Resumes (up to {maxBatchSize})</label>
              <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all ${
                  isDragActive
                    ? 'border-brand-500 bg-brand-50 shadow-brand-sm'
                    : 'border-brand-200 hover:border-brand-400 hover:bg-brand-50/40'
                }`}
              >
                <input {...getInputProps()} />
                <div className="w-12 h-12 rounded-2xl bg-brand-50 ring-1 ring-brand-100 flex items-center justify-center mx-auto mb-3">
                  <Upload className="w-6 h-6 text-brand-500" />
                </div>
                <p className="text-slate-600 font-medium">{isDragActive ? 'Drop resumes here...' : 'Drag & drop multiple resumes'}</p>
                <p className="text-sm text-slate-400 mt-1">PDF, DOCX — up to {maxBatchSize} files</p>
              </div>
              {files.length > 0 && (
                <div className="mt-3 space-y-1.5 max-h-40 overflow-y-auto">
                  {files.map((f, i) => (
                    <div key={i} className="flex items-center gap-2.5 px-3 py-2 bg-brand-50/60 rounded-xl ring-1 ring-brand-100 text-sm">
                      <div className="w-6 h-6 rounded-lg bg-brand-100 flex items-center justify-center shrink-0">
                        <FileText className="w-3.5 h-3.5 text-brand-600" />
                      </div>
                      <span className="flex-1 text-brand-900 font-medium truncate">{f.name}</span>
                      <span className="text-slate-400 shrink-0 text-xs">{(f.size / 1024).toFixed(0)}KB</span>
                      <button onClick={() => removeFile(i)} className="text-slate-400 hover:text-red-500 shrink-0 transition-colors">
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* JD with Saved JD selector */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-bold text-slate-700">Job Description</label>

                {/* Saved JD Dropdown */}
                <div className="relative" ref={pickerRef}>
                  <button
                    type="button"
                    onClick={() => setShowJdPicker((v) => !v)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-brand-700 bg-brand-50 hover:bg-brand-100 transition-colors"
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
                    <div className="absolute right-0 top-full mt-1.5 w-72 bg-white border border-brand-100 rounded-2xl shadow-brand-lg z-30 max-h-64 overflow-y-auto py-1">
                      {savedJds.length === 0 ? (
                        <p className="text-xs text-slate-400 px-4 py-3">No saved JDs yet. Paste a JD and click Save below.</p>
                      ) : (
                        <>
                          <p className="text-[10px] uppercase tracking-wide text-slate-400 font-semibold px-3 py-1.5 sticky top-0 bg-white/95 border-b border-brand-50">
                            Select a Job Description
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
                            <Link to="/templates" className="text-xs text-brand-700 font-medium hover:text-brand-800 flex items-center gap-1">
                              <LayoutTemplate className="w-3 h-3" />
                              Manage all templates →
                            </Link>
                          </div>
                        </>
                      )}
                    </div>
                  )}
                </div>
              </div>

              <textarea
                value={jdText}
                onChange={(e) => setJdText(e.target.value)}
                placeholder="Paste the job description for all resumes..."
                rows={6}
                className="w-full px-4 py-3 rounded-2xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 resize-none text-slate-700 placeholder-slate-400 text-sm bg-white"
              />

              {/* Save JD button - below textarea */}
              <div className="flex justify-end mt-2">
                <button
                  type="button"
                  onClick={handleSaveJd}
                  disabled={saveLoading || !jdText.trim()}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors disabled:opacity-40
                    text-slate-500 hover:text-brand-700 hover:bg-brand-50"
                >
                  {savedNotice ? (
                    <><Check className="w-3.5 h-3.5 text-green-600" /> <span className="text-green-600">Saved!</span></>
                  ) : saveLoading ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <><BookmarkPlus className="w-3.5 h-3.5" /> Save this JD</>
                  )}
                </button>
              </div>
            </div>

            {/* Upload Progress */}
            {isUploading && overallProgress && (
              <div className="p-4 bg-blue-50 ring-1 ring-blue-200 rounded-2xl space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium text-blue-900">Uploading files...</span>
                  <span className="text-blue-700">{overallProgress.percent}%</span>
                </div>
                <div className="w-full bg-blue-100 rounded-full h-2 overflow-hidden">
                  <div 
                    className="bg-blue-500 h-full transition-all duration-300 ease-out"
                    style={{ width: `${overallProgress.percent}%` }}
                  />
                </div>
                <div className="text-xs text-blue-600">
                  {overallProgress.completedFiles} of {overallProgress.totalFiles} files uploaded
                </div>
              </div>
            )}

            {error && (
              <div className="p-3.5 bg-red-50 ring-1 ring-red-200 rounded-2xl flex items-center gap-2.5 text-sm text-red-700">
                <AlertTriangle className="w-4 h-4 shrink-0" /> {error}
              </div>
            )}

            {/* Usage Status Banner */}
            {usageCheck && !error && (
              <div className={`p-3.5 rounded-2xl flex items-center justify-between text-sm ${
                usageCheck.allowed
                  ? files.length > (usageCheck.remaining || 0) && usageCheck.remaining !== Infinity
                    ? 'bg-amber-50 ring-1 ring-amber-200 text-amber-700'
                    : 'bg-green-50 ring-1 ring-green-200 text-green-700'
                  : 'bg-red-50 ring-1 ring-red-200 text-red-700'
              }`}>
                <div className="flex items-center gap-2.5">
                  <Sparkles className="w-4 h-4 shrink-0" />
                  {usageCheck.allowed ? (
                    files.length > (usageCheck.remaining || 0) && usageCheck.remaining !== Infinity ? (
                      <span>Only {usageCheck.remaining} analyses remaining — you added {files.length} files</span>
                    ) : (
                      <span>{usageCheck.remaining === Infinity ? 'Unlimited' : usageCheck.remaining} analyses remaining this month</span>
                    )
                  ) : (
                    <span>{usageCheck.message}</span>
                  )}
                </div>
                {(!usageCheck.allowed || (files.length > (usageCheck.remaining || 0) && usageCheck.remaining !== Infinity)) && (
                  <Link
                    to="/settings"
                    className="text-xs font-semibold underline hover:no-underline"
                  >
                    Upgrade →
                  </Link>
                )}
              </div>
            )}

            <button
              onClick={handleAnalyze}
              disabled={isLoading || !files.length || !jdText.trim() || (usageCheck && !usageCheck.allowed)}
              className="w-full py-3.5 btn-brand text-white font-bold rounded-2xl disabled:opacity-50 disabled:cursor-not-allowed shadow-brand flex items-center justify-center gap-2 text-sm"
            >
              {isLoading
                ? <><Loader2 className="w-5 h-5 animate-spin" /> Analyzing {files.length} resumes...</>
                : `Analyze ${files.length || ''} Resumes`}
            </button>
          </div>
        )}

        {/* Results */}
        {results && (
          <div className="space-y-4 card-animate">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div>
                <h3 className="text-xl font-extrabold text-brand-900 tracking-tight">Ranked Shortlist</h3>
                <p className="text-sm text-slate-500 font-medium">{results.total} candidates analyzed</p>
              </div>
              <div className="flex gap-2 flex-wrap">
                <button
                  onClick={() => { setResults(null); setFiles([]) }}
                  className="px-3 py-2 ring-1 ring-brand-200 text-sm font-semibold text-brand-700 rounded-xl hover:bg-brand-50 transition-colors"
                >
                  New Batch
                </button>
                <button
                  onClick={() => exportCsv(selected.length ? selected : allIds)}
                  className="flex items-center gap-2 px-3 py-2 ring-1 ring-brand-200 text-sm font-semibold text-brand-700 rounded-xl hover:bg-brand-50 transition-colors"
                >
                  <Download className="w-4 h-4" /> CSV
                </button>
                <button
                  onClick={() => exportExcel(selected.length ? selected : allIds)}
                  className="flex items-center gap-2 px-3 py-2 bg-green-600 text-white text-sm font-bold rounded-xl hover:bg-green-700 transition-colors shadow-sm"
                >
                  <Download className="w-4 h-4" /> Excel
                </button>
              </div>
            </div>

            <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-brand-50 border-b border-brand-100">
                  <tr>
                    <th className="px-4 py-3.5 text-left w-10">
                      <input
                        type="checkbox"
                        checked={selected.length === allIds.length && allIds.length > 0}
                        onChange={(e) => setSelected(e.target.checked ? allIds : [])}
                        className="rounded"
                      />
                    </th>
                    <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Rank</th>
                    <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">File</th>
                    <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Score</th>
                    <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Recommendation</th>
                    <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Risk</th>
                    <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {results.results.map((row) => {
                    const r  = row.result
                    const id = r.result_id
                    return (
                      <tr key={row.rank} className="border-b border-brand-50 hover:bg-brand-50/40 transition-colors">
                        <td className="px-4 py-3.5">
                          <input
                            type="checkbox"
                            checked={selected.includes(id)}
                            onChange={() => id && toggleSelect(id)}
                            className="rounded"
                          />
                        </td>
                        <td className="px-4 py-3.5">
                          <div className="flex items-center gap-1.5">
                            {row.rank === 1 && <Trophy className="w-4 h-4 text-amber-500" />}
                            <span className="font-extrabold text-brand-900">#{row.rank}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3.5 text-brand-900 font-medium max-w-[200px] truncate">{row.filename}</td>
                        <td className="px-4 py-3.5"><FitBadge score={r.fit_score} /></td>
                        <td className="px-4 py-3.5"><RecommendBadge rec={r.final_recommendation} /></td>
                        <td className="px-4 py-3.5">
                          <span className={`text-xs font-bold ${
                            !r.risk_level       ? 'text-slate-400' :
                            r.risk_level === 'Low'  ? 'text-green-700' :
                            r.risk_level === 'High' ? 'text-red-700'   : 'text-amber-700'
                          }`}>{r.risk_level || '—'}</span>
                        </td>
                        <td className="px-4 py-3.5">
                          <button
                            onClick={() => navigate('/report', { 
                              state: { 
                                result: r,
                                fromBatch: true,
                                batchResults: results
                              } 
                            })}
                            className="text-xs text-brand-600 hover:text-brand-700 font-bold hover:underline"
                          >
                            View Report
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
