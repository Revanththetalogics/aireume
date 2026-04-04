import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, X, Loader2, Trophy, AlertTriangle, Download } from 'lucide-react'
import NavBar from '../components/NavBar'
import { analyzeBatch, exportCsv, exportExcel } from '../lib/api'

function FitBadge({ score }) {
  let color = 'bg-red-50 text-red-700 ring-red-200'
  if (score >= 70) color = 'bg-green-50 text-green-700 ring-green-200'
  else if (score >= 45) color = 'bg-amber-50 text-amber-700 ring-amber-200'
  return <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ring-1 ${color}`}>{score}</span>
}

function RecommendBadge({ rec }) {
  const styles = {
    Shortlist: 'bg-green-50 text-green-700 ring-green-200',
    Consider:  'bg-amber-50 text-amber-700 ring-amber-200',
    Reject:    'bg-red-50 text-red-700 ring-red-200',
  }
  return <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ring-1 ${styles[rec] || 'bg-slate-50 text-slate-600 ring-slate-200'}`}>{rec}</span>
}

export default function BatchPage() {
  const navigate = useNavigate()
  const [files, setFiles]         = useState([])
  const [jdText, setJdText]       = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [results, setResults]     = useState(null)
  const [error, setError]         = useState('')
  const [selected, setSelected]   = useState([])

  const onDrop = useCallback((accepted) => {
    setFiles(prev => [...prev, ...accepted].slice(0, 50))
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc'],
    },
    maxFiles: 50,
    maxSize: 10 * 1024 * 1024,
  })

  const removeFile = (idx) => setFiles(prev => prev.filter((_, i) => i !== idx))

  const handleAnalyze = async () => {
    if (!files.length || !jdText.trim()) {
      setError('Add at least one resume and a job description')
      return
    }
    setError('')
    setIsLoading(true)
    setResults(null)
    try {
      const data = await analyzeBatch(files, jdText)
      setResults(data)
      setSelected([])
    } catch (err) {
      setError(err.response?.data?.detail || 'Batch analysis failed')
    } finally {
      setIsLoading(false)
    }
  }

  const toggleSelect = (id) => {
    setSelected(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])
  }

  const allIds = results?.results?.map(r => r.result?.result_id).filter(Boolean) || []

  return (
    <div className="min-h-screen bg-surface">
      <NavBar />
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <div className="card-animate">
          <h2 className="text-3xl font-extrabold text-brand-900 tracking-tight">Batch Resume Screening</h2>
          <p className="text-slate-500 text-sm mt-1 font-medium">Upload up to 50 resumes against one JD — get a ranked shortlist instantly.</p>
        </div>

        {!results && (
          <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6 space-y-5 card-animate">
            {/* Multi-file dropzone */}
            <div>
              <label className="block text-sm font-bold text-slate-700 mb-2">Resumes (up to 50)</label>
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
                <p className="text-sm text-slate-400 mt-1">PDF, DOCX — up to 50 files</p>
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

            {/* JD */}
            <div>
              <label className="block text-sm font-bold text-slate-700 mb-2">Job Description</label>
              <textarea
                value={jdText}
                onChange={(e) => setJdText(e.target.value)}
                placeholder="Paste the job description for all resumes..."
                rows={6}
                className="w-full px-4 py-3 rounded-2xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 resize-none text-slate-700 placeholder-slate-400 text-sm bg-white"
              />
            </div>

            {error && (
              <div className="p-3.5 bg-red-50 ring-1 ring-red-200 rounded-2xl flex items-center gap-2.5 text-sm text-red-700">
                <AlertTriangle className="w-4 h-4 shrink-0" /> {error}
              </div>
            )}

            <button
              onClick={handleAnalyze}
              disabled={isLoading || !files.length || !jdText.trim()}
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
                            r.risk_level === 'Low' ? 'text-green-700' :
                            r.risk_level === 'High' ? 'text-red-700' : 'text-amber-700'
                          }`}>{r.risk_level}</span>
                        </td>
                        <td className="px-4 py-3.5">
                          <button
                            onClick={() => navigate('/report', { state: { result: r } })}
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
