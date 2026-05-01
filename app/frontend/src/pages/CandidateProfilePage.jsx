import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Mail, Phone, Briefcase, Building2, Clock, Download, Eye,
  ChevronDown, ChevronRight, CheckCircle2, AlertTriangle, GraduationCap,
  Award, Globe, FileText, Activity
} from 'lucide-react'
import {
  getCandidate, getCandidateTimeline, updateResultStatus,
  downloadCandidateResume, viewCandidateResume
} from '../lib/api'

/** Coerce any value to a render-safe string. Objects become JSON; null/undefined → '' */
function safeStr(v) {
  if (v == null) return ''
  if (typeof v === 'string') return v
  if (typeof v === 'number' || typeof v === 'boolean') return String(v)
  try { return JSON.stringify(v) } catch { return String(v) }
}

const STATUS_OPTIONS = ['pending', 'shortlisted', 'rejected', 'in-review', 'hired']

const STATUS_CONFIG = {
  pending:     { label: 'Pending',     color: 'bg-slate-100 text-slate-700 ring-slate-200' },
  shortlisted: { label: 'Shortlisted', color: 'bg-green-100 text-green-700 ring-green-200' },
  rejected:    { label: 'Rejected',    color: 'bg-red-100 text-red-700 ring-red-200' },
  'in-review': { label: 'In Review',   color: 'bg-amber-100 text-amber-700 ring-amber-200' },
  hired:       { label: 'Hired',       color: 'bg-emerald-100 text-emerald-700 ring-emerald-200' },
}

function ScoreBadge({ score }) {
  if (score == null) return <span className="text-slate-400 text-xs font-medium">—</span>
  let color = 'text-red-700 bg-red-50 ring-red-200'
  if (score >= 70) color = 'text-green-700 bg-green-50 ring-green-200'
  else if (score >= 45) color = 'text-amber-700 bg-amber-50 ring-amber-200'
  return <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ring-1 ${color}`}>{score}</span>
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

function RecommendationBadge({ recommendation }) {
  if (!recommendation) return null
  const r = recommendation.toLowerCase()
  let color = 'bg-slate-100 text-slate-700 ring-slate-200'
  if (r.includes('strong hire') || r.includes('stronghire')) color = 'bg-green-100 text-green-800 ring-green-300'
  else if (r.includes('hire')) color = 'bg-green-50 text-green-700 ring-green-200'
  else if (r.includes('strong reject') || r.includes('strongreject')) color = 'bg-red-100 text-red-800 ring-red-300'
  else if (r.includes('reject')) color = 'bg-red-50 text-red-700 ring-red-200'
  else if (r.includes('shortlist')) color = 'bg-blue-50 text-blue-700 ring-blue-200'
  else if (r.includes('consider')) color = 'bg-amber-50 text-amber-700 ring-amber-200'
  return <span className={`px-2.5 py-1 rounded-full text-xs font-bold ring-1 ${color}`}>{safeStr(recommendation)}</span>
}

function ScoreBar({ label, score, colorClass }) {
  if (score == null) return null
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs font-semibold text-slate-500 w-32 shrink-0">{label}</span>
      <div className="flex-1 h-2.5 bg-slate-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${colorClass}`}
          style={{ width: `${Math.min(score, 100)}%` }}
        />
      </div>
      <span className="text-sm font-bold text-slate-700 w-8 text-right">{score}</span>
    </div>
  )
}

function CollapsibleQuestion({ question, index }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="border border-brand-100 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center gap-2 px-4 py-3 text-left hover:bg-brand-50/40 transition-colors"
      >
        {open ? <ChevronDown className="w-4 h-4 text-brand-500 shrink-0" /> : <ChevronRight className="w-4 h-4 text-brand-400 shrink-0" />}
        <span className="text-sm font-medium text-brand-900">Q{index + 1}: {safeStr(question)}</span>
      </button>
    </div>
  )
}

function TimelineItem({ icon: Icon, iconColor, title, subtitle, detail }) {
  return (
    <div className="flex gap-3 relative">
      <div className="flex flex-col items-center">
        <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${iconColor}`}>
          <Icon className="w-4 h-4" />
        </div>
        <div className="w-px flex-1 bg-brand-100 mt-1" />
      </div>
      <div className="pb-5">
        <p className="text-sm font-semibold text-brand-900">{title}</p>
        {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
        {detail && <p className="text-xs text-slate-400 mt-0.5">{detail}</p>}
      </div>
    </div>
  )
}

function Toast({ message, onDone }) {
  useEffect(() => {
    const t = setTimeout(onDone, 2500)
    return () => clearTimeout(t)
  }, [onDone])
  return (
    <div className="fixed bottom-6 right-6 z-50 bg-brand-900 text-white px-5 py-3 rounded-2xl shadow-brand-lg text-sm font-semibold card-animate">
      {message}
    </div>
  )
}

export default function CandidateProfilePage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [candidate, setCandidate] = useState(null)
  const [timeline, setTimeline] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState(0)
  const [toast, setToast] = useState(null)

  useEffect(() => {
    async function fetchData() {
      setLoading(true)
      setError(null)
      try {
        const [profileData, timelineData] = await Promise.all([
          getCandidate(id),
          getCandidateTimeline(id)
        ])
        setCandidate(profileData)
        setTimeline(timelineData.timeline || [])
      } catch (err) {
        if (err.response?.status === 404) {
          setError('not_found')
        } else {
          setError('error')
        }
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [id])

  const handleStatusChange = async (resultId, newStatus) => {
    try {
      await updateResultStatus(resultId, newStatus)
      setCandidate(prev => ({
        ...prev,
        screening_results: prev.screening_results.map(r =>
          r.id === resultId ? { ...r, status: newStatus } : r
        )
      }))
      setToast(`Status updated to ${STATUS_CONFIG[newStatus]?.label || newStatus}`)
    } catch {
      setToast('Failed to update status')
    }
  }

  // ── Loading State ──
  if (loading) return (
    <div className="flex justify-center py-32">
      <div className="w-8 h-8 border-4 border-brand-600 border-t-transparent rounded-full animate-spin" />
    </div>
  )

  // ── Error State ──
  if (error === 'not_found') return (
    <div className="max-w-5xl mx-auto px-4 py-16 text-center">
      <div className="w-16 h-16 rounded-2xl bg-brand-50 ring-1 ring-brand-200 flex items-center justify-center mx-auto mb-4">
        <Briefcase className="w-8 h-8 text-brand-300" />
      </div>
      <h2 className="text-xl font-bold text-brand-900 mb-2">Candidate Not Found</h2>
      <p className="text-slate-500 mb-6">The candidate you're looking for doesn't exist or has been removed.</p>
      <button
        onClick={() => navigate('/candidates')}
        className="px-5 py-2.5 btn-brand text-white text-sm font-bold rounded-xl shadow-brand-sm"
      >
        Back to Candidates
      </button>
    </div>
  )

  if (error) return (
    <div className="max-w-5xl mx-auto px-4 py-16 text-center">
      <div className="w-16 h-16 rounded-2xl bg-red-50 ring-1 ring-red-200 flex items-center justify-center mx-auto mb-4">
        <AlertTriangle className="w-8 h-8 text-red-300" />
      </div>
      <h2 className="text-xl font-bold text-brand-900 mb-2">Failed to Load Candidate</h2>
      <p className="text-slate-500 mb-6">Something went wrong. Please try again.</p>
      <button
        onClick={() => navigate('/candidates')}
        className="px-5 py-2.5 btn-brand text-white text-sm font-bold rounded-xl shadow-brand-sm"
      >
        Back to Candidates
      </button>
    </div>
  )

  if (!candidate) return null

  // ── Derived Data ──
  const results = candidate.screening_results || []
  const bestScore = results.length > 0
    ? Math.max(...results.map(r => r.fit_score ?? 0))
    : null
  const latestResult = results.length > 0 ? results[results.length - 1] : null
  const currentStatus = latestResult?.status || 'pending'

  const activeResult = results[activeTab] || null

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">

      {/* ── Sticky Header ── */}
      <div className="sticky top-16 z-30 bg-white/95 backdrop-blur-xl rounded-2xl ring-1 ring-brand-100 shadow-brand-sm px-6 py-4 card-animate">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/candidates')}
              className="p-2 hover:bg-brand-50 rounded-xl transition-colors text-slate-400 hover:text-brand-600"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <div className="flex items-center gap-3 flex-wrap">
                <h1 className="text-2xl font-extrabold text-brand-900 tracking-tight">
                  {safeStr(candidate.name) || 'Unknown Candidate'}
                </h1>
                {bestScore != null && <ScoreBadge score={bestScore} />}
                <StatusPill
                  status={currentStatus}
                  onChange={(s) => latestResult && handleStatusChange(latestResult.id, s)}
                />
              </div>
              <div className="flex items-center gap-4 mt-1 text-sm text-slate-500">
                {candidate.email && (
                  <a href={`mailto:${candidate.email}`} className="flex items-center gap-1 hover:text-brand-600 transition-colors">
                    <Mail className="w-3.5 h-3.5" />
                    {safeStr(candidate.email)}
                  </a>
                )}
                {candidate.phone && (
                  <a href={`tel:${candidate.phone}`} className="flex items-center gap-1 hover:text-brand-600 transition-colors">
                    <Phone className="w-3.5 h-3.5" />
                    {safeStr(candidate.phone)}
                  </a>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {candidate.has_resume && (
              <>
                <button
                  onClick={() => viewCandidateResume(candidate.id).catch(() => setToast('Resume not available'))}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold text-brand-700 ring-1 ring-brand-200 hover:bg-brand-50 transition-colors"
                  title="View original resume"
                >
                  <Eye className="w-3.5 h-3.5" />
                  View Resume
                </button>
                <button
                  onClick={() => downloadCandidateResume(candidate.id, candidate.resume_filename || `resume_${candidate.id}.pdf`).catch(() => setToast('Resume not available'))}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold text-brand-700 ring-1 ring-brand-200 hover:bg-brand-50 transition-colors"
                  title="Download original resume"
                >
                  <Download className="w-3.5 h-3.5" />
                  Download
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* ── 2-Column Body ── */}
      <div className="flex flex-col lg:flex-row gap-6">

        {/* ── Left Sidebar (1/3) ── */}
        <div className="w-full lg:w-1/3 space-y-5">

          {/* Contact Card */}
          <div className="bg-white rounded-xl ring-1 ring-brand-100 shadow-brand-sm p-5 space-y-3">
            <h3 className="text-sm font-bold text-brand-700 uppercase tracking-wide">Contact Info</h3>
            <div className="space-y-2">
              {candidate.email ? (
                <div className="flex items-center gap-2 text-sm">
                  <Mail className="w-4 h-4 text-brand-400" />
                  <a href={`mailto:${candidate.email}`} className="text-brand-600 hover:underline">{safeStr(candidate.email)}</a>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-sm text-slate-400">
                  <Mail className="w-4 h-4" />
                  No email
                </div>
              )}
              {candidate.phone ? (
                <div className="flex items-center gap-2 text-sm">
                  <Phone className="w-4 h-4 text-brand-400" />
                  <a href={`tel:${candidate.phone}`} className="text-brand-600 hover:underline">{safeStr(candidate.phone)}</a>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-sm text-slate-400">
                  <Phone className="w-4 h-4" />
                  No phone
                </div>
              )}
              {candidate.current_role && (
                <div className="flex items-center gap-2 text-sm">
                  <Briefcase className="w-4 h-4 text-brand-400" />
                  <span className="text-slate-700">{safeStr(candidate.current_role)}</span>
                </div>
              )}
              {candidate.current_company && (
                <div className="flex items-center gap-2 text-sm">
                  <Building2 className="w-4 h-4 text-brand-400" />
                  <span className="text-slate-700">{safeStr(candidate.current_company)}</span>
                </div>
              )}
              {candidate.total_years_exp != null && (
                <div className="flex items-center gap-2 text-sm">
                  <Clock className="w-4 h-4 text-brand-400" />
                  <span className="text-slate-700">{candidate.total_years_exp} year{candidate.total_years_exp !== 1 ? 's' : ''} experience</span>
                </div>
              )}
              {!candidate.email && !candidate.phone && !candidate.current_role && !candidate.current_company && candidate.total_years_exp == null && (
                <p className="text-sm text-slate-400">No contact information available</p>
              )}
            </div>
          </div>

          {/* Skills Cloud */}
          <div className="bg-white rounded-xl ring-1 ring-brand-100 shadow-brand-sm p-5">
            <h3 className="text-sm font-bold text-brand-700 uppercase tracking-wide mb-3">Skills</h3>
            {candidate.parsed_skills && candidate.parsed_skills.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {candidate.parsed_skills.map((skill, i) => (
                  <span key={i} className="px-2 py-0.5 bg-green-50 text-green-700 text-xs rounded-full font-semibold ring-1 ring-green-100">
                    {safeStr(skill)}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-400">No skills data</p>
            )}
          </div>

          {/* Education Timeline */}
          <div className="bg-white rounded-xl ring-1 ring-brand-100 shadow-brand-sm p-5">
            <h3 className="text-sm font-bold text-brand-700 uppercase tracking-wide mb-3">Education</h3>
            {candidate.parsed_education && candidate.parsed_education.length > 0 ? (
              <div className="space-y-3">
                {candidate.parsed_education.map((edu, i) => (
                  <TimelineItem
                    key={i}
                    icon={GraduationCap}
                    iconColor="bg-blue-50 text-blue-600"
                    title={safeStr(edu.degree) || 'Degree not specified'}
                    subtitle={safeStr(edu.institution) || 'Institution not specified'}
                    detail={edu.year ? `Class of ${safeStr(edu.year)}` : null}
                  />
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-400">No education data</p>
            )}
          </div>

          {/* Certifications */}
          {candidate.certifications && candidate.certifications.length > 0 && (
            <div className="bg-white rounded-xl ring-1 ring-brand-100 shadow-brand-sm p-5">
              <h3 className="text-sm font-bold text-brand-700 uppercase tracking-wide mb-3">Certifications</h3>
              <ul className="space-y-1.5">
                {candidate.certifications.map((cert, i) => (
                  <li key={i} className="flex items-center gap-2 text-sm text-slate-700">
                    <Award className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                    {safeStr(cert)}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Languages */}
          {candidate.languages && candidate.languages.length > 0 && (
            <div className="bg-white rounded-xl ring-1 ring-brand-100 shadow-brand-sm p-5">
              <h3 className="text-sm font-bold text-brand-700 uppercase tracking-wide mb-3">Languages</h3>
              <div className="flex flex-wrap gap-1.5">
                {candidate.languages.map((lang, i) => (
                  <span key={i} className="px-2 py-0.5 bg-slate-50 text-slate-600 text-xs rounded-full font-medium ring-1 ring-slate-200 flex items-center gap-1">
                    <Globe className="w-3 h-3" />
                    {safeStr(lang)}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* ── Right Main Area (2/3) ── */}
        <div className="w-full lg:w-2/3 space-y-5">

          {/* Professional Summary */}
          {candidate.professional_summary && (
            <div className="bg-white rounded-xl ring-1 ring-brand-100 shadow-brand-sm p-5">
              <h3 className="text-sm font-bold text-brand-700 uppercase tracking-wide mb-3">Professional Summary</h3>
              <p className="text-sm text-slate-600 leading-relaxed whitespace-pre-line">{safeStr(candidate.professional_summary)}</p>
            </div>
          )}

          {/* Screening Results Tabs */}
          {results.length > 0 && (
            <div className="bg-white rounded-xl ring-1 ring-brand-100 shadow-brand-sm overflow-hidden">
              <div className="border-b border-brand-100 overflow-x-auto">
                <div className="flex">
                  {results.map((r, i) => (
                    <button
                      key={r.id}
                      onClick={() => setActiveTab(i)}
                      className={`flex items-center gap-2 px-4 py-3 text-sm font-semibold whitespace-nowrap border-b-2 transition-colors shrink-0 ${
                        i === activeTab
                          ? 'border-brand-600 text-brand-700 bg-brand-50/60'
                          : 'border-transparent text-slate-500 hover:text-brand-600 hover:bg-brand-50/30'
                      }`}
                    >
                      {safeStr(r.jd_name) || `Result ${i + 1}`}
                      <ScoreBadge score={r.fit_score} />
                    </button>
                  ))}
                </div>
              </div>

              {activeResult && (
                <div className="p-5 space-y-5">

                  {/* Score Breakdown */}
                  <div className="space-y-2">
                    <h4 className="text-sm font-bold text-slate-700">Score Breakdown</h4>
                    <ScoreBar
                      label="Fit Score"
                      score={activeResult.fit_score}
                      colorClass={
                        activeResult.fit_score >= 70 ? 'bg-green-500' :
                        activeResult.fit_score >= 45 ? 'bg-amber-500' : 'bg-red-500'
                      }
                    />
                    <ScoreBar
                      label="Deterministic Score"
                      score={activeResult.deterministic_score}
                      colorClass={
                        (activeResult.deterministic_score ?? 0) >= 70 ? 'bg-blue-500' :
                        (activeResult.deterministic_score ?? 0) >= 45 ? 'bg-amber-400' : 'bg-red-400'
                      }
                    />
                    <div className="flex items-center gap-3 mt-2">
                      <span className="text-xs font-semibold text-slate-500">Recommendation:</span>
                      <RecommendationBadge recommendation={activeResult.recommendation} />
                      <span className="text-xs text-slate-400">•</span>
                      <StatusPill
                        status={activeResult.status || 'pending'}
                        onChange={(s) => handleStatusChange(activeResult.id, s)}
                      />
                    </div>
                  </div>

                  {/* Skills Comparison */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <h4 className="text-sm font-bold text-slate-700 mb-2">Matched Skills</h4>
                      {activeResult.matched_skills && activeResult.matched_skills.length > 0 ? (
                        <div className="flex flex-wrap gap-1.5">
                          {activeResult.matched_skills.map((skill, i) => (
                            <span key={i} className="px-2 py-0.5 bg-green-50 text-green-700 text-xs rounded-full font-semibold ring-1 ring-green-100">
                              {safeStr(skill)}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-slate-400">No matched skills</p>
                      )}
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-slate-700 mb-2">Missing Skills</h4>
                      {activeResult.missing_skills && activeResult.missing_skills.length > 0 ? (
                        <div className="flex flex-wrap gap-1.5">
                          {activeResult.missing_skills.map((skill, i) => (
                            <span key={i} className="px-2 py-0.5 bg-red-50 text-red-700 text-xs rounded-full font-semibold ring-1 ring-red-100">
                              {safeStr(skill)}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-slate-400">No missing skills</p>
                      )}
                    </div>
                  </div>

                  {/* Strengths & Weaknesses */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <h4 className="text-sm font-bold text-slate-700 mb-2">Strengths</h4>
                      {activeResult.strengths && activeResult.strengths.length > 0 ? (
                        <ul className="space-y-1.5">
                          {activeResult.strengths.map((s, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                              <CheckCircle2 className="w-4 h-4 text-green-500 shrink-0 mt-0.5" />
                              {safeStr(s)}
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-sm text-slate-400">No strengths listed</p>
                      )}
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-slate-700 mb-2">Weaknesses</h4>
                      {activeResult.weaknesses && activeResult.weaknesses.length > 0 ? (
                        <ul className="space-y-1.5">
                          {activeResult.weaknesses.map((w, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                              <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                              {safeStr(w)}
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-sm text-slate-400">No weaknesses listed</p>
                      )}
                    </div>
                  </div>

                  {/* Interview Questions */}
                  {activeResult.interview_questions && activeResult.interview_questions.length > 0 && (
                    <div>
                      <h4 className="text-sm font-bold text-slate-700 mb-2">Interview Questions</h4>
                      <div className="space-y-2">
                        {activeResult.interview_questions.map((q, i) => (
                          <CollapsibleQuestion key={i} question={q} index={i} />
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Narrative Summary */}
                  {activeResult.narrative && (
                    <div>
                      <h4 className="text-sm font-bold text-slate-700 mb-2">Narrative Summary</h4>
                      <div className="bg-brand-50/60 rounded-xl p-4 text-sm text-slate-600 leading-relaxed whitespace-pre-line ring-1 ring-brand-100">
                        {safeStr(activeResult.narrative)}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {results.length === 0 && (
            <div className="bg-white rounded-xl ring-1 ring-brand-100 shadow-brand-sm p-8 text-center">
              <FileText className="w-8 h-8 text-brand-300 mx-auto mb-3" />
              <p className="text-sm text-slate-500 font-medium">No screening results yet</p>
              <p className="text-xs text-slate-400 mt-1">Analyze this candidate against a job description to see results here.</p>
            </div>
          )}

          {/* Work Experience Timeline */}
          {candidate.parsed_work_exp && candidate.parsed_work_exp.length > 0 && (
            <div className="bg-white rounded-xl ring-1 ring-brand-100 shadow-brand-sm p-5">
              <h3 className="text-sm font-bold text-brand-700 uppercase tracking-wide mb-4">Work Experience</h3>
              <div className="space-y-0">
                {candidate.parsed_work_exp.map((exp, i) => (
                  <TimelineItem
                    key={i}
                    icon={Briefcase}
                    iconColor="bg-brand-50 text-brand-600"
                    title={safeStr(exp.title) || 'Role not specified'}
                    subtitle={`${safeStr(exp.company) || 'Company not specified'}${exp.duration ? ` · ${safeStr(exp.duration)}` : ''}`}
                    detail={exp.description ? safeStr(exp.description) : null}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Activity Timeline */}
          {timeline.length > 0 && (
            <div className="bg-white rounded-xl ring-1 ring-brand-100 shadow-brand-sm p-5">
              <h3 className="text-sm font-bold text-brand-700 uppercase tracking-wide mb-4">Activity</h3>
              <div className="space-y-0">
                {timeline.map((evt, i) => (
                  <TimelineItem
                    key={i}
                    icon={Activity}
                    iconColor="bg-slate-50 text-slate-500"
                    title={safeStr(evt.event)}
                    subtitle={evt.jd_name ? `for ${safeStr(evt.jd_name)}` : null}
                    detail={`${new Date(evt.timestamp).toLocaleString()}${evt.details ? ` · ${safeStr(evt.details)}` : ''}`}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {toast && <Toast message={toast} onDone={() => setToast(null)} />}
    </div>
  )
}
