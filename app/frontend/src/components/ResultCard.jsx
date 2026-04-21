import {
  ThumbsUp, ThumbsDown, AlertTriangle, ChevronDown, ChevronUp,
  CheckCircle, XCircle, Target, TrendingUp, Shield, ClipboardList,
  Copy, Check, Mail, X, Loader2, Lightbulb, BookOpen, Compass, Cpu,
  Sparkles, Info, UserCheck,
} from 'lucide-react'
import { useState, useEffect, useRef } from 'react'
import SkillsRadar from './SkillsRadar'
import { generateEmail, getNarrative } from '../lib/api'

// ─── Small reusable components ────────────────────────────────────────────────

/** Coerce any value to a render-safe string. Objects become JSON; null/undefined → '' */
function safeStr(v) {
  if (v == null) return ''
  if (typeof v === 'string') return v
  if (typeof v === 'number' || typeof v === 'boolean') return String(v)
  try { return JSON.stringify(v) } catch { return String(v) }
}

function ScoreBar({ label, value, color }) {
  const barColor = {
    green:  'bg-green-500',
    blue:   'bg-brand-500',
    amber:  'bg-amber-500',
    purple: 'bg-brand-600',
    teal:   'bg-teal-500',
    rose:   'bg-rose-400',
  }[color] || 'bg-brand-400'

  return (
    <div>
      <div className="flex justify-between items-center mb-1.5">
        <span className="text-xs font-semibold text-slate-600">{label}</span>
        <span className="text-xs font-bold text-brand-700">{value ?? '—'}%</span>
      </div>
      <div className="w-full bg-brand-100 rounded-full h-2">
        <div
          className={`h-2 rounded-full transition-all duration-700 ${barColor}`}
          style={{ width: `${Math.max(0, Math.min(100, value ?? 0))}%` }}
        />
      </div>
    </div>
  )
}

function RiskBadge({ level }) {
  const styles = {
    Low:    'bg-green-100 text-green-700 ring-green-200',
    Medium: 'bg-amber-100 text-amber-700 ring-amber-200',
    High:   'bg-red-100 text-red-700 ring-red-200',
  }
  return (
    <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ring-1 ${styles[level] || styles.Medium}`}>
      {level} Risk
    </span>
  )
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1500) }}
      className="p-1.5 rounded-lg hover:bg-brand-50 transition-colors text-slate-400 hover:text-brand-600"
      title="Copy"
    >
      {copied ? <Check className="w-3.5 h-3.5 text-green-600" /> : <Copy className="w-3.5 h-3.5" />}
    </button>
  )
}

function CollapsibleSection({ title, icon: Icon, iconColor = 'text-brand-600', bgColor = 'bg-brand-50', children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="ring-1 ring-brand-100 rounded-2xl overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between p-4 hover:bg-brand-50/60 transition-colors"
      >
        <div className="flex items-center gap-2">
          <div className={`w-6 h-6 rounded-lg ${bgColor} flex items-center justify-center`}>
            <Icon className={`w-3.5 h-3.5 ${iconColor}`} />
          </div>
          <span className="font-bold text-brand-900 text-sm">{title}</span>
        </div>
        {open
          ? <ChevronUp className="w-4 h-4 text-brand-500" />
          : <ChevronDown className="w-4 h-4 text-brand-500" />}
      </button>
      {open && (
        <div className="px-4 pb-4 border-t border-brand-50 pt-3">
          {children}
        </div>
      )}
    </div>
  )
}

// ─── Email modal ──────────────────────────────────────────────────────────────

function EmailModal({ candidateId, resultId, onClose }) {
  const [type, setType]       = useState('shortlist')
  const [draft, setDraft]     = useState(null)
  const [loading, setLoading] = useState(false)
  const [copied, setCopied]   = useState(false)

  const EMAIL_TYPES = [
    { value: 'shortlist',      label: 'Shortlist' },
    { value: 'rejection',      label: 'Rejection' },
    { value: 'screening_call', label: 'Screening Call' },
  ]

  const handleGenerate = async () => {
    if (!candidateId) {
      setDraft({ subject: 'N/A', body: 'Save candidate first to generate personalized emails.' })
      return
    }
    setLoading(true)
    try {
      const result = await generateEmail(candidateId, type)
      setDraft(result)
    } catch {
      setDraft({ subject: 'Generation failed', body: 'Could not generate email. Please try again.' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white/95 backdrop-blur-xl rounded-3xl ring-1 ring-brand-100 shadow-brand-xl w-full max-w-lg card-animate">
        <div className="flex items-center justify-between p-5 border-b border-brand-50">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-brand-50 flex items-center justify-center">
              <Mail className="w-4 h-4 text-brand-600" />
            </div>
            <h3 className="font-bold text-brand-900">Generate Email</h3>
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-brand-50 rounded-xl transition-colors">
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>
        <div className="p-5 space-y-4">
          <div className="flex gap-2">
            {EMAIL_TYPES.map(t => (
              <button
                key={t.value}
                onClick={() => { setType(t.value); setDraft(null) }}
                className={`px-3 py-1.5 rounded-xl text-sm font-semibold transition-all ${
                  type === t.value
                    ? 'bg-brand-600 text-white shadow-brand-sm'
                    : 'bg-brand-50 text-slate-600 hover:bg-brand-100 hover:text-brand-700'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          {draft && (
            <div className="space-y-3">
              <div>
                <label className="text-xs font-bold text-slate-500 uppercase tracking-wide">Subject</label>
                <p className="text-sm font-semibold text-brand-900 mt-1">{draft.subject}</p>
              </div>
              <div>
                <label className="text-xs font-bold text-slate-500 uppercase tracking-wide">Body</label>
                <textarea
                  value={draft.body}
                  onChange={(e) => setDraft({ ...draft, body: e.target.value })}
                  rows={8}
                  className="w-full mt-1.5 px-3 py-2.5 text-sm ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 rounded-xl resize-none"
                />
              </div>
            </div>
          )}

          <div className="flex justify-between items-center pt-1">
            <button
              onClick={handleGenerate}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 btn-brand text-white text-sm font-bold rounded-xl disabled:opacity-60 shadow-brand-sm"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Mail className="w-4 h-4" />}
              {loading ? 'Generating...' : 'Generate'}
            </button>
            {draft && (
              <button
                onClick={() => { navigator.clipboard.writeText(`Subject: ${draft.subject}\n\n${draft.body}`); setCopied(true); setTimeout(() => setCopied(false), 1500) }}
                className="flex items-center gap-2 px-4 py-2 ring-1 ring-brand-200 text-brand-700 text-sm font-semibold rounded-xl hover:bg-brand-50 transition-colors"
              >
                {copied ? <Check className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4" />}
                {copied ? 'Copied!' : 'Copy Email'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Analysis source badge ────────────────────────────────────────────────────

function AnalysisSourceBadge({ narrativeReady, isPolling, analysisQuality, aiEnhanced }) {
  if (isPolling) {
    return (
      <div className="flex items-center gap-3 p-3 bg-brand-50 ring-1 ring-brand-200 rounded-2xl">
        <div className="w-4 h-4 rounded-full border-2 border-brand-300 border-t-brand-600 animate-spin shrink-0" />
        <p className="text-xs font-semibold text-brand-700 flex-1">
          AI analysis enhancing report…
        </p>
      </div>
    )
  }

  // Only show "AI Enhanced Report" badge for REAL LLM narratives (ai_enhanced === true)
  if (narrativeReady && aiEnhanced === true) {
    return (
      <div className="flex items-center gap-3 p-3 bg-green-50 ring-1 ring-green-200 rounded-2xl">
        <Sparkles className="w-4 h-4 text-green-600 shrink-0" />
        <p className="text-xs font-semibold text-green-700 flex-1">
          AI Enhanced Report
        </p>
        {analysisQuality && (
          <span className={`text-xs font-bold px-2 py-0.5 rounded-full ring-1 shrink-0 ${
            analysisQuality === 'high'   ? 'bg-green-100 text-green-700 ring-green-200' :
            analysisQuality === 'medium' ? 'bg-amber-100 text-amber-700 ring-amber-200' :
                                          'bg-red-100 text-red-700 ring-red-200'
          }`}>
            {analysisQuality} quality
          </span>
        )}
      </div>
    )
  }

  // Show "Analysis complete" for fallback narratives (ai_enhanced === false or missing)
  if (narrativeReady && aiEnhanced === false) {
    return (
      <div className="flex items-center gap-3 p-3 bg-slate-50 ring-1 ring-slate-200 rounded-2xl">
        <CheckCircle className="w-4 h-4 text-slate-600 shrink-0" />
        <p className="text-xs font-semibold text-slate-700 flex-1">
          Analysis complete
        </p>
      </div>
    )
  }

  return null
}

// ─── Pending banner (kept for isPending / null fit_score case) ────────────────

function PendingBanner() {
  return (
    <div className="flex items-center gap-3 p-4 bg-slate-50 ring-1 ring-slate-200 rounded-2xl">
      <AlertTriangle className="w-5 h-5 text-slate-400 shrink-0" />
      <div>
        <p className="text-sm font-semibold text-slate-600">Automated analysis unavailable</p>
        <p className="text-xs text-slate-400 mt-0.5">Manual review required — check Ollama service and retry.</p>
      </div>
    </div>
  )
}

// ─── Main ResultCard ──────────────────────────────────────────────────────────

export default function ResultCard({ result, defaultExpandEducation = false }) {
  const [showInterviewKit, setShowInterviewKit] = useState(false)
  const [showEmailModal, setShowEmailModal]     = useState(false)
  const [activeQTab, setActiveQTab]             = useState('technical')
  
  // Narrative polling state
  const [narrativeData, setNarrativeData]       = useState(null)
  const [narrativeError, setNarrativeError]     = useState(null)
  const [isPolling, setIsPolling]               = useState(false)
  const pollAttemptRef                          = useRef(0)
  const pollingTimeoutRef                       = useRef(null)

  const {
    fit_score, strengths, weaknesses, education_analysis,
    risk_signals, final_recommendation, score_breakdown,
    matched_skills, missing_skills, risk_level,
    interview_questions, result_id, candidate_id,
    explainability, adjacent_skills,
    skill_analysis, edu_timeline_analysis, jd_analysis,
    recommendation_rationale,
    narrative_pending, analysis_quality,
    fit_summary, concerns, score_rationales, risk_summary, skill_depth,
    analysis_id,
  } = result

  // Defensive fallback: use result_id if analysis_id is not available (for backward compatibility)
  const effectiveAnalysisId = analysis_id || result_id

  // Backward compatibility: use concerns if available, otherwise fall back to weaknesses
  const concernsList = concerns || weaknesses || []

  const isPending = final_recommendation === 'Pending' || fit_score === null || fit_score === undefined
  
  // Determine if narrative is ready (either from polling or already in result)
  const narrativeReady = narrativeData !== null || (narrative_pending === false && (strengths?.length > 0 || concerns?.length > 0))
  
  // Check if narrative is AI-enhanced (real LLM response vs fallback)
  // narrativeData comes from polling, result.narrative_json would be from initial result
  const aiEnhanced = narrativeData?.ai_enhanced ?? result?.ai_enhanced ?? null

  // Narrative polling effect with adaptive timing
  useEffect(() => {
    // Only start polling if narrative is pending and we have an effective analysis_id
    if (!narrative_pending || !effectiveAnalysisId) return
    
    setIsPolling(true)
    setNarrativeError(null)
    pollAttemptRef.current = 0
    
    const MAX_ATTEMPTS = 36 // ~2.25 min total: 15*2s + 21*5s = 30s + 105s
    
    const getPollDelay = (attempt) => {
      // First 15 attempts: 2s interval (covers first 30s for cloud models)
      // After 15 attempts: 5s interval (for slower local models)
      return attempt < 15 ? 2000 : 5000
    }
    
    const stopPolling = () => {
      setIsPolling(false)
      if (pollingTimeoutRef.current) {
        clearTimeout(pollingTimeoutRef.current)
        pollingTimeoutRef.current = null
      }
    }
    
    const scheduleNextPoll = () => {
      const delay = getPollDelay(pollAttemptRef.current)
      pollingTimeoutRef.current = setTimeout(poll, delay)
    }
    
    const poll = async () => {
      try {
        const response = await getNarrative(effectiveAnalysisId)
        
        if (response.status === 'ready' && response.narrative) {
          // Narrative is ready, stop polling and merge data
          setNarrativeData(response.narrative)
          stopPolling()
        } else if (response.status === 'failed') {
          // Narrative failed, use fallback data and show error
          setNarrativeData(response.narrative || {})
          setNarrativeError(response.error || 'AI enhancement failed')
          stopPolling()
        } else {
          // Still pending, increment attempts and schedule next poll
          pollAttemptRef.current += 1
          
          if (pollAttemptRef.current >= MAX_ATTEMPTS) {
            // Max attempts reached, stop polling
            stopPolling()
          } else {
            // Schedule next poll with adaptive delay
            scheduleNextPoll()
          }
        }
      } catch (err) {
        // On error, continue polling until max attempts
        console.debug('Narrative polling error:', err)
        pollAttemptRef.current += 1
        
        if (pollAttemptRef.current >= MAX_ATTEMPTS) {
          stopPolling()
        } else {
          scheduleNextPoll()
        }
      }
    }
    
    // Poll immediately, then schedule next with adaptive delay
    poll()
    
    // Cleanup on unmount
    return () => {
      if (pollingTimeoutRef.current) {
        clearTimeout(pollingTimeoutRef.current)
        pollingTimeoutRef.current = null
      }
    }
  }, [narrative_pending, effectiveAnalysisId])

  let badgeColor  = 'bg-amber-100 text-amber-800 ring-amber-200'
  let BadgeIcon   = Target
  if (final_recommendation === 'Shortlist') {
    badgeColor = 'bg-green-100 text-green-800 ring-green-200'
    BadgeIcon  = CheckCircle
  } else if (final_recommendation === 'Reject') {
    badgeColor = 'bg-red-100 text-red-800 ring-red-200'
    BadgeIcon  = XCircle
  } else if (isPending) {
    badgeColor = 'bg-slate-100 text-slate-600 ring-slate-200'
    BadgeIcon  = AlertTriangle
  }

  const QTABS = [
    { key: 'technical',   label: 'Technical',   questions: interview_questions?.technical_questions   || [] },
    { key: 'behavioral',  label: 'Behavioral',  questions: interview_questions?.behavioral_questions  || [] },
    { key: 'culture_fit', label: 'Culture Fit', questions: interview_questions?.culture_fit_questions || [] },
  ]
  
  // Merge narrative data with existing result data
  const mergedStrengths = narrativeData?.strengths || strengths || []
  const mergedConcerns = narrativeData?.concerns || narrativeData?.weaknesses || concerns || weaknesses || []

  return (
    <>
      <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6 md:p-8 space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h2 className="text-2xl font-bold text-brand-900 tracking-tight">Analysis Results</h2>
          <div className="flex items-center gap-2 flex-wrap">
            {risk_level && !isPending && <RiskBadge level={risk_level} />}
            <span className={`flex items-center gap-1.5 px-4 py-1.5 rounded-full text-sm font-bold ring-1 ${badgeColor}`}>
              <BadgeIcon className="w-4 h-4" />
              {safeStr(final_recommendation)}
            </span>
            <button
              onClick={() => setShowEmailModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl ring-1 ring-brand-200 text-sm text-brand-700 hover:bg-brand-50 transition-colors font-semibold"
              title="Generate email"
            >
              <Mail className="w-4 h-4" />
              <span className="hidden sm:inline">Email</span>
            </button>
          </div>
        </div>

        {/* Analysis source badge — shows polling state or AI enhanced status */}
        {!isPending && (
          <AnalysisSourceBadge
            narrativeReady={narrativeReady}
            isPolling={isPolling}
            analysisQuality={analysis_quality}
            aiEnhanced={aiEnhanced}
          />
        )}

        {/* Narrative error banner — shown when AI enhancement failed */}
        {narrativeError && (
          <div className="mt-2 flex items-center gap-2 rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 text-sm text-amber-800">
            <svg className="h-4 w-4 flex-shrink-0 text-amber-500" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.168 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 6a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 6zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
            </svg>
            <span>AI enhancement unavailable: {narrativeError}. Showing standard analysis.</span>
          </div>
        )}

        {/* Standard mode info banner — shown when ai_enhanced is false without error */}
        {narrativeData && !narrativeData.ai_enhanced && !narrativeError && (
          <div className="mt-2 flex items-center gap-2 rounded-lg bg-blue-50 border border-blue-200 px-3 py-2 text-sm text-blue-700">
            <svg className="h-4 w-4 flex-shrink-0 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z" clipRule="evenodd" />
            </svg>
            <span>AI analysis used standard mode.</span>
          </div>
        )}

        {/* Pending banner */}
        {isPending && <PendingBanner />}

        {/* Fit Summary Banner */}
        {fit_summary && fit_summary.trim() && (
          <div className="bg-gradient-to-r from-indigo-500 to-blue-600 rounded-2xl p-5 text-white shadow-lg">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-xl bg-white/20 flex items-center justify-center shrink-0">
                <UserCheck className="w-4 h-4 text-white" />
              </div>
              <div>
                <h3 className="text-sm font-bold uppercase tracking-wide text-indigo-100 mb-1">Executive Summary</h3>
                <p className="text-sm leading-relaxed text-white/95">{safeStr(fit_summary)}</p>
              </div>
            </div>
          </div>
        )}

        {/* Score Breakdown */}
        {score_breakdown && Object.keys(score_breakdown).length > 0 && !isPending && (
          <div className="bg-brand-50/60 rounded-2xl p-5 ring-1 ring-brand-100">
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp className="w-4 h-4 text-brand-500" />
              <h3 className="text-sm font-bold text-brand-800 uppercase tracking-wide">Score Breakdown</h3>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <ScoreBar label="Skill Match"   value={score_breakdown.skill_match ?? 0}      color="blue" />
              <ScoreBar label="Experience"    value={score_breakdown.experience_match ?? 0} color="green" />
              <ScoreBar label="Education"     value={score_breakdown.education ?? 0}        color="amber" />
              <ScoreBar label="Timeline"      value={score_breakdown.timeline ?? score_breakdown.stability ?? 0} color="purple" />
              {score_breakdown.architecture != null && (
                <ScoreBar label="Architecture" value={score_breakdown.architecture}          color="teal" />
              )}
              {score_breakdown.domain_fit != null && (
                <ScoreBar label="Domain Fit"   value={score_breakdown.domain_fit}            color="rose" />
              )}
            </div>
            {recommendation_rationale && (
              <p className="text-xs text-slate-500 mt-3 italic">{safeStr(recommendation_rationale)}</p>
            )}
            {risk_summary?.seniority_alignment && (
              <div className="mt-3 pt-3 border-t border-brand-100 flex items-center gap-2">
                <Info className="w-3.5 h-3.5 text-brand-500" />
                <span className="text-xs font-semibold text-brand-700">Seniority Alignment:</span>
                <span className="text-xs text-slate-600">{safeStr(risk_summary.seniority_alignment)}</span>
              </div>
            )}
          </div>
        )}

        {/* Skills Intel */}
        {((matched_skills?.length > 0) || (missing_skills?.length > 0)) && (
          <div className="grid grid-cols-2 gap-4">
            {matched_skills?.length > 0 && (
              <div className="bg-green-50 rounded-2xl p-4 ring-1 ring-green-100 border-l-4 border-green-500">
                <div className="flex items-center gap-1.5 mb-2.5">
                  <CheckCircle className="w-4 h-4 text-green-600" />
                  <span className="text-xs font-bold text-green-700 uppercase tracking-wide">Matched</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {matched_skills.slice(0, 12).map((s, i) => (
                    <span key={i} className="px-2 py-0.5 bg-green-100 text-green-800 text-xs rounded-lg font-semibold inline-flex items-center gap-1">
                      {safeStr(s)}
                      {skill_depth && skill_depth[safeStr(s)] && (
                        <span className="text-[10px] text-green-600 font-medium">({safeStr(skill_depth[safeStr(s)])}x)</span>
                      )}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {missing_skills?.length > 0 && (
              <div className="bg-red-50 rounded-2xl p-4 ring-1 ring-red-100 border-l-4 border-red-400">
                <div className="flex items-center gap-1.5 mb-2.5">
                  <XCircle className="w-4 h-4 text-red-600" />
                  <span className="text-xs font-bold text-red-700 uppercase tracking-wide">Missing</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {missing_skills.slice(0, 10).map((s, i) => (
                    <span key={i} className="px-2 py-0.5 bg-red-100 text-red-800 text-xs rounded-lg font-semibold">{safeStr(s)}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Adjacent skills */}
        {adjacent_skills?.length > 0 && (
          <div className="bg-blue-50 rounded-2xl p-4 ring-1 ring-blue-100">
            <div className="flex items-center gap-1.5 mb-2.5">
              <Compass className="w-4 h-4 text-blue-600" />
              <span className="text-xs font-bold text-blue-700 uppercase tracking-wide">Adjacent Skills (bonus context)</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {adjacent_skills.slice(0, 10).map((s, i) => (
                <span key={i} className="px-2 py-0.5 bg-blue-100 text-blue-800 text-xs rounded-lg font-semibold">{safeStr(s)}</span>
              ))}
            </div>
          </div>
        )}

        {/* Skills Gap Visualization */}
        <SkillsRadar matchedSkills={matched_skills || []} missingSkills={missing_skills || []} />

        {/* Risk Flags Section */}
        {risk_summary?.risk_flags && risk_summary.risk_flags.length > 0 && (
          <div className="bg-slate-50 rounded-2xl p-5 ring-1 ring-slate-200">
            <div className="flex items-center gap-2 mb-4">
              <AlertTriangle className="w-4 h-4 text-amber-600" />
              <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wide">Risk Flags</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              {risk_summary.risk_flags.map((flag, i) => {
                const severityColors = {
                  high: 'bg-red-100 text-red-800 ring-red-200',
                  medium: 'bg-orange-100 text-orange-800 ring-orange-200',
                  low: 'bg-yellow-100 text-yellow-800 ring-yellow-200',
                }
                const colorClass = severityColors[flag.severity] || severityColors.low
                return (
                  <div
                    key={i}
                    className={`px-3 py-1.5 rounded-xl text-xs font-semibold ring-1 ${colorClass} cursor-help`}
                    title={safeStr(flag.detail) || ''}
                  >
                    {safeStr(flag.flag)}
                    {flag.severity && (
                      <span className="ml-1.5 text-[10px] uppercase opacity-75">({safeStr(flag.severity)})</span>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Strengths / Concerns / Risks */}
        <div className="grid md:grid-cols-3 gap-4">
          <div className="bg-green-50 rounded-2xl p-4 ring-1 ring-green-100 border-l-4 border-green-500">
            <div className="flex items-center gap-2 mb-3">
              <ThumbsUp className="w-4 h-4 text-green-600" />
              <h3 className="font-bold text-green-800 text-sm">
                Strengths
                {narrativeData?.strengths && aiEnhanced === true && (
                  <span className="ml-2 text-[10px] font-semibold text-green-600 bg-green-100 px-1.5 py-0.5 rounded-full">AI Enhanced</span>
                )}
              </h3>
            </div>
            <ul className="space-y-1.5">
              {mergedStrengths.length > 0 ? (
                mergedStrengths.slice(0, 5).map((s, i) => (
                  <li key={i} className="text-sm text-green-700 flex items-start gap-2">
                    <span className="text-green-500 mt-1 shrink-0">•</span>{safeStr(s)}
                  </li>
                ))
              ) : <li className="text-sm text-green-600 italic">No specific strengths identified</li>}
            </ul>
          </div>

          <div className="bg-red-50 rounded-2xl p-4 ring-1 ring-red-100 border-l-4 border-red-400">
            <div className="flex items-center gap-2 mb-3">
              <ThumbsDown className="w-4 h-4 text-red-600" />
              <h3 className="font-bold text-red-800 text-sm">
                Concerns
                {(narrativeData?.concerns || narrativeData?.weaknesses) && aiEnhanced === true && (
                  <span className="ml-2 text-[10px] font-semibold text-red-600 bg-red-100 px-1.5 py-0.5 rounded-full">AI Enhanced</span>
                )}
              </h3>
            </div>
            <ul className="space-y-1.5">
              {mergedConcerns.length > 0 ? (
                mergedConcerns.slice(0, 5).map((w, i) => (
                  <li key={i} className="text-sm text-red-700 flex items-start gap-2">
                    <span className="text-red-500 mt-1 shrink-0">•</span>{safeStr(w)}
                  </li>
                ))
              ) : <li className="text-sm text-red-600 italic">No significant concerns</li>}
            </ul>
          </div>

          <div className="bg-amber-50 rounded-2xl p-4 ring-1 ring-amber-100 border-l-4 border-amber-400">
            <div className="flex items-center gap-2 mb-3">
              <Shield className="w-4 h-4 text-amber-600" />
              <h3 className="font-bold text-amber-800 text-sm">Risk Signals</h3>
            </div>
            <ul className="space-y-1.5">
              {risk_signals?.length > 0 ? (
                risk_signals.map((risk, i) => (
                  <li key={i} className="text-sm text-amber-700 flex items-start gap-2">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-500 mt-0.5 shrink-0" />
                    {typeof risk === 'string' ? risk : risk.description}
                  </li>
                ))
              ) : <li className="text-sm text-amber-600 italic">No risk signals detected</li>}
            </ul>
          </div>
        </div>

        {/* Explainability - uses score_rationales as fallback when explainability is missing */}
        {(() => {
          // Determine which data source to use: prefer explainability, fall back to score_rationales
          const hasExplainability = explainability && Object.keys(explainability).length > 0
          const hasScoreRationales = score_rationales && Object.keys(score_rationales).length > 0
          
          if (!hasExplainability && !hasScoreRationales) return null
          
          // Use explainability if it has meaningful content, otherwise use score_rationales
          const source = hasExplainability ? explainability : score_rationales
          const isFallback = !hasExplainability && hasScoreRationales
          
          return (
            <CollapsibleSection
              title={isFallback ? "Score Rationales — Why this score?" : "Explainability — Why this score?"}
              icon={Lightbulb}
              iconColor="text-yellow-600"
              bgColor="bg-yellow-50"
            >
              <div className="space-y-3">
                {(source.overall_rationale || source.domain_rationale) && (
                  <div className="p-3 bg-brand-50 rounded-xl ring-1 ring-brand-100">
                    <p className="text-sm font-semibold text-brand-800 mb-1">Overall</p>
                    <p className="text-sm text-slate-600 leading-relaxed">
                      {safeStr(source.overall_rationale || source.domain_rationale)}
                    </p>
                  </div>
                )}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {[
                    { key: 'skill_rationale',       label: 'Skills' },
                    { key: 'experience_rationale',   label: 'Experience' },
                    { key: 'education_rationale',    label: 'Education' },
                    { key: 'timeline_rationale',     label: 'Timeline' },
                    { key: 'domain_rationale',       label: 'Domain Fit' },
                  ].filter(f => source[f.key]).map(f => (
                    <div key={f.key} className="p-3 bg-slate-50 rounded-xl ring-1 ring-slate-100">
                      <p className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1">{f.label}</p>
                      <p className="text-xs text-slate-600 leading-relaxed">{safeStr(source[f.key])}</p>
                    </div>
                  ))}
                </div>
              </div>
            </CollapsibleSection>
          )
        })()}

        {/* Education Analysis */}
        <CollapsibleSection
          title="Education Analysis"
          icon={BookOpen}
          iconColor="text-brand-600"
          bgColor="bg-brand-50"
          defaultOpen={defaultExpandEducation}
        >
          <div className="space-y-3">
            {edu_timeline_analysis?.field_alignment && (
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wide">Field Alignment</span>
                <span className={`px-2 py-0.5 rounded-full text-xs font-bold ring-1 ${
                  edu_timeline_analysis.field_alignment === 'aligned'
                    ? 'bg-green-100 text-green-700 ring-green-200'
                    : edu_timeline_analysis.field_alignment === 'partially_aligned'
                    ? 'bg-amber-100 text-amber-700 ring-amber-200'
                    : 'bg-red-100 text-red-700 ring-red-200'
                }`}>
                  {safeStr(edu_timeline_analysis.field_alignment).replace('_', ' ')}
                </span>
              </div>
            )}
            <p className="text-sm text-slate-600 leading-relaxed">
              {safeStr(edu_timeline_analysis?.education_analysis || education_analysis) || 'No education analysis available.'}
            </p>
            {edu_timeline_analysis?.timeline_analysis && (
              <div className="mt-2 pt-2 border-t border-brand-50">
                <p className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1">Timeline</p>
                <p className="text-sm text-slate-600 leading-relaxed">{safeStr(edu_timeline_analysis.timeline_analysis)}</p>
              </div>
            )}
            {edu_timeline_analysis?.gap_interpretation && (
              <div className="mt-2 pt-2 border-t border-brand-50">
                <p className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1">Gap Context</p>
                <p className="text-sm text-slate-600 leading-relaxed italic">{safeStr(edu_timeline_analysis.gap_interpretation)}</p>
              </div>
            )}
          </div>
        </CollapsibleSection>

        {/* Domain Fit & Architecture */}
        {(skill_analysis?.domain_fit_comment || skill_analysis?.architecture_comment) && (
          <CollapsibleSection
            title="Domain Fit & Architecture Assessment"
            icon={Cpu}
            iconColor="text-teal-600"
            bgColor="bg-teal-50"
          >
            <div className="space-y-3">
              {skill_analysis.domain_fit_comment && (
                <div>
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1">Domain Fit</p>
                  <p className="text-sm text-slate-600 leading-relaxed">{safeStr(skill_analysis.domain_fit_comment)}</p>
                </div>
              )}
              {skill_analysis.architecture_comment && (
                <div className="pt-2 border-t border-teal-50">
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1">Architecture & System Design</p>
                  <p className="text-sm text-slate-600 leading-relaxed">{safeStr(skill_analysis.architecture_comment)}</p>
                </div>
              )}
            </div>
          </CollapsibleSection>
        )}

        {/* Interview Kit */}
        {interview_questions && (
          <div className="ring-1 ring-brand-200 rounded-2xl bg-brand-50/40 overflow-hidden">
            <button
              onClick={() => setShowInterviewKit(!showInterviewKit)}
              className="w-full flex items-center justify-between p-4 hover:bg-brand-50 transition-colors"
            >
              <div className="flex items-center gap-2.5">
                <ClipboardList className="w-4 h-4 text-brand-600" />
                <span className="font-bold text-brand-800 text-sm">Interview Kit</span>
                <span className="text-xs bg-brand-100 text-brand-700 px-2 py-0.5 rounded-full font-semibold">
                  {(interview_questions.technical_questions?.length || 0) +
                   (interview_questions.behavioral_questions?.length || 0) +
                   (interview_questions.culture_fit_questions?.length || 0)} questions
                </span>
              </div>
              {showInterviewKit
                ? <ChevronUp className="w-4 h-4 text-brand-600" />
                : <ChevronDown className="w-4 h-4 text-brand-600" />}
            </button>

            {showInterviewKit && (
              <div className="px-4 pb-4 border-t border-brand-100">
                <div className="flex gap-1.5 mb-4 mt-3">
                  {QTABS.filter(t => t.questions.length > 0).map(t => (
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
                {QTABS.filter(t => t.key === activeQTab).map(t => (
                  <ol key={t.key} className="space-y-2">
                    {t.questions.map((q, i) => (
                      <li key={i} className="flex items-start gap-3 p-3 bg-white rounded-xl ring-1 ring-brand-100">
                        <span className="text-xs font-bold text-brand-400 mt-0.5 w-5 shrink-0">{i + 1}.</span>
                        <p className="text-sm text-slate-700 flex-1">{typeof q === 'string' ? q : JSON.stringify(q)}</p>
                        <CopyButton text={typeof q === 'string' ? q : JSON.stringify(q)} />
                      </li>
                    ))}
                  </ol>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {showEmailModal && (
        <EmailModal
          candidateId={candidate_id}
          resultId={result_id}
          onClose={() => setShowEmailModal(false)}
        />
      )}
    </>
  )
}
