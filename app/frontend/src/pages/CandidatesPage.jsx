import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Users, ChevronRight, Clock, Star } from 'lucide-react'
import NavBar from '../components/NavBar'
import { getCandidates, getCandidate } from '../lib/api'

function ScoreBadge({ score }) {
  if (score == null) return <span className="text-slate-400 text-xs">—</span>
  let color = 'text-red-600 bg-red-50'
  if (score >= 70) color = 'text-green-600 bg-green-50'
  else if (score >= 45) color = 'text-amber-600 bg-amber-50'
  return <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${color}`}>{score}</span>
}

function CandidateDetail({ candidateId, onClose }) {
  const navigate = useNavigate()
  const [candidate, setCandidate] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getCandidate(candidateId).then(setCandidate).finally(() => setLoading(false))
  }, [candidateId])

  if (loading) return (
    <div className="flex items-center justify-center h-48">
      <div className="w-6 h-6 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
    </div>
  )
  if (!candidate) return null

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end sm:items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between p-5 border-b border-slate-100">
          <div>
            <h3 className="font-bold text-slate-900 text-lg">{candidate.name || 'Unknown'}</h3>
            <p className="text-sm text-slate-500">{candidate.email}</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-xl font-bold p-1">×</button>
        </div>
        <div className="overflow-y-auto p-5 space-y-4">
          <p className="text-sm font-medium text-slate-600">{candidate.history?.length || 0} applications tracked</p>
          {candidate.history?.map((r) => (
            <div key={r.id} className="flex items-center justify-between p-4 bg-slate-50 rounded-xl border border-slate-200">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <ScoreBadge score={r.fit_score} />
                  <span className={`text-xs font-semibold ${
                    r.final_recommendation === 'Shortlist' ? 'text-green-600' :
                    r.final_recommendation === 'Reject' ? 'text-red-600' : 'text-amber-600'
                  }`}>{r.final_recommendation}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    r.status === 'hired' ? 'bg-green-100 text-green-700' :
                    r.status === 'rejected' ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-600'
                  }`}>{r.status}</span>
                </div>
                <p className="text-xs text-slate-400">{new Date(r.timestamp).toLocaleDateString()}</p>
              </div>
              <button
                onClick={() => { onClose(); navigate('/report', { state: { result: r } }) }}
                className="text-xs text-blue-600 hover:underline font-medium flex items-center gap-1"
              >
                View <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default function CandidatesPage() {
  const [candidates, setCandidates] = useState([])
  const [total, setTotal]           = useState(0)
  const [search, setSearch]         = useState('')
  const [page, setPage]             = useState(1)
  const [loading, setLoading]       = useState(true)
  const [selectedId, setSelectedId] = useState(null)

  const fetchCandidates = async (s = search, p = page) => {
    setLoading(true)
    try {
      const data = await getCandidates({ search: s, page: p, page_size: 20 })
      setCandidates(data.candidates)
      setTotal(data.total)
    } catch {
      setCandidates([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchCandidates() }, [page])

  const handleSearch = (e) => {
    e.preventDefault()
    setPage(1)
    fetchCandidates(search, 1)
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <NavBar />
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h2 className="text-2xl font-bold text-slate-900">Candidates</h2>
            <p className="text-slate-500 text-sm mt-1">{total} candidates tracked in your workspace</p>
          </div>
          <form onSubmit={handleSearch} className="flex gap-2">
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by name or email..."
                className="pl-9 pr-4 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 w-64"
              />
            </div>
            <button type="submit" className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors">
              Search
            </button>
          </form>
        </div>

        {loading ? (
          <div className="flex justify-center py-12">
            <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : candidates.length === 0 ? (
          <div className="text-center py-16 bg-white rounded-xl border border-slate-200">
            <Users className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <p className="text-slate-500">No candidates yet. Analyze some resumes to get started.</p>
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Name</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Email</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Applications</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Best Score</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Added</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {candidates.map(c => (
                  <tr key={c.id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-slate-800">{c.name || '—'}</td>
                    <td className="px-4 py-3 text-slate-500">{c.email || '—'}</td>
                    <td className="px-4 py-3">
                      <span className="text-slate-700 font-medium">{c.result_count}</span>
                    </td>
                    <td className="px-4 py-3"><ScoreBadge score={c.best_score} /></td>
                    <td className="px-4 py-3 text-slate-400 text-xs">{new Date(c.created_at).toLocaleDateString()}</td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => setSelectedId(c.id)}
                        className="text-xs text-blue-600 hover:underline font-medium flex items-center gap-1"
                      >
                        View <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {/* Pagination */}
            {total > 20 && (
              <div className="flex items-center justify-between p-4 border-t border-slate-100">
                <p className="text-xs text-slate-500">Page {page} of {Math.ceil(total / 20)}</p>
                <div className="flex gap-2">
                  <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="px-3 py-1 text-xs border border-slate-200 rounded-lg disabled:opacity-40 hover:bg-slate-50">Prev</button>
                  <button onClick={() => setPage(p => p + 1)} disabled={page >= Math.ceil(total / 20)} className="px-3 py-1 text-xs border border-slate-200 rounded-lg disabled:opacity-40 hover:bg-slate-50">Next</button>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
      {selectedId && <CandidateDetail candidateId={selectedId} onClose={() => setSelectedId(null)} />}
    </div>
  )
}
