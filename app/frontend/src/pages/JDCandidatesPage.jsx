import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import {
  Users, ArrowLeft, Filter, ChevronDown, CheckCircle2, XCircle,
  Clock, UserCheck, AlertTriangle, ChevronUp, ChevronDown as SortDesc,
  List, Columns, Briefcase, ChevronRight
} from 'lucide-react'
import { getJDCandidates, bulkUpdateStatus, updateResultStatus, getCandidatePipeline } from '../lib/api'
import { STATUS_OPTIONS, STATUS_CONFIG, getScoreColor, PIPELINE_STAGES } from '../lib/constants'
import Skeleton from '../components/Skeleton'
import CandidateCard from '../components/CandidateCard'
import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts'
import { useOptimisticUpdate } from '../hooks/useOptimisticUpdate'

/** Coerce any value to a render-safe string. Objects become JSON; null/undefined → '' */
function safeStr(v) {
  if (v == null) return ''
  if (typeof v === 'string') return v
  if (typeof v === 'number' || typeof v === 'boolean') return String(v)
  try { return JSON.stringify(v) } catch { return String(v) }
}

// ── Kanban column config (same as KanbanBoard.jsx) ──

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
  const color = getScoreColor(score)
  return (
    <span className={`inline-flex items-center justify-center min-w-[2.5rem] px-2 py-0.5 rounded-full text-xs font-bold ring-1 ${color.text} ${color.bg} ${color.ring}`}>
      {score}
    </span>
  )
}

function KanbanScoreBadge({ score }) {
  if (score == null) return <span className="text-slate-400 text-xs font-medium">—</span>
  const color = getScoreColor(score)
  return <span className={`px-2 py-0.5 rounded-full text-xs font-bold ring-1 ${color.text} ${color.bg} ${color.ring}`}>{score}</span>
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
  const total = PIPELINE_STAGES.reduce((sum, s) => sum + (counts[s] || 0), 0)
  if (total === 0) return null

  return (
    <div className="bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 shadow-brand-sm p-4 card-animate">
      <div className="flex items-center gap-3 mb-2">
        <span className="text-sm font-bold text-brand-800">Funnel Progress</span>
        <span className="ml-auto text-xs font-semibold text-slate-500">{total} total</span>
      </div>
      <div className="flex w-full h-5 rounded-full overflow-hidden ring-1 ring-brand-100">
        {PIPELINE_STAGES.map(status => {
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
        {PIPELINE_STAGES.map(status => {
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
  const [selectedIds, setSelectedIds] = useState(new Set())
  const [bulkLoading, setBulkLoading] = useState(false)

  // ── Kanban state ──
  const [kanbanColumns, setKanbanColumns] = useState({})
  const [kanbanCounts, setKanbanCounts] = useState({})
  const [kanbanLoading, setKanbanLoading] = useState(false)
  const [dragOverColumn, setDragOverColumn] = useState(null)
  const [draggingId, setDraggingId] = useState(null)
  const [toast, setToast] = useState(null)
  const [confirmDialog, setConfirmDialog] = useState(null)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const searchInputRef = useRef(null)

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
  useEffect(() => { setSelectedIds(new Set()) }, [statusFilter, sortBy, sortOrder])

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
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleAll = () => {
    if (selectedIds.size === candidates.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(candidates.map(c => c.id || c.result_id)))
    }
  }

  const clearSelection = () => setSelectedIds(new Set())

  const { optimisticUpdate } = useOptimisticUpdate()

  // ── Status change (list view) ──
  const handleStatusChange = (resultId, newStatus) => {
    const prevStatus = candidates.find(c => (c.id || c.result_id) === resultId)?.status
    optimisticUpdate({
      items: candidates,
      setItems: setCandidates,
      itemId: resultId,
      idField: (c) => c.id || c.result_id,
      field: 'status',
      newValue: newStatus,
      apiCall: () => updateResultStatus(resultId, newStatus),
      undoApiCall: () => updateResultStatus(resultId, prevStatus),
      undoMessage: `Candidate marked as ${STATUS_CONFIG[newStatus]?.label || newStatus}`,
    })
  }

  // ── Bulk actions ──
  const handleBulkAction = async (status) => {
    if (selectedIds.size === 0) return
    setBulkLoading(true)
    try {
      await bulkUpdateStatus(jdId, [...selectedIds], status)
      setCandidates(prev =>
        prev.map(c =>
          selectedIds.has(c.id || c.result_id) ? { ...c, status } : c
        )
      )
      setSelectedIds(new Set())
    } catch {
      // Silently fail
    } finally {
      setBulkLoading(false)
    }
  }

  const handleBulkShortlist = async () => {
    await handleBulkAction('shortlisted')
  }

  const handleBulkReject = async () => {
    await handleBulkAction('rejected')
  }

  const handleSortChange = (newSortBy) => {
    if (newSortBy === sortBy) {
      setSortOrder(prev => (prev === 'desc' ? 'asc' : 'desc'))
    } else {
      setSortBy(newSortBy)
      setSortOrder(newSortBy === 'name' ? 'asc' : 'desc')
    }
  }

  // ── Keyboard shortcuts (list view only) ──
  useKeyboardShortcuts({
    items: candidates,
    selectedIndex,
    onSelect: setSelectedIndex,
    onShortlist: (candidate) => {
      const rid = candidate?.latest_result_id || candidate?.id || candidate?.result_id
      if (rid) handleStatusChange(rid, 'shortlisted')
    },
    onReject: (candidate) => {
      const rid = candidate?.latest_result_id || candidate?.id || candidate?.result_id
      if (rid) handleStatusChange(rid, 'rejected')
    },
    onOpen: (candidate) => navigate('/report', { state: { result: candidate } }),
    onSearch: () => searchInputRef.current?.focus(),
    enabled: viewMode === 'list',
  })

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
                  ? `${PIPELINE_STAGES.reduce((s, k) => s + (kanbanCounts[k] || 0), 0)} candidate${PIPELINE_STAGES.reduce((s, k) => s + (kanbanCounts[k] || 0), 0) !== 1 ? 's' : ''} in pipeline`
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
                ref={searchInputRef}
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
            <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand overflow-hidden">
              <Skeleton variant="list" count={8} />
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
              {/* Select All Header */}
              <div className="flex items-center gap-3 bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 shadow-brand-sm px-4 py-3 card-animate">
                <input
                  type="checkbox"
                  checked={selectedIds.size === candidates.length && candidates.length > 0}
                  onChange={toggleAll}
                  className="w-4 h-4 rounded border-brand-300 text-brand-600 focus:ring-brand-500 cursor-pointer"
                />
                <span className="text-sm font-semibold text-slate-700">
                  {selectedIds.size > 0
                    ? `${selectedIds.size} of ${candidates.length} selected`
                    : `${candidates.length} candidate${candidates.length !== 1 ? 's' : ''}`
                  }
                </span>
              </div>

              {/* Candidate Cards */}
              <div className="space-y-3">
                {candidates.map((c, idx) => {
                  const id = c.id || c.result_id
                  return (
                    <div key={id} className="flex items-start gap-3">
                      <div className="pt-5 pl-2">
                        <input
                          type="checkbox"
                          checked={selectedIds.has(id)}
                          onChange={() => toggleSelect(id)}
                          className="w-4 h-4 rounded border-brand-300 text-brand-600 focus:ring-brand-500 cursor-pointer"
                        />
                      </div>
                      <div className={`flex-1 min-w-0 ${selectedIndex === idx ? 'ring-2 ring-brand-500 rounded-xl' : ''}`}>
                        <CandidateCard
                          candidate={{
                            id,
                            name: c.candidate_name || c.name,
                            email: c.email,
                            title: c.title || c.current_role,
                            fit_score: c.fit_score ?? c.score,
                            status: c.status || 'pending',
                            skills: (c.matched_skills || c.skills_matched || c.skills || []).map(s =>
                              typeof s === 'string' ? { name: s, score: 80 } : s
                            ),
                            highlights: (c.highlights || []).map(h =>
                              typeof h === 'string' ? { text: h, type: 'strength' } : h
                            ),
                            job_title: jdName,
                          }}
                          onStatusChange={handleStatusChange}
                          onSelect={(card) => navigate('/report', { state: { resultId: card.id } })}
                          selected={selectedIndex === idx}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>

              {/* Floating Bulk Actions Bar */}
              {selectedIds.size > 0 && (
                <div className="fixed bottom-6 left-1/2 -translate-x-1/2 bg-white rounded-xl shadow-xl border border-slate-200 px-6 py-3 flex items-center gap-4 z-50">
                  <span className="text-sm font-medium text-slate-700">{selectedIds.size} selected</span>
                  <button onClick={handleBulkShortlist} disabled={bulkLoading} className="px-3 py-1.5 bg-emerald-50 text-emerald-700 rounded-lg text-sm font-medium hover:bg-emerald-100 disabled:opacity-60">
                    Shortlist All
                  </button>
                  <button onClick={handleBulkReject} disabled={bulkLoading} className="px-3 py-1.5 bg-red-50 text-red-700 rounded-lg text-sm font-medium hover:bg-red-100 disabled:opacity-60">
                    Reject All
                  </button>
                  <button onClick={() => setSelectedIds(new Set())} className="px-3 py-1.5 text-slate-500 text-sm hover:text-slate-700">
                    Clear
                  </button>
                </div>
              )}
            </>
          )
        ) : (
          /* ───── KANBAN VIEW ───── */
          kanbanLoading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
              <Skeleton variant="card" count={5} />
            </div>
          ) : (
            <div className="space-y-4">
              {/* Funnel Progress Bar */}
              <FunnelProgressBar counts={kanbanCounts} />

              {/* Kanban Columns */}
              <div className="flex gap-4 overflow-x-auto pb-2" style={{ minHeight: '60vh' }}>
                {PIPELINE_STAGES.map(status => {
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
