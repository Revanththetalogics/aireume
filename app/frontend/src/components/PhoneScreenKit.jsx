import { useState, useEffect } from 'react'
import {
  ChevronDown, ChevronUp, ClipboardList, User, Eye, MessageCircle, Loader2,
  MessageSquare, CheckCircle, Star,
} from 'lucide-react'
import { getEvaluations, saveEvaluation, saveOverallAssessment, generateDebrief, getScorecard } from '../lib/api'

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(text).then(() => {
          setCopied(true)
          setTimeout(() => setCopied(false), 1500)
        })
      }}
      className="shrink-0 p-1 rounded text-slate-300 hover:text-brand-500 transition-colors"
      title="Copy question"
    >
      {copied ? (
        <svg className="w-3.5 h-3.5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      ) : (
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
        </svg>
      )}
    </button>
  )
}

function normalizeQ(q) {
  if (typeof q === 'string') return { text: q, what_to_listen_for: [], follow_ups: [] }
  if (q && typeof q === 'object') return {
    text: q.text || String(q),
    what_to_listen_for: q.what_to_listen_for || [],
    follow_ups: q.follow_ups || [],
  }
  return { text: String(q), what_to_listen_for: [], follow_ups: [] }
}

function getQuestionPriority(qText, missingSkills, matchedSkills) {
  const lower = qText.toLowerCase()
  if (missingSkills.some(s => lower.includes(s.toLowerCase()))) return 'high'
  if (matchedSkills.some(s => lower.includes(s.toLowerCase()))) return 'low'
  return 'medium'
}

function extractSkillFromQuestion(qText, missingSkills, matchedSkills) {
  const lower = qText.toLowerCase()
  for (const skill of missingSkills || []) {
    if (lower.includes(skill.toLowerCase())) return skill
  }
  for (const skill of matchedSkills || []) {
    if (lower.includes(skill.toLowerCase())) return skill
  }
  return 'this skill'
}

// Map 5-star value → backend rating string
function starsToRating(stars) {
  if (stars >= 4) return 'strong'
  if (stars === 3) return 'adequate'
  return 'weak'
}

// Map backend rating string → star count (for display when loading saved evals)
function ratingToStars(rating) {
  if (rating === 'strong') return 5
  if (rating === 'adequate') return 3
  if (rating === 'weak') return 1
  return 0
}

// Star color based on count
function starColor(stars) {
  if (stars >= 4) return 'text-emerald-500'
  if (stars === 3) return 'text-amber-500'
  if (stars >= 1) return 'text-red-400'
  return 'text-slate-300'
}

function StarRating({ stars, onChange, saving }) {
  const [hovered, setHovered] = useState(0)
  const display = hovered || stars

  return (
    <div className="flex items-center gap-1.5">
      <span className="text-xs font-semibold text-slate-500 mr-0.5">Rate:</span>
      <div className="flex items-center gap-0.5">
        {[1, 2, 3, 4, 5].map(n => (
          <button
            key={n}
            type="button"
            onMouseEnter={() => setHovered(n)}
            onMouseLeave={() => setHovered(0)}
            onClick={() => onChange(n)}
            className="p-0.5 transition-transform hover:scale-110 focus:outline-none"
            title={n === 1 ? 'Weak' : n === 2 ? 'Weak' : n === 3 ? 'Adequate' : n === 4 ? 'Strong' : 'Strong'}
          >
            <Star
              className={`w-4 h-4 transition-colors ${
                n <= display
                  ? (hovered ? starColor(hovered) : starColor(stars))
                  : 'text-slate-200'
              }`}
              fill={n <= display ? 'currentColor' : 'none'}
            />
          </button>
        ))}
      </div>
      {stars > 0 && (
        <span className={`text-xs font-semibold ${starColor(stars)}`}>
          {stars >= 4 ? 'Strong' : stars === 3 ? 'Adequate' : 'Weak'}
        </span>
      )}
      {saving && <Loader2 className="w-3 h-3 animate-spin text-slate-400 ml-1" />}
    </div>
  )
}

const CATEGORY_META = {
  technical:            { label: 'Technical',            color: 'text-blue-700',   bg: 'bg-blue-50',   ring: 'ring-blue-200',   dot: 'bg-blue-500' },
  behavioral:           { label: 'Behavioral',           color: 'text-violet-700', bg: 'bg-violet-50', ring: 'ring-violet-200', dot: 'bg-violet-500' },
  culture_fit:          { label: 'Culture Fit',          color: 'text-teal-700',   bg: 'bg-teal-50',   ring: 'ring-teal-200',   dot: 'bg-teal-500' },
  experience_deep_dive: { label: 'Experience Deep-Dive', color: 'text-orange-700', bg: 'bg-orange-50', ring: 'ring-orange-200', dot: 'bg-orange-500' },
}

/**
 * PhoneScreenKit — redesigned Screen Kit for the split-view phone screen mode.
 *
 * Layout: flat scrollable list of all questions grouped by category with dividers.
 * Rating: 5-star inline per question, mapped to strong/adequate/weak on save.
 *
 * Props:
 *   interview_questions  — result.analysis_result?.interview_questions or result.interview_questions
 *   resultId             — for loading/saving evaluations
 *   analysisData         — { missing_skills: string[], matched_skills: string[] }
 *   onDebriefGenerated   — optional callback(debrief) after successful debrief generation
 */
export default function PhoneScreenKit({ interview_questions, resultId, analysisData, onDebriefGenerated }) {
  const [expandedGuidance, setExpandedGuidance] = useState({})
  const [evaluations, setEvaluations] = useState({})    // key: `${category}_${index}` → { rating, notes, stars }
  const [savingEval, setSavingEval] = useState({})
  const [evalLoaded, setEvalLoaded] = useState(false)
  const [conversationSummary, setConversationSummary] = useState('')
  const [summaryError, setSummaryError] = useState('')
  const [submittingSummary, setSubmittingSummary] = useState(false)
  const [debriefGenerated, setDebriefGenerated] = useState(false)
  const [recommendation, setRecommendation] = useState('')

  const CATEGORIES = [
    { key: 'technical',            questions: interview_questions?.technical_questions            || [] },
    { key: 'behavioral',           questions: interview_questions?.behavioral_questions           || [] },
    { key: 'culture_fit',          questions: interview_questions?.culture_fit_questions          || [] },
    { key: 'experience_deep_dive', questions: interview_questions?.experience_deep_dive_questions || [] },
  ].filter(c => c.questions.length > 0)

  const totalQ = CATEGORIES.reduce((s, c) => s + c.questions.length, 0)

  // Load evaluations
  useEffect(() => {
    if (!resultId || evalLoaded) return
    const load = async () => {
      try {
        const data = await getEvaluations(resultId)
        const map = {}
        data.forEach(e => {
          map[`${e.question_category}_${e.question_index}`] = {
            rating: e.rating,
            notes: e.notes || '',
            stars: ratingToStars(e.rating),
          }
        })
        setEvaluations(map)
      } catch (err) {
        console.error('PhoneScreenKit: failed to load evaluations', err)
      }
      setEvalLoaded(true)
    }
    load()
  }, [resultId, evalLoaded])

  // Load existing overall assessment
  useEffect(() => {
    if (!resultId) return
    const load = async () => {
      try {
        const data = await getScorecard(resultId)
        if (data?.overall_assessment) setConversationSummary(data.overall_assessment)
      } catch (err) {
        console.error('PhoneScreenKit: failed to load overall assessment', err)
      }
    }
    load()
  }, [resultId])

  const handleStarRating = async (category, index, stars) => {
    const key = `${category}_${index}`
    const rating = starsToRating(stars)
    const current = evaluations[key] || {}
    setEvaluations(prev => ({ ...prev, [key]: { ...current, rating, stars } }))
    setSavingEval(prev => ({ ...prev, [key]: true }))
    try {
      await saveEvaluation(resultId, {
        question_category: category,
        question_index: index,
        rating,
        notes: current.notes || null,
      })
    } catch (err) {
      console.error('PhoneScreenKit: failed to save eval', err)
    }
    setSavingEval(prev => ({ ...prev, [key]: false }))
  }

  const toggleGuidance = (key) => {
    setExpandedGuidance(prev => ({ ...prev, [key]: !prev[key] }))
  }

  const handleSubmitSummary = async () => {
    setSummaryError('')
    if (conversationSummary.trim().length < 100) {
      setSummaryError('Summary must be at least 100 characters. Please provide more detail about the conversation.')
      return
    }
    const allSkills = [...(analysisData?.missing_skills || []), ...(analysisData?.matched_skills || [])]
    const summaryLower = conversationSummary.toLowerCase()
    const hasSkillMention = allSkills.some(skill => summaryLower.includes(skill.toLowerCase()))
    if (!hasSkillMention && allSkills.length > 0) {
      setSummaryError('Please mention at least one specific skill from the job requirements (e.g., ' + allSkills.slice(0, 3).join(', ') + ').')
      return
    }
    if (!recommendation) {
      setSummaryError('Please select your recommendation before submitting.')
      return
    }
    setSubmittingSummary(true)
    try {
      await saveOverallAssessment(resultId, { overall_assessment: conversationSummary })
      const debrief = await generateDebrief(resultId, conversationSummary, recommendation)
      setDebriefGenerated(true)
      if (onDebriefGenerated) onDebriefGenerated(debrief)
    } catch (err) {
      setSummaryError('Failed to generate debrief. Please try again.')
      console.error('Debrief generation failed:', err)
    }
    setSubmittingSummary(false)
  }

  if (!interview_questions) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-slate-400 gap-3 p-8">
        <ClipboardList className="w-10 h-10 opacity-30" />
        <p className="text-sm font-medium">No Screen Kit questions available for this candidate.</p>
      </div>
    )
  }

  const missingSkills = analysisData?.missing_skills || []
  const matchedSkills = analysisData?.matched_skills || []

  // Count rated questions
  const ratedCount = Object.values(evaluations).filter(e => e.stars > 0).length

  return (
    <div className="flex flex-col h-full">

      {/* ── Header ── */}
      <div className="shrink-0 px-5 pt-4 pb-3 border-b border-slate-100 bg-white">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ClipboardList className="w-4 h-4 text-brand-600" />
            <span className="font-bold text-brand-800 text-sm">Screen Kit</span>
            <span className="text-xs bg-brand-100 text-brand-700 px-2 py-0.5 rounded-full font-semibold">
              {totalQ} questions
            </span>
          </div>
          {ratedCount > 0 && (
            <span className="text-xs text-slate-400 font-medium">
              {ratedCount}/{totalQ} rated
            </span>
          )}
        </div>

        {/* Candidate Briefing */}
        {interview_questions?.candidate_briefing && (
          <div className="mt-3 p-3 bg-slate-50 rounded-xl ring-1 ring-slate-200">
            <div className="flex items-center gap-2 mb-2">
              <User className="w-3.5 h-3.5 text-brand-600" />
              <span className="font-bold text-brand-800 text-xs">Candidate Briefing</span>
            </div>
            {interview_questions.candidate_briefing.profile_snapshot && (
              <p className="text-xs text-slate-600 mb-2 leading-relaxed">
                {interview_questions.candidate_briefing.profile_snapshot}
              </p>
            )}
            <div className="grid grid-cols-2 gap-3">
              {interview_questions.candidate_briefing.strengths_to_confirm?.length > 0 && (
                <div>
                  <span className="text-[10px] font-semibold text-emerald-700 uppercase tracking-wide">Strengths to Confirm</span>
                  <ul className="mt-1 space-y-0.5">
                    {interview_questions.candidate_briefing.strengths_to_confirm.map((s, i) => (
                      <li key={i} className="flex items-start gap-1 text-xs text-slate-600">
                        <span className="text-emerald-500 mt-0.5 shrink-0">&#10003;</span>
                        {s}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {interview_questions.candidate_briefing.areas_to_probe?.length > 0 && (
                <div>
                  <span className="text-[10px] font-semibold text-amber-700 uppercase tracking-wide">Areas to Probe</span>
                  <ul className="mt-1 space-y-0.5">
                    {interview_questions.candidate_briefing.areas_to_probe.map((a, i) => (
                      <li key={i} className="flex items-start gap-1 text-xs text-slate-600">
                        <span className="text-amber-500 mt-0.5 shrink-0">&#9679;</span>
                        {a}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ── Flat scrollable question list ── */}
      <div className="flex-1 overflow-y-auto">
        {CATEGORIES.map((cat, catIdx) => {
          const meta = CATEGORY_META[cat.key]
          return (
            <div key={cat.key}>
              {/* Category divider */}
              <div className={`sticky top-0 z-10 flex items-center gap-2.5 px-5 py-2 ${meta.bg} border-b border-t ${catIdx === 0 ? 'border-t-0' : ''} border-slate-100`}>
                <span className={`w-2 h-2 rounded-full shrink-0 ${meta.dot}`} />
                <span className={`text-xs font-bold uppercase tracking-wide ${meta.color}`}>{meta.label}</span>
                <span className="text-xs text-slate-400 font-medium">· {cat.questions.length} questions</span>
              </div>

              {/* Questions in this category */}
              <ol className="px-5 py-3 space-y-3">
                {cat.questions.map((rawQ, originalIndex) => {
                  const q = normalizeQ(rawQ)
                  const priority = getQuestionPriority(q.text, missingSkills, matchedSkills)
                  const guidanceKey = `${cat.key}_${originalIndex}`
                  const evalKey = `${cat.key}_${originalIndex}`
                  const hasGuidance = q.what_to_listen_for.length > 0 || q.follow_ups.length > 0
                  const extractedSkill = extractSkillFromQuestion(q.text, missingSkills, matchedSkills)
                  const currentStars = evaluations[evalKey]?.stars || 0
                  const currentRating = evaluations[evalKey]?.rating

                  return (
                    <li
                      key={originalIndex}
                      className={`bg-white rounded-xl ring-1 shadow-sm transition-shadow hover:shadow-md ${
                        currentStars >= 4 ? 'ring-emerald-200' :
                        currentStars === 3 ? 'ring-amber-200' :
                        currentStars >= 1 ? 'ring-red-200' :
                        'ring-slate-100'
                      }`}
                    >
                      {/* Question header */}
                      <div className="p-4 pb-3">
                        <div className="flex items-start gap-3">
                          <span className={`mt-0.5 text-xs font-bold w-5 shrink-0 ${meta.color}`}>
                            {originalIndex + 1}.
                          </span>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm text-slate-700 leading-relaxed">{q.text}</p>
                            <div className="flex flex-wrap items-center gap-1.5 mt-2">
                              {priority === 'high' && (
                                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-50 text-red-600 ring-1 ring-red-100">
                                  Gap
                                </span>
                              )}
                              {priority === 'low' && (
                                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-green-50 text-green-600 ring-1 ring-green-100">
                                  Confirm
                                </span>
                              )}
                            </div>
                          </div>
                          <CopyButton text={q.text} />
                        </div>

                        {/* Guidance toggle */}
                        {hasGuidance && (
                          <div className="ml-8 mt-2">
                            <button
                              onClick={() => toggleGuidance(guidanceKey)}
                              className="text-xs font-semibold text-brand-500 hover:text-brand-700 flex items-center gap-1 transition-colors"
                            >
                              {expandedGuidance[guidanceKey] ? 'Hide guidance' : 'Show guidance'}
                              {expandedGuidance[guidanceKey]
                                ? <ChevronUp className="w-3 h-3" />
                                : <ChevronDown className="w-3 h-3" />}
                            </button>

                            {expandedGuidance[guidanceKey] && (
                              <div className="mt-2 space-y-2">
                                {q.what_to_listen_for.length > 0 && (
                                  <div className="p-2.5 bg-brand-50/60 rounded-lg">
                                    <span className="text-xs font-semibold text-brand-700 uppercase tracking-wide flex items-center gap-1">
                                      <Eye className="w-3 h-3" /> What to Listen For
                                    </span>
                                    <ul className="mt-1.5 space-y-1">
                                      {q.what_to_listen_for.map((item, j) => (
                                        <li key={j} className="text-xs text-slate-600 flex items-start gap-1.5">
                                          <span className="text-brand-400 mt-0.5 shrink-0">&#8226;</span>
                                          {item}
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                                {q.follow_ups.length > 0 && (
                                  <div className="p-2.5 bg-indigo-50/60 rounded-lg">
                                    <span className="text-xs font-semibold text-indigo-700 uppercase tracking-wide flex items-center gap-1">
                                      <MessageCircle className="w-3 h-3" /> Follow-Up Questions
                                    </span>
                                    <ul className="mt-1.5 space-y-1">
                                      {q.follow_ups.map((fu, j) => (
                                        <li key={j} className="text-xs text-slate-600 flex items-start gap-1.5">
                                          <span className="text-indigo-400 mt-0.5 shrink-0">&#8594;</span>
                                          {fu}
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Rating row */}
                      <div className="px-4 pb-3 pt-2 border-t border-slate-100">
                        <StarRating
                          stars={currentStars}
                          onChange={(stars) => handleStarRating(cat.key, originalIndex, stars)}
                          saving={savingEval[evalKey]}
                        />

                        {/* Adaptive follow-up prompt */}
                        {currentRating === 'weak' && (
                          <div className="mt-2.5 p-2.5 bg-amber-50 border border-amber-200 rounded-lg">
                            <p className="text-xs font-semibold text-amber-700 mb-1">&#128161; Understand their level:</p>
                            <p className="text-xs text-amber-600 italic">
                              &ldquo;What do you know about {extractedSkill}? How have you applied it in your work?&rdquo;
                            </p>
                          </div>
                        )}
                        {currentRating === 'adequate' && (
                          <div className="mt-2.5 p-2.5 bg-blue-50 border border-blue-200 rounded-lg">
                            <p className="text-xs font-semibold text-blue-700 mb-1">&#128161; Dig deeper to decide:</p>
                            <p className="text-xs text-blue-600 italic">
                              &ldquo;Can you elaborate on your experience with {extractedSkill}? Tell me about a complex scenario where you used it.&rdquo;
                            </p>
                          </div>
                        )}
                      </div>
                    </li>
                  )
                })}
              </ol>
            </div>
          )
        })}
      </div>

      {/* ── Conversation Summary ── */}
      <div className="shrink-0 border-t border-slate-200 px-5 pt-4 pb-5 bg-slate-50">
        <div className="flex items-center gap-2 mb-1">
          <MessageSquare className="w-4 h-4 text-brand-600" />
          <span className="font-bold text-brand-800 text-sm">Conversation Summary</span>
        </div>
        <p className="text-xs text-slate-500 mb-3">
          After your call, summarize why this candidate is or isn&apos;t suitable for this role.
        </p>

        {/* Recommendation chips */}
        <div className="mb-3">
          <span className="text-xs font-semibold text-slate-600 block mb-2">Your Recommendation</span>
          <div className="flex flex-wrap gap-2">
            {[
              { value: 'strong_hire',    label: 'Strong Hire',    selected: 'bg-emerald-600 text-white ring-emerald-600',  idle: 'ring-emerald-300' },
              { value: 'lean_hire',      label: 'Lean Hire',      selected: 'bg-teal-600 text-white ring-teal-600',        idle: 'ring-teal-300' },
              { value: 'no_decision',    label: 'No Decision',    selected: 'bg-slate-500 text-white ring-slate-500',      idle: 'ring-slate-300' },
              { value: 'lean_no_hire',   label: 'Lean No Hire',   selected: 'bg-orange-500 text-white ring-orange-500',    idle: 'ring-orange-300' },
              { value: 'strong_no_hire', label: 'Strong No Hire', selected: 'bg-red-600 text-white ring-red-600',          idle: 'ring-red-300' },
            ].map(opt => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setRecommendation(opt.value)}
                className={`px-3 py-1.5 rounded-full text-xs font-semibold ring-1 transition-all ${
                  recommendation === opt.value
                    ? opt.selected
                    : `bg-white text-slate-600 ${opt.idle} hover:bg-slate-50`
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
          placeholder="Summarize your conversation — why is this candidate suitable or not for this role? Mention specific skills, strengths, and gaps you observed during the call."
          rows={4}
          className="w-full text-sm text-slate-700 bg-white border border-slate-200 rounded-lg px-4 py-3 resize-none focus:outline-none focus:ring-2 focus:ring-brand-300 focus:border-brand-300 placeholder:text-slate-400"
        />

        {summaryError && (
          <p className="mt-2 text-xs text-red-600">{summaryError}</p>
        )}
        {debriefGenerated && (
          <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded-lg flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-green-600 shrink-0" />
            <span className="text-sm text-green-700 font-medium">Debrief generated. View it in the Recruiter Scorecard below.</span>
          </div>
        )}
        <div className="flex items-center justify-between mt-3">
          <span className="text-xs text-slate-400">{conversationSummary.length} / 100 min</span>
          <button
            onClick={handleSubmitSummary}
            disabled={submittingSummary}
            className="px-4 py-2 bg-brand-600 text-white text-sm font-semibold rounded-lg hover:bg-brand-700 disabled:opacity-50 transition-colors"
          >
            {submittingSummary ? 'Generating Debrief…' : 'Submit & Generate Debrief'}
          </button>
        </div>
      </div>
    </div>
  )
}
