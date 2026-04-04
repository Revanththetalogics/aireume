import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Users, ChevronRight, X } from 'lucide-react'
import { getCandidates, getCandidate } from '../lib/api'

function ScoreBadge({ score }) {
  if (score == null) return <span className="text-slate-400 text-xs font-medium">—</span>
  let color = 'text-red-700 bg-red-50 ring-red-200'
  if (score >= 70) color = 'text-green-700 bg-green-50 ring-green-200'
  else if (score >= 45) color = 'text-amber-700 bg-amber-50 ring-amber-200'
  return <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ring-1 ${color}`}>{score}</span>
}

function CandidateDetail({ candidateId, onClose }) {
  const navigate = useNavigate()
  const [candidate, setCandidate] = useState(null)
  const [loading, setLoading]     = useState(true)

  useEffect(() => {
    getCandidate(candidateId).then(setCandidate).finally(() => setLoading(false))
  }, [candidateId])

  if (loading) return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center">
      <div className="w-8 h-8 border-4 border-brand-600 border-t-transparent rounded-full animate-spin" />
    </div>
  )
  if (!candidate) return null

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-end sm:items-center justify-center p-4">
      <div className="bg-white/95 backdrop-blur-xl rounded-3xl ring-1 ring-brand-100 shadow-brand-xl w-full max-w-2xl max-h-[90vh] flex flex-col card-animate">
        <div className="flex items-center justify-between p-5 border-b border-brand-50">
          <div>
            <h3 className="font-extrabold text-brand-900 text-lg tracking-tight">{candidate.name || 'Unknown'}</h3>
            <p className="text-sm text-slate-500">{candidate.email}</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-brand-50 rounded-xl transition-colors text-slate-400 hover:text-brand-600"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="overflow-y-auto p-5 space-y-3">
          <p className="text-sm font-semibold text-slate-500">{candidate.history?.length || 0} applications tracked</p>
          {candidate.history?.map((r) => (
            <div key={r.id} className="flex items-center justify-between p-4 bg-brand-50/60 rounded-2xl ring-1 ring-brand-100">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <ScoreBadge score={r.fit_score} />
                  <span className={`text-xs font-bold ${
                    r.final_recommendation === 'Shortlist' ? 'text-green-700' :
                    r.final_recommendation === 'Reject'    ? 'text-red-700'   : 'text-amber-700'
                  }`}>{r.final_recommendation}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ring-1 ${
                    r.status === 'hired'    ? 'bg-green-100 text-green-700 ring-green-200' :
                    r.status === 'rejected' ? 'bg-red-100   text-red-700   ring-red-200'   : 'bg-slate-100 text-slate-600 ring-slate-200'
                  }`}>{r.status}</span>
                </div>
                <p className="text-xs text-slate-400 font-medium">{new Date(r.timestamp).toLocaleDateString()}</p>
              </div>
              <button
                onClick={() => { onClose(); navigate('/report', { state: { result: r } }) }}
                className="text-xs text-brand-600 hover:text-brand-700 font-bold flex items-center gap-1 hover:underline"
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
    <div>
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <div className="flex items-center justify-between flex-wrap gap-3 card-animate">
          <div>
            <h2 className="text-3xl font-extrabold text-brand-900 tracking-tight">Candidates</h2>
            <p className="text-slate-500 text-sm mt-1 font-medium">{total} candidates tracked in your workspace</p>
          </div>
          <form onSubmit={handleSearch} className="flex gap-2">
            <div className="relative">
              <Search className="w-4 h-4 text-brand-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by name or email..."
                className="pl-9 pr-4 py-2.5 text-sm ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 rounded-xl bg-white w-64 placeholder-slate-400"
              />
            </div>
            <button type="submit" className="px-4 py-2.5 btn-brand text-white text-sm font-bold rounded-xl shadow-brand-sm">
              Search
            </button>
          </form>
        </div>

        {loading ? (
          <div className="flex justify-center py-16">
            <div className="w-8 h-8 border-4 border-brand-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : candidates.length === 0 ? (
          <div className="text-center py-16 bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand card-animate">
            <div className="w-16 h-16 rounded-2xl bg-brand-50 ring-1 ring-brand-200 flex items-center justify-center mx-auto mb-4">
              <Users className="w-8 h-8 text-brand-300" />
            </div>
            <p className="text-slate-500 font-medium">No candidates yet. Analyze some resumes to get started.</p>
          </div>
        ) : (
          <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand overflow-hidden card-animate">
            <table className="w-full text-sm">
              <thead className="bg-brand-50 border-b border-brand-100">
                <tr>
                  <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Name</th>
                  <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Email</th>
                  <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Applications</th>
                  <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Best Score</th>
                  <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Added</th>
                  <th className="px-4 py-3.5"></th>
                </tr>
              </thead>
              <tbody>
                {candidates.map(c => (
                  <tr key={c.id} className="border-b border-brand-50 hover:bg-brand-50/40 transition-colors">
                    <td className="px-4 py-3.5 font-bold text-brand-900">{c.name || '—'}</td>
                    <td className="px-4 py-3.5 text-slate-500 font-medium">{c.email || '—'}</td>
                    <td className="px-4 py-3.5">
                      <span className="text-brand-700 font-bold">{c.result_count}</span>
                    </td>
                    <td className="px-4 py-3.5"><ScoreBadge score={c.best_score} /></td>
                    <td className="px-4 py-3.5 text-slate-400 text-xs font-medium">{new Date(c.created_at).toLocaleDateString()}</td>
                    <td className="px-4 py-3.5">
                      <button
                        onClick={() => setSelectedId(c.id)}
                        className="text-xs text-brand-600 hover:text-brand-700 font-bold flex items-center gap-1 hover:underline"
                      >
                        View <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {total > 20 && (
              <div className="flex items-center justify-between p-4 border-t border-brand-50">
                <p className="text-xs text-slate-500 font-medium">Page {page} of {Math.ceil(total / 20)}</p>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="px-3 py-1.5 text-xs ring-1 ring-brand-200 rounded-xl disabled:opacity-40 hover:bg-brand-50 font-semibold text-brand-700 transition-colors"
                  >
                    Prev
                  </button>
                  <button
                    onClick={() => setPage(p => p + 1)}
                    disabled={page >= Math.ceil(total / 20)}
                    className="px-3 py-1.5 text-xs ring-1 ring-brand-200 rounded-xl disabled:opacity-40 hover:bg-brand-50 font-semibold text-brand-700 transition-colors"
                  >
                    Next
                  </button>
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
