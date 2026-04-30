import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Users, ArrowLeft, Filter, ChevronDown, CheckCircle2, XCircle,
  Clock, UserCheck, AlertTriangle, ChevronUp, ChevronDown as SortDesc
} from 'lucide-react'
import { getJDCandidates, bulkUpdateStatus, updateResultStatus } from '../lib/api'

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

function relativeTime(dateStr) {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  if (days < 30) return `${days}d ago`
  return new Date(dateStr).toLocaleDateString()
}

function ScoreBadge({ score }) {
  if (score == null) return <span className="text-slate-400 text-xs font-medium">—</span>
  let color = 'text-red-700 bg-red-50 ring-red-200'
  if (score >= 70) color = 'text-green-700 bg-green-50 ring-green-200'
  else if (score >= 40) color = 'text-amber-700 bg-amber-50 ring-amber-200'
  return (
    <span className={`inline-flex items-center justify-center min-w-[2.5rem] px-2 py-0.5 rounded-full text-xs font-bold ring-1 ${color}`}>
      {score}
    </span>
  )
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

function SkillTag({ skill, type = 'matched' }) {
  const cls = type === 'matched'
    ? 'bg-green-50 text-green-700 ring-green-200'
    : 'bg-red-50 text-red-600 ring-red-200'
  return (
    <span className={`inline-block px-2 py-0.5 rounded-md text-xs font-medium ring-1 ${cls}`}>
      {safeStr(skill)}
    </span>
  )
}

export default function JDCandidatesPage() {
  const { id: jdId } = useParams()
  const navigate = useNavigate()

  const [candidates, setCandidates] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [jdName, setJdName] = useState('')

  // Filters
  const [statusFilter, setStatusFilter] = useState('')
  const [sortBy, setSortBy] = useState('fit_score')
  const [sortOrder, setSortOrder] = useState('desc')

  // Selection
  const [selected, setSelected] = useState(new Set())
  const [bulkLoading, setBulkLoading] = useState(false)

  const fetchCandidates = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getJDCandidates(jdId, {
        sortBy,
        sortOrder,
        status: statusFilter,
      })
      // API returns { candidates: [...], jd_name?: string, total: number }
      const list = data.candidates || data.results || data || []
      setCandidates(Array.isArray(list) ? list : [])
      setJdName(data.jd_name || data.name || `JD #${jdId}`)
    } catch (err) {
      setError(err.message || 'Failed to fetch candidates')
      setCandidates([])
    } finally {
      setLoading(false)
    }
  }, [jdId, sortBy, sortOrder, statusFilter])

  useEffect(() => { fetchCandidates() }, [fetchCandidates])

  // Reset selection when filters change
  useEffect(() => { setSelected(new Set()) }, [statusFilter, sortBy, sortOrder])

  // ── Selection helpers ──
  const toggleSelect = (id) => {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleAll = () => {
    if (selected.size === candidates.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(candidates.map(c => c.id || c.result_id)))
    }
  }

  const clearSelection = () => setSelected(new Set())

  // ── Status change ──
  const handleStatusChange = async (resultId, newStatus) => {
    try {
      await updateResultStatus(resultId, newStatus)
      setCandidates(prev =>
        prev.map(c => (c.id || c.result_id) === resultId ? { ...c, status: newStatus } : c)
      )
    } catch {
      // Silently fail — UI stays consistent
    }
  }

  // ── Bulk actions ──
  const handleBulkAction = async (status) => {
    if (selected.size === 0) return
    setBulkLoading(true)
    try {
      await bulkUpdateStatus(jdId, [...selected], status)
      setCandidates(prev =>
        prev.map(c =>
          selected.has(c.id || c.result_id) ? { ...c, status } : c
        )
      )
      setSelected(new Set())
    } catch {
      // Silently fail
    } finally {
      setBulkLoading(false)
    }
  }

  const handleSortChange = (newSortBy) => {
    if (newSortBy === sortBy) {
      setSortOrder(prev => (prev === 'desc' ? 'asc' : 'desc'))
    } else {
      setSortBy(newSortBy)
      setSortOrder(newSortBy === 'name' ? 'asc' : 'desc')
    }
  }

  const SortIcon = ({ field }) => {
    if (sortBy !== field) return null
    return sortOrder === 'asc'
      ? <ChevronUp className="w-3 h-3 inline ml-0.5" />
      : <SortDesc className="w-3 h-3 inline ml-0.5" />
  }

  return (
    <div>
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-3 card-animate">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/jd-library')}
              className="p-2 hover:bg-brand-50 rounded-xl text-slate-400 hover:text-brand-600 transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h2 className="text-3xl font-extrabold text-brand-900 tracking-tight">
                {jdName || `JD #${jdId}`}
              </h2>
              <p className="text-slate-500 text-sm mt-1 font-medium">
                {candidates.length} candidate{candidates.length !== 1 ? 's' : ''} analyzed
              </p>
            </div>
          </div>
        </div>

        {/* Filter / Sort Bar */}
        <div className="flex flex-wrap items-center gap-4 bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 shadow-brand-sm p-4 card-animate">
          <div className="flex items-center gap-2">
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
          </div>
          <div className="flex items-center gap-2 ml-auto">
            <span className="text-sm font-semibold text-slate-700">Sort:</span>
            <div className="flex gap-1">
              {[
                { key: 'fit_score', label: 'Score' },
                { key: 'name', label: 'Name' },
                { key: 'date', label: 'Date' },
              ].map(opt => (
                <button
                  key={opt.key}
                  onClick={() => handleSortChange(opt.key)}
                  className={`px-3 py-1.5 text-xs rounded-lg font-medium transition-all flex items-center ${
                    sortBy === opt.key
                      ? 'bg-brand-600 text-white shadow-brand-sm'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {opt.label}
                  <SortIcon field={opt.key} />
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Content */}
        {loading ? (
          <div className="flex justify-center py-16">
            <div className="w-8 h-8 border-4 border-brand-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : error ? (
          <div className="text-center py-16 bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-red-100 shadow-brand card-animate">
            <div className="w-16 h-16 rounded-2xl bg-red-50 ring-1 ring-red-200 flex items-center justify-center mx-auto mb-4">
              <AlertTriangle className="w-8 h-8 text-red-300" />
            </div>
            <p className="text-red-600 font-medium">{error}</p>
          </div>
        ) : candidates.length === 0 ? (
          <div className="text-center py-16 bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand card-animate">
            <div className="w-16 h-16 rounded-2xl bg-brand-50 ring-1 ring-brand-200 flex items-center justify-center mx-auto mb-4">
              <Users className="w-8 h-8 text-brand-300" />
            </div>
            <p className="text-slate-500 font-medium">
              No candidates analyzed for this JD yet. Analyze resumes to get started.
            </p>
          </div>
        ) : (
          <>
            {/* Bulk Action Bar */}
            {selected.size > 0 && (
              <div className="sticky top-20 z-20 flex items-center gap-3 bg-brand-900 text-white px-5 py-3 rounded-2xl shadow-brand-lg card-animate">
                <span className="text-sm font-bold">
                  {selected.size} selected
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

            {/* Candidate Table */}
            <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand overflow-hidden card-animate">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-brand-50 border-b border-brand-100">
                    <tr>
                      <th className="px-4 py-3.5 text-left w-10">
                        <input
                          type="checkbox"
                          checked={selected.size === candidates.length && candidates.length > 0}
                          onChange={toggleAll}
                          className="w-4 h-4 rounded border-brand-300 text-brand-600 focus:ring-brand-500 cursor-pointer"
                        />
                      </th>
                      <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Rank</th>
                      <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Candidate</th>
                      <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Score</th>
                      <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Status</th>
                      <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Recommendation</th>
                      <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Skills</th>
                      <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Exp.</th>
                      <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Analyzed</th>
                    </tr>
                  </thead>
                  <tbody>
                    {candidates.map((c, idx) => {
                      const id = c.id || c.result_id
                      const matchedSkills = c.matched_skills || c.skills_matched || []
                      const missingSkills = c.missing_skills || c.skills_missing || []
                      const rec = c.final_recommendation || c.recommendation || ''
                      const exp = c.total_experience_years ?? c.experience_years ?? c.years_experience
                      const analyzedDate = c.created_at || c.analyzed_at || c.timestamp || c.date

                      return (
                        <tr
                          key={id}
                          className={`border-b border-brand-50 hover:bg-brand-50/40 transition-colors ${
                            selected.has(id) ? 'bg-brand-50/60' : ''
                          }`}
                        >
                          {/* Checkbox */}
                          <td className="px-4 py-3.5">
                            <input
                              type="checkbox"
                              checked={selected.has(id)}
                              onChange={() => toggleSelect(id)}
                              className="w-4 h-4 rounded border-brand-300 text-brand-600 focus:ring-brand-500 cursor-pointer"
                            />
                          </td>
                          {/* Rank */}
                          <td className="px-4 py-3.5">
                            <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-brand-50 ring-1 ring-brand-200 text-xs font-extrabold text-brand-700">
                              {idx + 1}
                            </span>
                          </td>
                          {/* Candidate Name */}
                          <td className="px-4 py-3.5">
                            <button
                              onClick={() => navigate('/report', { state: { result: c } })}
                              className="font-bold text-brand-900 hover:text-brand-600 hover:underline transition-colors text-left"
                            >
                              {safeStr(c.candidate_name || c.name) || '—'}
                            </button>
                          </td>
                          {/* Score */}
                          <td className="px-4 py-3.5">
                            <ScoreBadge score={c.fit_score ?? c.score} />
                          </td>
                          {/* Status */}
                          <td className="px-4 py-3.5">
                            <StatusPill
                              status={c.status || 'pending'}
                              onChange={(newStatus) => handleStatusChange(id, newStatus)}
                            />
                          </td>
                          {/* Recommendation */}
                          <td className="px-4 py-3.5">
                            <span className={`text-xs font-bold ${
                              rec === 'Shortlist' || rec === 'shortlist' ? 'text-green-700' :
                              rec === 'Reject'    || rec === 'reject'    ? 'text-red-700'   : 'text-amber-700'
                            }`}>
                              {safeStr(rec) || '—'}
                            </span>
                          </td>
                          {/* Skills */}
                          <td className="px-4 py-3.5">
                            <div className="flex flex-wrap gap-1 max-w-[220px]">
                              {Array.isArray(matchedSkills) && matchedSkills.slice(0, 5).map((s, i) => (
                                <SkillTag key={i} skill={s} type="matched" />
                              ))}
                              {matchedSkills.length > 5 && (
                                <span className="px-2 py-0.5 text-xs font-semibold text-slate-500 bg-slate-50 rounded-md">
                                  +{matchedSkills.length - 5} more
                                </span>
                              )}
                              {Array.isArray(missingSkills) && missingSkills.slice(0, 3).map((s, i) => (
                                <SkillTag key={`m${i}`} skill={s} type="missing" />
                              ))}
                            </div>
                          </td>
                          {/* Experience */}
                          <td className="px-4 py-3.5">
                            <span className="text-xs font-semibold text-slate-600">
                              {exp != null ? `${safeStr(exp)} yr${Number(exp) !== 1 ? 's' : ''}` : '—'}
                            </span>
                          </td>
                          {/* Analyzed Date */}
                          <td className="px-4 py-3.5">
                            <span className="text-xs text-slate-400 font-medium">
                              {relativeTime(analyzedDate)}
                            </span>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  )
}
