import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Mail, Phone, Briefcase, Building2, Clock, Download, Eye,
  ChevronDown, ChevronRight, ChevronUp, CheckCircle2, CheckCircle, AlertTriangle,
  AlertCircle, Info, ShieldAlert, ClipboardCheck, XCircle, Sparkles,
  GraduationCap, Award, Globe, FileText, Activity, User, X,
  MessageSquare, Trash2
} from 'lucide-react'
import {
  getCandidate, getCandidateTimeline, updateResultStatus,
  downloadCandidateResume, viewCandidateResume,
  getCandidateNotes, addCandidateNote, deleteCandidateNote
} from '../lib/api'

/** Coerce any value to a render-safe string. Objects become JSON; null/undefined → '' */
function safeStr(v) {
  if (v == null) return ''
  if (typeof v === 'string') return v
  if (typeof v === 'number' || typeof v === 'boolean') return String(v)
  try { return JSON.stringify(v) } catch { return String(v) }
}

/** Match active screening result to its full history item */
function getActiveHistory(activeResult, history) {
  if (!activeResult || !history || !history.length) return null
  let m = history.find(h => h.role_template_id && h.role_template_id === activeResult.role_template_id)
  if (!m) m = history.find(h => (h.id || h.result_id) === activeResult.id)
  return m || null
}

/** Deterministic color class from a string */
function stringToColor(str) {
  let hash = 0
  for (let i = 0; i < str.length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash)
  const c = ['bg-blue-100 text-blue-700','bg-indigo-100 text-indigo-700','bg-purple-100 text-purple-700','bg-pink-100 text-pink-700','bg-rose-100 text-rose-700','bg-amber-100 text-amber-700','bg-teal-100 text-teal-700','bg-cyan-100 text-cyan-700']
  return c[Math.abs(hash) % c.length]
}

/** Compute duration string from start/end dates */
function computeDuration(startDate, endDate) {
  if (!startDate) return null
  try {
    const start = new Date(startDate)
    if (isNaN(start.getTime())) return null
    const isPresent = !endDate || endDate.toLowerCase() === 'present'
    const end = isPresent ? new Date() : new Date(endDate)
    if (!isPresent && isNaN(end.getTime())) return null
    let months = (end.getFullYear() - start.getFullYear()) * 12 + (end.getMonth() - start.getMonth())
    if (months < 0) return null
    const y = Math.floor(months / 12), m = months % 12
    if (y > 0 && m > 0) return `${y}y ${m}m`
    if (y > 0) return `${y}y`
    return `${months}m`
  } catch { return null }
}

/** Compute gap months between two date strings */
function computeGapMonths(prevEnd, nextStart) {
  if (!prevEnd || !nextStart) return null
  try {
    const end = new Date(prevEnd), start = new Date(nextStart)
    if (isNaN(end.getTime()) || isNaN(start.getTime())) return null
    const months = (start.getFullYear() - end.getFullYear()) * 12 + (start.getMonth() - end.getMonth())
    return months > 3 ? months : null
  } catch { return null }
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
          <div className="absolute left-0 top-full mt-1 w-36 bg-white border border-gray-200 shadow-lg rounded-xl py-1 z-50">
            {STATUS_OPTIONS.map(s => {
              const sc = STATUS_CONFIG[s]
              return (
                <button
                  key={s}
                  onClick={(e) => { e.stopPropagation(); setOpen(false); onChange(s) }}
                  className={`w-full flex items-center gap-2 px-3 py-2 text-xs font-medium hover:bg-gray-50 transition-colors ${
                    s === status ? 'text-indigo-700 bg-indigo-50/60' : 'text-slate-600'
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
      <span className="text-xs font-semibold text-slate-500 w-36 shrink-0">{label}</span>
      <div className="flex-1 h-2.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 bg-gradient-to-r ${colorClass}`}
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
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center gap-2 px-4 py-3 text-left hover:bg-gray-50 transition-colors"
      >
        {open ? <ChevronDown className="w-4 h-4 text-indigo-500 shrink-0" /> : <ChevronRight className="w-4 h-4 text-gray-400 shrink-0" />}
        <span className="text-sm font-medium text-slate-800">Q{index + 1}: {safeStr(question)}</span>
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
        <div className="w-px flex-1 bg-gray-200 mt-1" />
      </div>
      <div className="pb-5">
        <p className="text-sm font-semibold text-slate-800">{title}</p>
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
    <div className="fixed bottom-6 right-6 z-50 bg-slate-900 text-white px-5 py-3 rounded-2xl shadow-xl text-sm font-semibold animate-in">
      {message}
    </div>
  )
}

/* ── Skeleton loader ── */
function SkeletonBlock({ className }) {
  return <div className={`animate-pulse bg-gray-200 rounded ${className || ''}`} />
}

function ProfileSkeleton() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      {/* Header skeleton */}
      <div className="sticky top-0 z-10 bg-white border-b border-gray-200 shadow-sm px-6 py-4 -mx-4 sm:-mx-6 lg:-mx-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <SkeletonBlock className="w-10 h-10 rounded-lg" />
            <div className="space-y-2">
              <SkeletonBlock className="h-7 w-48 rounded" />
              <SkeletonBlock className="h-4 w-32 rounded" />
            </div>
          </div>
          <div className="flex gap-2">
            <SkeletonBlock className="h-9 w-24 rounded-lg" />
            <SkeletonBlock className="h-9 w-24 rounded-lg" />
          </div>
        </div>
      </div>
      {/* Body skeleton */}
      <div className="flex flex-col lg:flex-row gap-6 mt-6">
        <div className="w-full lg:w-80 space-y-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="bg-white rounded-lg shadow-sm border border-gray-200 p-5 space-y-3">
              <SkeletonBlock className="h-4 w-20 rounded" />
              <SkeletonBlock className="h-3 w-full rounded" />
              <SkeletonBlock className="h-3 w-3/4 rounded" />
              <SkeletonBlock className="h-3 w-1/2 rounded" />
            </div>
          ))}
        </div>
        <div className="flex-1 space-y-4">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-5 space-y-3">
            <SkeletonBlock className="h-4 w-40 rounded" />
            <SkeletonBlock className="h-16 w-full rounded" />
          </div>
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-5 space-y-3">
            <SkeletonBlock className="h-4 w-32 rounded" />
            <SkeletonBlock className="h-3 w-full rounded" />
            <SkeletonBlock className="h-3 w-5/6 rounded" />
          </div>
        </div>
      </div>
    </div>
  )
}

/* ── Card wrapper for consistent styling ── */
function Card({ children, className }) {
  return (
    <div className={`bg-white rounded-lg shadow-sm border border-gray-200 p-5 ${className || ''}`}>
      {children}
    </div>
  )
}

function CardTitle({ children, icon: Icon, badge }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      {Icon && <Icon className="w-4 h-4 text-slate-400" />}
      <h3 className="text-sm font-bold text-slate-700 uppercase tracking-wide">{children}</h3>
      {badge != null && (
        <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-600 ring-1 ring-slate-200">
          {badge}
        </span>
      )}
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
  const [skillsExpanded, setSkillsExpanded] = useState(false)
  const [riskExpanded, setRiskExpanded] = useState(true)
  const [origSummaryExpanded, setOrigSummaryExpanded] = useState(false)
  const [notes, setNotes] = useState([])
  const [notesLoading, setNotesLoading] = useState(false)
  const [newNoteText, setNewNoteText] = useState('')

  const loadNotes = async (candidateId) => {
    setNotesLoading(true)
    try {
      const data = await getCandidateNotes(candidateId)
      setNotes(data)
    } catch {
      setNotes([])
    } finally {
      setNotesLoading(false)
    }
  }

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
        loadNotes(id)
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
  if (loading) return <ProfileSkeleton />

  // ── 404 State ──
  if (error === 'not_found') return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-center">
      <div className="w-20 h-20 rounded-2xl bg-gray-100 ring-1 ring-gray-200 flex items-center justify-center mx-auto mb-5">
        <User className="w-10 h-10 text-gray-300" />
      </div>
      <h2 className="text-2xl font-bold text-slate-900 mb-2">Candidate Not Found</h2>
      <p className="text-slate-500 mb-8 max-w-md mx-auto">
        The candidate you're looking for doesn't exist or may have been removed from the system.
      </p>
      <button
        onClick={() => navigate('/candidates')}
        className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-bold rounded-xl shadow-sm transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Candidates
      </button>
    </div>
  )

  // ── Error State ──
  if (error) return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-center">
      <div className="w-20 h-20 rounded-2xl bg-red-50 ring-1 ring-red-200 flex items-center justify-center mx-auto mb-5">
        <AlertTriangle className="w-10 h-10 text-red-300" />
      </div>
      <h2 className="text-2xl font-bold text-slate-900 mb-2">Failed to Load Candidate</h2>
      <p className="text-slate-500 mb-8">Something went wrong. Please try again.</p>
      <button
        onClick={() => navigate('/candidates')}
        className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-bold rounded-xl shadow-sm transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
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
  const history = candidate.history || []
  const activeHist = getActiveHistory(activeResult, history)

  // Skill grouping for Task 48
  const parsedSkills = (candidate.parsed_skills || []).slice().sort((a, b) =>
    String(a).localeCompare(String(b))
  )
  const SKILLS_PREVIEW = 6
  const matchedSet = new Set((activeResult?.matched_skills || []).map(s => String(s).toLowerCase()))
  const missingSet = new Set((activeResult?.missing_skills || []).map(s => String(s).toLowerCase()))
  const matchedSkills = activeResult ? parsedSkills.filter(s => matchedSet.has(String(s).toLowerCase())) : []
  const missingFromJd = activeResult ? (activeResult.missing_skills || []).filter(s => !parsedSkills.some(p => String(p).toLowerCase() === String(s).toLowerCase())) : []
  const otherSkills = activeResult ? parsedSkills.filter(s => !matchedSet.has(String(s).toLowerCase()) && !missingSet.has(String(s).toLowerCase())) : parsedSkills

  return (
    <div className="min-h-screen bg-gray-50">
      {/* ── Sticky Header ── */}
      <div className="sticky top-0 z-10 bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-4 gap-4">
            <div className="flex items-center gap-4 min-w-0">
              <button
                onClick={() => navigate('/candidates')}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-slate-400 hover:text-slate-600 shrink-0"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              <div className="min-w-0">
                <div className="flex items-center gap-3 flex-wrap">
                  <h1 className="text-xl font-bold text-slate-900 tracking-tight truncate">
                    {safeStr(candidate.name) || 'Unknown Candidate'}
                  </h1>
                  {bestScore != null && <ScoreBadge score={bestScore} />}
                  <StatusPill
                    status={currentStatus}
                    onChange={(s) => latestResult && handleStatusChange(latestResult.id, s)}
                  />
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {candidate.has_resume && (
                <>
                  <button
                    onClick={() => viewCandidateResume(candidate.id).catch(() => setToast('Resume not available'))}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold text-slate-700 ring-1 ring-gray-300 hover:bg-gray-50 transition-colors"
                    title="View original resume"
                  >
                    <Eye className="w-3.5 h-3.5" />
                    View Resume
                  </button>
                  <button
                    onClick={() => downloadCandidateResume(candidate.id, candidate.resume_filename || `resume_${candidate.id}.pdf`).catch(() => setToast('Resume not available'))}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 transition-colors shadow-sm"
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
      </div>

      {/* ── 2-Column Body ── */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex flex-col lg:flex-row gap-6">

          {/* ── Left Sidebar ── */}
          <div className="w-full lg:w-80 shrink-0 space-y-4">

            {/* Contact Card */}
            <Card>
              <CardTitle icon={Mail}>Contact</CardTitle>
              <div className="space-y-2.5">
                {candidate.email ? (
                  <a href={`mailto:${candidate.email}`} className="flex items-center gap-2.5 text-sm text-slate-700 hover:text-indigo-600 transition-colors group">
                    <Mail className="w-4 h-4 text-slate-400 group-hover:text-indigo-500" />
                    <span className="truncate">{safeStr(candidate.email)}</span>
                  </a>
                ) : (
                  <div className="flex items-center gap-2.5 text-sm text-slate-400">
                    <Mail className="w-4 h-4" />
                    <span>No email provided</span>
                  </div>
                )}
                {candidate.phone ? (
                  <a href={`tel:${candidate.phone}`} className="flex items-center gap-2.5 text-sm text-slate-700 hover:text-indigo-600 transition-colors group">
                    <Phone className="w-4 h-4 text-slate-400 group-hover:text-indigo-500" />
                    <span>{safeStr(candidate.phone)}</span>
                  </a>
                ) : (
                  <div className="flex items-center gap-2.5 text-sm text-slate-400">
                    <Phone className="w-4 h-4" />
                    <span>Not provided</span>
                  </div>
                )}
                {candidate.current_role && (
                  <div className="flex items-center gap-2.5 text-sm text-slate-700">
                    <Briefcase className="w-4 h-4 text-slate-400" />
                    <span>{safeStr(candidate.current_role)}</span>
                  </div>
                )}
                {candidate.current_company && (
                  <div className="flex items-center gap-2.5 text-sm text-slate-700">
                    <Building2 className="w-4 h-4 text-slate-400" />
                    <span>{safeStr(candidate.current_company)}</span>
                  </div>
                )}
                {candidate.total_years_exp != null && (
                  <div className="flex items-center gap-2.5 text-sm text-slate-700">
                    <Clock className="w-4 h-4 text-slate-400" />
                    <span>{candidate.total_years_exp} year{candidate.total_years_exp !== 1 ? 's' : ''} experience</span>
                  </div>
                )}
                {!candidate.email && !candidate.phone && !candidate.current_role && !candidate.current_company && candidate.total_years_exp == null && (
                  <p className="text-sm text-slate-400 italic">No contact information available</p>
                )}
              </div>
            </Card>

            {/* Skills Card — Task 48: Skill Relevance Highlighting */}
            <Card>
              <CardTitle icon={Sparkles} badge={parsedSkills.length > 0 ? parsedSkills.length : undefined}>
                {activeResult ? `Skills · Matched ${matchedSkills.length} · Missing ${missingFromJd.length} · Other ${otherSkills.length}` : 'Skills'}
              </CardTitle>
              {parsedSkills.length > 0 ? (
                <div className="space-y-3">
                  {activeResult ? (
                    <>
                      {matchedSkills.length > 0 && (
                        <div>
                          <div className="flex items-center gap-1.5 mb-1.5"><span className="w-2 h-2 rounded-full bg-green-500" /><span className="text-xs font-semibold text-green-700">Matched</span></div>
                          <div className="flex flex-wrap gap-1.5">{(skillsExpanded ? matchedSkills : matchedSkills.slice(0, SKILLS_PREVIEW)).map((s, i) => <span key={i} className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-800 border border-green-300 font-medium">{safeStr(s)}</span>)}{matchedSkills.length > SKILLS_PREVIEW && !skillsExpanded && <button onClick={() => setSkillsExpanded(true)} className="text-xs text-indigo-600 font-semibold">+{matchedSkills.length - SKILLS_PREVIEW} more</button>}</div>
                        </div>
                      )}
                      {missingFromJd.length > 0 && (
                        <div>
                          <div className="flex items-center gap-1.5 mb-1.5"><span className="w-2 h-2 rounded-full bg-red-500" /><span className="text-xs font-semibold text-red-700">Missing from JD</span></div>
                          <div className="flex flex-wrap gap-1.5">{(skillsExpanded ? missingFromJd : missingFromJd.slice(0, SKILLS_PREVIEW)).map((s, i) => <span key={i} className="text-xs px-2 py-0.5 rounded-full bg-red-50 text-red-700 border border-red-200 font-medium">{safeStr(s)}</span>)}{missingFromJd.length > SKILLS_PREVIEW && !skillsExpanded && <button onClick={() => setSkillsExpanded(true)} className="text-xs text-indigo-600 font-semibold">+{missingFromJd.length - SKILLS_PREVIEW} more</button>}</div>
                        </div>
                      )}
                      {otherSkills.length > 0 && (
                        <div>
                          <div className="flex items-center gap-1.5 mb-1.5"><span className="w-2 h-2 rounded-full bg-gray-400" /><span className="text-xs font-semibold text-gray-600">Other Skills</span></div>
                          <div className="flex flex-wrap gap-1.5">{(skillsExpanded ? otherSkills : otherSkills.slice(0, SKILLS_PREVIEW)).map((s, i) => <span key={i} className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-700 font-medium">{safeStr(s)}</span>)}{otherSkills.length > SKILLS_PREVIEW && !skillsExpanded && <button onClick={() => setSkillsExpanded(true)} className="text-xs text-indigo-600 font-semibold">+{otherSkills.length - SKILLS_PREVIEW} more</button>}</div>
                        </div>
                      )}
                      {skillsExpanded && <button onClick={() => setSkillsExpanded(false)} className="text-xs text-slate-500 hover:text-slate-700 font-medium">Show less</button>}
                    </>
                  ) : (
                    <>
                      <div className="flex flex-wrap gap-1.5">{(skillsExpanded ? parsedSkills : parsedSkills.slice(0, 12)).map((skill, i) => <span key={i} className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-700 font-medium">{safeStr(skill)}</span>)}</div>
                      {parsedSkills.length > 12 && !skillsExpanded && <button onClick={() => setSkillsExpanded(true)} className="mt-2 text-xs text-indigo-600 hover:text-indigo-800 font-semibold">Show all ({parsedSkills.length})</button>}
                      {skillsExpanded && <button onClick={() => setSkillsExpanded(false)} className="mt-2 text-xs text-slate-500 hover:text-slate-700 font-medium">Show less</button>}
                    </>
                  )}
                </div>
              ) : (
                <p className="text-sm text-slate-400 italic">No skills data available</p>
              )}
            </Card>

            {/* Education Card */}
            <Card>
              <CardTitle icon={GraduationCap}>Education</CardTitle>
              {candidate.parsed_education && candidate.parsed_education.length > 0 ? (
                <div className="space-y-3">
                  {candidate.parsed_education.map((edu, i) => (
                    <div key={i} className="flex gap-3">
                      <div className="w-8 h-8 rounded-full bg-blue-50 flex items-center justify-center shrink-0">
                        <GraduationCap className="w-4 h-4 text-blue-500" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-slate-800 truncate">{safeStr(edu.degree) || 'Degree not specified'}</p>
                        <p className="text-xs text-slate-500">{safeStr(edu.institution) || 'Institution not specified'}</p>
                        {edu.year && <p className="text-xs text-slate-400">Class of {safeStr(edu.year)}</p>}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center py-3 text-center">
                  <GraduationCap className="w-8 h-8 text-gray-200 mb-2" />
                  <p className="text-sm text-slate-400 italic">No education data available</p>
                </div>
              )}
            </Card>

            {/* Certifications Card */}
            {candidate.certifications && candidate.certifications.length > 0 && (
              <Card>
                <CardTitle icon={Award}>Certifications</CardTitle>
                <ul className="space-y-1.5">
                  {candidate.certifications.map((cert, i) => (
                    <li key={i} className="flex items-center gap-2 text-sm text-slate-700">
                      <Award className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                      {safeStr(cert)}
                    </li>
                  ))}
                </ul>
              </Card>
            )}

            {/* Languages Card */}
            {candidate.languages && candidate.languages.length > 0 && (
              <Card>
                <CardTitle icon={Globe}>Languages</CardTitle>
                <div className="flex flex-wrap gap-1.5">
                  {candidate.languages.map((lang, i) => (
                    <span key={i} className="text-xs px-2 py-0.5 rounded-full bg-slate-50 text-slate-600 font-medium ring-1 ring-slate-200 flex items-center gap-1">
                      <Globe className="w-3 h-3" />
                      {safeStr(lang)}
                    </span>
                  ))}
                </div>
              </Card>
            )}
          </div>

          {/* ── Right Main Area ── */}
          <div className="flex-1 min-w-0 space-y-4">

            {/* Task 47A: Risk/Red Flags Card */}
            {activeHist && (() => {
              const rs = activeHist.risk_summary || {}
              const flags = rs.risk_flags || []
              const gaps = activeHist.employment_gaps || []
              const shortStints = (activeHist.edu_timeline_analysis || {}).short_stints || []
              const eligibility = activeHist.eligibility || {}
              const seniority = rs.seniority_alignment
              const hasCritical = flags.some(f => (f.severity || '').toLowerCase() === 'critical')
              const hasRisks = flags.length > 0 || gaps.length > 0 || shortStints.length > 0 || eligibility.eligible === false || (seniority && seniority.match !== 'match')
              const borderClass = hasCritical ? 'border-red-500' : hasRisks ? 'border-amber-500' : 'border-green-500'
              const riskCount = flags.length + gaps.length + shortStints.length + (eligibility.eligible === false ? 1 : 0)
              const defaultOpen = hasRisks
              const isExpanded = riskExpanded || defaultOpen
              return (
                <div className={`bg-white rounded-lg shadow-sm border border-gray-200 border-l-4 ${borderClass} p-5`}>
                  <button onClick={() => setRiskExpanded(v => !v)} className="w-full flex items-center gap-2 mb-1">
                    <ShieldAlert className={`w-4 h-4 ${hasCritical ? 'text-red-500' : hasRisks ? 'text-amber-500' : 'text-green-500'}`} />
                    <h3 className="text-sm font-bold text-slate-700 uppercase tracking-wide">Risk Assessment</h3>
                    {riskCount > 0 && <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-700 ring-1 ring-red-200">{riskCount} risk{riskCount !== 1 ? 's' : ''}</span>}
                    {isExpanded ? <ChevronUp className="w-4 h-4 text-slate-400 ml-auto" /> : <ChevronDown className="w-4 h-4 text-slate-400 ml-auto" />}
                  </button>
                  {isExpanded && (
                    <div className="mt-3 space-y-2">
                      {flags.map((f, i) => {
                        const sev = (f.severity || '').toLowerCase()
                        const Icon = sev === 'critical' ? AlertTriangle : sev === 'warning' ? AlertCircle : Info
                        const color = sev === 'critical' ? 'text-red-600' : sev === 'warning' ? 'text-amber-600' : 'text-blue-600'
                        return <div key={i} className="flex items-start gap-2"><Icon className={`w-4 h-4 ${color} shrink-0 mt-0.5`} /><div><p className="text-sm font-medium text-slate-800">{safeStr(f.flag)}</p>{f.detail && <p className="text-xs text-slate-500">{safeStr(f.detail)}</p>}</div></div>
                      })}
                      {gaps.map((g, i) => <div key={`gap-${i}`} className="flex items-start gap-2"><Clock className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" /><p className="text-sm text-slate-700">Employment gap: {safeStr(g.duration || g.duration_months ? `${g.duration_months || g.duration} months` : 'Detected')}</p></div>)}
                      {shortStints.map((s, i) => <div key={`stint-${i}`} className="flex items-start gap-2"><AlertCircle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" /><p className="text-sm text-slate-700">Short tenure at {safeStr(s.company)}</p></div>)}
                      {eligibility.eligible === false && <div className="flex items-start gap-2"><XCircle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" /><p className="text-sm text-red-700 font-medium">Eligibility: {safeStr(eligibility.reason || 'Not eligible')}</p></div>}
                      {seniority && seniority.match !== 'match' && <div className="flex items-start gap-2"><AlertCircle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" /><p className="text-sm text-slate-700">Seniority mismatch: {safeStr(seniority.jd_seniority || seniority.expected)} expected, {safeStr(seniority.candidate_seniority || seniority.actual)} found</p></div>}
                      {!hasRisks && <div className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-green-500" /><p className="text-sm text-green-700 font-medium">No significant risks detected</p></div>}
                    </div>
                  )}
                </div>
              )
            })()}

            {/* Task 49A: Professional Summary Card with AI badge */}
            <Card className="relative">
              <CardTitle icon={FileText}>Professional Summary</CardTitle>
              {(() => {
                const aiSummary = activeResult?.candidate_profile_summary || candidate.ai_professional_summary
                const rawSummary = candidate.professional_summary
                const showAi = !!aiSummary
                const showRaw = rawSummary && aiSummary && rawSummary.trim() !== aiSummary.trim()
                return showAi ? (
                  <div>
                    <span className="absolute top-5 right-5 text-xs font-medium text-indigo-500 bg-indigo-50 px-2 py-0.5 rounded-full inline-flex items-center gap-1"><Sparkles className="w-3 h-3" />AI Generated</span>
                    <div className="bg-gray-50 rounded-lg p-4 border border-gray-100"><p className="text-sm text-slate-600 leading-relaxed whitespace-pre-line">{safeStr(aiSummary)}</p></div>
                    {showRaw && (
                      <div className="mt-2">
                        <button onClick={() => setOrigSummaryExpanded(v => !v)} className="text-xs text-slate-500 hover:text-slate-700 font-medium flex items-center gap-1">
                          {origSummaryExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                          View Original Resume Summary
                        </button>
                        {origSummaryExpanded && <p className="mt-1 text-sm text-slate-500 leading-relaxed whitespace-pre-line pl-2 border-l-2 border-gray-200">{safeStr(rawSummary)}</p>}
                      </div>
                    )}
                  </div>
                ) : rawSummary ? (
                  <div className="bg-gray-50 rounded-lg p-4 border border-gray-100"><p className="text-sm text-slate-600 leading-relaxed whitespace-pre-line">{safeStr(rawSummary)}</p></div>
                ) : (
                  <div className="flex flex-col items-center py-6 text-center"><FileText className="w-8 h-8 text-gray-200 mb-2" /><p className="text-sm text-slate-400 italic">No professional summary available</p></div>
                )
              })()}
            </Card>

            {/* Screening Results Tabs */}
            {results.length > 0 && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
                {/* Tab bar */}
                <div className="border-b border-gray-200 overflow-x-auto bg-white">
                  <div className="flex">
                    {results.map((r, i) => (
                      <button
                        key={r.id}
                        onClick={() => setActiveTab(i)}
                        className={`flex items-center gap-2 px-4 py-3 text-sm font-semibold whitespace-nowrap border-b-2 transition-colors shrink-0 ${
                          i === activeTab
                            ? 'border-indigo-600 text-indigo-700 bg-indigo-50/60'
                            : 'border-transparent text-slate-500 hover:text-indigo-600 hover:bg-gray-50'
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

                    {/* Task 47B: JD Requirements Comparison Table */}
                    {activeHist && (() => {
                      const jd = activeHist.jd_analysis || {}
                      const cp = activeHist.candidate_profile || {}
                      const ms = activeResult.matched_skills || []
                      const mis = activeResult.missing_skills || []
                      const reqSkills = jd.required_skills || []
                      const niceSkills = jd.nice_to_have_skills || []
                      const reqYears = jd.required_years
                      const candYears = cp.total_effective_years
                      const niceMatched = niceSkills.filter(ns => parsedSkills.some(ps => String(ps).toLowerCase() === String(ns).toLowerCase())).length
                      const skillPct = reqSkills.length > 0 ? Math.round((ms.length / reqSkills.length) * 100) : 0
                      const skillStatus = skillPct >= 70 ? { icon: CheckCircle, color: 'text-green-600', label: `${skillPct}% matched` } : skillPct >= 40 ? { icon: AlertCircle, color: 'text-amber-600', label: `${skillPct}% matched` } : { icon: XCircle, color: 'text-red-600', label: `${skillPct}% matched` }
                      const expStatus = reqYears != null && candYears != null ? (candYears > reqYears ? { icon: CheckCircle, color: 'text-green-600', label: 'Exceeds' } : candYears >= reqYears - 1 ? { icon: CheckCircle, color: 'text-green-600', label: 'Meets' } : { icon: XCircle, color: 'text-red-600', label: 'Below' }) : null
                      const domainScore = activeHist.skill_analysis?.domain_match_score
                      const domainStatus = domainScore != null ? (domainScore >= 70 ? { icon: CheckCircle, color: 'text-green-600', label: 'Strong match' } : domainScore >= 40 ? { icon: AlertCircle, color: 'text-amber-600', label: 'Partial match' } : { icon: XCircle, color: 'text-red-600', label: 'Weak match' }) : null
                      const srStatus = jd.seniority && cp.current_role ? { icon: CheckCircle, color: 'text-green-600', label: 'Aligned' } : null
                      const rows = [
                        { label: 'Core Skills', expects: `${reqSkills.length} required`, has: `${ms.length} matched`, status: skillStatus },
                        niceSkills.length > 0 ? { label: 'Nice-to-Have', expects: `${niceSkills.length} listed`, has: `${niceMatched} matched`, status: { icon: AlertCircle, color: 'text-amber-600', label: 'Bonus' } } : null,
                        expStatus ? { label: 'Experience', expects: `${reqYears} years`, has: `${candYears} years`, status: expStatus } : null,
                        domainStatus ? { label: 'Domain', expects: safeStr(jd.domain), has: safeStr(activeHist.candidate_domain || cp.current_role), status: domainStatus } : null,
                        srStatus ? { label: 'Seniority', expects: safeStr(jd.seniority), has: safeStr(cp.current_role), status: srStatus } : null,
                      ].filter(Boolean)
                      return rows.length > 0 ? (
                        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                          <div className="flex items-center gap-2 px-4 py-3 bg-gray-50 border-b border-gray-200"><ClipboardCheck className="w-4 h-4 text-slate-400" /><h3 className="text-sm font-bold text-slate-700 uppercase tracking-wide">Requirements Match</h3></div>
                          <table className="w-full text-sm">
                            <thead><tr className="border-b border-gray-200 text-xs text-slate-500 uppercase"><th className="text-left px-4 py-2 font-semibold">Requirement</th><th className="text-left px-4 py-2 font-semibold">JD Expects</th><th className="text-left px-4 py-2 font-semibold">Candidate Has</th><th className="text-left px-4 py-2 font-semibold">Status</th></tr></thead>
                            <tbody>{rows.map((r, i) => { const SIcon = r.status.icon; return <tr key={i} className={i % 2 === 1 ? 'bg-gray-50' : ''}><td className="px-4 py-2 font-medium text-slate-800">{r.label}</td><td className="px-4 py-2 text-slate-600">{r.expects}</td><td className="px-4 py-2 text-slate-600">{r.has}</td><td className="px-4 py-2"><span className={`inline-flex items-center gap-1 ${r.status.color} font-medium`}><SIcon className="w-3.5 h-3.5" />{r.status.label}</span></td></tr> })}</tbody>
                          </table>
                        </div>
                      ) : null
                    })()}

                    {/* Score Breakdown */}
                    <div className="space-y-2.5">
                      <h4 className="text-sm font-bold text-slate-700">Score Breakdown</h4>
                      <ScoreBar
                        label="Fit Score"
                        score={activeResult.fit_score}
                        colorClass={
                          activeResult.fit_score >= 70 ? 'from-green-400 to-green-600' :
                          activeResult.fit_score >= 45 ? 'from-amber-400 to-amber-500' : 'from-red-400 to-red-500'
                        }
                      />
                      <ScoreBar
                        label="Deterministic Score"
                        score={activeResult.deterministic_score}
                        colorClass={
                          (activeResult.deterministic_score ?? 0) >= 70 ? 'from-blue-400 to-blue-600' :
                          (activeResult.deterministic_score ?? 0) >= 45 ? 'from-amber-300 to-amber-500' : 'from-red-300 to-red-500'
                        }
                      />
                      <div className="flex items-center gap-3 mt-2 pt-2 border-t border-gray-100">
                        <span className="text-xs font-semibold text-slate-500">Recommendation:</span>
                        <RecommendationBadge recommendation={activeResult.recommendation} />
                        <span className="text-xs text-slate-300">|</span>
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
                              <span key={i} className="px-2 py-0.5 bg-green-50 text-green-700 text-xs rounded-full font-semibold ring-1 ring-green-200">
                                {safeStr(skill)}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <p className="text-sm text-slate-400 italic">No matched skills</p>
                        )}
                      </div>
                      <div>
                        <h4 className="text-sm font-bold text-slate-700 mb-2">Missing Skills</h4>
                        {activeResult.missing_skills && activeResult.missing_skills.length > 0 ? (
                          <div className="flex flex-wrap gap-1.5">
                            {activeResult.missing_skills.map((skill, i) => (
                              <span key={i} className="px-2 py-0.5 bg-red-50 text-red-700 text-xs rounded-full font-semibold ring-1 ring-red-200">
                                {safeStr(skill)}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <p className="text-sm text-slate-400 italic">No missing skills</p>
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
                          <p className="text-sm text-slate-400 italic">No strengths listed</p>
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
                          <p className="text-sm text-slate-400 italic">No weaknesses listed</p>
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
                        <blockquote className="border-l-4 border-indigo-300 bg-indigo-50/50 rounded-r-lg p-4 text-sm text-slate-600 leading-relaxed whitespace-pre-line italic">
                          {safeStr(activeResult.narrative)}
                        </blockquote>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {results.length === 0 && (
              <Card className="text-center py-8">
                <FileText className="w-10 h-10 text-gray-200 mx-auto mb-3" />
                <p className="text-sm text-slate-500 font-medium">No screening results yet</p>
                <p className="text-xs text-slate-400 mt-1">Analyze this candidate against a job description to see results here.</p>
              </Card>
            )}

            {/* Task 49B: Work Experience Timeline — Enhanced */}
            <Card>
              <CardTitle icon={Briefcase}>Work Experience</CardTitle>
              {candidate.parsed_work_exp && candidate.parsed_work_exp.length > 0 ? (
                <div className="space-y-0">
                  {candidate.parsed_work_exp.map((exp, i) => {
                    const isCurrent = !exp.end_date || String(exp.end_date).toLowerCase() === 'present'
                    const dur = computeDuration(exp.start_date, exp.end_date)
                    const company = safeStr(exp.company) || 'Company not specified'
                    const colorClass = stringToColor(company)
                    const initial = company.charAt(0).toUpperCase()
                    const prevExp = i > 0 ? candidate.parsed_work_exp[i - 1] : null
                    const gapMonths = prevExp ? computeGapMonths(prevExp.end_date, exp.start_date) : null
                    const sameCompany = prevExp && safeStr(prevExp.company).toLowerCase() === company.toLowerCase()
                    return (
                      <div key={i}>
                        {gapMonths != null && (
                          <div className="flex items-center gap-2 py-2 ml-4 border-l-2 border-dashed border-amber-300 pl-4">
                            <span className="text-xs text-amber-600 font-medium">Gap: ~{gapMonths} months</span>
                          </div>
                        )}
                        <div className={`flex gap-3 relative ${isCurrent ? 'border-l-2 border-indigo-500 pl-2 -ml-0.5' : ''}`}>
                          <div className="flex flex-col items-center">
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 text-xs font-bold ${colorClass}`}>{initial}</div>
                            <div className="w-px flex-1 bg-gray-200 mt-1" />
                          </div>
                          <div className="pb-5 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <p className="text-sm font-semibold text-slate-800">{safeStr(exp.title) || 'Role not specified'}</p>
                              {isCurrent && <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-indigo-100 text-indigo-700">Current</span>}
                              {sameCompany && <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-600">{safeStr(prevExp.title) ? 'Internal move' : 'Promoted'}</span>}
                            </div>
                            <p className="text-xs text-slate-500">{company}{exp.duration ? ` · ${safeStr(exp.duration)}` : ''}{dur ? ` · ${dur}` : ''}</p>
                            {exp.description && <p className="text-xs text-slate-400 mt-0.5 line-clamp-2">{safeStr(exp.description)}</p>}
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <div className="flex flex-col items-center py-4 text-center">
                  <Briefcase className="w-8 h-8 text-gray-200 mb-2" />
                  <p className="text-sm text-slate-400 italic">No work experience data available</p>
                </div>
              )}
            </Card>

            {/* Notes Card */}
            <Card>
              <CardTitle icon={MessageSquare} badge={notes.length > 0 ? notes.length : undefined}>Notes</CardTitle>
              {/* Add note form */}
              <div className="flex gap-2 mb-4">
                <textarea
                  value={newNoteText}
                  onChange={(e) => setNewNoteText(e.target.value)}
                  placeholder="Add a note about this candidate..."
                  maxLength={2000}
                  rows={2}
                  className="flex-1 text-sm border border-gray-200 rounded-lg px-3 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-indigo-300 focus:border-indigo-400 placeholder:text-slate-400"
                />
                <button
                  onClick={async () => {
                    if (!newNoteText.trim()) return
                    try {
                      await addCandidateNote(candidate.id, newNoteText.trim())
                      setNewNoteText('')
                      loadNotes(candidate.id)
                      setToast('Note added')
                    } catch {
                      setToast('Failed to add note')
                    }
                  }}
                  disabled={!newNoteText.trim()}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-200 disabled:text-gray-400 text-white text-sm font-semibold rounded-lg transition-colors shrink-0"
                >
                  Add Note
                </button>
              </div>
              {/* Notes list */}
              {notesLoading ? (
                <div className="space-y-3">
                  {[1, 2].map(i => <SkeletonBlock key={i} className="h-16 w-full rounded" />)}
                </div>
              ) : notes.length > 0 ? (
                <div className="space-y-3">
                  {notes.map(note => {
                    const displayName = note.user_name || (note.user_email ? note.user_email.split('@')[0] : 'User')
                    const noteColor = stringToColor(displayName)
                    const initial = displayName.charAt(0).toUpperCase()
                    const relativeTime = (() => {
                      if (!note.created_at) return ''
                      const now = new Date()
                      const then = new Date(note.created_at)
                      const diffMs = now - then
                      const diffMins = Math.floor(diffMs / 60000)
                      if (diffMins < 1) return 'Just now'
                      if (diffMins < 60) return `${diffMins}m ago`
                      const diffHours = Math.floor(diffMins / 60)
                      if (diffHours < 24) return `${diffHours}h ago`
                      const diffDays = Math.floor(diffHours / 24)
                      if (diffDays === 1) return 'Yesterday'
                      if (diffDays < 7) return `${diffDays}d ago`
                      return then.toLocaleDateString()
                    })()
                    return (
                      <div key={note.id} className="flex gap-3 group">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 text-xs font-bold ${noteColor}`}>
                          {initial}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-semibold text-slate-800">{safeStr(displayName)}</span>
                            <span className="text-xs text-slate-400">{relativeTime}</span>
                            {note.is_own && (
                              <button
                                onClick={async () => {
                                  if (!window.confirm('Delete this note?')) return
                                  try {
                                    await deleteCandidateNote(candidate.id, note.id)
                                    loadNotes(candidate.id)
                                    setToast('Note deleted')
                                  } catch {
                                    setToast('Failed to delete note')
                                  }
                                }}
                                className="opacity-0 group-hover:opacity-100 p-1 text-slate-400 hover:text-red-500 transition-all"
                                title="Delete note"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            )}
                          </div>
                          <p className="text-sm text-slate-600 mt-0.5 whitespace-pre-line">{safeStr(note.text)}</p>
                        </div>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <div className="flex flex-col items-center py-4 text-center">
                  <MessageSquare className="w-8 h-8 text-gray-200 mb-2" />
                  <p className="text-sm text-slate-400 italic">No notes yet. Add observations about this candidate.</p>
                </div>
              )}
            </Card>

            {/* Activity Timeline */}
            {timeline.length > 0 && (
              <Card>
                <CardTitle icon={Activity}>Activity</CardTitle>
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
              </Card>
            )}
          </div>
        </div>
      </div>

      {toast && <Toast message={toast} onDone={() => setToast(null)} />}
    </div>
  )
}
