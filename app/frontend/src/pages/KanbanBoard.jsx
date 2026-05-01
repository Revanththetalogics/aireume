import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Columns, User, Briefcase } from 'lucide-react'
import { getCandidatePipeline, updateResultStatus } from '../lib/api'

/** Coerce any value to a render-safe string. */
function safeStr(v) {
  if (v == null) return ''
  if (typeof v === 'string') return v
  if (typeof v === 'number' || typeof v === 'boolean') return String(v)
  try { return JSON.stringify(v) } catch { return String(v) }
}

const COLUMN_ORDER = ['pending', 'in-review', 'shortlisted', 'rejected', 'hired']

const COLUMN_CONFIG = {
  pending:     {
    label: 'Pending',
    headerBg: 'bg-amber-50',
    headerText: 'text-amber-800',
    headerBorder: 'border-amber-200',
    badgeBg: 'bg-amber-100',
    badgeText: 'text-amber-700',
    ring: 'ring-amber-200',
    dropHighlight: 'bg-amber-50/60 border-amber-300',
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
  },
}

function ScoreBadge({ score }) {
  if (score == null) return <span className="text-slate-400 text-xs font-medium">—</span>
  let color = 'text-red-700 bg-red-50 ring-red-200'
  if (score >= 70) color = 'text-green-700 bg-green-50 ring-green-200'
  else if (score >= 50) color = 'text-amber-700 bg-amber-50 ring-amber-200'
  return <span className={`px-2 py-0.5 rounded-full text-xs font-bold ring-1 ${color}`}>{score}</span>
}

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

export default function KanbanBoard() {
  const navigate = useNavigate()
  const [columns, setColumns] = useState({})
  const [counts, setCounts] = useState({})
  const [loading, setLoading] = useState(true)
  const [dragOverColumn, setDragOverColumn] = useState(null)
  const [draggingId, setDraggingId] = useState(null)
  const [toast, setToast] = useState(null)

  const fetchPipeline = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getCandidatePipeline()
      setColumns(data.columns || {})
      setCounts(data.counts || {})
    } catch {
      setToast({ message: 'Failed to load pipeline', type: 'error' })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchPipeline()
  }, [fetchPipeline])

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
    // Only clear if we're actually leaving the column container
    const rect = e.currentTarget.getBoundingClientRect()
    const x = e.clientX
    const y = e.clientY
    if (x < rect.left || x > rect.right || y < rect.top || y > rect.bottom) {
      setDragOverColumn(null)
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

    const { id, latest_result_id, sourceStatus } = payload
    if (!id || !latest_result_id || sourceStatus === targetStatus) return

    // Find the candidate in the source column
    const candidate = columns[sourceStatus]?.find(c => c.id === id)
    if (!candidate) return

    // Optimistic update: move card immediately
    const previousColumns = { ...columns }
    const previousCounts = { ...counts }

    setColumns(prev => {
      const next = { ...prev }
      next[sourceStatus] = next[sourceStatus].filter(c => c.id !== id)
      next[targetStatus] = [...(next[targetStatus] || []), { ...candidate }]
      return next
    })
    setCounts(prev => ({
      ...prev,
      [sourceStatus]: Math.max(0, (prev[sourceStatus] || 0) - 1),
      [targetStatus]: (prev[targetStatus] || 0) + 1,
    }))

    try {
      await updateResultStatus(latest_result_id, targetStatus)
    } catch {
      // Rollback on failure
      setColumns(previousColumns)
      setCounts(previousCounts)
      setToast({ message: 'Failed to update status. Please try again.', type: 'error' })
    }
  }

  if (loading) {
    return (
      <div className="h-[calc(100vh-4rem)] flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-brand-600 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col">
      <main className="flex-1 overflow-hidden px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-10 h-10 rounded-xl bg-brand-50 ring-1 ring-brand-200 flex items-center justify-center">
            <Columns className="w-5 h-5 text-brand-600" />
          </div>
          <div>
            <h2 className="text-2xl font-extrabold text-brand-900 tracking-tight">Pipeline</h2>
            <p className="text-slate-500 text-sm font-medium">Drag and drop candidates between columns</p>
          </div>
        </div>

        <div className="flex gap-4 overflow-x-auto pb-2 h-full">
          {COLUMN_ORDER.map(status => {
            const cfg = COLUMN_CONFIG[status]
            const items = columns[status] || []
            const count = counts[status] || 0
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
                        <User className={`w-5 h-5 ${cfg.badgeText}`} />
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
                          <ScoreBadge score={candidate.best_score} />
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
      </main>

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
