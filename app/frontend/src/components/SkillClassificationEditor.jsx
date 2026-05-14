import { useState, useCallback, useRef, useEffect } from 'react'
import {
  X, ArrowRightLeft, Plus, ChevronDown, ChevronUp,
  Briefcase, Layers, Loader2, GripVertical, Sparkles, Ban, Lightbulb,
  Flame, TrendingUp, Users, AlertTriangle, CheckCircle2,
  Save, FolderOpen, Trash2, Check
} from 'lucide-react'
import {
  getSkillTemplates,
  createSkillTemplate,
  deleteSkillTemplate,
} from '../lib/api'

/**
 * SkillClassificationEditor
 *
 * Allows users to review and edit AI-extracted skill classifications
 * before proceeding with analysis. Supports drag-and-drop, inline
 * editing, and promotion from excluded/suggested pools.
 */

function safeStr(v) {
  if (v == null) return ''
  if (typeof v === 'string') return v
  if (typeof v === 'number' || typeof v === 'boolean') return String(v)
  try { return JSON.stringify(v) } catch { return String(v) }
}

function ConfidenceDot({ confidence }) {
  const isHigh = confidence === 'high'
  return (
    <span
      className={`inline-block w-2 h-2 rounded-full shrink-0 ${
        isHigh ? 'bg-green-500' : 'bg-amber-400'
      }`}
      title={`${isHigh ? 'High' : 'Medium'} confidence`}
    />
  )
}

function CountBadge({ count, variant }) {
  const colors =
    variant === 'must'
      ? 'bg-brand-100 text-brand-700'
      : 'bg-blue-100 text-blue-700'
  return (
    <span className={`ml-2 px-2 py-0.5 rounded-full text-[10px] font-bold ${colors}`}>
      {count}
    </span>
  )
}

function SkillPill({
  skill,
  index,
  column,
  onMove,
  onRemove,
  onProficiencyChange,
  onDragStart,
  onDragEnd,
  isDragging,
  dragOverIndex,
  dragOverColumn,
  onDragOverItem,
}) {
  const isDraggedOver = dragOverColumn === column && dragOverIndex === index
  const proficiencyOptions = ['Basic', 'Intermediate', 'Advanced', 'Expert']

  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, index, column)}
      onDragEnd={onDragEnd}
      onDragOver={(e) => onDragOverItem(e, index, column)}
      className={`group flex flex-col gap-1 px-3 py-2 rounded-xl text-sm font-medium
        transition-all duration-200 cursor-grab active:cursor-grabbing
        ${
          isDragging
            ? 'opacity-40'
            : 'opacity-100'
        }
        ${
          isDraggedOver
            ? 'ring-2 ring-brand-400 bg-brand-50'
            : 'ring-1 ring-slate-200 bg-white hover:ring-brand-300 hover:shadow-brand-sm'
        }
      `}
    >
      <div className="flex items-center gap-2">
        <GripVertical className="w-3.5 h-3.5 text-slate-300 shrink-0" />
        <ConfidenceDot confidence={skill.confidence} />
        <span className="truncate flex-1 text-slate-700">{safeStr(skill.skill)}</span>

        {/* Market Demand Badges */}
        {skill.is_hot === true && (
          <Flame className="w-3.5 h-3.5 text-orange-500 shrink-0" title="Hot skill — high market demand" />
        )}
        {skill.is_in_demand === true && (
          <TrendingUp className="w-3.5 h-3.5 text-green-500 shrink-0" title="In-demand skill — trending upward" />
        )}

        <button
          onClick={() => onMove(index, column)}
          className="p-1 rounded-md text-slate-400 hover:text-brand-600 hover:bg-brand-50 transition-colors"
          title={`Move to ${column === 'must' ? 'Good-to-Have' : 'Must-Have'}`}
        >
          <ArrowRightLeft className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={() => onRemove(index, column)}
          className="p-1 rounded-md text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors"
          title="Remove"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Proficiency Selector */}
      <div className="flex items-center gap-1.5 pl-5">
        <span className="text-[10px] text-slate-400 uppercase tracking-wide">Level:</span>
        <select
          value={skill.proficiency_expected || 'intermediate'}
          onChange={(e) => onProficiencyChange(index, column, e.target.value)}
          className="text-xs px-1.5 py-0.5 rounded border border-slate-200 bg-slate-50 text-slate-600 focus:outline-none focus:ring-1 focus:ring-brand-300 cursor-pointer"
        >
          {proficiencyOptions.map((opt) => (
            <option key={opt.toLowerCase()} value={opt.toLowerCase()}>{opt}</option>
          ))}
        </select>
      </div>
    </div>
  )
}

export default function SkillClassificationEditor({
  data,
  onConfirm,
  onSkip,
  loading,
  teamContext,
}) {
  // ─── State ────────────────────────────────────────────────────────────
  const [mustHave, setMustHave] = useState(
    () => (data?.required_skills || []).map((s) => ({ ...s }))
  )
  const [niceToHave, setNiceToHave] = useState(
    () => (data?.nice_to_have_skills || []).map((s) => ({ ...s }))
  )

  const [newSkill, setNewSkill] = useState('')
  const [showExcluded, setShowExcluded] = useState(false)
  const [showSuggested, setShowSuggested] = useState(false)

  // Drag state
  const [draggedIndex, setDraggedIndex] = useState(null)
  const [draggedColumn, setDraggedColumn] = useState(null)
  const [dragOverIndex, setDragOverIndex] = useState(null)
  const [dragOverColumn, setDragOverColumn] = useState(null)
  const [isDraggingOver, setIsDraggingOver] = useState({ must: false, nice: false })

  const dragCounter = useRef({ must: 0, nice: 0 })

  // Template state
  const [savedTemplates, setSavedTemplates] = useState([])
  const [templateLoading, setTemplateLoading] = useState(false)
  const [showTemplateDropdown, setShowTemplateDropdown] = useState(false)
  const [saveModalOpen, setSaveModalOpen] = useState(false)
  const [templateName, setTemplateName] = useState('')
  const [saveLoading, setSaveLoading] = useState(false)
  const [toast, setToast] = useState(null)  // { message, type: 'success' | 'error' }

  // Load templates on mount
  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        setTemplateLoading(true)
        const templates = await getSkillTemplates()
        if (!cancelled) setSavedTemplates(templates || [])
      } catch {
        // Silently fail — templates are a nice-to-have feature
      } finally {
        if (!cancelled) setTemplateLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [])

  // Auto-dismiss toast after 3s
  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => setToast(null), 3000)
    return () => clearTimeout(t)
  }, [toast])

  // ─── Helpers ──────────────────────────────────────────────────────────
  const moveSkill = useCallback((index, fromColumn) => {
    if (fromColumn === 'must') {
      const skill = mustHave[index]
      setMustHave((prev) => prev.filter((_, i) => i !== index))
      setNiceToHave((prev) => [...prev, skill])
    } else {
      const skill = niceToHave[index]
      setNiceToHave((prev) => prev.filter((_, i) => i !== index))
      setMustHave((prev) => [...prev, skill])
    }
  }, [mustHave, niceToHave])

  const removeSkill = useCallback((index, column) => {
    if (column === 'must') {
      setMustHave((prev) => prev.filter((_, i) => i !== index))
    } else {
      setNiceToHave((prev) => prev.filter((_, i) => i !== index))
    }
  }, [])

  const updateProficiency = useCallback((index, column, proficiency) => {
    if (column === 'must') {
      setMustHave((prev) => {
        const updated = [...prev]
        updated[index] = { ...updated[index], proficiency_expected: proficiency }
        return updated
      })
    } else {
      setNiceToHave((prev) => {
        const updated = [...prev]
        updated[index] = { ...updated[index], proficiency_expected: proficiency }
        return updated
      })
    }
  }, [])

  const addSkill = useCallback((targetColumn) => {
    const name = newSkill.trim()
    if (!name) return

    const skillObj = {
      skill: name,
      confidence: 'high',
      source: 'user',
      proficiency_expected: targetColumn === 'must' ? 'intermediate' : 'basic',
    }

    if (targetColumn === 'must') {
      setMustHave((prev) => [...prev, skillObj])
    } else {
      setNiceToHave((prev) => [...prev, skillObj])
    }
    setNewSkill('')
  }, [newSkill])

  const promoteExcluded = useCallback((skillName) => {
    setNiceToHave((prev) => [
      ...prev,
      { skill: skillName, confidence: 'medium', source: 'promoted', proficiency_expected: 'basic' },
    ])
  }, [])

  const addSuggested = useCallback((skillName) => {
    setNiceToHave((prev) => [
      ...prev,
      { skill: skillName, confidence: 'medium', source: 'suggested', proficiency_expected: 'basic' },
    ])
  }, [])

  const handleConfirm = useCallback(() => {
    onConfirm({
      required_skills: mustHave.map((s) => ({
        skill: typeof s === 'string' ? s : (s.skill || s),
        proficiency: s.proficiency_expected || 'intermediate',
      })),
      nice_to_have_skills: niceToHave.map((s) => ({
        skill: typeof s === 'string' ? s : (s.skill || s),
        proficiency: s.proficiency_expected || 'basic',
      })),
    })
  }, [mustHave, niceToHave, onConfirm])

  // ─── Template Handlers ──────────────────────────────────────────────
  const handleSaveTemplate = useCallback(async () => {
    const name = templateName.trim()
    if (!name) return
    try {
      setSaveLoading(true)
      await createSkillTemplate({
        name,
        required_skills: mustHave.map((s) => ({
          skill: typeof s === 'string' ? s : (s.skill || s),
          proficiency: s.proficiency_expected || 'intermediate',
        })),
        nice_to_have_skills: niceToHave.map((s) => ({
          skill: typeof s === 'string' ? s : (s.skill || s),
          proficiency: s.proficiency_expected || 'basic',
        })),
      })
      // Refresh templates list
      const templates = await getSkillTemplates()
      setSavedTemplates(templates || [])
      setSaveModalOpen(false)
      setTemplateName('')
      setToast({ message: `Template "${name}" saved`, type: 'success' })
    } catch (err) {
      setToast({ message: 'Failed to save template', type: 'error' })
    } finally {
      setSaveLoading(false)
    }
  }, [mustHave, niceToHave, templateName])

  const handleLoadTemplate = useCallback((template) => {
    const requiredSkills = (template.required_skills || []).map((s) => ({
      skill: typeof s === 'string' ? s : s.skill,
      confidence: s.confidence || 'high',
      source: s.source || 'template',
      proficiency_expected: s.proficiency || 'intermediate',
    }))
    const niceToHaveSkills = (template.nice_to_have_skills || []).map((s) => ({
      skill: typeof s === 'string' ? s : s.skill,
      confidence: s.confidence || 'medium',
      source: s.source || 'template',
      proficiency_expected: s.proficiency || 'basic',
    }))
    setMustHave(requiredSkills)
    setNiceToHave(niceToHaveSkills)
    setShowTemplateDropdown(false)
    setToast({ message: `Loaded "${template.name}"`, type: 'success' })
  }, [])

  const handleDeleteTemplate = useCallback(async (e, templateId, templateName) => {
    e.stopPropagation()
    try {
      await deleteSkillTemplate(templateId)
      setSavedTemplates((prev) => prev.filter((t) => t.id !== templateId))
      setToast({ message: `Deleted "${templateName}"`, type: 'success' })
    } catch {
      setToast({ message: 'Failed to delete template', type: 'error' })
    }
  }, [])

  // ─── Drag & Drop Handlers ─────────────────────────────────────────────
  const handleDragStart = (e, index, column) => {
    setDraggedIndex(index)
    setDraggedColumn(column)
    e.dataTransfer.effectAllowed = 'move'
    // Set a small delay so the original element stays visible briefly
    e.dataTransfer.setData('text/plain', JSON.stringify({ index, column }))
  }

  const handleDragEnd = () => {
    setDraggedIndex(null)
    setDraggedColumn(null)
    setDragOverIndex(null)
    setDragOverColumn(null)
    setIsDraggingOver({ must: false, nice: false })
    dragCounter.current = { must: 0, nice: 0 }
  }

  const handleDragOverColumn = (e, column) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    setIsDraggingOver((prev) => ({ ...prev, [column]: true }))
  }

  const handleDragLeaveColumn = (e, column) => {
    dragCounter.current[column] -= 1
    if (dragCounter.current[column] <= 0) {
      setIsDraggingOver((prev) => ({ ...prev, [column]: false }))
      if (dragOverColumn === column) {
        setDragOverIndex(null)
        setDragOverColumn(null)
      }
    }
  }

  const handleDragEnterColumn = (e, column) => {
    dragCounter.current[column] += 1
    setIsDraggingOver((prev) => ({ ...prev, [column]: true }))
  }

  const handleDropOnColumn = (e, targetColumn) => {
    e.preventDefault()
    dragCounter.current = { must: 0, nice: 0 }
    setIsDraggingOver({ must: false, nice: false })

    const payload = e.dataTransfer.getData('text/plain')
    if (!payload) return

    let src
    try {
      src = JSON.parse(payload)
    } catch {
      return
    }

    const { index: srcIndex, column: srcColumn } = src
    if (srcColumn === targetColumn) {
      // Reordering within same column
      if (dragOverIndex == null || dragOverIndex === srcIndex) {
        setDragOverIndex(null)
        setDragOverColumn(null)
        return
      }
      if (targetColumn === 'must') {
        const items = [...mustHave]
        const [moved] = items.splice(srcIndex, 1)
        items.splice(dragOverIndex, 0, moved)
        setMustHave(items)
      } else {
        const items = [...niceToHave]
        const [moved] = items.splice(srcIndex, 1)
        items.splice(dragOverIndex, 0, moved)
        setNiceToHave(items)
      }
    } else {
      // Moving between columns
      moveSkill(srcIndex, srcColumn)
    }

    setDragOverIndex(null)
    setDragOverColumn(null)
  }

  const handleDragOverItem = (e, index, column) => {
    e.preventDefault()
    e.stopPropagation()
    setDragOverIndex(index)
    setDragOverColumn(column)
  }

  // ─── Render ───────────────────────────────────────────────────────────
  const contextBadges = [
    { label: safeStr(data?.role_title), icon: Briefcase },
    { label: safeStr(data?.seniority), icon: Layers },
    { label: safeStr(data?.domain), icon: Sparkles },
    { label: safeStr(data?.job_function), icon: Lightbulb },
  ].filter((b) => b.label)

  const excludedSkills = (data?.excluded_skills || [])
  const suggestedAdditions = (data?.suggested_additions || [])

  return (
    <div className="w-full max-w-5xl mx-auto space-y-6 animate-fade-up">
      {/* Toast notification */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold shadow-lg transition-all animate-fade-up
          ${toast.type === 'success' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'}`}
        >
          {toast.type === 'success' ? <CheckCircle2 className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
          {toast.message}
        </div>
      )}

      {/* Save as Template Modal */}
      {saveModalOpen && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/30">
          <div className="bg-white rounded-2xl p-6 ring-1 ring-slate-200 shadow-xl w-full max-w-sm mx-4">
            <h3 className="text-sm font-bold text-slate-800 mb-3">Save as Template</h3>
            <input
              type="text"
              value={templateName}
              onChange={(e) => setTemplateName(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleSaveTemplate() }}
              placeholder="Template name..."
              className="w-full px-4 py-2.5 rounded-xl text-sm bg-slate-50 border border-slate-200
                text-slate-800 placeholder-slate-400
                focus:outline-none focus:ring-2 focus:ring-brand-300 focus:border-brand-300 transition-all"
              autoFocus
            />
            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => { setSaveModalOpen(false); setTemplateName('') }}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50 transition-all"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveTemplate}
                disabled={!templateName.trim() || saveLoading}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-40 disabled:cursor-not-allowed transition-all flex items-center gap-1.5"
              >
                {saveLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="bg-white rounded-2xl p-6 ring-1 ring-slate-200 shadow-brand-sm">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <h2 className="text-lg font-bold text-slate-800 mb-1">
              Review Skill Classification
            </h2>
            <p className="text-sm text-slate-500 mb-4">
              Verify which skills are must-haves vs. good-to-have before analysis.
            </p>
          </div>

          {/* Template controls */}
          <div className="flex items-center gap-2 shrink-0">
            {/* Load Template dropdown */}
            <div className="relative">
              <button
                onClick={() => setShowTemplateDropdown((v) => !v)}
                className="px-3 py-2 rounded-xl text-xs font-semibold bg-white text-slate-600 ring-1 ring-slate-200
                  hover:bg-slate-50 hover:text-slate-800 transition-all flex items-center gap-1.5"
              >
                <FolderOpen className="w-3.5 h-3.5" />
                Load Template
              </button>
              {showTemplateDropdown && (
                <div className="absolute right-0 top-full mt-1 w-64 bg-white rounded-xl ring-1 ring-slate-200 shadow-lg z-30 max-h-60 overflow-y-auto">
                  {savedTemplates.length === 0 ? (
                    <div className="px-4 py-3 text-xs text-slate-400 text-center">No saved templates</div>
                  ) : (
                    savedTemplates.map((t) => (
                      <div
                        key={t.id}
                        onClick={() => handleLoadTemplate(t)}
                        className="flex items-center justify-between px-3 py-2 hover:bg-slate-50 cursor-pointer transition-colors group"
                      >
                        <span className="text-sm text-slate-700 truncate flex-1">{t.name}</span>
                        <button
                          onClick={(e) => handleDeleteTemplate(e, t.id, t.name)}
                          className="p-1 rounded text-slate-300 hover:text-red-500 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-all"
                          title="Delete template"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>

            {/* Save Classification button */}
            <button
              onClick={() => setSaveModalOpen(true)}
              className="px-3 py-2 rounded-xl text-xs font-semibold bg-brand-600 text-white
                hover:bg-brand-700 transition-all flex items-center gap-1.5"
            >
              <Save className="w-3.5 h-3.5" />
              Save Classification
            </button>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          {contextBadges.map(({ label, icon: Icon }, i) => (
            <span
              key={i}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-brand-50 text-brand-700 ring-1 ring-brand-100"
            >
              <Icon className="w-3.5 h-3.5" />
              {label}
            </span>
          ))}
        </div>
      </div>

      {/* JD Quality Card */}
      {data?.jd_quality && (
        <div className="bg-white rounded-2xl p-5 ring-1 ring-slate-200 shadow-brand-sm">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-bold text-slate-700">JD Quality Score</h4>
            <div className="flex items-center gap-3">
              <span className="text-2xl font-bold text-brand-700">{data.jd_quality.grade}</span>
              <span className="text-sm text-gray-500">{data.jd_quality.overall_score}/100</span>
            </div>
          </div>
          <div className="space-y-2 mb-3">
            {Object.entries(data.jd_quality.dimensions || {}).map(([key, dim]) => (
              <div key={key} className="flex items-center gap-3">
                <span className="text-xs text-slate-600 w-32 shrink-0 capitalize">{key.replace(/_/g, ' ')}</span>
                <div className="flex-1 bg-gray-200 rounded h-2">
                  <div
                    className="bg-indigo-500 h-2 rounded transition-all"
                    style={{ width: `${(dim.score / dim.max) * 100}%` }}
                  />
                </div>
                <span className="text-xs text-slate-500 w-10 text-right">{dim.score}/{dim.max}</span>
              </div>
            ))}
          </div>
          {data.jd_quality.improvement_tips && data.jd_quality.improvement_tips.length > 0 && (
            <details className="text-sm">
              <summary className="cursor-pointer text-slate-600 hover:text-slate-800 font-medium">
                Improvement Tips ({data.jd_quality.improvement_tips.length})
              </summary>
              <ul className="mt-2 space-y-1 pl-4 list-disc text-slate-600 text-xs">
                {data.jd_quality.improvement_tips.map((tip, i) => (
                  <li key={i}>{tip}</li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}

      {/* Market Summary Banner */}
      {data?.market_summary && !data.market_summary.error && (
        <div className="flex flex-wrap items-center gap-4 text-sm bg-blue-50 text-blue-800 px-4 py-2.5 rounded-xl ring-1 ring-blue-100">
          <span className="inline-flex items-center gap-1">
            <Flame className="w-3.5 h-3.5 text-orange-500" />
            <span className="font-medium">{data.market_summary.hot_skills_count}</span> hot skills
          </span>
          <span className="inline-flex items-center gap-1">
            <TrendingUp className="w-3.5 h-3.5 text-green-600" />
            <span className="font-medium">{data.market_summary.in_demand_count}</span> in-demand
          </span>
          <span>
            Market alignment: <strong>{data.market_summary.market_alignment}</strong>
          </span>
        </div>
      )}

      {/* Team Context Banner */}
      {teamContext && (teamContext.team_has?.length > 0 || teamContext.team_gaps?.length > 0) && (
        <div className="bg-white rounded-2xl p-5 ring-1 ring-slate-200 shadow-brand-sm space-y-3">
          <div className="flex items-center gap-2">
            <Users className="w-4 h-4 text-brand-500" />
            <h4 className="text-sm font-bold text-slate-700 uppercase tracking-wide">Team Context</h4>
          </div>

          {teamContext.team_has?.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
                <span className="text-xs font-semibold text-green-700 uppercase tracking-wide">Team has</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {teamContext.team_has.map((skill, i) => (
                  <span
                    key={`team-has-${i}`}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold
                      bg-green-50 text-green-700 ring-1 ring-green-200"
                  >
                    {safeStr(skill)}
                  </span>
                ))}
              </div>
            </div>
          )}

          {teamContext.team_gaps?.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                <span className="text-xs font-semibold text-amber-700 uppercase tracking-wide">Team gaps</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {teamContext.team_gaps.map((skill, i) => (
                  <span
                    key={`team-gap-${i}`}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold
                      bg-amber-50 text-amber-700 ring-1 ring-amber-200"
                  >
                    {safeStr(skill)}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Two-column layout */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Must-Have Column */}
        <div
          className={`bg-white rounded-2xl p-5 ring-1 ring-slate-200 shadow-brand-sm transition-all duration-200
            ${isDraggingOver.must && draggedColumn !== 'must' ? 'ring-2 ring-brand-400 bg-brand-50/50' : ''}
          `}
          onDragOver={(e) => handleDragOverColumn(e, 'must')}
          onDragEnter={(e) => handleDragEnterColumn(e, 'must')}
          onDragLeave={(e) => handleDragLeaveColumn(e, 'must')}
          onDrop={(e) => handleDropOnColumn(e, 'must')}
        >
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center">
              <h3 className="text-sm font-bold text-slate-700 uppercase tracking-wide">
                Must-Have Skills
              </h3>
              <CountBadge count={mustHave.length} variant="must" />
            </div>
          </div>

          <div className="space-y-2 min-h-[120px]">
            {mustHave.length === 0 ? (
              <div className="text-center py-8 text-slate-400 text-sm">
                Drop skills here or add below
              </div>
            ) : (
              mustHave.map((skill, i) => (
                <SkillPill
                  key={`must-${skill.skill}-${i}`}
                  skill={skill}
                  index={i}
                  column="must"
                  onMove={moveSkill}
                  onRemove={removeSkill}
                  onProficiencyChange={updateProficiency}
                  onDragStart={handleDragStart}
                  onDragEnd={handleDragEnd}
                  isDragging={draggedColumn === 'must' && draggedIndex === i}
                  dragOverIndex={dragOverIndex}
                  dragOverColumn={dragOverColumn}
                  onDragOverItem={handleDragOverItem}
                />
              ))
            )}
          </div>
        </div>

        {/* Nice-to-Have Column */}
        <div
          className={`bg-white rounded-2xl p-5 ring-1 ring-slate-200 shadow-brand-sm transition-all duration-200
            ${isDraggingOver.nice && draggedColumn !== 'nice' ? 'ring-2 ring-blue-400 bg-blue-50/50' : ''}
          `}
          onDragOver={(e) => handleDragOverColumn(e, 'nice')}
          onDragEnter={(e) => handleDragEnterColumn(e, 'nice')}
          onDragLeave={(e) => handleDragLeaveColumn(e, 'nice')}
          onDrop={(e) => handleDropOnColumn(e, 'nice')}
        >
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center">
              <h3 className="text-sm font-bold text-slate-700 uppercase tracking-wide">
                Good-to-Have Skills
              </h3>
              <CountBadge count={niceToHave.length} variant="nice" />
            </div>
          </div>

          <div className="space-y-2 min-h-[120px]">
            {niceToHave.length === 0 ? (
              <div className="text-center py-8 text-slate-400 text-sm">
                Drop skills here or add below
              </div>
            ) : (
              niceToHave.map((skill, i) => (
                <SkillPill
                  key={`nice-${skill.skill}-${i}`}
                  skill={skill}
                  index={i}
                  column="nice"
                  onMove={moveSkill}
                  onRemove={removeSkill}
                  onProficiencyChange={updateProficiency}
                  onDragStart={handleDragStart}
                  onDragEnd={handleDragEnd}
                  isDragging={draggedColumn === 'nice' && draggedIndex === i}
                  dragOverIndex={dragOverIndex}
                  dragOverColumn={dragOverColumn}
                  onDragOverItem={handleDragOverItem}
                />
              ))
            )}
          </div>
        </div>
      </div>

      {/* Add Skill Input */}
      <div className="bg-white rounded-2xl p-5 ring-1 ring-slate-200 shadow-brand-sm">
        <label className="block text-xs font-bold text-slate-700 uppercase tracking-wide mb-3">
          Add Custom Skill
        </label>
        <div className="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            value={newSkill}
            onChange={(e) => setNewSkill(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault()
                addSkill('must')
              }
            }}
            placeholder="Enter a skill name..."
            className="flex-1 px-4 py-2.5 rounded-xl text-sm bg-slate-50 border border-slate-200
              text-slate-800 placeholder-slate-400
              focus:outline-none focus:ring-2 focus:ring-brand-300 focus:border-brand-300
              transition-all"
          />
          <div className="flex gap-2">
            <button
              onClick={() => addSkill('must')}
              disabled={!newSkill.trim()}
              className="px-4 py-2.5 rounded-xl text-xs font-semibold bg-brand-600 text-white
                hover:bg-brand-700 disabled:opacity-40 disabled:cursor-not-allowed
                transition-all flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" />
              Add to Must-Have
            </button>
            <button
              onClick={() => addSkill('nice')}
              disabled={!newSkill.trim()}
              className="px-4 py-2.5 rounded-xl text-xs font-semibold bg-blue-600 text-white
                hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed
                transition-all flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" />
              Add to Good-to-Have
            </button>
          </div>
        </div>
      </div>

      {/* Excluded Skills */}
      {excludedSkills.length > 0 && (
        <div className="bg-white rounded-2xl ring-1 ring-slate-200 shadow-brand-sm overflow-hidden">
          <button
            onClick={() => setShowExcluded((v) => !v)}
            className="w-full flex items-center justify-between p-5 hover:bg-slate-50 transition-colors"
          >
            <div className="flex items-center gap-2">
              <Ban className="w-4 h-4 text-slate-500" />
              <span className="text-sm font-bold text-slate-700 uppercase tracking-wide">
                Excluded Skills
              </span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-600">
                {excludedSkills.length}
              </span>
              <span className="text-xs text-slate-400 ml-1">
                (filtered soft skills)
              </span>
            </div>
            {showExcluded ? (
              <ChevronUp className="w-4 h-4 text-slate-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-slate-400" />
            )}
          </button>
          {showExcluded && (
            <div className="px-5 pb-5">
              <div className="flex flex-wrap gap-2">
                {excludedSkills.map((skill, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
                      bg-slate-100 text-slate-600 ring-1 ring-slate-200"
                  >
                    {safeStr(skill)}
                    <button
                      onClick={() => promoteExcluded(skill)}
                      className="p-0.5 rounded hover:bg-white hover:text-brand-600 transition-colors"
                      title="Promote to Good-to-Have"
                    >
                      <Plus className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Suggested Additions */}
      {suggestedAdditions.length > 0 && (
        <div className="bg-white rounded-2xl ring-1 ring-slate-200 shadow-brand-sm overflow-hidden">
          <button
            onClick={() => setShowSuggested((v) => !v)}
            className="w-full flex items-center justify-between p-5 hover:bg-slate-50 transition-colors"
          >
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-brand-500" />
              <span className="text-sm font-bold text-slate-700 uppercase tracking-wide">
                Suggested Additions
              </span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-brand-100 text-brand-700">
                {suggestedAdditions.length}
              </span>
              <span className="text-xs text-slate-400 ml-1">
                (domain-standard skills)
              </span>
            </div>
            {showSuggested ? (
              <ChevronUp className="w-4 h-4 text-slate-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-slate-400" />
            )}
          </button>
          {showSuggested && (
            <div className="px-5 pb-5">
              <div className="flex flex-wrap gap-2">
                {suggestedAdditions.map((skill, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
                      bg-brand-50 text-brand-700 ring-1 ring-brand-100"
                  >
                    {safeStr(skill)}
                    <button
                      onClick={() => addSuggested(skill)}
                      className="p-0.5 rounded hover:bg-white hover:text-brand-800 transition-colors"
                      title="Add to Good-to-Have"
                    >
                      <Plus className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Footer Actions */}
      <div className="flex flex-col sm:flex-row items-center justify-end gap-3 pt-2 pb-6">
        <button
          onClick={onSkip}
          disabled={loading}
          className="w-full sm:w-auto px-6 py-2.5 rounded-xl text-sm font-semibold
            bg-white text-slate-600 ring-1 ring-slate-200
            hover:bg-slate-50 hover:text-slate-800
            disabled:opacity-50 disabled:cursor-not-allowed
            transition-all"
        >
          Skip & Use Defaults
        </button>
        <button
          onClick={handleConfirm}
          disabled={loading}
          className="w-full sm:w-auto px-6 py-2.5 rounded-xl text-sm font-semibold
            bg-gradient-brand text-white shadow-brand
            hover:shadow-brand-lg hover:opacity-95
            disabled:opacity-50 disabled:cursor-not-allowed
            transition-all flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              Confirm & Analyze
            </>
          )}
        </button>
      </div>
    </div>
  )
}
