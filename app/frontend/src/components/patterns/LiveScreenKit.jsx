import { useState, useEffect, useMemo } from 'react'
import {
  ChevronLeft, ChevronRight, ClipboardList, User, Eye,
  MessageCircle, Loader2, MessageSquare, CheckCircle, Star, List, Mic2, Pencil, Smartphone, Copy, Mail,
} from 'lucide-react'
import { getEvaluations, saveEvaluation, saveOverallAssessment, generateDebrief, getScorecard } from '../../lib/api'
import { showSuccess, showError } from '../../lib/toast'
import { Button, Badge, Card, SegmentedControl } from '../ui'
import { LIVE_SCREEN, INTERVIEW } from '../../lib/uxLabels'
import {
  flattenQuestions,
  hasBriefingContent,
  getQuestionPriority,
  starsToRating,
  ratingToStars,
  getCategoriesFromKit,
  CATEGORY_META,
  sanitizeBriefingForDisplay,
  applyVoiceTone,
  buildGlanceBullets,
  formatHmDebriefText,
} from '../../lib/liveScreenKitUtils'

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      type="button"
      onClick={() => {
        navigator.clipboard.writeText(text).then(() => {
          setCopied(true)
          setTimeout(() => setCopied(false), 1500)
        })
      }}
      className="shrink-0 p-1.5 rounded-lg text-slate-400 hover:text-brand-600 hover:bg-brand-50 transition-colors"
      title="Copy question"
    >
      {copied ? <CheckCircle className="w-3.5 h-3.5 text-emerald-500" /> : <ClipboardList className="w-3.5 h-3.5" />}
    </button>
  )
}

function StarRating({ stars, onChange, saving }) {
  const [hovered, setHovered] = useState(0)
  const display = hovered || stars
  const color = (n) => {
    if (n >= 4) return 'text-emerald-500'
    if (n === 3) return 'text-amber-500'
    if (n >= 1) return 'text-red-400'
    return 'text-slate-200'
  }

  return (
    <div className="flex items-center gap-1.5">
      <span className="text-xs font-semibold text-slate-500">Rate answer:</span>
      <div className="flex items-center gap-0.5">
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            type="button"
            onMouseEnter={() => setHovered(n)}
            onMouseLeave={() => setHovered(0)}
            onClick={() => onChange(n)}
            className="p-0.5 transition-transform hover:scale-110"
          >
            <Star className={`w-4 h-4 ${n <= display ? color(display) : 'text-slate-200'}`} fill={n <= display ? 'currentColor' : 'none'} />
          </button>
        ))}
      </div>
      {saving && <Loader2 className="w-3 h-3 animate-spin text-slate-400" />}
    </div>
  )
}

const RECOMMENDATIONS = [
  { value: 'strong_hire', label: 'Strong Hire' },
  { value: 'lean_hire', label: 'Lean Hire' },
  { value: 'no_decision', label: 'No Decision' },
  { value: 'lean_no_hire', label: 'Lean No Hire' },
  { value: 'strong_no_hire', label: 'Strong No Hire' },
]

/**
 * Live Screen Kit — teleprompter-first call mode + post-call debrief.
 */
export default function LiveScreenKit({
  kit,
  isFallback = false,
  interviewKitStatus,
  resultId,
  analysisData = {},
  candidateName = '',
  roleTitle = '',
  fitScore = null,
  onDebriefGenerated,
}) {
  const [phase, setPhase] = useState('call')
  const [viewMode, setViewMode] = useState('teleprompter')
  const [voiceTone, setVoiceTone] = useState('conversational')
  const [questionIndex, setQuestionIndex] = useState(0)
  const [askedKeys, setAskedKeys] = useState({})
  const [questionEdits, setQuestionEdits] = useState({})
  const [editingKey, setEditingKey] = useState(null)
  const [evaluations, setEvaluations] = useState({})
  const [savingEval, setSavingEval] = useState({})
  const [evalErrors, setEvalErrors] = useState({})
  const [evalLoaded, setEvalLoaded] = useState(false)
  const [conversationSummary, setConversationSummary] = useState('')
  const [summaryError, setSummaryError] = useState('')
  const [submittingSummary, setSubmittingSummary] = useState(false)
  const [debriefGenerated, setDebriefGenerated] = useState(false)
  const [lastDebrief, setLastDebrief] = useState(null)
  const [recommendation, setRecommendation] = useState('')

  const missingSkills = analysisData.missing_skills || []
  const matchedSkills = analysisData.matched_skills || []
  const flatQuestions = useMemo(() => flattenQuestions(kit), [kit])
  const categories = useMemo(() => getCategoriesFromKit(kit), [kit])
  const totalQ = flatQuestions.length
  const current = flatQuestions[questionIndex]
  const briefing = useMemo(
    () => sanitizeBriefingForDisplay(kit?.candidate_briefing),
    [kit],
  )
  const glanceBullets = useMemo(
    () => buildGlanceBullets(briefing, flatQuestions),
    [briefing, flatQuestions],
  )
  const ratedCount = useMemo(
    () => Object.values(evaluations).filter((e) => e?.stars > 0).length,
    [evaluations],
  )

  const getQuestionText = (item) => {
    if (!item) return ''
    const key = `${item.category}_${item.index}`
    return questionEdits[key] || item.question.text
  }

  useEffect(() => {
    if (!resultId || evalLoaded) return
    getEvaluations(resultId)
      .then((data) => {
        const map = {}
        data.forEach((e) => {
          map[`${e.question_category}_${e.question_index}`] = {
            rating: e.rating,
            stars: ratingToStars(e.rating),
          }
        })
        setEvaluations(map)
      })
      .catch(() => {})
      .finally(() => setEvalLoaded(true))
  }, [resultId, evalLoaded])

  useEffect(() => {
    if (!resultId) return
    getScorecard(resultId)
      .then((data) => {
        if (data?.overall_assessment) setConversationSummary(data.overall_assessment)
      })
      .catch(() => {})
  }, [resultId])

  const handleStarRating = async (category, index, stars) => {
    const key = `${category}_${index}`
    const rating = starsToRating(stars)
    setEvaluations((prev) => ({ ...prev, [key]: { rating, stars } }))
    setSavingEval((prev) => ({ ...prev, [key]: true }))
    setEvalErrors((prev) => ({ ...prev, [key]: null }))
    try {
      await saveEvaluation(resultId, {
        question_category: category,
        question_index: index,
        rating,
        notes: null,
      })
    } catch {
      setEvalErrors((prev) => ({ ...prev, [key]: 'Failed to save rating' }))
      showError('Could not save answer rating. Check your connection and try again.')
    }
    setSavingEval((prev) => ({ ...prev, [key]: false }))
  }

  const saveQuestionEdit = (key, text) => {
    const trimmed = (text || '').trim()
    if (!trimmed) return
    setQuestionEdits((prev) => ({ ...prev, [key]: trimmed }))
    setEditingKey(null)
  }

  const handleEndCall = () => {
    if (ratedCount === 0) {
      const proceed = window.confirm(
        'No questions rated yet. End call anyway? Ratings help build the scorecard.',
      )
      if (!proceed) return
    }
    setPhase('debrief')
  }

  const copyHmSummary = (debriefData) => {
    const text = formatHmDebriefText({
      candidateName,
      roleTitle,
      fitScore,
      recommendation,
      summary: conversationSummary,
      debrief: debriefData?.debrief || lastDebrief?.debrief,
    })
    navigator.clipboard.writeText(text).then(() => {
      showSuccess('HM summary copied — paste into your ATS or email')
    }).catch(() => showError('Could not copy to clipboard'))
  }

  const emailHmSummary = (debriefData) => {
    const body = formatHmDebriefText({
      candidateName,
      roleTitle,
      fitScore,
      recommendation,
      summary: conversationSummary,
      debrief: debriefData?.debrief || lastDebrief?.debrief,
    })
    const subject = encodeURIComponent(`Screen summary: ${candidateName} — ${roleTitle || 'Role'}`)
    window.location.href = `mailto:?subject=${subject}&body=${encodeURIComponent(body)}`
  }

  const toggleAsked = (key) => {
    setAskedKeys((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  const handleSubmitSummary = async () => {
    setSummaryError('')
    if (!recommendation) {
      setSummaryError('Select a recommendation before submitting.')
      return
    }
    if (conversationSummary.trim().length < 20) {
      setSummaryError('Add a brief summary (at least 20 characters).')
      return
    }
    setSubmittingSummary(true)
    try {
      await saveOverallAssessment(resultId, { overall_assessment: conversationSummary })
      const debrief = await generateDebrief(resultId, conversationSummary, recommendation)
      setLastDebrief(debrief)
      setDebriefGenerated(true)
      onDebriefGenerated?.(debrief)
      showSuccess('Debrief saved to scorecard')
    } catch {
      setSummaryError('Failed to generate debrief. Please try again.')
    }
    setSubmittingSummary(false)
  }

  if (interviewKitStatus === 'pending' || interviewKitStatus === 'processing') {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 p-8">
        <Loader2 className="w-8 h-8 animate-spin text-brand-500" />
        <p className="text-sm font-medium text-slate-600">{LIVE_SCREEN.readinessLoading}</p>
        <p className="text-xs text-slate-400 text-center max-w-xs">{LIVE_SCREEN.readinessLoadingHint}</p>
      </div>
    )
  }

  if (!kit || totalQ === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 p-8 text-center">
        <ClipboardList className="w-10 h-10 text-slate-300" />
        <p className="text-sm font-medium text-slate-600">{LIVE_SCREEN.readinessEmpty}</p>
        <p className="text-xs text-slate-400 max-w-xs">{LIVE_SCREEN.readinessEmptyHint}</p>
      </div>
    )
  }

  if (phase === 'debrief') {
    return (
      <div className="flex flex-col h-full bg-surface">
        <div className="shrink-0 px-5 py-4 border-b border-brand-100 bg-white">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-brand-600" />
            <h2 className="font-bold text-brand-900">{LIVE_SCREEN.debriefTitle}</h2>
          </div>
          <p className="text-xs text-slate-500 mt-1">{LIVE_SCREEN.debriefHint}</p>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          <div>
            <span className="text-xs font-semibold text-slate-600 block mb-2">Recommendation</span>
            <div className="flex flex-wrap gap-2">
              {RECOMMENDATIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setRecommendation(opt.value)}
                  className={`px-3 py-1.5 rounded-full text-xs font-semibold ring-1 transition-all ${
                    recommendation === opt.value
                      ? 'bg-brand-600 text-white ring-brand-600'
                      : 'bg-white text-slate-600 ring-brand-200 hover:bg-brand-50'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <textarea
            value={conversationSummary}
            onChange={(e) => setConversationSummary(e.target.value)}
            placeholder="Brief summary of the call — key strengths, gaps, and your hiring lean."
            rows={6}
            className="w-full text-sm text-slate-700 bg-white ring-1 ring-brand-100 rounded-xl px-4 py-3 resize-none focus:outline-none focus:ring-2 focus:ring-brand-300"
          />

          {summaryError && <p className="text-xs text-red-600">{summaryError}</p>}
          {debriefGenerated && (
            <Card className="p-3 flex flex-col gap-3 bg-emerald-50 ring-emerald-200">
              <div className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
                <span className="text-sm text-emerald-800">Debrief saved to the scorecard.</span>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button variant="secondary" size="sm" className="gap-1.5" onClick={() => copyHmSummary(lastDebrief)}>
                  <Copy className="w-3.5 h-3.5" /> Copy for ATS
                </Button>
                <Button variant="secondary" size="sm" className="gap-1.5" onClick={() => emailHmSummary(lastDebrief)}>
                  <Mail className="w-3.5 h-3.5" /> Email HM
                </Button>
              </div>
            </Card>
          )}
        </div>

        <div className="shrink-0 p-5 border-t border-brand-100 bg-white flex items-center justify-between gap-3">
          <Button variant="ghost" size="sm" onClick={() => setPhase('call')}>
            Back to questions
          </Button>
          <Button loading={submittingSummary} onClick={handleSubmitSummary}>
            Submit & generate debrief
          </Button>
        </div>
      </div>
    )
  }

  const currentKey = current ? `${current.category}_${current.index}` : ''
  const currentEval = evaluations[currentKey]
  const priority = current ? getQuestionPriority(current.question.text, missingSkills, matchedSkills) : 'medium'

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="shrink-0 px-4 py-3 border-b border-brand-100 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Mic2 className="w-4 h-4 text-brand-600" />
            <span className="font-bold text-brand-900 text-sm">{INTERVIEW.liveScreenKit}</span>
            <Badge color="brand">{totalQ} questions</Badge>
            {isFallback && <Badge color="amber">{LIVE_SCREEN.fallbackBadge}</Badge>}
          </div>
          <SegmentedControl
            options={[
              { label: LIVE_SCREEN.teleprompter, value: 'teleprompter' },
              { label: 'Glance', value: 'glance' },
              { label: LIVE_SCREEN.checklist, value: 'list' },
            ]}
            value={viewMode}
            onChange={setViewMode}
          />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-slate-500 font-medium">Voice:</span>
          <SegmentedControl
            options={[
              { label: 'Conversational', value: 'conversational' },
              { label: 'Formal', value: 'formal' },
            ]}
            value={voiceTone}
            onChange={setVoiceTone}
          />
        </div>

        {hasBriefingContent(briefing) && (
          <Card className="p-3 bg-brand-50/50 ring-brand-100">
            <div className="flex items-center gap-2 mb-2">
              <User className="w-3.5 h-3.5 text-brand-600" />
              <span className="font-bold text-brand-800 text-xs">{LIVE_SCREEN.briefing}</span>
            </div>
            {briefing.profile_snapshot && (
              <p className="text-xs text-slate-600 mb-2 leading-relaxed">{briefing.profile_snapshot}</p>
            )}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
              {briefing.strengths_to_confirm?.length > 0 && (
                <ul className="space-y-0.5 text-slate-600">
                  {briefing.strengths_to_confirm.slice(0, 3).map((s, i) => (
                    <li key={i} className="text-emerald-700">+ {s}</li>
                  ))}
                </ul>
              )}
              {briefing.areas_to_probe?.length > 0 && (
                <ul className="space-y-0.5 text-slate-600">
                  {briefing.areas_to_probe.slice(0, 3).map((a, i) => (
                    <li key={i} className="text-amber-700">? {a}</li>
                  ))}
                </ul>
              )}
            </div>
          </Card>
        )}
      </div>

      {/* Call body */}
      <div className="flex-1 min-h-0 overflow-y-auto">
        {viewMode === 'glance' && (
          <div className="p-5 max-w-lg mx-auto space-y-3">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 uppercase tracking-wide">
              <Smartphone className="w-3.5 h-3.5" /> Glance mode — 5 bullets before you dial
            </div>
            <ol className="space-y-2">
              {glanceBullets.map((bullet, i) => (
                <li key={i} className="text-sm text-slate-700 p-3 rounded-xl bg-brand-50/60 ring-1 ring-brand-100">
                  {applyVoiceTone(bullet, voiceTone)}
                </li>
              ))}
            </ol>
          </div>
        )}

        {viewMode === 'teleprompter' && current && (
          <div className="p-5 flex flex-col gap-4 max-w-2xl mx-auto">
            <div className="flex items-center justify-between text-xs text-slate-500 font-medium">
              <span>{LIVE_SCREEN.questionProgress(questionIndex + 1, totalQ)}</span>
              <span className={CATEGORY_META[current.category]?.color}>{current.categoryLabel}</span>
            </div>

            <Card className="p-6 ring-brand-100 shadow-brand-sm">
              <div className="flex items-start justify-between gap-3">
                {editingKey === currentKey ? (
                  <textarea
                    className="flex-1 text-base font-semibold text-brand-900 leading-snug w-full min-h-[80px] p-2 rounded-lg ring-1 ring-brand-200"
                    defaultValue={getQuestionText(current)}
                    onBlur={(e) => saveQuestionEdit(currentKey, e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault()
                        saveQuestionEdit(currentKey, e.target.value)
                      }
                    }}
                    autoFocus
                  />
                ) : (
                  <p className="text-lg sm:text-xl font-semibold text-brand-900 leading-snug">
                    {applyVoiceTone(getQuestionText(current), voiceTone)}
                  </p>
                )}
                <div className="flex gap-1 shrink-0">
                  <button
                    type="button"
                    onClick={() => setEditingKey(currentKey)}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-brand-600 hover:bg-brand-50"
                    title="Edit question"
                  >
                    <Pencil className="w-3.5 h-3.5" />
                  </button>
                  <CopyButton text={getQuestionText(current)} />
                </div>
              </div>

              <div className="flex flex-wrap gap-2 mt-3">
                {priority === 'high' && <Badge color="red">Skill gap</Badge>}
                {priority === 'low' && <Badge color="green">Confirm strength</Badge>}
                <button
                  type="button"
                  onClick={() => toggleAsked(currentKey)}
                  className={`text-xs font-semibold px-2.5 py-1 rounded-full ring-1 transition-colors ${
                    askedKeys[currentKey]
                      ? 'bg-emerald-100 text-emerald-700 ring-emerald-200'
                      : 'bg-slate-50 text-slate-600 ring-slate-200 hover:bg-brand-50'
                  }`}
                >
                  {askedKeys[currentKey] ? 'Asked ✓' : LIVE_SCREEN.markedAsked}
                </button>
              </div>

              {current.question.what_to_listen_for?.length > 0 && (
                <div className="mt-4 p-3 rounded-xl bg-brand-50/80 ring-1 ring-brand-100">
                  <span className="text-xs font-bold text-brand-700 uppercase tracking-wide flex items-center gap-1">
                    <Eye className="w-3 h-3" /> {LIVE_SCREEN.listenFor}
                  </span>
                  <ul className="mt-2 space-y-1">
                    {current.question.what_to_listen_for.map((item, j) => (
                      <li key={j} className="text-sm text-slate-600 flex gap-2">
                        <span className="text-brand-400">•</span>{item}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {current.question.follow_ups?.length > 0 && (
                <div className="mt-3 p-3 rounded-xl bg-indigo-50/80 ring-1 ring-indigo-100">
                  <span className="text-xs font-bold text-indigo-700 uppercase tracking-wide flex items-center gap-1">
                    <MessageCircle className="w-3 h-3" /> {LIVE_SCREEN.followUps}
                  </span>
                  <ul className="mt-2 space-y-1">
                    {current.question.follow_ups.map((fu, j) => (
                      <li key={j} className="text-sm text-slate-600">{fu}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="mt-4 pt-4 border-t border-slate-100">
                <StarRating
                  stars={currentEval?.stars || 0}
                  onChange={(stars) => handleStarRating(current.category, current.index, stars)}
                  saving={savingEval[currentKey]}
                />
                {evalErrors[currentKey] && (
                  <p className="text-xs text-red-600 mt-1">{evalErrors[currentKey]}</p>
                )}
              </div>
            </Card>

            <div className="flex items-center justify-between gap-2">
              <Button
                variant="secondary"
                size="sm"
                disabled={questionIndex <= 0}
                onClick={() => setQuestionIndex((i) => Math.max(0, i - 1))}
              >
                <ChevronLeft className="w-4 h-4" /> Previous
              </Button>
              <Button
                variant="secondary"
                size="sm"
                disabled={questionIndex >= totalQ - 1}
                onClick={() => setQuestionIndex((i) => Math.min(totalQ - 1, i + 1))}
              >
                Next <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          </div>
        )}

        {viewMode === 'list' && (
          <div className="divide-y divide-brand-50">
            {categories.map((cat) => {
              const meta = CATEGORY_META[cat.key]
              return (
                <div key={cat.key}>
                  <div className={`sticky top-0 z-10 flex items-center gap-2 px-4 py-2 ${meta.bg} ring-1 ring-brand-50`}>
                    <span className={`w-2 h-2 rounded-full ${meta.dot}`} />
                    <span className={`text-xs font-bold uppercase ${meta.color}`}>{meta.label}</span>
                  </div>
                  <ol className="p-4 space-y-2">
                    {cat.questions.map((rawQ, idx) => {
                      const q = typeof rawQ === 'string' ? { text: rawQ } : rawQ
                      const key = `${cat.key}_${idx}`
                      const flatIdx = flatQuestions.findIndex(
                        (f) => f.category === cat.key && f.index === idx,
                      )
                      return (
                        <li key={key}>
                          <button
                            type="button"
                            onClick={() => {
                              setViewMode('teleprompter')
                              setQuestionIndex(flatIdx >= 0 ? flatIdx : 0)
                            }}
                            className={`w-full text-left p-3 rounded-xl ring-1 transition-colors ${
                              askedKeys[key] ? 'ring-emerald-200 bg-emerald-50/50' : 'ring-brand-100 hover:bg-brand-50/50'
                            }`}
                          >
                            <p className="text-sm text-slate-700">
                              {questionEdits[key] || applyVoiceTone(q.text, voiceTone)}
                            </p>
                          </button>
                        </li>
                      )
                    })}
                  </ol>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Footer — end call */}
      <div className="shrink-0 p-4 border-t border-brand-100 bg-white flex items-center justify-between gap-3">
        <span className="text-xs text-slate-400">
          {Object.keys(askedKeys).filter((k) => askedKeys[k]).length}/{totalQ} marked asked
          {ratedCount > 0 ? ` · ${ratedCount} rated` : ''}
        </span>
        <Button onClick={handleEndCall} className="gap-2">
          <List className="w-4 h-4" />
          {LIVE_SCREEN.endCall}
        </Button>
      </div>
    </div>
  )
}
