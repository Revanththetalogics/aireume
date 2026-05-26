import { useState, useEffect } from 'react'
import {
  ChevronDown, ChevronUp, ClipboardList, User, Eye, MessageCircle, Loader2,
  MessageSquare, CheckCircle,
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

function sortQuestionsWithPriority(questions, analysisData) {
  const missing = analysisData?.missing_skills || []
  const matched = analysisData?.matched_skills || []
  return questions
    .map((rawQ, originalIndex) => {
      const q = normalizeQ(rawQ)
      const priority = getQuestionPriority(q.text, missing, matched)
      return { rawQ, q, originalIndex, priority }
    })
    .sort((a, b) => {
      const order = { high: 0, medium: 1, low: 2 }
      return order[a.priority] - order[b.priority]
    })
}

/**
 * PhoneScreenKit — standalone Screen Kit panel for the split-view phone screen mode.
 *
 * Props:
 *   interview_questions  — result.analysis_result?.interview_questions or result.interview_questions
 *   resultId             — for loading/saving evaluations
 *   analysisData         — { missing_skills: string[], matched_skills: string[] }
 *   onDebriefGenerated   — optional callback(debrief) after successful debrief generation
 */
export default function PhoneScreenKit({ interview_questions, resultId, analysisData, onDebriefGenerated }) {
  const [activeQTab, setActiveQTab] = useState('technical')
  const [expandedGuidance, setExpandedGuidance] = useState({})
  const [evaluations, setEvaluations] = useState({})
  const [savingEval, setSavingEval] = useState({})
  const [evalLoaded, setEvalLoaded] = useState(false)
  const [conversationSummary, setConversationSummary] = useState('')
  const [summaryError, setSummaryError] = useState('')
  const [submittingSummary, setSubmittingSummary] = useState(false)
  const [debriefGenerated, setDebriefGenerated] = useState(false)

  const QTABS = [
    { key: 'technical',           label: 'Technical',           questions: interview_questions?.technical_questions            || [] },
    { key: 'behavioral',          label: 'Behavioral',          questions: interview_questions?.behavioral_questions           || [] },
    { key: 'culture_fit',         label: 'Culture Fit',         questions: interview_questions?.culture_fit_questions          || [] },
    { key: 'experience_deep_dive',label: 'Experience Deep-Dive',questions: interview_questions?.experience_deep_dive_questions || [] },
  ]

  const activeTabs = QTABS.filter(t => t.questions.length > 0)
  const totalQ = activeTabs.reduce((s, t) => s + t.questions.length, 0)

  // Pick the first available tab on mount / when data loads
  useEffect(() => {
    if (activeTabs.length > 0 && !activeTabs.find(t => t.key === activeQTab)) {
      setActiveQTab(activeTabs[0].key)
    }
  }, [interview_questions])

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
        if (data?.overall_assessment) {
          setConversationSummary(data.overall_assessment)
        }
      } catch (err) {
        console.error('PhoneScreenKit: failed to load overall assessment', err)
      }
    }
    load()
  }, [resultId])

  const handleSaveEval = async (category, index, field, value) => {
    const key = `${category}_${index}`
    const current = evaluations[key] || {}
    const updated = { ...current, [field]: value }
    setEvaluations(prev => ({ ...prev, [key]: updated }))
    setSavingEval(prev => ({ ...prev, [key]: true }))
    try {
      await saveEvaluation(resultId, {
        question_category: category,
        question_index: index,
        rating: updated.rating || null,
        notes: updated.notes || null,
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

    // Validation 1: minimum length
    if (conversationSummary.trim().length < 100) {
      setSummaryError('Summary must be at least 100 characters. Please provide more detail about the conversation.')
      return
    }

    // Validation 2: must mention at least one skill (from analysisData)
    const allSkills = [...(analysisData?.missing_skills || []), ...(analysisData?.matched_skills || [])]
    const summaryLower = conversationSummary.toLowerCase()
    const hasSkillMention = allSkills.some(skill => summaryLower.includes(skill.toLowerCase()))
    if (!hasSkillMention && allSkills.length > 0) {
      setSummaryError('Please mention at least one specific skill from the job requirements (e.g., ' + allSkills.slice(0, 3).join(', ') + ').')
      return
    }

    // Validation 3: must contain directional indicator
    const directionalWords = ['strong', 'weak', 'suitable', 'not suitable', 'recommend', 'concern', 'gap', 'proficient', 'lacks', 'excellent', 'poor', 'confident', 'hesitant', 'advance', 'reject', 'hold']
    const hasDirection = directionalWords.some(word => summaryLower.includes(word))
    if (!hasDirection) {
      setSummaryError('Please include your recommendation direction (e.g., mention if candidate is strong/weak, if you recommend advancing or have concerns).')
      return
    }

    // All validations passed — submit
    setSubmittingSummary(true)
    try {
      // First save the overall assessment
      await saveOverallAssessment(resultId, { overall_assessment: conversationSummary })
      // Then generate debrief
      const debrief = await generateDebrief(resultId, conversationSummary)
      setDebriefGenerated(true)
      // Notify parent of successful debrief generation (optional callback)
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

  return (
    <div className="flex flex-col h-full">
      {/* Header row */}
      <div className="shrink-0 px-4 pt-4 pb-3 border-b border-slate-100">
        <div className="flex items-center gap-2 mb-1">
          <ClipboardList className="w-4 h-4 text-brand-600" />
          <span className="font-bold text-brand-800 text-sm">Screen Kit</span>
          <span className="text-xs bg-brand-100 text-brand-700 px-2 py-0.5 rounded-full font-semibold">
            {totalQ} questions
          </span>
        </div>

        {/* Candidate Briefing */}
        {interview_questions?.candidate_briefing && (
          <div className="mt-3 p-3 bg-gradient-to-r from-brand-50 to-indigo-50 rounded-xl ring-1 ring-brand-200">
            <div className="flex items-center gap-2 mb-2">
              <User className="w-3.5 h-3.5 text-brand-600" />
              <span className="font-bold text-brand-800 text-xs">Candidate Briefing</span>
            </div>
            {interview_questions.candidate_briefing.profile_snapshot && (
              <p className="text-xs text-slate-700 mb-2 leading-relaxed">
                {interview_questions.candidate_briefing.profile_snapshot}
              </p>
            )}
            <div className="grid grid-cols-2 gap-2">
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

        {/* Question Tabs */}
        <div className="flex gap-1.5 mt-3 flex-wrap">
          {activeTabs.map(t => (
            <button
              key={t.key}
              onClick={() => setActiveQTab(t.key)}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
                activeQTab === t.key
                  ? 'bg-brand-600 text-white shadow-brand-sm'
                  : 'bg-white text-slate-600 ring-1 ring-brand-200 hover:bg-brand-50 hover:text-brand-700'
              }`}
            >
              {t.label} ({t.questions.length})
            </button>
          ))}
        </div>
      </div>

      {/* Question list — scrollable */}
      <div className="flex-1 overflow-y-auto px-4 py-3">
        {QTABS.filter(t => t.key === activeQTab).map(t => {
          const sorted = sortQuestionsWithPriority(t.questions, analysisData)
          return (
            <ol key={t.key} className="space-y-3">
              {sorted.map(({ rawQ, q, originalIndex, priority }) => {
                const guidanceKey = `${t.key}_${originalIndex}`
                const hasGuidance = q.what_to_listen_for.length > 0 || q.follow_ups.length > 0
                const evalKey = `${t.key}_${originalIndex}`
                const extractedSkill = extractSkillFromQuestion(q.text, missingSkills, matchedSkills)

                return (
                  <li key={originalIndex} className="p-3 bg-white rounded-xl ring-1 ring-brand-100 shadow-sm">
                    {/* Question text */}
                    <div className="flex items-start gap-3">
                      <span className="text-xs font-bold text-brand-400 mt-0.5 w-5 shrink-0">{originalIndex + 1}.</span>
                      <div className="flex-1">
                        <p className="text-sm text-slate-700 leading-relaxed">{q.text}</p>
                        <div className="flex gap-1.5 mt-1.5">
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
                              <div className="p-2 bg-brand-50/60 rounded-lg">
                                <span className="text-xs font-semibold text-brand-700 uppercase tracking-wide flex items-center gap-1">
                                  <Eye className="w-3 h-3" /> What to Listen For
                                </span>
                                <ul className="mt-1 space-y-0.5">
                                  {q.what_to_listen_for.map((item, j) => (
                                    <li key={j} className="text-xs text-slate-600 flex items-start gap-1.5">
                                      <span className="text-brand-400 mt-0.5">&#8226;</span>
                                      {item}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                            {q.follow_ups.length > 0 && (
                              <div className="p-2 bg-indigo-50/60 rounded-lg">
                                <span className="text-xs font-semibold text-indigo-700 uppercase tracking-wide flex items-center gap-1">
                                  <MessageCircle className="w-3 h-3" /> Follow-Up Questions
                                </span>
                                <ul className="mt-1 space-y-0.5">
                                  {q.follow_ups.map((fu, j) => (
                                    <li key={j} className="text-xs text-slate-600 flex items-start gap-1.5">
                                      <span className="text-indigo-400 mt-0.5">&#8594;</span>
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

                    {/* Evaluation row */}
                    <div className="ml-8 mt-3 pt-3 border-t border-slate-100">
                      <div className="flex items-center gap-2 mb-2 flex-wrap">
                        <span className="text-xs font-semibold text-slate-500">Rate:</span>
                        {[
                          { value: 'strong',   label: 'Strong',   activeClass: 'bg-emerald-100 text-emerald-700 ring-emerald-300' },
                          { value: 'adequate', label: 'Adequate', activeClass: 'bg-amber-100 text-amber-700 ring-amber-300' },
                          { value: 'weak',     label: 'Weak',     activeClass: 'bg-red-100 text-red-700 ring-red-300' },
                        ].map(opt => {
                          const isActive = evaluations[evalKey]?.rating === opt.value
                          return (
                            <button
                              key={opt.value}
                              onClick={() => handleSaveEval(t.key, originalIndex, 'rating', opt.value)}
                              className={`px-2.5 py-1 rounded-lg text-xs font-semibold ring-1 transition-all ${
                                isActive
                                  ? opt.activeClass
                                  : 'bg-white text-slate-400 ring-slate-200 hover:ring-slate-300'
                              }`}
                            >
                              {opt.label}
                            </button>
                          )
                        })}
                        {savingEval[evalKey] && (
                          <span className="flex items-center gap-1 text-xs text-slate-400 italic">
                            <Loader2 className="w-3 h-3 animate-spin" /> Saving…
                          </span>
                        )}
                      </div>

                      {/* Follow-up prompt based on rating */}
                      {evaluations[evalKey]?.rating === 'weak' && (
                        <div className="mt-2 p-2.5 bg-amber-50 border border-amber-200 rounded-lg">
                          <p className="text-xs font-semibold text-amber-700 mb-1">💡 Understand their level:</p>
                          <p className="text-xs text-amber-600 italic">
                            &ldquo;What do you know about {extractedSkill}? How have you applied it in your work?&rdquo;
                          </p>
                        </div>
                      )}
                      {evaluations[evalKey]?.rating === 'adequate' && (
                        <div className="mt-2 p-2.5 bg-blue-50 border border-blue-200 rounded-lg">
                          <p className="text-xs font-semibold text-blue-700 mb-1">💡 Dig deeper to decide:</p>
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
          )
        })}
      </div>

      {/* Conversation Summary Section */}
      <div className="shrink-0 border-t border-slate-200 p-4 bg-slate-50">
        <div className="flex items-center gap-2 mb-2">
          <MessageSquare className="w-4 h-4 text-brand-600" />
          <span className="font-bold text-brand-800 text-sm">Conversation Summary</span>
        </div>
        <p className="text-xs text-slate-500 mb-3">
          After your call, summarize why this candidate is or isn&apos;t suitable for this role.
        </p>
        <textarea
          value={conversationSummary}
          onChange={(e) => setConversationSummary(e.target.value)}
          placeholder="Summarize your conversation — why is this candidate suitable or not for this role? Mention specific skills, strengths, and gaps you observed during the call."
          rows={5}
          className="w-full text-sm text-slate-700 bg-white border border-slate-200 rounded-lg px-4 py-3 resize-none focus:outline-none focus:ring-2 focus:ring-brand-300 focus:border-brand-300 placeholder:text-slate-400"
        />
        {summaryError && (
          <p className="mt-2 text-xs text-red-600">{summaryError}</p>
        )}
        {debriefGenerated && (
          <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded-lg flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-green-600 shrink-0" />
            <span className="text-sm text-green-700 font-medium">Debrief generated successfully! View it in the Recruiter Scorecard below.</span>
          </div>
        )}
        <div className="flex items-center justify-between mt-3">
          <span className="text-xs text-slate-400">{conversationSummary.length} characters (min 100)</span>
          <button
            onClick={handleSubmitSummary}
            disabled={submittingSummary}
            className="px-4 py-2 bg-brand-600 text-white text-sm font-semibold rounded-lg hover:bg-brand-700 disabled:opacity-50 transition-colors"
          >
            {submittingSummary ? 'Generating Debrief...' : 'Submit & Generate Debrief'}
          </button>
        </div>
      </div>
    </div>
  )
}
