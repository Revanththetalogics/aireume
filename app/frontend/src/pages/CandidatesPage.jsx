import { useState, useEffect, useMemo } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Search, Users, ChevronRight, X, FileText, Eye, Filter, ChevronDown, CheckCircle2, XCircle, ArrowUp, ArrowDown } from 'lucide-react'
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

const AVATAR_COLORS = [
  'bg-blue-500', 'bg-purple-500', 'bg-pink-500', 'bg-indigo-500',
  'bg-teal-500', 'bg-orange-500', 'bg-cyan-500', 'bg-rose-500',
  'bg-violet-500', 'bg-emerald-500',
]

function getInitials(name) {
  if (!name) return '??'
  const parts = name.trim().split(/\s+/)
  if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
  return parts[0].slice(0, 2).toUpperCase()
}

function getAvatarColor(name) {
  let hash = 0
  for (let i = 0; i < (name || '').length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash)
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length]
}

function ScoreBadge({ score }) {
  if (score == null) return <span className="text-slate-400 text-xs font-medium">—</span>
  let color = 'bg-red-100 text-red-700'
  if (score >= 70) color = 'bg-green-100 text-green-700'
  else if (score >= 50) color = 'bg-amber-100 text-amber-700'
  return <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${color}`}>{score}</span>
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
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const initialStatus = searchParams.get('status') || ''

  const [candidates, setCandidates] = useState([])
  const [total, setTotal]           = useState(0)
  const [search, setSearch]         = useState('')
  const [page, setPage]             = useState(1)
  const [loading, setLoading]       = useState(true)
  const [selectedId, setSelectedId] = useState(null)
  const [statusFilter, setStatusFilter] = useState(initialStatus)
  const [skillFilter, setSkillFilter] = useState('')
  const [toast, setToast]           = useState(null)
  const [selectedIds, setSelectedIds] = useState(new Set())
  const [bulkLoading, setBulkLoading] = useState(false)
  const [sortBy, setSortBy] = useState('created_at')
  const [sortOrder, setSortOrder] = useState('desc')
  const [scoreFilter, setScoreFilter] = useState('all')

  const fetchCandidates = async (s = search, p = page, st = statusFilter, sk = skillFilter) => {
    setLoading(true)
    try {
      const params = { search: s, page: p, page_size: 20 }
      if (st) params.status = st
      if (sk) params.skill = sk
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
    fetchCandidates(search, 1, statusFilter, skillFilter)
  }, [statusFilter])

  // Re-fetch when skill filter changes
  useEffect(() => {
    setPage(1)
    fetchCandidates(search, 1, statusFilter, skillFilter)
  }, [skillFilter])

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
  const selectableIds = displayedCandidates.filter(c => c.latest_result_id).map(c => c.latest_result_id)

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

  // ── Sort handler ──
  const handleSort = (column) => {
    if (sortBy === column) {
      setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(column)
      setSortOrder('desc')
    }
  }

  // ── Filtered + sorted candidates ──
  const displayedCandidates = useMemo(() => {
    let list = [...candidates]

    // Score filter
    if (scoreFilter !== 'all') {
      list = list.filter(c => {
        const s = c.best_score
        if (s == null) return scoreFilter === 'below50'
        if (scoreFilter === '70plus') return s >= 70
        if (scoreFilter === '50to69') return s >= 50 && s <= 69
        if (scoreFilter === 'below50') return s < 50
        return true
      })
    }

    // Sort
    list.sort((a, b) => {
      let valA, valB
      switch (sortBy) {
        case 'name':
          valA = (a.name || '').toLowerCase()
          valB = (b.name || '').toLowerCase()
          break
        case 'best_score':
          valA = a.best_score ?? -1
          valB = b.best_score ?? -1
          break
        case 'result_count':
          valA = a.result_count ?? 0
          valB = b.result_count ?? 0
          break
        case 'created_at':
          valA = a.created_at ? new Date(a.created_at).getTime() : 0
          valB = b.created_at ? new Date(b.created_at).getTime() : 0
          break
        default:
          return 0
      }
      if (valA < valB) return sortOrder === 'asc' ? -1 : 1
      if (valA > valB) return sortOrder === 'asc' ? 1 : -1
      return 0
    })

    return list
  }, [candidates, sortBy, sortOrder, scoreFilter])

  // Sort indicator icon for a column header
  const SortIcon = ({ column }) => {
    if (sortBy !== column) return null
    return sortOrder === 'asc'
      ? <ArrowUp className="w-3 h-3 inline ml-0.5" />
      : <ArrowDown className="w-3 h-3 inline ml-0.5" />
  }

  return (
    <div>
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <div className="flex items-center justify-between flex-wrap gap-3 card-animate">
          <div>
            <h2 className="text-3xl font-extrabold text-brand-900 tracking-tight">Candidates</h2>
            <p className="text-slate-500 text-sm mt-1 font-medium">
              {statusFilter || skillFilter || scoreFilter !== 'all'
                ? `Showing ${total} candidate${total !== 1 ? 's' : ''}${statusFilter ? ` with status: ${STATUS_CONFIG[statusFilter]?.label || statusFilter}` : ''}${skillFilter ? ` matching skill: "${skillFilter}"` : ''}${scoreFilter !== 'all' ? ` — ${scoreFilter === '70plus' ? '70+ (Strong)' : scoreFilter === '50to69' ? '50-69 (Moderate)' : 'Below 50 (Weak)'}` : ''}`
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

        {/* Status & Skill Filter Bar */}
        <div className="flex items-center gap-3 bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 shadow-brand-sm px-4 py-3 card-animate flex-wrap">
          <Filter className="w-4 h-4 text-slate-500" />
          <div className="flex items-center gap-1.5">
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
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-sm font-semibold text-slate-700">Skill:</span>
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-brand-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                value={skillFilter}
                onChange={(e) => setSkillFilter(e.target.value)}
                placeholder="Filter by skill..."
                className="pl-8 pr-3 py-1.5 text-xs ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 rounded-lg bg-white w-40 placeholder-slate-400"
              />
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-sm font-semibold text-slate-700">Score:</span>
            <select
              value={scoreFilter}
              onChange={(e) => setScoreFilter(e.target.value)}
              className="px-3 py-1.5 text-xs rounded-lg font-medium bg-slate-100 text-slate-600 border-0 focus:ring-2 focus:ring-brand-500"
            >
              <option value="all">All Scores</option>
              <option value="70plus">70+ (Strong)</option>
              <option value="50to69">50-69 (Moderate)</option>
              <option value="below50">Below 50 (Weak)</option>
            </select>
          </div>
          {(statusFilter || skillFilter || scoreFilter !== 'all') && (
            <button
              onClick={() => { setStatusFilter(''); setSkillFilter(''); setScoreFilter('all') }}
              className="text-xs text-brand-600 hover:text-brand-700 font-bold hover:underline"
            >
              Clear filters
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
              {statusFilter || skillFilter || scoreFilter !== 'all'
                ? `No candidates matching current filters.`
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
            <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[900px]">
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
                  <th
                    onClick={() => handleSort('name')}
                    className={`px-4 py-3.5 text-left text-xs uppercase tracking-wide min-w-[180px] cursor-pointer hover:text-indigo-600 select-none ${sortBy === 'name' ? 'font-extrabold text-indigo-600' : 'font-bold text-brand-700'}`}
                  >
                    Name <SortIcon column="name" />
                  </th>
                  <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Email</th>
                  <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Status</th>
                  <th
                    onClick={() => handleSort('result_count')}
                    className={`px-4 py-3.5 text-left text-xs uppercase tracking-wide cursor-pointer hover:text-indigo-600 select-none ${sortBy === 'result_count' ? 'font-extrabold text-indigo-600' : 'font-bold text-brand-700'}`}
                  >
                    Applications <SortIcon column="result_count" />
                  </th>
                  <th
                    onClick={() => handleSort('best_score')}
                    className={`px-4 py-3.5 text-left text-xs uppercase tracking-wide cursor-pointer hover:text-indigo-600 select-none ${sortBy === 'best_score' ? 'font-extrabold text-indigo-600' : 'font-bold text-brand-700'}`}
                  >
                    Best Score <SortIcon column="best_score" />
                  </th>
                  <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide min-w-[140px]">Top Skills</th>
                  <th
                    onClick={() => handleSort('created_at')}
                    className={`px-4 py-3.5 text-left text-xs uppercase tracking-wide min-w-[80px] cursor-pointer hover:text-indigo-600 select-none ${sortBy === 'created_at' ? 'font-extrabold text-indigo-600' : 'font-bold text-brand-700'}`}
                  >
                    Added <SortIcon column="created_at" />
                  </th>
                  <th className="px-4 py-3.5"></th>
                </tr>
              </thead>
              <tbody>
                {displayedCandidates.map(c => (
                  <tr
                    key={c.id}
                    onClick={() => navigate(`/candidates/${c.id}`)}
                    className={`border-b border-brand-50 cursor-pointer hover:bg-gray-50 transition-colors ${
                      selectedIds.has(c.latest_result_id) ? 'bg-brand-50/60' : ''
                    }`}
                  >
                    <td className="px-4 py-3.5" onClick={e => e.stopPropagation()}>
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
                    <td className="px-4 py-3.5">
                      <div className="flex items-center gap-2.5">
                        <span className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0 ${getAvatarColor(c.name)}`}>
                          {getInitials(c.name)}
                        </span>
                        <span className="font-bold text-brand-900 hover:text-brand-700 transition-colors">
                          {c.name || '—'}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3.5 text-slate-500 font-medium">{c.email || '—'}</td>
                    <td className="px-4 py-3.5" onClick={e => e.stopPropagation()}>
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
                    <td className="px-4 py-3.5">
                      {c.matched_skills && c.matched_skills.length > 0 ? (
                        <div className="flex flex-wrap gap-1 max-h-[3rem] overflow-hidden">
                          {c.matched_skills.slice(0, 3).map((skill, i) => (
                            <span key={i} className="px-1.5 py-0.5 bg-green-50 text-green-700 text-xs rounded font-semibold ring-1 ring-green-100 whitespace-nowrap">
                              {skill}
                            </span>
                          ))}
                          {c.matched_skills.length > 3 && (
                            <span className="px-1.5 py-0.5 bg-slate-50 text-slate-400 text-xs rounded font-medium ring-1 ring-slate-100 whitespace-nowrap">
                              +{c.matched_skills.length - 3}
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3.5 text-slate-400 text-xs font-medium whitespace-nowrap">
                      {c.created_at
                        ? new Date(c.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                        : '—'}
                    </td>
                    <td className="px-4 py-3.5">
                      <span className="text-xs text-brand-600 hover:text-brand-700 font-bold flex items-center gap-1 hover:underline">
                        View <ChevronRight className="w-3.5 h-3.5" />
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
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
