import {
  ThumbsUp, ThumbsDown, AlertTriangle, ChevronDown, ChevronUp,
  CheckCircle, XCircle, Target, TrendingUp, Shield, ClipboardList,
  Copy, Check, Mail, X, Loader2
} from 'lucide-react'
import { useState } from 'react'
import SkillsRadar from './SkillsRadar'
import { generateEmail } from '../lib/api'

function ScoreBar({ label, value, color }) {
  const barColor = {
    green:  'bg-green-500',
    blue:   'bg-blue-500',
    amber:  'bg-amber-500',
    purple: 'bg-purple-500'
  }[color] || 'bg-slate-400'

  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <span className="text-xs font-medium text-slate-600">{label}</span>
        <span className="text-xs font-bold text-slate-700">{value}%</span>
      </div>
      <div className="w-full bg-slate-100 rounded-full h-2">
        <div
          className={`h-2 rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
        />
      </div>
    </div>
  )
}

function RiskBadge({ level }) {
  const styles = {
    Low:    'bg-green-100 text-green-700 border-green-200',
    Medium: 'bg-amber-100 text-amber-700 border-amber-200',
    High:   'bg-red-100 text-red-700 border-red-200'
  }
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold border ${styles[level] || styles.Medium}`}>
      {level} Risk
    </span>
  )
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = () => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }
  return (
    <button
      onClick={handleCopy}
      className="p-1 rounded hover:bg-slate-100 transition-colors text-slate-400 hover:text-slate-700"
      title="Copy"
    >
      {copied ? <Check className="w-3.5 h-3.5 text-green-600" /> : <Copy className="w-3.5 h-3.5" />}
    </button>
  )
}

function EmailModal({ candidateId, resultId, onClose }) {
  const [type, setType]   = useState('shortlist')
  const [draft, setDraft] = useState(null)
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

  const handleCopy = () => {
    if (!draft) return
    navigator.clipboard.writeText(`Subject: ${draft.subject}\n\n${draft.body}`)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg">
        <div className="flex items-center justify-between p-5 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <Mail className="w-5 h-5 text-blue-600" />
            <h3 className="font-semibold text-slate-800">Generate Email</h3>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-slate-100 rounded transition-colors">
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>
        <div className="p-5 space-y-4">
          <div className="flex gap-2">
            {EMAIL_TYPES.map(t => (
              <button
                key={t.value}
                onClick={() => { setType(t.value); setDraft(null) }}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  type === t.value ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          {draft && (
            <div className="space-y-2">
              <div>
                <label className="text-xs font-medium text-slate-500 uppercase tracking-wide">Subject</label>
                <p className="text-sm font-medium text-slate-800 mt-1">{draft.subject}</p>
              </div>
              <div>
                <label className="text-xs font-medium text-slate-500 uppercase tracking-wide">Body</label>
                <textarea
                  value={draft.body}
                  onChange={(e) => setDraft({ ...draft, body: e.target.value })}
                  rows={8}
                  className="w-full mt-1 px-3 py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 resize-none"
                />
              </div>
            </div>
          )}

          <div className="flex justify-between items-center pt-2">
            <button
              onClick={handleGenerate}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-60 transition-colors"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Mail className="w-4 h-4" />}
              {loading ? 'Generating...' : 'Generate'}
            </button>
            {draft && (
              <button
                onClick={handleCopy}
                className="flex items-center gap-2 px-4 py-2 border border-slate-300 text-slate-700 text-sm font-medium rounded-lg hover:bg-slate-50 transition-colors"
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

export default function ResultCard({ result, defaultExpandEducation = false }) {
  const [showEducation, setShowEducation]     = useState(defaultExpandEducation)
  const [showInterviewKit, setShowInterviewKit] = useState(false)
  const [showEmailModal, setShowEmailModal]   = useState(false)
  const [activeQTab, setActiveQTab]           = useState('technical')

  const {
    fit_score, strengths, weaknesses, education_analysis,
    risk_signals, final_recommendation, score_breakdown,
    matched_skills, missing_skills, risk_level,
    interview_questions, result_id, candidate_id
  } = result

  let badgeColor = 'bg-yellow-100 text-yellow-800 border-yellow-200'
  let BadgeIcon  = Target
  if (final_recommendation === 'Shortlist') {
    badgeColor = 'bg-green-100 text-green-800 border-green-200'
    BadgeIcon  = CheckCircle
  } else if (final_recommendation === 'Reject') {
    badgeColor = 'bg-red-100 text-red-800 border-red-200'
    BadgeIcon  = XCircle
  }

  const QTABS = [
    { key: 'technical',    label: 'Technical',    questions: interview_questions?.technical_questions || [] },
    { key: 'behavioral',   label: 'Behavioral',   questions: interview_questions?.behavioral_questions || [] },
    { key: 'culture_fit',  label: 'Culture Fit',  questions: interview_questions?.culture_fit_questions || [] },
  ]

  return (
    <>
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 md:p-8 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h2 className="text-2xl font-semibold text-slate-800">Analysis Results</h2>
          <div className="flex items-center gap-2">
            {risk_level && <RiskBadge level={risk_level} />}
            <span className={`flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-semibold border ${badgeColor}`}>
              <BadgeIcon className="w-4 h-4" />
              {final_recommendation}
            </span>
            <button
              onClick={() => setShowEmailModal(true)}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-slate-200 text-sm text-slate-600 hover:bg-slate-50 transition-colors"
              title="Generate email"
            >
              <Mail className="w-4 h-4" />
              <span className="hidden sm:inline">Email</span>
            </button>
          </div>
        </div>

        {/* Score Breakdown */}
        {score_breakdown && Object.keys(score_breakdown).length > 0 && (
          <div className="bg-slate-50 rounded-lg p-5 border border-slate-200">
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp className="w-4 h-4 text-slate-500" />
              <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">Score Breakdown</h3>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <ScoreBar label="Skill Match"  value={score_breakdown.skill_match || 0}      color="blue" />
              <ScoreBar label="Experience"   value={score_breakdown.experience_match || 0} color="green" />
              <ScoreBar label="Stability"    value={score_breakdown.stability || 0}        color="purple" />
              <ScoreBar label="Education"    value={score_breakdown.education || 0}        color="amber" />
            </div>
          </div>
        )}

        {/* Skills Intel */}
        {((matched_skills?.length > 0) || (missing_skills?.length > 0)) && (
          <div className="grid grid-cols-2 gap-4">
            {matched_skills?.length > 0 && (
              <div className="bg-green-50 rounded-lg p-4 border border-green-100">
                <div className="flex items-center gap-1.5 mb-2">
                  <CheckCircle className="w-4 h-4 text-green-600" />
                  <span className="text-xs font-semibold text-green-700 uppercase tracking-wide">Matched Skills</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {matched_skills.slice(0, 10).map((s, i) => (
                    <span key={i} className="px-2 py-0.5 bg-green-100 text-green-800 text-xs rounded-full font-medium">{s}</span>
                  ))}
                </div>
              </div>
            )}
            {missing_skills?.length > 0 && (
              <div className="bg-red-50 rounded-lg p-4 border border-red-100">
                <div className="flex items-center gap-1.5 mb-2">
                  <XCircle className="w-4 h-4 text-red-600" />
                  <span className="text-xs font-semibold text-red-700 uppercase tracking-wide">Missing Skills</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {missing_skills.slice(0, 8).map((s, i) => (
                    <span key={i} className="px-2 py-0.5 bg-red-100 text-red-800 text-xs rounded-full font-medium">{s}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Skills Gap Visualization */}
        <SkillsRadar matchedSkills={matched_skills || []} missingSkills={missing_skills || []} />

        {/* Strengths / Weaknesses / Risks */}
        <div className="grid md:grid-cols-3 gap-4">
          <div className="bg-green-50 rounded-lg p-4 border-l-4 border-green-500">
            <div className="flex items-center gap-2 mb-3">
              <ThumbsUp className="w-5 h-5 text-green-600" />
              <h3 className="font-semibold text-green-800">Strengths</h3>
            </div>
            <ul className="space-y-2">
              {strengths?.length > 0 ? (
                strengths.slice(0, 5).map((s, i) => (
                  <li key={i} className="text-sm text-green-700 flex items-start gap-2">
                    <span className="text-green-500 mt-1">•</span>{s}
                  </li>
                ))
              ) : <li className="text-sm text-green-600 italic">No specific strengths identified</li>}
            </ul>
          </div>

          <div className="bg-red-50 rounded-lg p-4 border-l-4 border-red-500">
            <div className="flex items-center gap-2 mb-3">
              <ThumbsDown className="w-5 h-5 text-red-600" />
              <h3 className="font-semibold text-red-800">Weaknesses</h3>
            </div>
            <ul className="space-y-2">
              {weaknesses?.length > 0 ? (
                weaknesses.slice(0, 5).map((w, i) => (
                  <li key={i} className="text-sm text-red-700 flex items-start gap-2">
                    <span className="text-red-500 mt-1">•</span>{w}
                  </li>
                ))
              ) : <li className="text-sm text-red-600 italic">No significant weaknesses</li>}
            </ul>
          </div>

          <div className="bg-amber-50 rounded-lg p-4 border-l-4 border-amber-500">
            <div className="flex items-center gap-2 mb-3">
              <Shield className="w-5 h-5 text-amber-600" />
              <h3 className="font-semibold text-amber-800">Risk Signals</h3>
            </div>
            <ul className="space-y-2">
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

        {/* Education (collapsible) */}
        <div className="border border-slate-200 rounded-lg">
          <button
            onClick={() => setShowEducation(!showEducation)}
            className="w-full flex items-center justify-between p-4 hover:bg-slate-50 transition-colors"
          >
            <span className="font-semibold text-slate-700">Education Analysis</span>
            {showEducation ? <ChevronUp className="w-5 h-5 text-slate-500" /> : <ChevronDown className="w-5 h-5 text-slate-500" />}
          </button>
          {showEducation && (
            <div className="px-4 pb-4">
              <p className="text-sm text-slate-600 leading-relaxed">
                {education_analysis || 'No education analysis available.'}
              </p>
            </div>
          )}
        </div>

        {/* Interview Kit */}
        {interview_questions && (
          <div className="border border-blue-100 rounded-lg bg-blue-50/40">
            <button
              onClick={() => setShowInterviewKit(!showInterviewKit)}
              className="w-full flex items-center justify-between p-4 hover:bg-blue-50 transition-colors rounded-lg"
            >
              <div className="flex items-center gap-2">
                <ClipboardList className="w-5 h-5 text-blue-600" />
                <span className="font-semibold text-blue-800">Interview Kit</span>
                <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
                  {(interview_questions.technical_questions?.length || 0) +
                   (interview_questions.behavioral_questions?.length || 0) +
                   (interview_questions.culture_fit_questions?.length || 0)} questions
                </span>
              </div>
              {showInterviewKit ? <ChevronUp className="w-5 h-5 text-blue-600" /> : <ChevronDown className="w-5 h-5 text-blue-600" />}
            </button>

            {showInterviewKit && (
              <div className="px-4 pb-4">
                {/* Tab bar */}
                <div className="flex gap-1 mb-4">
                  {QTABS.filter(t => t.questions.length > 0).map(t => (
                    <button
                      key={t.key}
                      onClick={() => setActiveQTab(t.key)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                        activeQTab === t.key ? 'bg-blue-600 text-white' : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
                      }`}
                    >
                      {t.label} ({t.questions.length})
                    </button>
                  ))}
                </div>
                {/* Questions list */}
                {QTABS.filter(t => t.key === activeQTab).map(t => (
                  <ol key={t.key} className="space-y-2">
                    {t.questions.map((q, i) => (
                      <li key={i} className="flex items-start gap-3 p-3 bg-white rounded-lg border border-slate-100">
                        <span className="text-xs font-bold text-slate-400 mt-0.5 w-5 shrink-0">{i + 1}.</span>
                        <p className="text-sm text-slate-700 flex-1">{q}</p>
                        <CopyButton text={q} />
                      </li>
                    ))}
                  </ol>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Email modal */}
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
