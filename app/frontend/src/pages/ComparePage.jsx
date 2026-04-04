import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { GitCompare, Trophy, Check, Download } from 'lucide-react'
import NavBar from '../components/NavBar'
import { getHistory, compareResults, exportCsv } from '../lib/api'

function ScoreCell({ value, isWinner, color = 'brand' }) {
  const colors = {
    brand: 'text-brand-700 bg-brand-50 ring-brand-200',
    green: 'text-green-700 bg-green-50 ring-green-200',
    amber: 'text-amber-700 bg-amber-50 ring-amber-200',
  }
  return (
    <div className={`flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-xl font-bold text-sm ring-1 ${isWinner ? colors[color] : 'text-slate-600 bg-slate-50 ring-slate-200'}`}>
      {isWinner && <Trophy className="w-3.5 h-3.5" />}
      {value}%
    </div>
  )
}

export default function ComparePage() {
  const location = useLocation()
  const navigate  = useNavigate()
  const [history, setHistory]         = useState([])
  const [selected, setSelected]       = useState(location.state?.ids || [])
  const [comparison, setComparison]   = useState(null)
  const [loading, setLoading]         = useState(false)
  const [histLoading, setHistLoading] = useState(true)
  const [error, setError]             = useState('')

  useEffect(() => {
    getHistory().then(data => { setHistory(data); setHistLoading(false) }).catch(() => setHistLoading(false))
  }, [])

  const toggleSelect = (id) => {
    if (selected.includes(id)) {
      setSelected(prev => prev.filter(x => x !== id))
    } else if (selected.length < 5) {
      setSelected(prev => [...prev, id])
    }
  }

  const handleCompare = async () => {
    if (selected.length < 2) { setError('Select at least 2 candidates'); return }
    setError('')
    setLoading(true)
    try {
      const data = await compareResults(selected)
      setComparison(data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Comparison failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-surface">
      <NavBar />
      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <div className="card-animate">
          <h2 className="text-3xl font-extrabold text-brand-900 tracking-tight">Candidate Comparison</h2>
          <p className="text-slate-500 text-sm mt-1 font-medium">Select 2–5 candidates from history to compare side-by-side.</p>
        </div>

        {/* Selector */}
        {!comparison && (
          <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-5 space-y-4 card-animate">
            <div className="flex items-center justify-between">
              <p className="text-sm font-bold text-brand-700">
                <span className="text-brand-600">{selected.length}</span>/5 selected
              </p>
              <button
                onClick={handleCompare}
                disabled={selected.length < 2 || loading}
                className="flex items-center gap-2 px-4 py-2 btn-brand text-white text-sm font-bold rounded-xl disabled:opacity-50 shadow-brand-sm"
              >
                <GitCompare className="w-4 h-4" />
                {loading ? 'Comparing...' : 'Compare'}
              </button>
            </div>
            {error && <p className="text-sm text-red-600 font-medium">{error}</p>}

            {histLoading ? (
              <div className="flex justify-center py-8">
                <div className="w-6 h-6 border-4 border-brand-600 border-t-transparent rounded-full animate-spin" />
              </div>
            ) : (
              <div className="space-y-1.5 max-h-80 overflow-y-auto">
                {history.map(r => (
                  <div
                    key={r.id}
                    onClick={() => toggleSelect(r.id)}
                    className={`flex items-center gap-3 p-3 rounded-2xl ring-1 cursor-pointer transition-all ${
                      selected.includes(r.id)
                        ? 'ring-brand-300 bg-brand-50'
                        : 'ring-slate-200 hover:ring-brand-200 hover:bg-brand-50/40'
                    }`}
                  >
                    <div className={`w-5 h-5 rounded-lg ring-2 flex items-center justify-center shrink-0 transition-all ${
                      selected.includes(r.id)
                        ? 'ring-brand-600 bg-brand-600'
                        : 'ring-slate-300'
                    }`}>
                      {selected.includes(r.id) && <Check className="w-3 h-3 text-white" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-brand-900">Result #{r.id}</p>
                      <p className="text-xs text-slate-400 font-medium">{new Date(r.timestamp).toLocaleDateString()}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-bold px-2.5 py-0.5 rounded-full ring-1 ${
                        r.fit_score >= 70 ? 'bg-green-50 text-green-700 ring-green-200' :
                        r.fit_score >= 45 ? 'bg-amber-50 text-amber-700 ring-amber-200' : 'bg-red-50 text-red-700 ring-red-200'
                      }`}>{r.fit_score}</span>
                      <span className="text-xs text-slate-500 font-medium">{r.final_recommendation}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Comparison table */}
        {comparison && (
          <div className="space-y-4 card-animate">
            <div className="flex items-center justify-between">
              <h3 className="text-xl font-extrabold text-brand-900 tracking-tight">Comparison Results</h3>
              <div className="flex gap-2">
                <button
                  onClick={() => setComparison(null)}
                  className="px-3 py-2 ring-1 ring-brand-200 text-sm font-semibold rounded-xl hover:bg-brand-50 text-brand-700 transition-colors"
                >
                  New Comparison
                </button>
                <button
                  onClick={() => exportCsv(selected)}
                  className="flex items-center gap-2 px-3 py-2 ring-1 ring-brand-200 text-sm font-semibold rounded-xl hover:bg-brand-50 text-brand-700 transition-colors"
                >
                  <Download className="w-4 h-4" /> Export
                </button>
              </div>
            </div>

            <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-brand-50 border-b border-brand-100">
                  <tr>
                    <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide w-36">Category</th>
                    {comparison.candidates.map(c => (
                      <th key={c.id} className="px-4 py-3.5 text-center text-xs font-bold text-brand-900">
                        <div>{c.candidate_name}</div>
                        {c.winners?.overall && (
                          <div className="flex items-center justify-center gap-1 text-amber-600 mt-0.5">
                            <Trophy className="w-3 h-3" /> Best Overall
                          </div>
                        )}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[
                    { label: 'Fit Score',    key: 'fit_score',                       winnerKey: 'overall',    isScore: false },
                    { label: 'Recommendation', key: 'final_recommendation',          winnerKey: null,         isScore: false },
                    { label: 'Skill Match',  key: 'score_breakdown.skill_match',     winnerKey: 'skills',     isScore: true  },
                    { label: 'Experience',   key: 'score_breakdown.experience_match',winnerKey: 'experience', isScore: true  },
                    { label: 'Education',    key: 'score_breakdown.education',       winnerKey: 'education',  isScore: true  },
                    { label: 'Stability',    key: 'score_breakdown.stability',       winnerKey: 'stability',  isScore: true  },
                    { label: 'Risk Level',   key: 'risk_level',                      winnerKey: null,         isScore: false },
                  ].map(row => (
                    <tr key={row.label} className="border-b border-brand-50 hover:bg-brand-50/30 transition-colors">
                      <td className="px-4 py-3.5 text-xs font-bold text-brand-700 uppercase tracking-wide">{row.label}</td>
                      {comparison.candidates.map(c => {
                        const val = row.key.includes('.')
                          ? row.key.split('.').reduce((obj, k) => obj?.[k], c)
                          : c[row.key]
                        const isWinner = row.winnerKey ? c.winners?.[row.winnerKey] : false
                        return (
                          <td key={c.id} className="px-4 py-3.5 text-center">
                            {row.isScore ? (
                              <ScoreCell value={val ?? 0} isWinner={isWinner} color="brand" />
                            ) : row.key === 'fit_score' ? (
                              <span className={`font-extrabold text-xl ${isWinner ? 'text-amber-600' : 'text-brand-900'}`}>{val}</span>
                            ) : row.key === 'risk_level' ? (
                              <span className={`text-xs font-bold ${val === 'Low' ? 'text-green-700' : val === 'High' ? 'text-red-700' : 'text-amber-700'}`}>{val}</span>
                            ) : (
                              <span className={`text-xs font-bold ${val === 'Shortlist' ? 'text-green-700' : val === 'Reject' ? 'text-red-700' : 'text-amber-700'}`}>{val}</span>
                            )}
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                  <tr className="bg-brand-50/60">
                    <td className="px-4 py-3.5 text-xs font-bold text-brand-700 uppercase tracking-wide">Actions</td>
                    {comparison.candidates.map(c => (
                      <td key={c.id} className="px-4 py-3.5 text-center">
                        <button
                          onClick={() => navigate('/report', { state: { result: c } })}
                          className="text-xs text-brand-600 hover:text-brand-700 font-bold hover:underline"
                        >
                          View Report
                        </button>
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
