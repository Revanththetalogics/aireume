import { useState, useEffect, useMemo, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Search, Users, ChevronRight, X, FileText, Eye, Filter, ChevronDown, CheckCircle2, XCircle, ArrowUp, ArrowDown, List, LayoutGrid, Columns, Mail, Loader2 } from 'lucide-react'
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

/** Inline profile preview for Split Panel view — lighter than full CandidateProfilePage */
function SplitProfilePreview({ profile, onStatusChange, navigate }) {
  const firstResult = profile.history && profile.history.length > 0 ? profile.history[0] : null
  const matchedSkills = firstResult?.matched_skills || []
  const missingSkills = firstResult?.missing_skills || []
  const strengths = firstResult?.strengths || []
  const weaknesses = firstResult?.weaknesses || []
  const narrative = firstResult?.narrative_summary || firstResult?.narrative || ''
  const professionalSummary = profile.professional_summary || profile.summary || firstResult?.professional_summary || ''
  const scoreBreakdown = firstResult?.score_breakdown || firstResult?.category_scores || null
  const fitScore = firstResult?.fit_score ?? profile.best_score ?? null

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <span className={`w-12 h-12 rounded-full flex items-center justify-center text-white text-lg font-bold shrink-0 ${getAvatarColor(profile.name)}`}>
            {getInitials(profile.name)}
          </span>
          <div className="min-w-0">
            <h3 className="text-xl font-extrabold text-gray-900 truncate">{safeStr(profile.name) || 'Unknown'}</h3>
            {profile.email && <p className="text-sm text-gray-500 truncate">{safeStr(profile.email)}</p>}
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <ScoreBadge score={fitScore} />
          {firstResult?.id && (
            <StatusPill
              status={firstResult.status || profile.latest_status || 'pending'}
              onChange={(newStatus) => onStatusChange(firstResult.id, newStatus)}
            />
          )}
        </div>
      </div>

      {/* View Full Profile link */}
      <button
        onClick={() => navigate(`/candidates/${profile.id}`)}
        className="text-sm text-indigo-600 hover:text-indigo-800 font-bold flex items-center gap-1 hover:underline"
      >
        View Full Profile <ChevronRight className="w-4 h-4" />
      </button>

      {/* Professional Summary */}
      {professionalSummary && (
        <div>
          <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-1">Professional Summary</h4>
          <p className="text-sm text-gray-700 leading-relaxed">{safeStr(professionalSummary)}</p>
        </div>
      )}

      {/* Score Breakdown Bar */}
      {scoreBreakdown && typeof scoreBreakdown === 'object' && (
        <div>
          <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-2">Score Breakdown</h4>
          <div className="space-y-2">
            {Object.entries(scoreBreakdown).map(([key, val]) => {
              const numVal = typeof val === 'number' ? val : (typeof val?.score === 'number' ? val.score : 0)
              return (
                <div key={key} className="flex items-center gap-2">
                  <span className="text-xs text-gray-600 w-28 truncate" title={key}>{key}</span>
                  <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${numVal >= 70 ? 'bg-green-500' : numVal >= 50 ? 'bg-amber-500' : 'bg-red-500'}`}
                      style={{ width: `${Math.min(100, Math.max(0, numVal))}%` }}
                    />
                  </div>
                  <span className="text-xs font-bold text-gray-700 w-8 text-right">{numVal}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Matched / Missing Skills */}
      {(matchedSkills.length > 0 || missingSkills.length > 0) && (
        <div>
          <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-2">Skills</h4>
          <div className="flex flex-wrap gap-1.5">
            {matchedSkills.map((skill, i) => (
              <span key={`m${i}`} className="text-xs bg-green-100 text-green-700 rounded-full px-2 py-0.5 font-medium">{safeStr(skill)}</span>
            ))}
            {missingSkills.map((skill, i) => (
              <span key={`x${i}`} className="text-xs bg-red-100 text-red-700 rounded-full px-2 py-0.5 font-medium">{safeStr(skill)}</span>
            ))}
          </div>
        </div>
      )}

      {/* Strengths / Weaknesses */}
      {(strengths.length > 0 || weaknesses.length > 0) && (
        <div className="grid grid-cols-2 gap-4">
          {strengths.length > 0 && (
            <div>
              <h4 className="text-xs font-bold text-green-600 uppercase tracking-wide mb-1">Strengths</h4>
              <ul className="space-y-1">
                {strengths.slice(0, 5).map((s, i) => (
                  <li key={i} className="text-xs text-gray-700 flex items-start gap-1.5">
                    <CheckCircle2 className="w-3 h-3 text-green-500 mt-0.5 shrink-0" />
                    <span>{safeStr(s)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {weaknesses.length > 0 && (
            <div>
              <h4 className="text-xs font-bold text-red-600 uppercase tracking-wide mb-1">Weaknesses</h4>
              <ul className="space-y-1">
                {weaknesses.slice(0, 5).map((w, i) => (
                  <li key={i} className="text-xs text-gray-700 flex items-start gap-1.5">
                    <XCircle className="w-3 h-3 text-red-500 mt-0.5 shrink-0" />
                    <span>{safeStr(w)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Narrative Summary */}
      {narrative && (
        <div>
          <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-1">Narrative Summary</h4>
          <blockquote className="text-sm text-gray-700 leading-relaxed border-l-3 border-indigo-300 pl-4 italic bg-indigo-50/50 py-2 rounded-r-lg">
            {safeStr(narrative)}
          </blockquote>
        </div>
      )}
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
  const [viewMode, setViewMode] = useState(() => {
    try { return localStorage.getItem('candidates-view-mode') || 'table' } catch { return 'table' }
  })
  const [splitSelectedId, setSplitSelectedId] = useState(null)
  const [splitProfile, setSplitProfile] = useState(null)
  const [splitLoading, setSplitLoading] = useState(false)

  const handleViewModeChange = useCallback((mode) => {
    setViewMode(mode)
    try { localStorage.setItem('candidates-view-mode', mode) } catch { /* ignore */ }
    if (mode !== 'split') { setSplitSelectedId(null); setSplitProfile(null) }
  }, [])

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
          {/* View Mode Toggle */}
          <div className="flex items-center gap-1 ml-auto">
            <button
              onClick={() => handleViewModeChange('table')}
              className={`p-1.5 rounded-lg transition-colors ${viewMode === 'table' ? 'bg-indigo-600 text-white' : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'}`}
              title="Table view"
            >
              <List className="w-4 h-4" />
            </button>
            <button
              onClick={() => handleViewModeChange('cards')}
              className={`p-1.5 rounded-lg transition-colors ${viewMode === 'cards' ? 'bg-indigo-600 text-white' : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'}`}
              title="Cards view"
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
            <button
              onClick={() => handleViewModeChange('split')}
              className={`p-1.5 rounded-lg transition-colors ${viewMode === 'split' ? 'bg-indigo-600 text-white' : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'}`}
              title="Split panel view"
            >
              <Columns className="w-4 h-4" />
            </button>
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
            {/* Bulk Action Bar — only in table view */}
            {viewMode === 'table' && selectedIds.size > 0 && (
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

            {/* ── TABLE VIEW ── */}
            {viewMode === 'table' && (
            <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand overflow-hidden card-animate">
            <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[1100px]">
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
                  <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide max-w-[160px]">Top Skills</th>
                  <th
                    onClick={() => handleSort('created_at')}
                    className={`px-4 py-3.5 text-left text-xs uppercase tracking-wide whitespace-nowrap min-w-[90px] cursor-pointer hover:text-indigo-600 select-none ${sortBy === 'created_at' ? 'font-extrabold text-indigo-600' : 'font-bold text-brand-700'}`}
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
                    <td className="px-4 py-3.5 max-w-[160px] overflow-hidden">
                      {c.matched_skills && c.matched_skills.length > 0 ? (
                        <div className="flex flex-wrap gap-1 max-h-[2.5rem] overflow-hidden">
                          {c.matched_skills.slice(0, 2).map((skill, i) => (
                            <span key={i} className="px-1.5 py-0.5 bg-green-50 text-green-700 text-xs rounded font-semibold ring-1 ring-green-100 whitespace-nowrap">
                              {skill}
                            </span>
                          ))}
                          {c.matched_skills.length > 2 && (
                            <span className="px-1.5 py-0.5 bg-slate-50 text-slate-400 text-xs rounded font-medium ring-1 ring-slate-100 whitespace-nowrap">
                              +{c.matched_skills.length - 2}
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3.5 text-slate-400 text-xs font-medium whitespace-nowrap min-w-[90px]">
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
            )}

            {/* ── CARDS VIEW ── */}
            {viewMode === 'cards' && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {displayedCandidates.map(c => {
                  const statusCfg = STATUS_CONFIG[c.latest_status] || STATUS_CONFIG.pending
                  return (
                    <div
                      key={c.id}
                      onClick={() => navigate(`/candidates/${c.id}`)}
                      className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 hover:shadow-md transition-shadow cursor-pointer"
                    >
                      {/* Top row: Avatar + Name + Score */}
                      <div className="flex items-center gap-2.5 mb-3">
                        <span className={`w-10 h-10 rounded-full flex items-center justify-center text-white text-sm font-bold shrink-0 ${getAvatarColor(c.name)}`}>
                          {getInitials(c.name)}
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="font-bold text-gray-900 truncate">{c.name || '—'}</p>
                        </div>
                        <ScoreBadge score={c.best_score} />
                      </div>

                      {/* Email */}
                      {c.email && (
                        <div className="flex items-center gap-1.5 mb-2 min-w-0">
                          <Mail className="w-3 h-3 text-gray-400 shrink-0" />
                          <span className="text-xs text-gray-500 truncate">{c.email}</span>
                        </div>
                      )}

                      {/* Status badge */}
                      <div className="mb-2" onClick={e => e.stopPropagation()}>
                        {c.latest_result_id ? (
                          <StatusPill
                            status={c.latest_status || 'pending'}
                            onChange={(newStatus) => handleStatusChange(c.latest_result_id, newStatus)}
                          />
                        ) : (
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ring-1 ${statusCfg.color}`}>{statusCfg.label}</span>
                        )}
                      </div>

                      {/* Skills */}
                      {c.matched_skills && c.matched_skills.length > 0 && (
                        <div className="flex flex-wrap gap-1 mb-3">
                          {c.matched_skills.slice(0, 3).map((skill, i) => (
                            <span key={i} className="text-xs bg-gray-100 rounded-full px-2 py-0.5 text-gray-700 font-medium">{skill}</span>
                          ))}
                          {c.matched_skills.length > 3 && (
                            <span className="text-xs bg-gray-100 rounded-full px-2 py-0.5 text-gray-500 font-medium">+{c.matched_skills.length - 3}</span>
                          )}
                        </div>
                      )}

                      {/* Bottom: Applications + date */}
                      <div className="flex items-center justify-between text-xs text-gray-400 pt-2 border-t border-gray-100">
                        <span>Applications: {c.result_count ?? 0}</span>
                        <span>{c.created_at ? new Date(c.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '—'}</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}

            {/* ── SPLIT PANEL VIEW ── */}
            {viewMode === 'split' && (
              <div className="flex h-[calc(100vh-200px)] bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
                {/* Left panel — candidate list */}
                <div className="w-80 lg:w-96 shrink-0 border-r border-gray-200 overflow-y-auto">
                  {displayedCandidates.map(c => {
                    const isActive = splitSelectedId === c.id
                    const statusCfg = STATUS_CONFIG[c.latest_status] || STATUS_CONFIG.pending
                    const statusDotColor = c.latest_status === 'hired' ? 'bg-emerald-500'
                      : c.latest_status === 'shortlisted' ? 'bg-green-500'
                      : c.latest_status === 'rejected' ? 'bg-red-500'
                      : c.latest_status === 'in-review' ? 'bg-amber-500'
                      : 'bg-slate-400'
                    return (
                      <div
                        key={c.id}
                        onClick={() => {
                          setSplitSelectedId(c.id)
                          setSplitLoading(true)
                          setSplitProfile(null)
                          getCandidate(c.id)
                            .then(data => setSplitProfile(data))
                            .catch(() => setSplitProfile(null))
                            .finally(() => setSplitLoading(false))
                        }}
                        className={`flex items-center gap-2.5 px-4 py-3 cursor-pointer transition-colors border-l-3 ${
                          isActive ? 'bg-indigo-50 border-l-indigo-600' : 'border-l-transparent hover:bg-gray-50'
                        }`}
                      >
                        <span className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0 ${getAvatarColor(c.name)}`}>
                          {getInitials(c.name)}
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="font-bold text-gray-900 truncate text-sm">{c.name || '—'}</p>
                        </div>
                        <ScoreBadge score={c.best_score} />
                        <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${statusDotColor}`} title={statusCfg.label} />
                      </div>
                    )
                  })}
                </div>

                {/* Right panel — inline profile preview */}
                <div className="flex-1 overflow-y-auto p-6">
                  {!splitSelectedId ? (
                    <div className="flex flex-col items-center justify-center h-full text-gray-400">
                      <Users className="w-12 h-12 mb-3 text-gray-300" />
                      <p className="text-sm font-medium">Select a candidate to preview their profile</p>
                    </div>
                  ) : splitLoading ? (
                    <div className="flex items-center justify-center h-full">
                      <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
                    </div>
                  ) : !splitProfile ? (
                    <div className="flex flex-col items-center justify-center h-full text-gray-400">
                      <p className="text-sm font-medium">Failed to load candidate profile</p>
                    </div>
                  ) : (
                    <SplitProfilePreview
                      profile={splitProfile}
                      onStatusChange={handleStatusChange}
                      navigate={navigate}
                    />
                  )}
                </div>
              </div>
            )}

            {/* Pagination — shared for table & cards; split uses infinite scroll in left panel */}
            {viewMode !== 'split' && total > 20 && (
              <div className="flex items-center justify-between p-4 mt-4">
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
          </>
        )}
      </main>
      {selectedId && <CandidateDetail candidateId={selectedId} onClose={() => setSelectedId(null)} />}
      {toast && <Toast message={toast} onDone={() => setToast(null)} />}
    </div>
  )
}
