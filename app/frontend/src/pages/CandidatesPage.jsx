import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Search, Users, ChevronRight, X, FileText, Eye, Filter, ChevronDown, CheckCircle2, XCircle } from 'lucide-react'
import { getCandidates, getCandidate, viewCandidateResume, downloadCandidateResume, updateResultStatus } from '../lib/api'

/** Coerce any value to a render-safe string. Objects become JSON; null/undefined → '' */
function safeStr(v) {
  if (v == null) return ''
  if (typeof v === 'string') return v
  if (typeof v === 'number' || typeof v === 'boolean') return String(v)
  try { return JSON.stringify(v) } catch { return String(v) }
}

const STATUS_OPTIONS = ['pending', 'shortlisted', 'rejected', 'in-review', 'hired']

const STATUS_CONFIG = {
  pending:     { label: 'Pending',     color: 'bg-slate-100 text-slate-700 ring-slate-200' },
  shortlisted: { label: 'Shortlisted', color: 'bg-green-100 text-green-700 ring-green-200' },
  rejected:    { label: 'Rejected',    color: 'bg-red-100 text-red-700 ring-red-200' },
  'in-review': { label: 'In Review',   color: 'bg-amber-100 text-amber-700 ring-amber-200' },
  hired:       { label: 'Hired',       color: 'bg-emerald-100 text-emerald-700 ring-emerald-200' },
}

function ScoreBadge({ score }) {
  if (score == null) return <span className="text-slate-400 text-xs font-medium">—</span>
  let color = 'text-red-700 bg-red-50 ring-red-200'
  if (score >= 70) color = 'text-green-700 bg-green-50 ring-green-200'
  else if (score >= 45) color = 'text-amber-700 bg-amber-50 ring-amber-200'
  return <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ring-1 ${color}`}>{score}</span>
}

function StatusPill({ status, onChange }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.pending
  const [open, setOpen] = useState(false)

  return (
    <div className="relative">
      <button
        onClick={(e) => { e.stopPropagation(); setOpen(v => !v) }}
        className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold ring-1 cursor-pointer hover:opacity-80 transition-opacity ${cfg.color}`}
      >
        {cfg.label}
        <ChevronDown className="w-3 h-3" />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={(e) => { e.stopPropagation(); setOpen(false) }} />
          <div className="absolute left-0 top-full mt-1 w-36 bg-white border border-brand-100/80 shadow-lg rounded-xl py-1 z-50">
            {STATUS_OPTIONS.map(s => {
              const sc = STATUS_CONFIG[s]
              return (
                <button
                  key={s}
                  onClick={(e) => { e.stopPropagation(); setOpen(false); onChange(s) }}
                  className={`w-full flex items-center gap-2 px-3 py-2 text-xs font-medium hover:bg-brand-50 transition-colors ${
                    s === status ? 'text-brand-700 bg-brand-50/60' : 'text-slate-600'
                  }`}
                >
                  <span className={`w-2 h-2 rounded-full ring-1 ${sc.color}`} />
                  {sc.label}
                </button>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}

function Toast({ message, onDone }) {
  useEffect(() => {
    const t = setTimeout(onDone, 2500)
    return () => clearTimeout(t)
  }, [onDone])

  return (
    <div className="fixed bottom-6 right-6 z-50 bg-brand-900 text-white px-5 py-3 rounded-2xl shadow-brand-lg text-sm font-semibold card-animate">
      {message}
    </div>
  )
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
            <h3 className="font-extrabold text-brand-900 text-lg tracking-tight">{safeStr(candidate.name) || 'Unknown'}</h3>
            <p className="text-sm text-slate-500">{safeStr(candidate.email)}</p>
          </div>
          <div className="flex items-center gap-2">
            {candidate.id && (
              <>
                <button
                  onClick={() => viewCandidateResume(candidate.id).catch(() => alert('Resume not available'))}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-brand-700 ring-1 ring-brand-200 hover:bg-brand-50 transition-colors"
                  title="View original resume"
                >
                  <Eye className="w-3.5 h-3.5" />
                  View
                </button>
                <button
                  onClick={() => downloadCandidateResume(candidate.id, candidate.name ? `${candidate.name}_resume.pdf` : `resume_${candidate.id}.pdf`).catch(() => alert('Resume not available'))}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-brand-700 ring-1 ring-brand-200 hover:bg-brand-50 transition-colors"
                  title="Download original resume"
                >
                  <FileText className="w-3.5 h-3.5" />
                  Download
                </button>
              </>
            )}
            <button
              onClick={onClose}
              className="p-1.5 hover:bg-brand-50 rounded-xl transition-colors text-slate-400 hover:text-brand-600"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
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
                  }`}>{safeStr(r.final_recommendation)}</span>
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
  const [searchParams, setSearchParams] = useSearchParams()
  const initialStatus = searchParams.get('status') || ''

  const [candidates, setCandidates] = useState([])
  const [total, setTotal]           = useState(0)
  const [search, setSearch]         = useState('')
  const [page, setPage]             = useState(1)
  const [loading, setLoading]       = useState(true)
  const [selectedId, setSelectedId] = useState(null)
  const [statusFilter, setStatusFilter] = useState(initialStatus)
  const [toast, setToast]           = useState(null)
  const [selectedIds, setSelectedIds] = useState(new Set())
  const [bulkLoading, setBulkLoading] = useState(false)

  const fetchCandidates = async (s = search, p = page, st = statusFilter) => {
    setLoading(true)
    try {
      const params = { search: s, page: p, page_size: 20 }
      if (st) params.status = st
      const data = await getCandidates(params)
      setCandidates(data.candidates)
      setTotal(data.total)
    } catch {
      setCandidates([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchCandidates() }, [page])

  // Sync URL params when statusFilter changes (skip initial mount)
  useEffect(() => {
    if (statusFilter) {
      setSearchParams({ status: statusFilter }, { replace: true })
    } else {
      setSearchParams({}, { replace: true })
    }
    setPage(1)
    fetchCandidates(search, 1, statusFilter)
  }, [statusFilter])

  const handleSearch = (e) => {
    e.preventDefault()
    setPage(1)
    fetchCandidates(search, 1)
  }

  const handleStatusChange = async (resultId, newStatus) => {
    try {
      await updateResultStatus(resultId, newStatus)
      setCandidates(prev =>
        prev.map(c => c.latest_result_id === resultId ? { ...c, latest_status: newStatus } : c)
      )
      setToast(`Status updated to ${STATUS_CONFIG[newStatus]?.label || newStatus}`)
    } catch {
      setToast('Failed to update status')
    }
  }

  // ── Selection helpers ──
  const selectableIds = candidates.filter(c => c.latest_result_id).map(c => c.latest_result_id)

  const toggleSelect = (resultId) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(resultId)) next.delete(resultId)
      else next.add(resultId)
      return next
    })
  }

  const toggleAll = () => {
    if (selectedIds.size === selectableIds.length && selectableIds.length > 0) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(selectableIds))
    }
  }

  const clearSelection = () => setSelectedIds(new Set())

  // ── Bulk actions ──
  const handleBulkAction = async (status) => {
    if (selectedIds.size === 0) return
    setBulkLoading(true)
    try {
      await Promise.all([...selectedIds].map(id => updateResultStatus(id, status)))
      setCandidates(prev =>
        prev.map(c =>
          selectedIds.has(c.latest_result_id) ? { ...c, latest_status: status } : c
        )
      )
      setToast(`${selectedIds.size} candidate${selectedIds.size !== 1 ? 's' : ''} updated to ${STATUS_CONFIG[status]?.label || status}`)
      setSelectedIds(new Set())
    } catch {
      setToast('Failed to update some statuses')
    } finally {
      setBulkLoading(false)
    }
  }

  return (
    <div>
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <div className="flex items-center justify-between flex-wrap gap-3 card-animate">
          <div>
            <h2 className="text-3xl font-extrabold text-brand-900 tracking-tight">Candidates</h2>
            <p className="text-slate-500 text-sm mt-1 font-medium">
              {statusFilter
                ? `Showing ${total} candidate${total !== 1 ? 's' : ''} with status: ${STATUS_CONFIG[statusFilter]?.label || statusFilter}`
                : `${total} candidates tracked in your workspace`}
            </p>
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

        {/* Status Filter Bar */}
        <div className="flex items-center gap-3 bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 shadow-brand-sm px-4 py-3 card-animate">
          <Filter className="w-4 h-4 text-slate-500" />
          <span className="text-sm font-semibold text-slate-700">Status:</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 text-xs rounded-lg font-medium bg-slate-100 text-slate-600 border-0 focus:ring-2 focus:ring-brand-500"
          >
            <option value="">All</option>
            {STATUS_OPTIONS.map(s => (
              <option key={s} value={s}>{STATUS_CONFIG[s].label}</option>
            ))}
          </select>
          {statusFilter && (
            <button
              onClick={() => setStatusFilter('')}
              className="text-xs text-brand-600 hover:text-brand-700 font-bold hover:underline"
            >
              Clear filter
            </button>
          )}
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
            <p className="text-slate-500 font-medium">
              {statusFilter
                ? `No candidates with status "${STATUS_CONFIG[statusFilter]?.label || statusFilter}".`
                : 'No candidates yet. Analyze some resumes to get started.'}
            </p>
          </div>
        ) : (
          <>
            {/* Bulk Action Bar */}
            {selectedIds.size > 0 && (
              <div className="sticky top-20 z-20 flex items-center gap-3 bg-brand-900 text-white px-5 py-3 rounded-2xl shadow-brand-lg card-animate">
                <span className="text-sm font-bold">
                  {selectedIds.size} selected
                </span>
                <div className="flex-1" />
                <button
                  onClick={() => handleBulkAction('shortlisted')}
                  disabled={bulkLoading}
                  className="flex items-center gap-1.5 px-3.5 py-1.5 bg-green-600 hover:bg-green-700 text-white text-xs font-bold rounded-xl transition-colors disabled:opacity-60"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Shortlist Selected
                </button>
                <button
                  onClick={() => handleBulkAction('rejected')}
                  disabled={bulkLoading}
                  className="flex items-center gap-1.5 px-3.5 py-1.5 bg-red-600 hover:bg-red-700 text-white text-xs font-bold rounded-xl transition-colors disabled:opacity-60"
                >
                  <XCircle className="w-3.5 h-3.5" />
                  Reject Selected
                </button>
                <button
                  onClick={clearSelection}
                  className="flex items-center gap-1.5 px-3.5 py-1.5 bg-white/10 hover:bg-white/20 text-white text-xs font-bold rounded-xl transition-colors"
                >
                  Clear Selection
                </button>
              </div>
            )}
            <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand overflow-hidden card-animate">
            <table className="w-full text-sm">
              <thead className="bg-brand-50 border-b border-brand-100">
                <tr>
                  <th className="px-4 py-3.5 text-left w-10">
                    <input
                      type="checkbox"
                      checked={selectedIds.size === selectableIds.length && selectableIds.length > 0}
                      onChange={toggleAll}
                      className="w-4 h-4 rounded border-brand-300 text-brand-600 focus:ring-brand-500 cursor-pointer"
                    />
                  </th>
                  <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Name</th>
                  <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Email</th>
                  <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Status</th>
                  <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Applications</th>
                  <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Best Score</th>
                  <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Added</th>
                  <th className="px-4 py-3.5"></th>
                </tr>
              </thead>
              <tbody>
                {candidates.map(c => (
                  <tr key={c.id} className={`border-b border-brand-50 hover:bg-brand-50/40 transition-colors ${
                    selectedIds.has(c.latest_result_id) ? 'bg-brand-50/60' : ''
                  }`}>
                    <td className="px-4 py-3.5">
                      {c.latest_result_id ? (
                        <input
                          type="checkbox"
                          checked={selectedIds.has(c.latest_result_id)}
                          onChange={() => toggleSelect(c.latest_result_id)}
                          className="w-4 h-4 rounded border-brand-300 text-brand-600 focus:ring-brand-500 cursor-pointer"
                        />
                      ) : (
                        <span className="inline-block w-4 h-4" />
                      )}
                    </td>
                    <td className="px-4 py-3.5 font-bold text-brand-900">{c.name || '—'}</td>
                    <td className="px-4 py-3.5 text-slate-500 font-medium">{c.email || '—'}</td>
                    <td className="px-4 py-3.5">
                      {c.latest_result_id ? (
                        <StatusPill
                          status={c.latest_status || 'pending'}
                          onChange={(newStatus) => handleStatusChange(c.latest_result_id, newStatus)}
                        />
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </td>
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
          </>
        )}
      </main>
      {selectedId && <CandidateDetail candidateId={selectedId} onClose={() => setSelectedId(null)} />}
      {toast && <Toast message={toast} onDone={() => setToast(null)} />}
    </div>
  )
}
