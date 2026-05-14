import {
  ThumbsUp, ThumbsDown, AlertTriangle, ChevronDown, ChevronUp,
  CheckCircle, XCircle, Target, TrendingUp, Shield, ClipboardList,
  Copy, Check, Mail, X, Loader2, Lightbulb, BookOpen, Compass, Cpu,
  Sparkles, Info, UserCheck, User, Eye, MessageCircle, Star,
  Flame, CheckCircle2,
} from 'lucide-react'
import { useState, useEffect, useRef } from 'react'
import SkillsRadar from './SkillsRadar'
import AnimatedScore from './AnimatedScore'
import StreamingText from './StreamingText'
import { generateEmail, getNarrative, getEvaluations, saveEvaluation, recordOutcome, recordOutcomeFeedback } from '../lib/api'

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

// ─── Score Breakdown Panel with expandable evidence ──────────────────────────

function ScoreBreakdownPanel({ scoreBreakdown, recommendationRationale, riskSummary }) {
  const [showDetails, setShowDetails] = useState(false)

  // Handle both old (scalar) and new (dict) formats gracefully
  const skillBreakdown = scoreBreakdown?.skill_match
  const isSkillDetailed = typeof skillBreakdown === 'object' && skillBreakdown !== null
  const skillScore = isSkillDetailed ? (skillBreakdown.score ?? 0) : (skillBreakdown ?? 0)

  const expBreakdown = scoreBreakdown?.experience_match
  const isExpDetailed = typeof expBreakdown === 'object' && expBreakdown !== null
  const expScore = isExpDetailed ? (expBreakdown.score ?? 0) : (expBreakdown ?? 0)

  // Confidence dot color based on match_type
  const matchTypeColor = (type) => {
    if (type === 'exact') return 'bg-green-500'
    if (type === 'alias') return 'bg-amber-400'
    if (type === 'substring') return 'bg-orange-400'
    if (type === 'hierarchy_inferred') return 'bg-slate-300'
    return 'bg-blue-400'
  }

  const matchTypeLabel = (type) => {
    if (type === 'exact') return 'Exact'
    if (type === 'alias') return 'Alias'
    if (type === 'substring') return 'Partial'
    if (type === 'hierarchy_inferred') return 'Inferred'
    return type || 'Match'
  }

  return (
    <div className="bg-brand-50/60 rounded-2xl p-5 ring-1 ring-brand-100">
      {/* Header with toggle */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-brand-500" />
          <h3 className="text-sm font-bold text-brand-800 uppercase tracking-wide">Score Breakdown</h3>
        </div>
        <button
          onClick={() => setShowDetails(v => !v)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-brand-700 hover:bg-brand-100 transition-colors ring-1 ring-brand-200"
        >
          {showDetails ? (
            <>
              <ChevronUp className="w-3.5 h-3.5" />
              Hide Details
            </>
          ) : (
            <>
              <ChevronDown className="w-3.5 h-3.5" />
              View Score Details
            </>
          )}
        </button>
      </div>

      {/* Score bars — always visible */}
      <div className="grid grid-cols-2 gap-4">
        <ScoreBar label="Skill Match" value={skillScore} color="blue" />
        <ScoreBar label="Experience" value={expScore} color="green" />
        <ScoreBar label="Education" value={scoreBreakdown.education ?? 0} color="amber" />
        <ScoreBar label="Timeline" value={scoreBreakdown.timeline ?? scoreBreakdown.stability ?? 0} color="purple" />
        {scoreBreakdown.architecture != null && (
          <ScoreBar label="Architecture" value={scoreBreakdown.architecture} color="teal" />
        )}
        {scoreBreakdown.domain_fit != null && (
          <ScoreBar label="Domain Fit" value={scoreBreakdown.domain_fit} color="rose" />
        )}
      </div>

      {/* Expandable evidence details */}
      {showDetails && (
        <div className="mt-4 pt-4 border-t border-brand-200 space-y-4">

          {/* ── Skill Match Evidence ── */}
          {isSkillDetailed && (
            <div className="bg-white rounded-xl p-4 ring-1 ring-brand-100">
              <div className="flex items-center gap-2 mb-3">
                <CheckCircle2 className="w-4 h-4 text-brand-600" />
                <h4 className="text-sm font-bold text-slate-800">Skill Match Evidence</h4>
              </div>

              {/* Required skills progress */}
              {skillBreakdown.required_total > 0 && (
                <div className="mb-3">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-xs font-semibold text-slate-600">
                      Required Skills Matched
                    </span>
                    <span className="text-xs font-bold text-brand-700">
                      {Math.min(skillBreakdown.required_matched, skillBreakdown.required_total)}/{skillBreakdown.required_total}
                    </span>
                  </div>
                  <div className="w-full bg-brand-100 rounded-full h-2.5">
                    <div
                      className="h-2.5 rounded-full bg-brand-500 transition-all duration-500"
                      style={{ width: `${Math.min(100, (skillBreakdown.required_matched / Math.max(skillBreakdown.required_total, 1)) * 100)}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Nice-to-have skills progress */}
              {skillBreakdown.nice_total > 0 && (
                <div className="mb-3">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-xs font-semibold text-slate-600">
                      Nice-to-Have Skills Matched
                    </span>
                    <span className="text-xs font-bold text-amber-700">
                      {skillBreakdown.nice_matched}/{skillBreakdown.nice_total}
                    </span>
                  </div>
                  <div className="w-full bg-amber-100 rounded-full h-2.5">
                    <div
                      className="h-2.5 rounded-full bg-amber-500 transition-all duration-500"
                      style={{ width: `${Math.min(100, (skillBreakdown.nice_matched / Math.max(skillBreakdown.nice_total, 1)) * 100)}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Missing required skills */}
              {skillBreakdown.missing_required?.length > 0 && (
                <div className="mb-3">
                  <span className="text-xs font-semibold text-red-600 block mb-1.5">Missing Required Skills</span>
                  <div className="flex flex-wrap gap-1.5">
                    {skillBreakdown.missing_required.map((skill, i) => (
                      <span key={i} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700 ring-1 ring-red-200">
                        <XCircle className="w-3 h-3" />
                        {typeof skill === 'string' ? skill : skill?.skill || String(skill)}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Matched skills with confidence */}
              {skillBreakdown.matched_details?.length > 0 && (
                <div className="mb-3">
                  <span className="text-xs font-semibold text-green-700 block mb-1.5">Matched Skills</span>
                  <div className="flex flex-wrap gap-1.5">
                    {skillBreakdown.matched_details.map((m, i) => (
                      <span
                        key={i}
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-50 text-slate-700 ring-1 ring-green-200"
                        title={`${matchTypeLabel(m.match_type)} match — confidence: ${(m.confidence * 100).toFixed(0)}%`}
                      >
                        <span className={`w-2 h-2 rounded-full ${matchTypeColor(m.match_type)}`} />
                        {m.skill}
                        <span className="text-slate-400 text-[10px]">{(m.confidence * 100).toFixed(0)}%</span>
                      </span>
                    ))}
                  </div>
                  <div className="flex items-center gap-3 mt-2 text-[10px] text-slate-400">
                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500" /> Exact</span>
                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-400" /> Alias</span>
                    <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-orange-400" /> Partial</span>
                  </div>
                </div>
              )}

              {/* Proficiency adjustments */}
              {skillBreakdown.proficiency_adjustments?.length > 0 && (
                <div className="mb-3">
                  <span className="text-xs font-semibold text-indigo-700 block mb-1.5">Proficiency Adjustments</span>
                  <div className="space-y-1">
                    {skillBreakdown.proficiency_adjustments.map((p, i) => (
                      <div key={i} className="flex items-center gap-2 text-xs text-slate-600">
                        <span className="w-2 h-2 rounded-full bg-indigo-400" />
                        <span className="font-medium">{p.skill}</span>
                        <span className="text-slate-400">— required: {String(p.required)}</span>
                        <span className="px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-600 font-semibold text-[10px]">{p.factor}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Team gap bonus */}
              {skillBreakdown.team_gap_bonus > 0 && (
                <div className="flex items-center gap-2 mb-3">
                  <UserCheck className="w-3.5 h-3.5 text-teal-600" />
                  <span className="text-xs font-semibold text-teal-700">
                    Team Gap Bonus: +{skillBreakdown.team_gap_bonus}
                  </span>
                </div>
              )}

              {/* Trend factors applied */}
              {skillBreakdown.trend_factors_applied?.length > 0 && (
                <div>
                  <span className="text-xs font-semibold text-purple-700 block mb-1.5">Market Trend Factors</span>
                  <div className="space-y-1">
                    {skillBreakdown.trend_factors_applied.map((t, i) => (
                      <div key={i} className="flex items-center gap-2 text-xs text-slate-600">
                        <TrendingUp className={`w-3 h-3 ${t.direction === 'rising' ? 'text-green-500' : t.direction === 'falling' ? 'text-red-500' : 'text-slate-400'}`} />
                        <span className="font-medium">{t.skill}</span>
                        <span className="text-slate-400">— {t.direction}</span>
                        <span className={`px-1.5 py-0.5 rounded font-semibold text-[10px] ${
                          t.factor > 1 ? 'bg-green-50 text-green-700' : t.factor < 1 ? 'bg-red-50 text-red-700' : 'bg-slate-50 text-slate-600'
                        }`}>
                          ×{t.factor}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Confidence metadata */}
              {skillBreakdown.confidence_weighted && (
                <div className="mt-3 pt-3 border-t border-brand-100 flex items-center gap-2 text-xs text-slate-500">
                  <Info className="w-3 h-3" />
                  <span>Confidence-weighted scoring (avg: {((skillBreakdown.avg_confidence ?? 1) * 100).toFixed(0)}%)</span>
                </div>
              )}
            </div>
          )}

          {/* ── Experience Evidence ── */}
          {isExpDetailed && (
            <div className="bg-white rounded-xl p-4 ring-1 ring-brand-100">
              <div className="flex items-center gap-2 mb-3">
                <Star className="w-4 h-4 text-green-600" />
                <h4 className="text-sm font-bold text-slate-800">Experience</h4>
              </div>
              <div className="flex items-baseline gap-2 mb-2">
                {expBreakdown.actual_years != null && (
                  <span className="text-lg font-bold text-slate-800">{expBreakdown.actual_years}y</span>
                )}
                {expBreakdown.required_years != null && (
                  <span className="text-xs text-slate-500">vs {expBreakdown.required_years}y required</span>
                )}
              </div>
              {expBreakdown.explanation && (
                <p className="text-xs text-slate-600 italic">{expBreakdown.explanation}</p>
              )}
            </div>
          )}

          {/* ── Other score dimensions as simple bars ── */}
          <div className="bg-white rounded-xl p-4 ring-1 ring-brand-100">
            <div className="flex items-center gap-2 mb-3">
              <ClipboardList className="w-4 h-4 text-brand-600" />
              <h4 className="text-sm font-bold text-slate-800">Other Dimensions</h4>
            </div>
            <div className="space-y-2">
              <ScoreBar label="Education" value={scoreBreakdown.education ?? 0} color="amber" />
              <ScoreBar label="Timeline" value={scoreBreakdown.timeline ?? scoreBreakdown.stability ?? 0} color="purple" />
              {scoreBreakdown.architecture != null && (
                <ScoreBar label="Architecture" value={scoreBreakdown.architecture} color="teal" />
              )}
              {scoreBreakdown.domain_fit != null && (
                <ScoreBar label="Domain Fit" value={scoreBreakdown.domain_fit} color="rose" />
              )}
              {scoreBreakdown.risk_penalty > 0 && (
                <ScoreBar label="Risk Penalty" value={scoreBreakdown.risk_penalty} color="rose" />
              )}
            </div>
          </div>

          {/* Rationale & seniority */}
          {recommendationRationale && (
            <p className="text-xs text-slate-500 italic">{safeStr(recommendationRationale)}</p>
          )}
          {riskSummary?.seniority_alignment && (
            <div className="flex items-center gap-2">
              <Info className="w-3.5 h-3.5 text-brand-500" />
              <span className="text-xs font-semibold text-brand-700">Seniority Alignment:</span>
              <span className="text-xs text-slate-600">{safeStr(riskSummary.seniority_alignment)}</span>
            </div>
          )}
        </div>
      )}

      {/* Non-expanded rationale & seniority (always show) */}
      {!showDetails && recommendationRationale && (
        <p className="text-xs text-slate-500 mt-3 italic">{safeStr(recommendationRationale)}</p>
      )}
      {!showDetails && riskSummary?.seniority_alignment && (
        <div className="mt-3 pt-3 border-t border-brand-100 flex items-center gap-2">
          <Info className="w-3.5 h-3.5 text-brand-500" />
          <span className="text-xs font-semibold text-brand-700">Seniority Alignment:</span>
          <span className="text-xs text-slate-600">{safeStr(riskSummary.seniority_alignment)}</span>
        </div>
      )}
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
  const [expandedGuidance, setExpandedGuidance] = useState({})

  // Per-question evaluation state
  const [evaluations, setEvaluations] = useState({})   // { "technical_0": { rating: "strong", notes: "..." }, ... }
  const [savingEval, setSavingEval]   = useState({})   // { "technical_0": true } — loading states
  const [evalLoaded, setEvalLoaded]   = useState(false)

  // Outcome feedback state
  const [outcomeStatus, setOutcomeStatus]       = useState(null) // null | 'hired' | 'rejected' | 'withdrawn'
  const [outcomeId, setOutcomeId]               = useState(null)
  const [showStageSelect, setShowStageSelect]   = useState(false)
  const [selectedStage, setSelectedStage]       = useState('')
  const [outcomeNotes, setOutcomeNotes]         = useState('')
  const [savingOutcome, setSavingOutcome]       = useState(false)
  const [showFeedback, setShowFeedback]         = useState(false)
  const [feedbackRating, setFeedbackRating]     = useState(0)
  const [feedbackNotes, setFeedbackNotes]       = useState('')
  const [savingFeedback, setSavingFeedback]     = useState(false)
  const [outcomeError, setOutcomeError]         = useState(null)

  // Normalize interview question to structured format (backward compat)
  const normalizeQ = (q) => {
    if (typeof q === 'string') return { text: q, what_to_listen_for: [], follow_ups: [] };
    if (q && typeof q === 'object') return {
      text: q.text || String(q),
      what_to_listen_for: q.what_to_listen_for || [],
      follow_ups: q.follow_ups || [],
    };
    return { text: String(q), what_to_listen_for: [], follow_ups: [] };
  };

  const toggleGuidance = (key) => {
    setExpandedGuidance(prev => ({ ...prev, [key]: !prev[key] }));
  };

  // Load existing evaluations when Interview Kit is expanded
  useEffect(() => {
    if (showInterviewKit && result?.result_id && !evalLoaded) {
      const loadEvals = async () => {
        try {
          const data = await getEvaluations(result.result_id)
          const evalMap = {}
          data.forEach(e => {
            evalMap[`${e.question_category}_${e.question_index}`] = {
              rating: e.rating,
              notes: e.notes || '',
            }
          })
          setEvaluations(evalMap)
        } catch (err) {
          console.error('Failed to load evaluations:', err)
        }
        setEvalLoaded(true)
      }
      loadEvals()
    }
  }, [showInterviewKit, result?.result_id, evalLoaded])

  // Save evaluation handler
  const handleSaveEval = async (category, index, field, value) => {
    const key = `${category}_${index}`
    const current = evaluations[key] || {}
    const updated = { ...current, [field]: value }
    setEvaluations(prev => ({ ...prev, [key]: updated }))

    setSavingEval(prev => ({ ...prev, [key]: true }))
    try {
      await saveEvaluation(result.result_id, {
        question_category: category,
        question_index: index,
        rating: updated.rating || null,
        notes: updated.notes || null,
      })
    } catch (err) {
      console.error('Failed to save evaluation:', err)
    }
    setSavingEval(prev => ({ ...prev, [key]: false }))
  }

  // Outcome handler
  const handleOutcome = (decision) => {
    setOutcomeStatus(decision)
    setShowStageSelect(true)
    setOutcomeError(null)
  }

  const handleConfirmOutcome = async () => {
    if (!candidate_id) return
    setSavingOutcome(true)
    setOutcomeError(null)
    try {
      const data = {
        screening_result_id: result_id,
        decision: outcomeStatus,
      }
      if (selectedStage) data.stage = selectedStage
      if (outcomeNotes.trim()) data.notes = outcomeNotes.trim()
      const result = await recordOutcome(candidate_id, data)
      setOutcomeId(result.outcome_id || result.id)
      setShowStageSelect(false)
      // Show feedback for hired candidates
      if (outcomeStatus === 'hired') {
        setShowFeedback(true)
      }
    } catch (err) {
      setOutcomeError(err.response?.data?.detail || 'Failed to record outcome')
    } finally {
      setSavingOutcome(false)
    }
  }

  const handleSubmitFeedback = async () => {
    if (!outcomeId || feedbackRating === 0) return
    setSavingFeedback(true)
    try {
      await recordOutcomeFeedback(outcomeId, {
        rating: feedbackRating,
        notes: feedbackNotes.trim() || undefined,
      })
      setShowFeedback(false)
    } catch (err) {
      console.error('Failed to submit feedback:', err)
    } finally {
      setSavingFeedback(false)
    }
  }
  
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
    analysis_id, onet_hot_skills,
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
    { key: 'experience_deep_dive', label: 'Experience Deep-Dive', questions: interview_questions?.experience_deep_dive_questions || [] },
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
                <p className="text-sm leading-relaxed text-white/95">
                  <StreamingText text={safeStr(fit_summary)} isStreaming={isPolling} />
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Score Breakdown */}
        {score_breakdown && Object.keys(score_breakdown).length > 0 && !isPending && (
          <ScoreBreakdownPanel scoreBreakdown={score_breakdown} recommendationRationale={recommendation_rationale} riskSummary={risk_summary} />
        )}

        {/* Skills Intel — Tiered display when enhanced skill_analysis is available */}
        {skill_analysis?.matched_required != null ? (
          /* ── Tiered Skill Display (new backend data) ── */
          <div className="space-y-4">
            {/* Tiered score breakdown */}
            <div className="flex items-center gap-3 flex-wrap">
              <div className="flex items-center gap-2 bg-brand-50/80 ring-1 ring-brand-200 rounded-xl px-3 py-1.5">
                <TrendingUp className="w-3.5 h-3.5 text-brand-600" />
                <span className="text-xs font-bold text-brand-800">
                  Core Skills: {typeof score_breakdown?.skill_match === 'object' ? (score_breakdown?.skill_match?.score ?? skill_analysis.required_match_pct ?? 0) : (score_breakdown?.skill_match ?? skill_analysis.required_match_pct ?? 0)}%
                </span>
              </div>
              <div className="flex items-center gap-1.5 text-xs text-slate-500">
                <span className="font-semibold text-green-700">Must-have: {skill_analysis.required_match_pct ?? 0}%</span>
                <span className="text-slate-300">|</span>
                <span className="font-semibold text-amber-700">Good-to-have: {skill_analysis.nice_to_have_match_pct ?? 0}%</span>
                {skill_analysis.proficiency_analysis && Object.keys(skill_analysis.proficiency_analysis).length > 0 && (() => {
                  const profEntries = Object.values(skill_analysis.proficiency_analysis)
                  const avgMatch = profEntries.length > 0
                    ? Math.round((profEntries.reduce((sum, e) => sum + (e.match_factor ?? 0), 0) / profEntries.length) * 100)
                    : 0
                  return (
                    <>
                      <span className="text-slate-300">|</span>
                      <span className="font-semibold text-indigo-700">Proficiency match: {avgMatch}%</span>
                    </>
                  )
                })()}
              </div>
            </div>

            {/* Must-Have Skills */}
            {(() => {
              const matched = skill_analysis.matched_required || []
              const missing = skill_analysis.missing_required || []
              const total = matched.length + missing.length
              const profAnalysis = skill_analysis.proficiency_analysis || {}
              const hotSet = new Set((onet_hot_skills || []).map(s => typeof s === 'string' ? s.toLowerCase() : String(s).toLowerCase()))
              if (total === 0) return null
              return (
                <div className="bg-slate-50 rounded-2xl p-4 ring-1 ring-slate-200">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-5 h-5 rounded-md bg-red-100 flex items-center justify-center">
                      <Shield className="w-3 h-3 text-red-600" />
                    </div>
                    <span className="text-xs font-bold text-slate-800 uppercase tracking-wide">
                      Must-Have Skills
                    </span>
                    <span className="text-xs font-semibold text-slate-500">
                      ({matched.length}/{total} matched)
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {matched.map((s, i) => {
                      const skillName = safeStr(s)
                      const prof = profAnalysis[skillName] || profAnalysis[skillName.toLowerCase()]
                      const isHot = hotSet.has(skillName.toLowerCase())
                      let profPill = null
                      if (prof) {
                        const mf = prof.match_factor ?? 0
                        if (mf >= 1.0) {
                          profPill = (
                            <span className="ml-1 inline-flex items-center gap-0.5 text-[10px] font-semibold text-green-700 bg-green-200/60 rounded px-1 py-px">
                              <CheckCircle2 className="w-2.5 h-2.5" />
                              {safeStr(prof.estimated_candidate)}
                            </span>
                          )
                        } else if (mf >= 0.5) {
                          profPill = (
                            <span className="ml-1 inline-flex items-center gap-0.5 text-[10px] font-semibold text-amber-700 bg-amber-200/60 rounded px-1 py-px">
                              {safeStr(prof.estimated_candidate)} ({safeStr(prof.required)} expected)
                            </span>
                          )
                        } else {
                          profPill = (
                            <span className="ml-1 inline-flex items-center gap-0.5 text-[10px] font-semibold text-orange-700 bg-orange-200/60 rounded px-1 py-px">
                              {safeStr(prof.estimated_candidate)} ({safeStr(prof.required)} expected)
                            </span>
                          )
                        }
                      }
                      return (
                        <span
                          key={`mr-${i}`}
                          className="px-2.5 py-1 bg-green-100 border-2 border-green-400 text-green-800 text-xs rounded-lg font-medium inline-flex items-center gap-1"
                        >
                          <CheckCircle className="w-3 h-3 text-green-600" />
                          {skillName}
                          {profPill}
                          {isHot && <Flame className="w-3 h-3 text-orange-500" title="Hot skill — high market demand" />}
                          {skill_depth && skill_depth[skillName] && (
                            <span className="text-[10px] text-green-600 font-medium">({safeStr(skill_depth[skillName])}x)</span>
                          )}
                        </span>
                      )
                    })}
                    {missing.map((s, i) => {
                      const skillName = safeStr(s)
                      const isHot = hotSet.has(skillName.toLowerCase())
                      return (
                        <span
                          key={`mm-${i}`}
                          className="px-2.5 py-1 bg-red-100 border-2 border-red-400 text-red-800 text-xs rounded-lg font-medium inline-flex items-center gap-1"
                        >
                          <XCircle className="w-3 h-3 text-red-500" />
                          {skillName}
                          {isHot && <Flame className="w-3 h-3 text-orange-500" title="Hot skill — high market demand" />}
                        </span>
                      )
                    })}
                  </div>
                </div>
              )
            })()}

            {/* Good-to-Have Skills */}
            {(() => {
              const matched = skill_analysis.matched_nice_to_have || []
              const missing = skill_analysis.missing_nice_to_have || []
              const total = matched.length + missing.length
              const hotSet = new Set((onet_hot_skills || []).map(s => typeof s === 'string' ? s.toLowerCase() : String(s).toLowerCase()))
              if (total === 0) return null
              return (
                <div className="bg-amber-50/50 rounded-2xl p-4 ring-1 ring-amber-100">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-5 h-5 rounded-md bg-amber-100 flex items-center justify-center">
                      <Star className="w-3 h-3 text-amber-600" />
                    </div>
                    <span className="text-xs font-bold text-slate-800 uppercase tracking-wide">
                      Good-to-Have Skills
                    </span>
                    <span className="text-xs font-semibold text-slate-500">
                      ({matched.length}/{total} matched)
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {matched.map((s, i) => {
                      const skillName = safeStr(s)
                      const isHot = hotSet.has(skillName.toLowerCase())
                      return (
                        <span
                          key={`gr-${i}`}
                          className="px-2.5 py-1 bg-green-50 border border-green-200 text-green-700 text-xs rounded-lg font-medium inline-flex items-center gap-1"
                        >
                          <CheckCircle className="w-3 h-3 text-green-500" />
                          {skillName}
                          {isHot && <Flame className="w-3 h-3 text-orange-500" title="Hot skill — high market demand" />}
                          {skill_depth && skill_depth[skillName] && (
                            <span className="text-[10px] text-green-500 font-medium">({safeStr(skill_depth[skillName])}x)</span>
                          )}
                        </span>
                      )
                    })}
                    {missing.map((s, i) => {
                      const skillName = safeStr(s)
                      const isHot = hotSet.has(skillName.toLowerCase())
                      return (
                        <span
                          key={`gm-${i}`}
                          className="px-2.5 py-1 bg-amber-50 border border-amber-200 text-amber-700 text-xs rounded-lg font-medium inline-flex items-center gap-1"
                        >
                          <AlertTriangle className="w-3 h-3 text-amber-400" />
                          {skillName}
                          {isHot && <Flame className="w-3 h-3 text-orange-500" title="Hot skill — high market demand" />}
                        </span>
                      )
                    })}
                  </div>
                </div>
              )
            })()}
          </div>
        ) : (
          /* ── Legacy flat skill display (backward compat) ── */
          ((matched_skills?.length > 0) || (missing_skills?.length > 0)) && (
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
          )
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
                    {safeStr(typeof risk === 'string' ? risk : risk?.description)}
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
                   (interview_questions.culture_fit_questions?.length || 0) +
                   (interview_questions.experience_deep_dive_questions?.length || 0)} questions
                </span>
              </div>
              {showInterviewKit
                ? <ChevronUp className="w-4 h-4 text-brand-600" />
                : <ChevronDown className="w-4 h-4 text-brand-600" />}
            </button>

            {showInterviewKit && (
              <div className="px-4 pb-4 border-t border-brand-100">

                {/* Candidate Briefing */}
                {interview_questions?.candidate_briefing && (
                  <div className="mx-0 mt-3 mb-2 p-4 bg-gradient-to-r from-brand-50 to-indigo-50 rounded-xl ring-1 ring-brand-200">
                    <div className="flex items-center gap-2 mb-3">
                      <User className="w-4 h-4 text-brand-600" />
                      <span className="font-bold text-brand-800 text-sm">Candidate Briefing</span>
                    </div>

                    {/* Profile Snapshot */}
                    {interview_questions.candidate_briefing.profile_snapshot && (
                      <p className="text-sm text-slate-700 mb-3 leading-relaxed">
                        {interview_questions.candidate_briefing.profile_snapshot}
                      </p>
                    )}

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {/* Strengths to Confirm */}
                      {interview_questions.candidate_briefing.strengths_to_confirm?.length > 0 && (
                        <div>
                          <span className="text-xs font-semibold text-emerald-700 uppercase tracking-wide">Strengths to Confirm</span>
                          <ul className="mt-1 space-y-1">
                            {interview_questions.candidate_briefing.strengths_to_confirm.map((s, i) => (
                              <li key={i} className="flex items-start gap-1.5 text-sm text-slate-600">
                                <span className="text-emerald-500 mt-0.5">&#10003;</span>
                                {s}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Areas to Probe */}
                      {interview_questions.candidate_briefing.areas_to_probe?.length > 0 && (
                        <div>
                          <span className="text-xs font-semibold text-amber-700 uppercase tracking-wide">Areas to Probe</span>
                          <ul className="mt-1 space-y-1">
                            {interview_questions.candidate_briefing.areas_to_probe.map((a, i) => (
                              <li key={i} className="flex items-start gap-1.5 text-sm text-slate-600">
                                <span className="text-amber-500 mt-0.5">&#9679;</span>
                                {a}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>

                    {/* Context Notes — collapsible */}
                    {interview_questions.candidate_briefing.context_notes?.length > 0 && (
                      <div className="mt-3">
                        <button
                          onClick={() => setExpandedGuidance(prev => ({ ...prev, briefing_context: !prev.briefing_context }))}
                          className="text-xs font-semibold text-brand-600 hover:text-brand-800 flex items-center gap-1"
                        >
                          {expandedGuidance.briefing_context ? 'Hide' : 'Show'} question context
                          {expandedGuidance.briefing_context
                            ? <ChevronUp className="w-3 h-3" />
                            : <ChevronDown className="w-3 h-3" />}
                        </button>
                        {expandedGuidance.briefing_context && (
                          <ul className="mt-2 space-y-1 pl-2 border-l-2 border-brand-200">
                            {interview_questions.candidate_briefing.context_notes.map((n, i) => (
                              <li key={i} className="text-xs text-slate-500 italic">{n}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* Question Tabs */}
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

                {/* Enhanced Question Cards */}
                {QTABS.filter(t => t.key === activeQTab).map(t => (
                  <ol key={t.key} className="space-y-3">
                    {t.questions.map((rawQ, i) => {
                      const q = normalizeQ(rawQ);
                      const guidanceKey = `${t.key}_${i}`;
                      const hasGuidance = q.what_to_listen_for.length > 0 || q.follow_ups.length > 0;

                      return (
                        <li key={i} className="p-3 bg-white rounded-xl ring-1 ring-brand-100">
                          {/* Question text + copy */}
                          <div className="flex items-start gap-3">
                            <span className="text-xs font-bold text-brand-400 mt-0.5 w-5 shrink-0">{i + 1}.</span>
                            <p className="text-sm text-slate-700 flex-1">{q.text}</p>
                            <CopyButton text={q.text} />
                          </div>

                          {/* Expandable guidance toggle */}
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
                                <div className="mt-2 space-y-3">
                                  {/* What to Listen For */}
                                  {q.what_to_listen_for.length > 0 && (
                                    <div className="p-2.5 bg-brand-50/60 rounded-lg">
                                      <span className="text-xs font-semibold text-brand-700 uppercase tracking-wide flex items-center gap-1">
                                        <Eye className="w-3 h-3" /> What to Listen For
                                      </span>
                                      <ul className="mt-1.5 space-y-1">
                                        {q.what_to_listen_for.map((item, j) => (
                                          <li key={j} className="text-xs text-slate-600 flex items-start gap-1.5">
                                            <span className="text-brand-400 mt-0.5">&#8226;</span>
                                            {item}
                                          </li>
                                        ))}
                                      </ul>
                                    </div>
                                  )}

                                  {/* Follow-Up Questions */}
                                  {q.follow_ups.length > 0 && (
                                    <div className="p-2.5 bg-indigo-50/60 rounded-lg">
                                      <span className="text-xs font-semibold text-indigo-700 uppercase tracking-wide flex items-center gap-1">
                                        <MessageCircle className="w-3 h-3" /> Follow-Up Questions
                                      </span>
                                      <ul className="mt-1.5 space-y-1">
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

                          {/* Evaluation Section */}
                          <div className="ml-8 mt-3 pt-3 border-t border-slate-100">
                            {/* Rating Buttons */}
                            <div className="flex items-center gap-2 mb-2">
                              <span className="text-xs font-semibold text-slate-500">Rate:</span>
                              {[
                                { value: 'strong', label: 'Strong', activeClass: 'bg-emerald-100 text-emerald-700 ring-emerald-300' },
                                { value: 'adequate', label: 'Adequate', activeClass: 'bg-amber-100 text-amber-700 ring-amber-300' },
                                { value: 'weak', label: 'Weak', activeClass: 'bg-red-100 text-red-700 ring-red-300' },
                              ].map(opt => {
                                const evalKey = `${t.key}_${i}`
                                const isActive = evaluations[evalKey]?.rating === opt.value
                                return (
                                  <button
                                    key={opt.value}
                                    onClick={() => handleSaveEval(t.key, i, 'rating', opt.value)}
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
                              {savingEval[`${t.key}_${i}`] && (
                                <span className="text-xs text-slate-400 italic">Saving...</span>
                              )}
                            </div>

                            {/* Notes Text Area */}
                            <textarea
                              placeholder="Add interview notes for this question..."
                              value={evaluations[`${t.key}_${i}`]?.notes || ''}
                              onChange={(e) => {
                                const key = `${t.key}_${i}`
                                setEvaluations(prev => ({ ...prev, [key]: { ...prev[key], notes: e.target.value } }))
                              }}
                              onBlur={(e) => handleSaveEval(t.key, i, 'notes', e.target.value)}
                              rows={2}
                              className="w-full text-xs text-slate-600 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-brand-300 focus:border-brand-300 placeholder:text-slate-300"
                            />
                          </div>
                        </li>
                      );
                    })}
                  </ol>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Outcome Feedback Section */}
        {!isPending && candidate_id && (
          <div className="ring-1 ring-brand-200 rounded-2xl bg-brand-50/40 overflow-hidden">
            <div className="p-4">
              <div className="flex items-center gap-2 mb-3">
                <ClipboardList className="w-4 h-4 text-brand-600" />
                <span className="font-bold text-brand-800 text-sm">Hiring Decision</span>
              </div>

              {/* Outcome Status Badge — shown when outcome is recorded */}
              {outcomeStatus && !showStageSelect ? (
                <div className="flex items-center gap-3">
                  <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold ring-1 ${
                    outcomeStatus === 'hired'
                      ? 'bg-green-100 text-green-700 ring-green-200'
                      : outcomeStatus === 'rejected'
                      ? 'bg-red-100 text-red-700 ring-red-200'
                      : 'bg-slate-100 text-slate-600 ring-slate-200'
                  }`}>
                    {outcomeStatus === 'hired' && <CheckCircle className="w-3.5 h-3.5" />}
                    {outcomeStatus === 'rejected' && <XCircle className="w-3.5 h-3.5" />}
                    {outcomeStatus === 'withdrawn' && <AlertTriangle className="w-3.5 h-3.5" />}
                    {outcomeStatus.charAt(0).toUpperCase() + outcomeStatus.slice(1)}
                  </span>
                  {/* Feedback link for hired candidates */}
                  {outcomeStatus === 'hired' && outcomeId && !showFeedback && (
                    <button
                      onClick={() => setShowFeedback(true)}
                      className="text-xs font-semibold text-brand-600 hover:text-brand-800 transition-colors"
                    >
                      Add feedback
                    </button>
                  )}
                </div>
              ) : !outcomeStatus ? (
                /* Decision Buttons — shown when no outcome recorded */
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm text-slate-500">Decision:</span>
                  <button
                    onClick={() => handleOutcome('hired')}
                    className="px-3 py-1.5 text-xs rounded-xl font-semibold bg-green-50 text-green-700 ring-1 ring-green-200 hover:bg-green-100 transition-colors"
                  >
                    Hired
                  </button>
                  <button
                    onClick={() => handleOutcome('rejected')}
                    className="px-3 py-1.5 text-xs rounded-xl font-semibold bg-red-50 text-red-700 ring-1 ring-red-200 hover:bg-red-100 transition-colors"
                  >
                    Rejected
                  </button>
                  <button
                    onClick={() => handleOutcome('withdrawn')}
                    className="px-3 py-1.5 text-xs rounded-xl font-semibold bg-slate-50 text-slate-600 ring-1 ring-slate-200 hover:bg-slate-100 transition-colors"
                  >
                    Withdrawn
                  </button>
                </div>
              ) : null}

              {/* Stage Selection — shown after clicking a decision button */}
              {showStageSelect && (
                <div className="mt-3 space-y-3 p-3 bg-white rounded-xl ring-1 ring-brand-100">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-slate-500">Stage:</span>
                    <select
                      value={selectedStage}
                      onChange={(e) => setSelectedStage(e.target.value)}
                      className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2 py-1 focus:outline-none focus:ring-2 focus:ring-brand-300"
                    >
                      <option value="">Select stage (optional)</option>
                      <option value="screening">Screening</option>
                      <option value="phone_screen">Phone Screen</option>
                      <option value="interview">Interview</option>
                      <option value="offer">Offer</option>
                      <option value="onboarded">Onboarded</option>
                    </select>
                  </div>
                  <textarea
                    placeholder="Optional notes about this decision..."
                    value={outcomeNotes}
                    onChange={(e) => setOutcomeNotes(e.target.value)}
                    rows={2}
                    className="w-full text-xs text-slate-600 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-brand-300 placeholder:text-slate-300"
                  />
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleConfirmOutcome}
                      disabled={savingOutcome}
                      className="px-4 py-1.5 text-xs font-bold bg-brand-600 text-white rounded-xl hover:bg-brand-700 disabled:opacity-60 transition-colors flex items-center gap-1.5"
                    >
                      {savingOutcome && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                      Confirm
                    </button>
                    <button
                      onClick={() => { setShowStageSelect(false); setOutcomeStatus(null) }}
                      className="px-3 py-1.5 text-xs font-semibold text-slate-500 hover:text-slate-700 transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}

              {/* Feedback Rating — shown after marking as "hired" */}
              {showFeedback && outcomeId && (
                <div className="mt-3 p-3 bg-white rounded-xl ring-1 ring-brand-100 space-y-3">
                  <div>
                    <span className="text-xs font-semibold text-slate-500">Rate this hire:</span>
                    <div className="flex items-center gap-1 mt-1.5">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <button
                          key={star}
                          onClick={() => setFeedbackRating(star)}
                          className="transition-colors"
                        >
                          <Star
                            className={`w-5 h-5 ${
                              star <= feedbackRating
                                ? 'text-amber-400 fill-amber-400'
                                : 'text-slate-300'
                            }`}
                          />
                        </button>
                      ))}
                    </div>
                  </div>
                  <textarea
                    placeholder="Optional feedback notes..."
                    value={feedbackNotes}
                    onChange={(e) => setFeedbackNotes(e.target.value)}
                    rows={2}
                    className="w-full text-xs text-slate-600 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-brand-300 placeholder:text-slate-300"
                  />
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleSubmitFeedback}
                      disabled={savingFeedback || feedbackRating === 0}
                      className="px-4 py-1.5 text-xs font-bold bg-brand-600 text-white rounded-xl hover:bg-brand-700 disabled:opacity-60 transition-colors flex items-center gap-1.5"
                    >
                      {savingFeedback && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                      Submit Feedback
                    </button>
                    <button
                      onClick={() => setShowFeedback(false)}
                      className="px-3 py-1.5 text-xs font-semibold text-slate-500 hover:text-slate-700 transition-colors"
                    >
                      Skip
                    </button>
                  </div>
                </div>
              )}

              {/* Error message */}
              {outcomeError && (
                <p className="mt-2 text-xs text-red-600">{outcomeError}</p>
              )}
            </div>
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
