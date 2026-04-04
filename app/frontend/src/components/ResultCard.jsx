import {
  ThumbsUp, ThumbsDown, AlertTriangle, ChevronDown, ChevronUp,
  CheckCircle, XCircle, Target, TrendingUp, Shield, ClipboardList,
  Copy, Check, Mail, X, Loader2, Lightbulb, BookOpen, Compass, Cpu
} from 'lucide-react'
import { useState } from 'react'
import SkillsRadar from './SkillsRadar'
import { generateEmail } from '../lib/api'

// ─── Small reusable components ────────────────────────────────────────────────

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

// ─── Pending banner ────────────────────────────────────────────────────────────

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

  const {
    fit_score, strengths, weaknesses, education_analysis,
    risk_signals, final_recommendation, score_breakdown,
    matched_skills, missing_skills, risk_level,
    interview_questions, result_id, candidate_id,
    // New LangGraph fields
    explainability, adjacent_skills,
    skill_analysis, edu_timeline_analysis, jd_analysis,
    recommendation_rationale,
  } = result

  const isPending = final_recommendation === 'Pending' || fit_score === null || fit_score === undefined

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
              {final_recommendation}
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

        {/* Pending banner */}
        {isPending && <PendingBanner />}

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
              <p className="text-xs text-slate-500 mt-3 italic">{recommendation_rationale}</p>
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
                    <span key={i} className="px-2 py-0.5 bg-green-100 text-green-800 text-xs rounded-lg font-semibold">{s}</span>
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
                    <span key={i} className="px-2 py-0.5 bg-red-100 text-red-800 text-xs rounded-lg font-semibold">{s}</span>
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
                <span key={i} className="px-2 py-0.5 bg-blue-100 text-blue-800 text-xs rounded-lg font-semibold">{s}</span>
              ))}
            </div>
          </div>
        )}

        {/* Skills Gap Visualization */}
        <SkillsRadar matchedSkills={matched_skills || []} missingSkills={missing_skills || []} />

        {/* Strengths / Weaknesses / Risks */}
        <div className="grid md:grid-cols-3 gap-4">
          <div className="bg-green-50 rounded-2xl p-4 ring-1 ring-green-100 border-l-4 border-green-500">
            <div className="flex items-center gap-2 mb-3">
              <ThumbsUp className="w-4 h-4 text-green-600" />
              <h3 className="font-bold text-green-800 text-sm">Strengths</h3>
            </div>
            <ul className="space-y-1.5">
              {strengths?.length > 0 ? (
                strengths.slice(0, 5).map((s, i) => (
                  <li key={i} className="text-sm text-green-700 flex items-start gap-2">
                    <span className="text-green-500 mt-1 shrink-0">•</span>{s}
                  </li>
                ))
              ) : <li className="text-sm text-green-600 italic">No specific strengths identified</li>}
            </ul>
          </div>

          <div className="bg-red-50 rounded-2xl p-4 ring-1 ring-red-100 border-l-4 border-red-400">
            <div className="flex items-center gap-2 mb-3">
              <ThumbsDown className="w-4 h-4 text-red-600" />
              <h3 className="font-bold text-red-800 text-sm">Weaknesses</h3>
            </div>
            <ul className="space-y-1.5">
              {weaknesses?.length > 0 ? (
                weaknesses.slice(0, 5).map((w, i) => (
                  <li key={i} className="text-sm text-red-700 flex items-start gap-2">
                    <span className="text-red-500 mt-1 shrink-0">•</span>{w}
                  </li>
                ))
              ) : <li className="text-sm text-red-600 italic">No significant weaknesses</li>}
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

        {/* Explainability */}
        {explainability && Object.keys(explainability).length > 0 && (
          <CollapsibleSection
            title="Explainability — Why this score?"
            icon={Lightbulb}
            iconColor="text-yellow-600"
            bgColor="bg-yellow-50"
          >
            <div className="space-y-3">
              {explainability.overall_rationale && (
                <div className="p-3 bg-brand-50 rounded-xl ring-1 ring-brand-100">
                  <p className="text-sm font-semibold text-brand-800 mb-1">Overall</p>
                  <p className="text-sm text-slate-600 leading-relaxed">{explainability.overall_rationale}</p>
                </div>
              )}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {[
                  { key: 'skill_rationale',       label: 'Skills' },
                  { key: 'experience_rationale',   label: 'Experience' },
                  { key: 'education_rationale',    label: 'Education' },
                  { key: 'timeline_rationale',     label: 'Timeline' },
                ].filter(f => explainability[f.key]).map(f => (
                  <div key={f.key} className="p-3 bg-slate-50 rounded-xl ring-1 ring-slate-100">
                    <p className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1">{f.label}</p>
                    <p className="text-xs text-slate-600 leading-relaxed">{explainability[f.key]}</p>
                  </div>
                ))}
              </div>
            </div>
          </CollapsibleSection>
        )}

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
                  {edu_timeline_analysis.field_alignment.replace('_', ' ')}
                </span>
              </div>
            )}
            <p className="text-sm text-slate-600 leading-relaxed">
              {edu_timeline_analysis?.education_analysis || education_analysis || 'No education analysis available.'}
            </p>
            {edu_timeline_analysis?.timeline_analysis && (
              <div className="mt-2 pt-2 border-t border-brand-50">
                <p className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1">Timeline</p>
                <p className="text-sm text-slate-600 leading-relaxed">{edu_timeline_analysis.timeline_analysis}</p>
              </div>
            )}
            {edu_timeline_analysis?.gap_interpretation && (
              <div className="mt-2 pt-2 border-t border-brand-50">
                <p className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1">Gap Context</p>
                <p className="text-sm text-slate-600 leading-relaxed italic">{edu_timeline_analysis.gap_interpretation}</p>
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
                  <p className="text-sm text-slate-600 leading-relaxed">{skill_analysis.domain_fit_comment}</p>
                </div>
              )}
              {skill_analysis.architecture_comment && (
                <div className="pt-2 border-t border-teal-50">
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1">Architecture & System Design</p>
                  <p className="text-sm text-slate-600 leading-relaxed">{skill_analysis.architecture_comment}</p>
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
