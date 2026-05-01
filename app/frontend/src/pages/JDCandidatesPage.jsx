import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import {
  Users, ArrowLeft, Filter, ChevronDown, CheckCircle2, XCircle,
  Clock, UserCheck, AlertTriangle, ChevronUp, ChevronDown as SortDesc,
  List, Columns, Briefcase, ChevronRight
} from 'lucide-react'
import { getJDCandidates, bulkUpdateStatus, updateResultStatus, getCandidatePipeline } from '../lib/api'

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

// ── Kanban column config (same as KanbanBoard.jsx) ──
const KANBAN_COLUMN_ORDER = ['pending', 'in-review', 'shortlisted', 'rejected', 'hired']

const KANBAN_COLUMN_CONFIG = {
  pending:     {
    label: 'Pending',
    headerBg: 'bg-amber-50',
    headerText: 'text-amber-800',
    headerBorder: 'border-amber-200',
    badgeBg: 'bg-amber-100',
    badgeText: 'text-amber-700',
    ring: 'ring-amber-200',
    dropHighlight: 'bg-amber-50/60 border-amber-300',
    funnelColor: 'bg-amber-400',
  },
  'in-review': {
    label: 'In Review',
    headerBg: 'bg-blue-50',
    headerText: 'text-blue-800',
    headerBorder: 'border-blue-200',
    badgeBg: 'bg-blue-100',
    badgeText: 'text-blue-700',
    ring: 'ring-blue-200',
    dropHighlight: 'bg-blue-50/60 border-blue-300',
    funnelColor: 'bg-blue-400',
  },
  shortlisted: {
    label: 'Shortlisted',
    headerBg: 'bg-green-50',
    headerText: 'text-green-800',
    headerBorder: 'border-green-200',
    badgeBg: 'bg-green-100',
    badgeText: 'text-green-700',
    ring: 'ring-green-200',
    dropHighlight: 'bg-green-50/60 border-green-300',
    funnelColor: 'bg-green-400',
  },
  rejected:    {
    label: 'Rejected',
    headerBg: 'bg-red-50',
    headerText: 'text-red-800',
    headerBorder: 'border-red-200',
    badgeBg: 'bg-red-100',
    badgeText: 'text-red-700',
    ring: 'ring-red-200',
    dropHighlight: 'bg-red-50/60 border-red-300',
    funnelColor: 'bg-red-400',
  },
  hired:       {
    label: 'Hired',
    headerBg: 'bg-indigo-50',
    headerText: 'text-indigo-800',
    headerBorder: 'border-indigo-200',
    badgeBg: 'bg-indigo-100',
    badgeText: 'text-indigo-700',
    ring: 'ring-indigo-200',
    dropHighlight: 'bg-indigo-50/60 border-indigo-300',
    funnelColor: 'bg-indigo-400',
  },
}

/** Sort candidates within a column by best_score descending */
function sortColumnsByScore(cols) {
  const sorted = {}
  for (const status of Object.keys(cols)) {
    sorted[status] = [...(cols[status] || [])].sort((a, b) => {
      const sa = a.best_score ?? a.fit_score ?? a.score ?? -1
      const sb = b.best_score ?? b.fit_score ?? b.score ?? -1
      return sb - sa
    })
  }
  return sorted
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

function KanbanScoreBadge({ score }) {
  if (score == null) return <span className="text-slate-400 text-xs font-medium">—</span>
  let color = 'text-red-700 bg-red-50 ring-red-200'
  if (score >= 70) color = 'text-green-700 bg-green-50 ring-green-200'
  else if (score >= 50) color = 'text-amber-700 bg-amber-50 ring-amber-200'
  return <span className={`px-2 py-0.5 rounded-full text-xs font-bold ring-1 ${color}`}>{score}</span>
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

// ── Funnel Progress Bar ──
function FunnelProgressBar({ counts }) {
  const total = KANBAN_COLUMN_ORDER.reduce((sum, s) => sum + (counts[s] || 0), 0)
  if (total === 0) return null

  return (
    <div className="bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 shadow-brand-sm p-4 card-animate">
      <div className="flex items-center gap-3 mb-2">
        <span className="text-sm font-bold text-brand-800">Funnel Progress</span>
        <span className="ml-auto text-xs font-semibold text-slate-500">{total} total</span>
      </div>
      <div className="flex w-full h-5 rounded-full overflow-hidden ring-1 ring-brand-100">
        {KANBAN_COLUMN_ORDER.map(status => {
          const count = counts[status] || 0
          if (count === 0) return null
          const pct = (count / total) * 100
          const cfg = KANBAN_COLUMN_CONFIG[status]
          return (
            <div
              key={status}
              className={`${cfg.funnelColor} relative group transition-all`}
              style={{ width: `${pct}%` }}
              title={`${cfg.label}: ${count} (${pct.toFixed(1)}%)`}
            >
              {/* Tooltip on hover */}
              <div className="absolute -top-8 left-1/2 -translate-x-1/2 hidden group-hover:block bg-brand-900 text-white text-[10px] font-semibold px-2 py-1 rounded-lg whitespace-nowrap z-10">
                {cfg.label}: {count} ({pct.toFixed(0)}%)
              </div>
            </div>
          )
        })}
      </div>
      <div className="flex gap-4 mt-2 flex-wrap">
        {KANBAN_COLUMN_ORDER.map(status => {
          const count = counts[status] || 0
          const pct = total > 0 ? ((count / total) * 100).toFixed(0) : 0
          const cfg = KANBAN_COLUMN_CONFIG[status]
          return (
            <div key={status} className="flex items-center gap-1.5">
              <span className={`w-2.5 h-2.5 rounded-sm ${cfg.funnelColor}`} />
              <span className="text-[11px] font-semibold text-slate-600">
                {cfg.label}: {count} ({pct}%)
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Confirmation Dialog for destructive moves ──
function ConfirmDialog({ candidateName, targetLabel, onConfirm, onCancel }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-brand-lg ring-1 ring-brand-100 p-6 max-w-sm w-full mx-4 card-animate">
        <h3 className="text-lg font-bold text-brand-900 mb-2">Confirm Move</h3>
        <p className="text-sm text-slate-600 mb-5">
          Move <span className="font-semibold text-brand-900">{candidateName || 'this candidate'}</span> to{' '}
          <span className="font-semibold">{targetLabel}</span>?
        </p>
        <div className="flex justify-end gap-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-xl transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 text-sm font-bold text-white bg-brand-600 hover:bg-brand-700 rounded-xl transition-colors"
          >
            Confirm
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Toast ──
function Toast({ message, type = 'error', onDone }) {
  useEffect(() => {
    const t = setTimeout(onDone, 3000)
    return () => clearTimeout(t)
  }, [onDone])
  const bg = type === 'error' ? 'bg-red-600' : 'bg-brand-900'
  return (
    <div className={`fixed bottom-6 right-6 z-50 ${bg} text-white px-5 py-3 rounded-2xl shadow-brand-lg text-sm font-semibold card-animate`}>
      {message}
    </div>
  )
}

export default function JDCandidatesPage() {
  const { id: jdId } = useParams()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  // View mode
  const [viewMode, setViewMode] = useState(() =>
    searchParams.get('view') === 'kanban' ? 'kanban' : 'list'
  )

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

  // ── Kanban state ──
  const [kanbanColumns, setKanbanColumns] = useState({})
  const [kanbanCounts, setKanbanCounts] = useState({})
  const [kanbanLoading, setKanbanLoading] = useState(false)
  const [dragOverColumn, setDragOverColumn] = useState(null)
  const [draggingId, setDraggingId] = useState(null)
  const [toast, setToast] = useState(null)
  const [confirmDialog, setConfirmDialog] = useState(null)

  // ── List view fetch ──
  const fetchCandidates = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getJDCandidates(jdId, {
        sortBy,
        sortOrder,
        status: statusFilter,
      })
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

  // ── Kanban fetch ──
  const fetchKanban = useCallback(async () => {
    setKanbanLoading(true)
    try {
      const data = await getCandidatePipeline(jdId)
      setKanbanColumns(sortColumnsByScore(data.columns || {}))
      setKanbanCounts(data.counts || {})
    } catch {
      setToast({ message: 'Failed to load pipeline', type: 'error' })
    } finally {
      setKanbanLoading(false)
    }
  }, [jdId])

  useEffect(() => {
    if (viewMode === 'kanban') {
      fetchKanban()
    }
  }, [viewMode, fetchKanban])

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

  // ── Status change (list view) ──
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

  // ── Kanban drag handlers ──
  const handleDragStart = (e, candidate, sourceStatus) => {
    const payload = JSON.stringify({
      id: candidate.id,
      latest_result_id: candidate.latest_result_id,
      sourceStatus,
    })
    e.dataTransfer.setData('application/json', payload)
    e.dataTransfer.effectAllowed = 'move'
    setDraggingId(candidate.id)
  }

  const handleDragEnd = () => {
    setDraggingId(null)
    setDragOverColumn(null)
  }

  const handleDragOver = (e, status) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    setDragOverColumn(status)
  }

  const handleDragLeave = (e) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const x = e.clientX
    const y = e.clientY
    if (x < rect.left || x > rect.right || y < rect.top || y > rect.bottom) {
      setDragOverColumn(null)
    }
  }

  const executeDrop = async (payload, targetStatus) => {
    const { id, latest_result_id, sourceStatus } = payload
    if (!id || !latest_result_id || sourceStatus === targetStatus) return

    const candidate = kanbanColumns[sourceStatus]?.find(c => c.id === id)
    if (!candidate) return

    const previousColumns = { ...kanbanColumns }
    const previousCounts = { ...kanbanCounts }

    setKanbanColumns(prev => {
      const next = { ...prev }
      next[sourceStatus] = next[sourceStatus].filter(c => c.id !== id)
      next[targetStatus] = [...(next[targetStatus] || []), { ...candidate }]
      return sortColumnsByScore(next)
    })
    setKanbanCounts(prev => ({
      ...prev,
      [sourceStatus]: Math.max(0, (prev[sourceStatus] || 0) - 1),
      [targetStatus]: (prev[targetStatus] || 0) + 1,
    }))

    try {
      await updateResultStatus(latest_result_id, targetStatus)
    } catch {
      setKanbanColumns(previousColumns)
      setKanbanCounts(previousCounts)
      setToast({ message: 'Failed to update status. Please try again.', type: 'error' })
    }
  }

  const handleDrop = async (e, targetStatus) => {
    e.preventDefault()
    setDragOverColumn(null)
    setDraggingId(null)

    const raw = e.dataTransfer.getData('application/json')
    if (!raw) return

    let payload
    try {
      payload = JSON.parse(raw)
    } catch {
      return
    }

    const { id, sourceStatus } = payload
    if (!id || sourceStatus === targetStatus) return

    // Destructive move — show confirmation
    if (targetStatus === 'rejected' || targetStatus === 'hired') {
      const candidate = kanbanColumns[sourceStatus]?.find(c => c.id === id)
      setConfirmDialog({
        candidateName: candidate?.name || 'this candidate',
        targetLabel: KANBAN_COLUMN_CONFIG[targetStatus]?.label || targetStatus,
        payload,
        targetStatus,
      })
      return
    }

    executeDrop(payload, targetStatus)
  }

  // ── Render ──
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
                {viewMode === 'kanban'
                  ? `${KANBAN_COLUMN_ORDER.reduce((s, k) => s + (kanbanCounts[k] || 0), 0)} candidate${KANBAN_COLUMN_ORDER.reduce((s, k) => s + (kanbanCounts[k] || 0), 0) !== 1 ? 's' : ''} in pipeline`
                  : `${candidates.length} candidate${candidates.length !== 1 ? 's' : ''} analyzed`
                }
              </p>
            </div>
          </div>

          {/* View Toggle */}
          <div className="flex items-center gap-1 bg-white/90 backdrop-blur-md rounded-xl ring-1 ring-brand-100 p-1">
            <button
              onClick={() => setViewMode('list')}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-lg transition-all ${
                viewMode === 'list'
                  ? 'bg-brand-600 text-white shadow-brand-sm'
                  : 'text-slate-500 hover:bg-slate-100'
              }`}
            >
              <List className="w-3.5 h-3.5" />
              List
            </button>
            <button
              onClick={() => setViewMode('kanban')}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-lg transition-all ${
                viewMode === 'kanban'
                  ? 'bg-brand-600 text-white shadow-brand-sm'
                  : 'text-slate-500 hover:bg-slate-100'
              }`}
            >
              <Columns className="w-3.5 h-3.5" />
              Kanban
            </button>
          </div>
        </div>

        {/* Filter / Sort Bar — only in list view */}
        {viewMode === 'list' && (
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
        )}

        {/* Content */}
        {viewMode === 'list' ? (
          /* ───── LIST VIEW ───── */
          loading ? (
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
                            <td className="px-4 py-3.5">
                              <input
                                type="checkbox"
                                checked={selected.has(id)}
                                onChange={() => toggleSelect(id)}
                                className="w-4 h-4 rounded border-brand-300 text-brand-600 focus:ring-brand-500 cursor-pointer"
                              />
                            </td>
                            <td className="px-4 py-3.5">
                              <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-brand-50 ring-1 ring-brand-200 text-xs font-extrabold text-brand-700">
                                {idx + 1}
                              </span>
                            </td>
                            <td className="px-4 py-3.5">
                              <button
                                onClick={() => navigate('/report', { state: { result: c } })}
                                className="font-bold text-brand-900 hover:text-brand-600 hover:underline transition-colors text-left"
                              >
                                {safeStr(c.candidate_name || c.name) || '—'}
                              </button>
                            </td>
                            <td className="px-4 py-3.5">
                              <ScoreBadge score={c.fit_score ?? c.score} />
                            </td>
                            <td className="px-4 py-3.5">
                              <StatusPill
                                status={c.status || 'pending'}
                                onChange={(newStatus) => handleStatusChange(id, newStatus)}
                              />
                            </td>
                            <td className="px-4 py-3.5">
                              <span className={`text-xs font-bold ${
                                rec === 'Shortlist' || rec === 'shortlist' ? 'text-green-700' :
                                rec === 'Reject'    || rec === 'reject'    ? 'text-red-700'   : 'text-amber-700'
                              }`}>
                                {safeStr(rec) || '—'}
                              </span>
                            </td>
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
                            <td className="px-4 py-3.5">
                              <span className="text-xs font-semibold text-slate-600">
                                {exp != null ? `${safeStr(exp)} yr${Number(exp) !== 1 ? 's' : ''}` : '—'}
                              </span>
                            </td>
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
          )
        ) : (
          /* ───── KANBAN VIEW ───── */
          kanbanLoading ? (
            <div className="flex justify-center py-16">
              <div className="w-8 h-8 border-4 border-brand-600 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : (
            <div className="space-y-4">
              {/* Funnel Progress Bar */}
              <FunnelProgressBar counts={kanbanCounts} />

              {/* Kanban Columns */}
              <div className="flex gap-4 overflow-x-auto pb-2" style={{ minHeight: '60vh' }}>
                {KANBAN_COLUMN_ORDER.map(status => {
                  const cfg = KANBAN_COLUMN_CONFIG[status]
                  const items = kanbanColumns[status] || []
                  const count = kanbanCounts[status] || 0
                  const isDropTarget = dragOverColumn === status

                  return (
                    <div
                      key={status}
                      className={`flex-shrink-0 w-72 flex flex-col rounded-2xl border transition-colors duration-200 ${
                        isDropTarget
                          ? `${cfg.dropHighlight} border-2`
                          : 'bg-white/80 backdrop-blur-md border-brand-100'
                      }`}
                      onDragOver={(e) => handleDragOver(e, status)}
                      onDragLeave={handleDragLeave}
                      onDrop={(e) => handleDrop(e, status)}
                    >
                      {/* Column Header */}
                      <div className={`px-4 py-3 rounded-t-2xl border-b ${cfg.headerBg} ${cfg.headerBorder} flex items-center justify-between`}>
                        <span className={`text-sm font-bold ${cfg.headerText}`}>{cfg.label}</span>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${cfg.badgeBg} ${cfg.badgeText} ring-1 ${cfg.ring}`}>
                          {count}
                        </span>
                      </div>

                      {/* Card List */}
                      <div className="flex-1 overflow-y-auto p-3 space-y-3 min-h-0">
                        {items.length === 0 ? (
                          <div className="flex flex-col items-center justify-center py-8 text-center">
                            <div className={`w-10 h-10 rounded-xl ${cfg.headerBg} ring-1 ${cfg.ring} flex items-center justify-center mb-2`}>
                              <Users className={`w-5 h-5 ${cfg.badgeText}`} />
                            </div>
                            <p className="text-xs text-slate-400 font-medium">No candidates</p>
                          </div>
                        ) : (
                          items.map(candidate => (
                            <div
                              key={candidate.id}
                              draggable
                              onDragStart={(e) => handleDragStart(e, candidate, status)}
                              onDragEnd={handleDragEnd}
                              onClick={() => navigate(`/candidates/${candidate.id}`)}
                              className={`bg-white rounded-xl ring-1 ring-brand-100 shadow-brand-sm p-3 cursor-pointer hover:shadow-brand transition-shadow select-none ${
                                draggingId === candidate.id ? 'opacity-50' : ''
                              }`}
                            >
                              <div className="flex items-start justify-between gap-2 mb-2">
                                <div className="min-w-0">
                                  <p className="text-sm font-bold text-brand-900 truncate">
                                    {safeStr(candidate.name) || 'Unknown'}
                                  </p>
                                  {candidate.current_role && (
                                    <p className="text-xs text-slate-500 font-medium truncate flex items-center gap-1 mt-0.5">
                                      <Briefcase className="w-3 h-3 text-slate-400" />
                                      {safeStr(candidate.current_role)}
                                    </p>
                                  )}
                                </div>
                                <KanbanScoreBadge score={candidate.best_score} />
                              </div>

                              {candidate.matched_skills && candidate.matched_skills.length > 0 && (
                                <div className="flex flex-wrap gap-1 mb-2">
                                  {candidate.matched_skills.slice(0, 3).map((skill, i) => (
                                    <span
                                      key={i}
                                      className="px-1.5 py-0.5 bg-green-50 text-green-700 text-[10px] rounded font-semibold ring-1 ring-green-100"
                                    >
                                      {safeStr(skill)}
                                    </span>
                                  ))}
                                </div>
                              )}

                              {candidate.jd_name && (
                                <p className="text-[11px] text-slate-400 font-medium truncate">
                                  {safeStr(candidate.jd_name)}
                                </p>
                              )}
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )
        )}
      </main>

      {/* Confirm Dialog for destructive moves */}
      {confirmDialog && (
        <ConfirmDialog
          candidateName={confirmDialog.candidateName}
          targetLabel={confirmDialog.targetLabel}
          onConfirm={() => {
            executeDrop(confirmDialog.payload, confirmDialog.targetStatus)
            setConfirmDialog(null)
          }}
          onCancel={() => setConfirmDialog(null)}
        />
      )}

      {/* Toast */}
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onDone={() => setToast(null)}
        />
      )}
    </div>
  )
}
