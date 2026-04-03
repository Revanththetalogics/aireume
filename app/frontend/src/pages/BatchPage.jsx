import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, X, Loader2, Trophy, AlertTriangle, Download, CheckSquare } from 'lucide-react'
import NavBar from '../components/NavBar'
import { analyzeBatch, exportCsv, exportExcel } from '../lib/api'

function FitBadge({ score }) {
  let color = 'bg-red-100 text-red-700'
  if (score >= 70) color = 'bg-green-100 text-green-700'
  else if (score >= 45) color = 'bg-yellow-100 text-yellow-700'
  return <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${color}`}>{score}</span>
}

function RecommendBadge({ rec }) {
  const styles = {
    Shortlist: 'bg-green-100 text-green-700',
    Consider:  'bg-yellow-100 text-yellow-700',
    Reject:    'bg-red-100 text-red-700',
  }
  return <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${styles[rec] || 'bg-slate-100 text-slate-600'}`}>{rec}</span>
}

export default function BatchPage() {
  const navigate = useNavigate()
  const [files, setFiles]           = useState([])
  const [jdText, setJdText]         = useState('')
  const [isLoading, setIsLoading]   = useState(false)
  const [results, setResults]       = useState(null)
  const [error, setError]           = useState('')
  const [selected, setSelected]     = useState([])

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
    <div className="min-h-screen bg-slate-50">
      <NavBar />
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Batch Resume Screening</h2>
          <p className="text-slate-500 text-sm mt-1">Upload up to 50 resumes against one JD — get a ranked shortlist instantly.</p>
        </div>

        {!results && (
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-5">
            {/* Multi-file dropzone */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Resumes (up to 50)</label>
              <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                  isDragActive ? 'border-blue-500 bg-blue-50' : 'border-slate-300 hover:border-slate-400'
                }`}
              >
                <input {...getInputProps()} />
                <Upload className="w-10 h-10 text-slate-400 mx-auto mb-2" />
                <p className="text-slate-600">{isDragActive ? 'Drop resumes here...' : 'Drag & drop multiple resumes'}</p>
                <p className="text-sm text-slate-400 mt-1">PDF, DOCX — up to 50 files</p>
              </div>
              {files.length > 0 && (
                <div className="mt-3 space-y-1.5 max-h-40 overflow-y-auto">
                  {files.map((f, i) => (
                    <div key={i} className="flex items-center gap-2 px-3 py-1.5 bg-slate-50 rounded-lg border border-slate-200 text-sm">
                      <FileText className="w-4 h-4 text-blue-500 shrink-0" />
                      <span className="flex-1 text-slate-700 truncate">{f.name}</span>
                      <span className="text-slate-400 shrink-0">{(f.size / 1024).toFixed(0)}KB</span>
                      <button onClick={() => removeFile(i)} className="text-slate-400 hover:text-red-500 shrink-0">
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* JD */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Job Description</label>
              <textarea
                value={jdText}
                onChange={(e) => setJdText(e.target.value)}
                placeholder="Paste the job description for all resumes..."
                rows={6}
                className="w-full px-4 py-3 rounded-lg border border-slate-300 focus:ring-2 focus:ring-blue-500 resize-none text-slate-700 placeholder-slate-400 text-sm"
              />
            </div>

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-sm text-red-700">
                <AlertTriangle className="w-4 h-4 shrink-0" /> {error}
              </div>
            )}

            <button
              onClick={handleAnalyze}
              disabled={isLoading || !files.length || !jdText.trim()}
              className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
            >
              {isLoading ? <><Loader2 className="w-5 h-5 animate-spin" /> Analyzing {files.length} resumes...</> : `Analyze ${files.length || ''} Resumes`}
            </button>
          </div>
        )}

        {/* Results */}
        {results && (
          <div className="space-y-4">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div>
                <h3 className="text-lg font-bold text-slate-900">Ranked Shortlist</h3>
                <p className="text-sm text-slate-500">{results.total} candidates analyzed</p>
              </div>
              <div className="flex gap-2 flex-wrap">
                <button
                  onClick={() => { setResults(null); setFiles([]) }}
                  className="px-3 py-2 border border-slate-300 text-sm text-slate-700 rounded-lg hover:bg-slate-50 transition-colors"
                >
                  New Batch
                </button>
                <button
                  onClick={() => exportCsv(selected.length ? selected : allIds)}
                  className="flex items-center gap-2 px-3 py-2 border border-slate-300 text-sm text-slate-700 rounded-lg hover:bg-slate-50 transition-colors"
                >
                  <Download className="w-4 h-4" /> CSV
                </button>
                <button
                  onClick={() => exportExcel(selected.length ? selected : allIds)}
                  className="flex items-center gap-2 px-3 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 transition-colors"
                >
                  <Download className="w-4 h-4" /> Excel
                </button>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3 text-left w-10">
                      <input
                        type="checkbox"
                        checked={selected.length === allIds.length && allIds.length > 0}
                        onChange={(e) => setSelected(e.target.checked ? allIds : [])}
                        className="rounded"
                      />
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Rank</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">File</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Score</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Recommendation</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Risk</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {results.results.map((row) => {
                    const r = row.result
                    const id = r.result_id
                    return (
                      <tr key={row.rank} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                        <td className="px-4 py-3">
                          <input
                            type="checkbox"
                            checked={selected.includes(id)}
                            onChange={() => id && toggleSelect(id)}
                            className="rounded"
                          />
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-1">
                            {row.rank === 1 && <Trophy className="w-4 h-4 text-amber-500" />}
                            <span className="font-bold text-slate-700">#{row.rank}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-slate-700 max-w-[200px] truncate">{row.filename}</td>
                        <td className="px-4 py-3"><FitBadge score={r.fit_score} /></td>
                        <td className="px-4 py-3"><RecommendBadge rec={r.final_recommendation} /></td>
                        <td className="px-4 py-3">
                          <span className={`text-xs font-medium ${
                            r.risk_level === 'Low' ? 'text-green-600' :
                            r.risk_level === 'High' ? 'text-red-600' : 'text-amber-600'
                          }`}>{r.risk_level}</span>
                        </td>
                        <td className="px-4 py-3">
                          <button
                            onClick={() => navigate('/report', { state: { result: r } })}
                            className="text-xs text-blue-600 hover:underline font-medium"
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
