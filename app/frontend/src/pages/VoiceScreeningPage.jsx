import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  Phone, Settings as SettingsIcon, Clock, CheckCircle2, XCircle,
  AlertTriangle, Play, Pause, RefreshCw, ChevronRight, Loader2,
  Calendar, User, FileText, BarChart3, Mic, Volume2, Shield,
  ChevronDown, ChevronUp, Save, X, Edit3, PhoneCall, PhoneOff,
  MessageSquare, Star, TrendingUp, Search, Download, ExternalLink,
  StickyNote, CheckSquare, Square, Bell,
} from 'lucide-react'
import {
  getVoiceSettings, updateVoiceSettings, suggestInterviewOpening, getVoiceSessions, getVoiceSession,
  rescheduleVoiceCall, cancelVoiceSession,
  getVoiceAnalytics, bulkCancelVoiceSessions, exportVoiceSessions,
  getNextAvailableSlot, getCandidateNotes, addCandidateNote,
} from '../lib/api'
import VoiceScheduleModal from '../components/VoiceScheduleModal'
import VoiceAssessmentPanel from '../components/VoiceAssessmentPanel'
import VoiceTranscriptViewer from '../components/VoiceTranscriptViewer'
import { StaggerContainer, StaggerItem } from '../components/motion'
import usePermissions from '../hooks/usePermissions'

const OPENING_PLACEHOLDERS = '{candidate_first_name}, {role_title}, {company_name}, {bot_name}'

const STATUS_CONFIG = {
  scheduled:  { label: 'Scheduled',  color: 'bg-blue-100 text-blue-700',   icon: Calendar },
  ringing:    { label: 'Ringing',    color: 'bg-amber-100 text-amber-700', icon: Phone },
  in_progress:{ label: 'In Progress',color: 'bg-green-100 text-green-700', icon: PhoneCall },
  completed:  { label: 'Completed',  color: 'bg-emerald-100 text-emerald-700', icon: CheckCircle2 },
  failed:     { label: 'Failed',     color: 'bg-red-100 text-red-700',     icon: XCircle },
  no_answer:  { label: 'No Answer',  color: 'bg-orange-100 text-orange-700', icon: PhoneOff },
  escalated:  { label: 'Escalated',  color: 'bg-purple-100 text-purple-700', icon: AlertTriangle },
  cancelled:  { label: 'Cancelled',  color: 'bg-slate-100 text-slate-600', icon: X },
}

const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const VOICE_OPTIONS = [
  { value: 'female', label: 'Female' },
  { value: 'male', label: 'Male' },
]
const GREETING_OPTIONS = [
  { value: 'professional', label: 'Professional' },
  { value: 'casual', label: 'Casual' },
  { value: 'friendly', label: 'Friendly' },
]
const DETAIL_OPTIONS = [
  { value: 'brief', label: 'Brief Summary' },
  { value: 'full', label: 'Full Detail' },
]
const FOLLOW_UP_OPTIONS = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
]
const TIMEZONE_OPTIONS = [
  { value: 'UTC', label: 'UTC (Coordinated Universal Time)' },
  { value: 'America/New_York', label: 'US Eastern (ET)' },
  { value: 'America/Chicago', label: 'US Central (CT)' },
  { value: 'America/Denver', label: 'US Mountain (MT)' },
  { value: 'America/Los_Angeles', label: 'US Pacific (PT)' },
  { value: 'America/Anchorage', label: 'US Alaska (AKT)' },
  { value: 'Pacific/Honolulu', label: 'US Hawaii (HST)' },
  { value: 'Europe/London', label: 'UK (GMT/BST)' },
  { value: 'Europe/Berlin', label: 'Central Europe (CET)' },
  { value: 'Europe/Paris', label: 'France (CET)' },
  { value: 'Europe/Helsinki', label: 'Eastern Europe (EET)' },
  { value: 'Asia/Dubai', label: 'UAE (GST)' },
  { value: 'Asia/Kolkata', label: 'India (IST)' },
  { value: 'Asia/Bangkok', label: 'Thailand (ICT)' },
  { value: 'Asia/Singapore', label: 'Singapore (SGT)' },
  { value: 'Asia/Shanghai', label: 'China (CST)' },
  { value: 'Asia/Tokyo', label: 'Japan (JST)' },
  { value: 'Australia/Sydney', label: 'Australia Eastern (AEST)' },
  { value: 'Pacific/Auckland', label: 'New Zealand (NZST)' },
]

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.scheduled
  const Icon = cfg.icon
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold ${cfg.color}`}>
      <Icon className="w-3 h-3" />
      {cfg.label}
    </span>
  )
}

function Section({ title, icon: Icon, children, description, action }) {
  return (
    <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6 card-animate">
      <div className="flex items-start justify-between mb-5">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 rounded-2xl bg-brand-50 ring-1 ring-brand-100 flex items-center justify-center shrink-0">
            <Icon className="w-5 h-5 text-brand-600" />
          </div>
          <div>
            <h3 className="font-extrabold text-brand-900 text-lg tracking-tight">{title}</h3>
            {description && <p className="text-sm text-slate-500 mt-0.5">{description}</p>}
          </div>
        </div>
        {action}
      </div>
      {children}
    </div>
  )
}

function Field({ label, children, hint }) {
  return (
    <div>
      <label className="block text-sm font-semibold text-slate-700 mb-1.5">{label}</label>
      {children}
      {hint && <p className="text-xs text-slate-400 mt-1">{hint}</p>}
    </div>
  )
}

function TextInput({ value, onChange, placeholder, type = 'text' }) {
  return (
    <input
      type={type}
      value={value ?? ''}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full px-3.5 py-2.5 bg-white rounded-xl ring-1 ring-slate-200 focus:ring-2 focus:ring-brand-500 focus:border-transparent text-sm transition-all outline-none"
    />
  )
}

function Select({ value, onChange, options }) {
  return (
    <select
      value={value ?? ''}
      onChange={e => onChange(e.target.value)}
      className="w-full px-3.5 py-2.5 bg-white rounded-xl ring-1 ring-slate-200 focus:ring-2 focus:ring-brand-500 focus:border-transparent text-sm transition-all outline-none appearance-none"
    >
      {options.map(o => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  )
}

function DayPicker({ value, onChange }) {
  const days = value || [1, 2, 3, 4, 5]
  function toggle(dayIdx) {
    const next = days.includes(dayIdx)
      ? days.filter(d => d !== dayIdx)
      : [...days, dayIdx].sort()
    onChange(next)
  }
  return (
    <div className="flex gap-1.5">
      {DAY_NAMES.map((name, idx) => {
        const dayNum = idx + 1
        const active = days.includes(dayNum)
        return (
          <button
            key={idx}
            onClick={() => toggle(dayNum)}
            className={`w-9 h-9 rounded-lg text-xs font-bold transition-all ${
              active
                ? 'bg-brand-600 text-white shadow-sm'
                : 'bg-slate-100 text-slate-400 hover:bg-slate-200'
            }`}
          >
            {name}
          </button>
        )
      })}
    </div>
  )
}

export default function VoiceScreeningPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { isAdmin } = usePermissions()
  const initialTab = searchParams.get('tab') === 'settings' ? 'settings' : 'sessions'
  const [settings, setSettings] = useState(null)
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [sessionsLoading, setSessionsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [draft, setDraft] = useState(null)
  // Dirty detection: show save bar when any setting has changed
  const hasChanges = settings && draft && JSON.stringify(settings) !== JSON.stringify(draft)
  const [selectedSession, setSelectedSession] = useState(null)
  const [sessionDetail, setSessionDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [scheduleModal, setScheduleModal] = useState(false)
  const [editingSession, setEditingSession] = useState(null)
  const [activeTab, setActiveTab] = useState(initialTab) // sessions | settings

  useEffect(() => {
    const tab = searchParams.get('tab')
    if (tab === 'settings' || tab === 'sessions') setActiveTab(tab)
  }, [searchParams])
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState(null)
  const [selectedIds, setSelectedIds] = useState(new Set())
  const [analytics, setAnalytics] = useState(null)
  const [candidateNotes, setCandidateNotes] = useState([])
  const [quickNote, setQuickNote] = useState('')
  const [notesLoading, setNotesLoading] = useState(false)
  const [followUpCandidate, setFollowUpCandidate] = useState(null)
  const [suggestingOpening, setSuggestingOpening] = useState(false)

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      const [cfg, sess, analyticsData] = await Promise.all([
        getVoiceSettings(),
        getVoiceSessions({ limit: 50 }),
        getVoiceAnalytics().catch(() => null),
      ])
      setSettings(cfg)
      setDraft(cfg)
      setSessions(sess)
      setAnalytics(analyticsData)
    } catch (err) {
      setError(err.message || 'Failed to load voice settings')
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchSessions = useCallback(async (params = {}) => {
    try {
      setSessionsLoading(true)
      const query = { limit: 50, ...params }
      const sess = await getVoiceSessions(query)
      setSessions(sess)
    } catch { /* ignore */ }
    finally { setSessionsLoading(false) }
  }, [])

  const fetchAnalytics = useCallback(async () => {
    try {
      const data = await getVoiceAnalytics()
      setAnalytics(data)
    } catch { /* ignore */ }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  // Debounced search + filter
  useEffect(() => {
    const timeout = setTimeout(() => {
      const params = { limit: 50 }
      if (searchQuery.length >= 2) params.search = searchQuery
      if (statusFilter) params.status = statusFilter
      fetchSessions(params)
    }, 300)
    return () => clearTimeout(timeout)
  }, [searchQuery, statusFilter])

  async function handleSave() {
    try {
      setSaving(true)
      const updated = await updateVoiceSettings({
        bot_name: draft.bot_name,
        bot_voice_gender: draft.bot_voice_gender,
        greeting_style: draft.greeting_style,
        outbound_phone_number: draft.outbound_phone_number,
        caller_id_name: draft.caller_id_name,
        business_hours_start: draft.business_hours_start,
        business_hours_end: draft.business_hours_end,
        allowed_days: draft.allowed_days,
        timezone: draft.timezone,
        consent_script: draft.consent_script || null,
        call_duration_min: draft.call_duration_min,
        call_duration_max: draft.call_duration_max,
        max_retries: draft.max_retries,
        retry_intervals: draft.retry_intervals,
        assessment_detail_level: draft.assessment_detail_level,
        auto_update_status: draft.auto_update_status,
        follow_up_aggressiveness: draft.follow_up_aggressiveness,
        ...(isAdmin ? {
          use_custom_interview_opening: draft.use_custom_interview_opening ?? false,
          interview_opening_script: draft.interview_opening_script || null,
          company_about_blurb: draft.company_about_blurb || null,
        } : {}),
      })
      setSettings(updated)
      setDraft(updated)
      // settings and draft already synced
    } catch (err) {
      setError(err.message || 'Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  async function handleSessionClick(session) {
    setSelectedSession(session)
    setCandidateNotes([])
    setQuickNote('')
    try {
      setDetailLoading(true)
      const [detail, notes] = await Promise.all([
        getVoiceSession(session.id),
        session.candidate_id ? getCandidateNotes(session.candidate_id).catch(() => []) : Promise.resolve([]),
      ])
      setSessionDetail(detail)
      setCandidateNotes(Array.isArray(notes) ? notes.slice(0, 3) : [])
    } catch { /* ignore */ }
    finally { setDetailLoading(false) }
  }

  async function handleAddQuickNote() {
    if (!quickNote.trim() || !selectedSession?.candidate_id) return
    try {
      setNotesLoading(true)
      await addCandidateNote(selectedSession.candidate_id, quickNote.trim())
      setQuickNote('')
      const notes = await getCandidateNotes(selectedSession.candidate_id)
      setCandidateNotes(Array.isArray(notes) ? notes.slice(0, 3) : [])
    } catch (err) {
      setError(err.message || 'Failed to add note')
    } finally {
      setNotesLoading(false)
    }
  }

  function toggleSessionSelection(id, e) {
    e.stopPropagation()
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  async function handleBulkCancel() {
    if (selectedIds.size === 0) return
    if (!confirm(`Cancel ${selectedIds.size} session(s)?`)) return
    try {
      await bulkCancelVoiceSessions([...selectedIds])
      setSelectedIds(new Set())
      fetchSessions()
      fetchAnalytics()
    } catch (err) {
      setError(err.message || 'Failed to cancel sessions')
    }
  }

  async function handleExportCsv() {
    try {
      await exportVoiceSessions({ status: statusFilter || undefined, search: searchQuery || undefined })
    } catch (err) {
      setError(err.message || 'Failed to export')
    }
  }

  function closeDetail() {
    setSelectedSession(null)
    setSessionDetail(null)
  }

  if (loading) {
    return (
      <div className="h-screen bg-surface flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-brand-600 animate-spin" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-surface">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        {/* Breadcrumb back to the interview hub */}
        <button
          onClick={() => navigate('/ai-interviews')}
          className="inline-flex items-center gap-1 text-sm font-semibold text-slate-500 hover:text-brand-700 transition-colors mb-4"
        >
          <ChevronRight className="w-4 h-4 rotate-180" />
          AI Interviews
        </button>
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-brand-600 to-brand-400 flex items-center justify-center shadow-lg shadow-brand-200">
              <Mic className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-extrabold text-brand-900 tracking-tight">Voice Screening</h1>
              <p className="text-sm text-slate-500">AI-powered phone screening bot</p>
            </div>
          </div>
          <button
            onClick={() => setScheduleModal(true)}
            className="flex items-center gap-2 px-5 py-2.5 bg-brand-600 text-white rounded-xl font-semibold text-sm hover:bg-brand-700 transition-all shadow-sm shadow-brand-200"
          >
            <PhoneCall className="w-4 h-4" />
            Schedule Call
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-6 bg-white/60 backdrop-blur rounded-2xl p-1 ring-1 ring-brand-100 w-fit">
          {[
            { key: 'sessions', label: 'Sessions', icon: Phone },
            { key: 'settings', label: 'Settings', icon: SettingsIcon },
          ].map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-all ${
                activeTab === tab.key
                  ? 'bg-brand-600 text-white shadow-sm'
                  : 'text-slate-500 hover:text-brand-700 hover:bg-brand-50'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 ring-1 ring-red-200 rounded-2xl flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-red-500 shrink-0" />
            <p className="text-sm text-red-700">{error}</p>
            <button onClick={() => setError(null)} aria-label="Dismiss error" className="ml-auto text-red-400 hover:text-red-600">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Sessions Tab */}
        {activeTab === 'sessions' && (
          <div className="space-y-4">
            {/* Analytics Widget */}
            {analytics && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                  { label: 'Total Sessions', value: analytics.total, icon: Phone, color: 'text-brand-600 bg-brand-50' },
                  { label: 'Connection Rate', value: `${analytics.connection_rate}%`, icon: TrendingUp, color: 'text-emerald-600 bg-emerald-50' },
                  { label: 'Avg Duration', value: analytics.avg_duration_seconds ? `${Math.floor(analytics.avg_duration_seconds / 60)}m ${analytics.avg_duration_seconds % 60}s` : '—', icon: Clock, color: 'text-blue-600 bg-blue-50' },
                  { label: 'Today', value: analytics.today_count, icon: Calendar, color: 'text-amber-600 bg-amber-50' },
                ].map((stat, i) => (
                  <div key={i} className="bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 shadow-brand px-4 py-3 flex items-center gap-3">
                    <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${stat.color}`}>
                      <stat.icon className="w-4 h-4" />
                    </div>
                    <div>
                      <p className="text-xs text-slate-400 font-medium">{stat.label}</p>
                      <p className="text-lg font-bold text-slate-800">{stat.value}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {sessionsLoading && (
              <div className="flex justify-center py-8">
                <Loader2 className="w-6 h-6 text-brand-600 animate-spin" />
              </div>
            )}
            {!sessionsLoading && sessions.length === 0 && (
              <div className="text-center py-16">
                <Phone className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                <h3 className="text-lg font-bold text-slate-500 mb-2">No screening sessions yet</h3>
                <p className="text-sm text-slate-400 mb-6">Schedule a voice screening call to get started</p>
                <button
                  onClick={() => setScheduleModal(true)}
                  className="px-5 py-2.5 bg-brand-600 text-white rounded-xl font-semibold text-sm hover:bg-brand-700 transition-all"
                >
                  Schedule First Call
                </button>
              </div>
            )}
            {!sessionsLoading && sessions.length > 0 && (
              <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand overflow-hidden">
                {/* Header with search, filters, actions */}
                <div className="px-6 py-4 border-b border-brand-50 space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="font-bold text-brand-900">Recent Sessions</h3>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={handleExportCsv}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-500 hover:text-brand-600 hover:bg-brand-50 rounded-lg transition-colors"
                        title="Export CSV"
                      >
                        <Download className="w-3.5 h-3.5" />
                        Export
                      </button>
                      <button
                        onClick={() => fetchSessions()}
                        className="p-2 rounded-lg hover:bg-brand-50 text-slate-400 hover:text-brand-600 transition-colors"
                      >
                        <RefreshCw className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                  {/* Search + Status Filter */}
                  <div className="flex items-center gap-3">
                    <div className="relative flex-1">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                      <input
                        type="text"
                        value={searchQuery}
                        onChange={e => setSearchQuery(e.target.value)}
                        placeholder="Search by candidate name, email, or phone..."
                        className="w-full pl-9 pr-3 py-2 bg-slate-50 rounded-xl ring-1 ring-slate-200 focus:ring-2 focus:ring-brand-500 text-sm outline-none transition-all"
                      />
                    </div>
                    <div className="flex gap-1">
                      {[null, 'scheduled', 'completed', 'no_answer', 'failed', 'cancelled'].map(s => (
                        <button
                          key={s || 'all'}
                          onClick={() => setStatusFilter(s)}
                          className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                            statusFilter === s
                              ? 'bg-brand-600 text-white shadow-sm'
                              : 'text-slate-500 hover:bg-slate-100'
                          }`}
                        >
                          {s ? STATUS_CONFIG[s]?.label || s : 'All'}
                        </button>
                      ))}
                    </div>
                  </div>
                  {/* Bulk Actions Bar */}
                  {selectedIds.size > 0 && (
                    <div className="flex items-center gap-3 p-2 bg-brand-50 rounded-xl">
                      <span className="text-sm font-semibold text-brand-700">{selectedIds.size} selected</span>
                      <button
                        onClick={handleBulkCancel}
                        className="flex items-center gap-1 px-3 py-1 text-xs font-semibold text-red-600 bg-red-50 hover:bg-red-100 rounded-lg transition-colors"
                      >
                        <X className="w-3 h-3" /> Cancel Selected
                      </button>
                      <button
                        onClick={() => setSelectedIds(new Set())}
                        className="text-xs text-slate-500 hover:text-slate-700"
                      >
                        Clear
                      </button>
                    </div>
                  )}
                </div>
                <StaggerContainer className="divide-y divide-brand-50">
                  {sessions.map(session => (
                    <StaggerItem key={session.id}>
                    <div
                      className="w-full flex items-center gap-3 px-6 py-4 hover:bg-brand-50/50 transition-colors text-left cursor-pointer"
                      onClick={() => handleSessionClick(session)}
                    >
                      {/* Checkbox */}
                      {['scheduled', 'no_answer', 'failed', 'cancelled', 'ringing'].includes(session.status) && (
                        <button onClick={(e) => toggleSessionSelection(session.id, e)} className="shrink-0">
                          {selectedIds.has(session.id)
                            ? <CheckSquare className="w-4 h-4 text-brand-600" />
                            : <Square className="w-4 h-4 text-slate-300" />
                          }
                        </button>
                      )}
                      <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
                        session.status === 'completed' ? 'bg-emerald-100' :
                        session.status === 'in_progress' ? 'bg-green-100' :
                        session.status === 'failed' ? 'bg-red-100' :
                        'bg-slate-100'
                      }`}>
                        <Phone className={`w-5 h-5 ${
                          session.status === 'completed' ? 'text-emerald-600' :
                          session.status === 'in_progress' ? 'text-green-600' :
                          session.status === 'failed' ? 'text-red-600' :
                          'text-slate-500'
                        }`} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          {session.candidate_id ? (
                            <span
                              onClick={(e) => {
                                e.stopPropagation()
                                navigate(`/candidates/${session.candidate_id}`)
                              }}
                              className="text-sm font-semibold text-brand-600 hover:text-brand-800 hover:underline cursor-pointer"
                            >
                              {session.candidate_name || session.candidate_email || `Candidate #${session.candidate_id}`}
                            </span>
                          ) : (
                            <span className="text-sm font-semibold text-slate-800">
                              {session.candidate_name || session.candidate_email || `Candidate #${session.candidate_id}`}
                            </span>
                          )}
                          <span className="text-[10px] font-mono text-slate-400 bg-slate-50 px-1.5 py-0.5 rounded">
                            #{session.id}
                          </span>
                          {session.match_score != null && (
                            <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                              session.match_score >= 70 ? 'bg-emerald-100 text-emerald-700' :
                              session.match_score >= 50 ? 'bg-amber-100 text-amber-700' :
                              'bg-red-100 text-red-700'
                            }`}>
                              {session.match_score}%
                            </span>
                          )}
                          {session.call_count > 1 && (
                            <span className="text-xs text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded-full font-semibold">
                              {session.call_count}x called
                            </span>
                          )}
                          <StatusBadge status={session.status} />
                          <span className="text-xs text-slate-400">
                            {session.direction === 'inbound' ? '↙ Inbound' : '↗ Outbound'}
                          </span>
                        </div>
                        <div className="flex items-center gap-3 text-xs text-slate-400">
                          {session.jd_title && (
                            <span className="flex items-center gap-1">
                              <FileText className="w-3 h-3" />
                              {session.jd_title}
                            </span>
                          )}
                          <span className="flex items-center gap-1">
                            <Phone className="w-3 h-3" />
                            {session.phone_number}
                          </span>
                          {session.duration_seconds && (
                            <span className="flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              {Math.floor(session.duration_seconds / 60)}m {session.duration_seconds % 60}s
                            </span>
                          )}
                          {session.retry_count > 0 && (
                            <span className="flex items-center gap-1 text-amber-500">
                              <RefreshCw className="w-3 h-3" />
                              Retry #{session.retry_count}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="text-xs text-slate-400 mr-1">
                          {session.scheduled_at
                            ? new Date(session.scheduled_at).toLocaleString('en-US', { timeZone: settings?.timezone || undefined })
                            : session.created_at
                              ? new Date(session.created_at).toLocaleDateString('en-US', { timeZone: settings?.timezone || undefined })
                              : ''}
                          {settings?.timezone && (
                            <span className="ml-1 text-slate-300">
                              {settings.timezone.replace(/_/g, ' ').split('/').pop()}
                            </span>
                          )}
                        </div>
                        {['scheduled', 'no_answer', 'failed', 'cancelled'].includes(session.status) && (
                          <>
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                setEditingSession(session)
                                setScheduleModal(true)
                              }}
                              className="p-1.5 rounded-lg hover:bg-brand-100 text-brand-500 transition-colors"
                              title="Reschedule"
                            >
                              <Edit3 className="w-3.5 h-3.5" />
                            </button>
                            {!['cancelled', 'completed'].includes(session.status) && (
                              <button
                                onClick={async (e) => {
                                  e.stopPropagation()
                                  if (!confirm('Cancel this screening call?')) return
                                  try {
                                    await cancelVoiceSession(session.id)
                                    fetchSessions()
                                    fetchAnalytics()
                                  } catch (err) {
                                    setError(err.message || 'Failed to cancel')
                                  }
                                }}
                                className="p-1.5 rounded-lg hover:bg-red-100 text-red-400 transition-colors"
                                title="Cancel"
                                aria-label="Cancel session"
                              >
                                <X className="w-3.5 h-3.5" />
                              </button>
                            )}
                          </>
                        )}
                        <ChevronRight className="w-4 h-4 text-slate-300" />
                      </div>
                    </div>
                    </StaggerItem>
                  ))}
                </StaggerContainer>
              </div>
            )}
          </div>
        )}

        {/* Settings Tab */}
        {activeTab === 'settings' && draft && (
          <div className="space-y-6">
            {/* Bot Identity */}
            <Section
              title="Bot Identity"
              icon={Volume2}
              description="Configure how the AI bot presents itself to candidates"
              action={
                <div className="flex gap-2">
                  <button
                    onClick={handleSave}
                    disabled={saving || !hasChanges}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-semibold text-white bg-brand-600 hover:bg-brand-700 rounded-lg transition-colors disabled:opacity-50"
                  >
                    {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                    Save
                  </button>
                </div>
              }
            >
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Field label="Bot Name">
                  <TextInput
                    value={draft.bot_name}
                    onChange={v => setDraft({ ...draft, bot_name: v })}
                    placeholder="ARIA"
                  />
                </Field>
                <Field label="Voice">
                  <Select
                    value={draft.bot_voice_gender}
                    onChange={v => setDraft({ ...draft, bot_voice_gender: v })}
                    options={VOICE_OPTIONS}
                  />
                </Field>
                <Field label="Greeting Style">
                  <Select
                    value={draft.greeting_style}
                    onChange={v => setDraft({ ...draft, greeting_style: v })}
                    options={GREETING_OPTIONS}
                  />
                </Field>
                <Field label="Caller ID Name">
                  <TextInput
                    value={draft.caller_id_name}
                    onChange={v => setDraft({ ...draft, caller_id_name: v })}
                    placeholder="ARIA Screening"
                  />
                </Field>
                <Field label="Outbound Phone Number">
                  <TextInput
                    value={draft.outbound_phone_number}
                    onChange={v => setDraft({ ...draft, outbound_phone_number: v })}
                    placeholder="+14155551234"
                    hint="E.164 format"
                  />
                </Field>
              </div>
            </Section>

            {/* Schedule & Business Hours */}
            <Section title="Schedule & Business Hours" icon={Clock} description="When the bot is allowed to make calls">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <Field label="Timezone">
                  <Select
                    value={draft.timezone}
                    onChange={v => setDraft({ ...draft, timezone: v })}
                    options={TIMEZONE_OPTIONS}
                  />
                </Field>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Start Time">
                    <TextInput
                      value={draft.business_hours_start}
                      onChange={v => setDraft({ ...draft, business_hours_start: v })}
                      placeholder="09:00"
                    />
                  </Field>
                  <Field label="End Time">
                    <TextInput
                      value={draft.business_hours_end}
                      onChange={v => setDraft({ ...draft, business_hours_end: v })}
                      placeholder="17:00"
                    />
                  </Field>
                </div>
              </div>
              <Field label="Allowed Days">
                <DayPicker
                  value={draft.allowed_days}
                  onChange={v => setDraft({ ...draft, allowed_days: v })}
                />
              </Field>
            </Section>

            {/* Call Behavior */}
            <Section title="Call Behavior" icon={PhoneCall} description="Duration, retries, and follow-up settings">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                <Field label="Min Duration (sec)">
                  <TextInput
                    value={draft.call_duration_min}
                    onChange={v => setDraft({ ...draft, call_duration_min: parseInt(v) || 180 })}
                    type="number"
                  />
                </Field>
                <Field label="Max Duration (sec)">
                  <TextInput
                    value={draft.call_duration_max}
                    onChange={v => setDraft({ ...draft, call_duration_max: parseInt(v) || 420 })}
                    type="number"
                  />
                </Field>
                <Field label="Max Retries">
                  <TextInput
                    value={draft.max_retries}
                    onChange={v => setDraft({ ...draft, max_retries: parseInt(v) || 3 })}
                    type="number"
                  />
                </Field>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Field label="Assessment Detail Level">
                  <Select
                    value={draft.assessment_detail_level}
                    onChange={v => setDraft({ ...draft, assessment_detail_level: v })}
                    options={DETAIL_OPTIONS}
                  />
                </Field>
                <Field label="Follow-up Aggressiveness">
                  <Select
                    value={draft.follow_up_aggressiveness}
                    onChange={v => setDraft({ ...draft, follow_up_aggressiveness: v })}
                    options={FOLLOW_UP_OPTIONS}
                  />
                </Field>
              </div>
              <div className="mt-4 flex items-center gap-3">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={draft.auto_update_status ?? true}
                    onChange={e => setDraft({ ...draft, auto_update_status: e.target.checked })}
                    className="w-4 h-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                  />
                  <span className="text-sm font-medium text-slate-700">Auto-update candidate status after screening</span>
                </label>
              </div>
            </Section>

            {/* Compliance */}
            <Section title="Compliance" icon={Shield} description="Consent recording and custom scripts">
              {isAdmin && (
                <div className="mb-6 pb-6 border-b border-slate-100 space-y-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-slate-800">Custom interview opening</p>
                      <p className="text-xs text-slate-500 mt-1">
                        Replaces the default voice and live-screen opener. Recording consent stays a separate step.
                        Placeholders: {OPENING_PLACEHOLDERS}
                      </p>
                    </div>
                    <label className="flex items-center gap-2 cursor-pointer shrink-0">
                      <input
                        type="checkbox"
                        checked={draft.use_custom_interview_opening ?? false}
                        onChange={e => setDraft({ ...draft, use_custom_interview_opening: e.target.checked })}
                        className="w-4 h-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                      />
                      <span className="text-sm font-medium text-slate-700">Enabled</span>
                    </label>
                  </div>
                  <Field label="Company context (optional, for AI draft)">
                    <textarea
                      value={draft.company_about_blurb || ''}
                      onChange={e => setDraft({ ...draft, company_about_blurb: e.target.value || null })}
                      placeholder="Brief description of your company for AI-assisted drafting..."
                      rows={2}
                      className="w-full px-3.5 py-2.5 bg-white rounded-xl ring-1 ring-slate-200 focus:ring-2 focus:ring-brand-500 focus:border-transparent text-sm transition-all outline-none resize-none"
                    />
                  </Field>
                  <Field label="Opening script">
                    <textarea
                      value={draft.interview_opening_script || ''}
                      onChange={e => setDraft({ ...draft, interview_opening_script: e.target.value || null })}
                      placeholder={`Hi {candidate_first_name}, this is {bot_name} from {company_name} about the {role_title} role...`}
                      rows={4}
                      disabled={!(draft.use_custom_interview_opening ?? false)}
                      className="w-full px-3.5 py-2.5 bg-white rounded-xl ring-1 ring-slate-200 focus:ring-2 focus:ring-brand-500 focus:border-transparent text-sm transition-all outline-none resize-none disabled:bg-slate-50 disabled:text-slate-400"
                    />
                  </Field>
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      disabled={suggestingOpening}
                      onClick={async () => {
                        try {
                          setSuggestingOpening(true)
                          const { script } = await suggestInterviewOpening({
                            company_about: draft.company_about_blurb || undefined,
                            tone: draft.greeting_style || 'professional',
                          })
                          setDraft(prev => ({
                            ...prev,
                            use_custom_interview_opening: true,
                            interview_opening_script: script,
                          }))
                        } catch (err) {
                          setError(err.message || 'Failed to suggest opening')
                        } finally {
                          setSuggestingOpening(false)
                        }
                      }}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-brand-700 bg-brand-50 hover:bg-brand-100 rounded-lg transition-colors disabled:opacity-50"
                    >
                      {suggestingOpening ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Mic className="w-3.5 h-3.5" />}
                      Suggest draft with AI
                    </button>
                  </div>
                </div>
              )}
              <Field label="Custom Consent Script (optional)">
                <textarea
                  value={draft.consent_script || ''}
                  onChange={e => setDraft({ ...draft, consent_script: e.target.value || null })}
                  placeholder="Leave empty to use default consent script..."
                  rows={3}
                  className="w-full px-3.5 py-2.5 bg-white rounded-xl ring-1 ring-slate-200 focus:ring-2 focus:ring-brand-500 focus:border-transparent text-sm transition-all outline-none resize-none"
                />
              </Field>
            </Section>

            {/* Notifications */}
            <Section title="Notifications" icon={Bell} description="Candidate reminders and notification preferences">
              <div className="space-y-4">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={draft.notification_enabled ?? false}
                    onChange={e => setDraft({ ...draft, notification_enabled: e.target.checked })}
                    className="w-4 h-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                  />
                  <span className="text-sm font-medium text-slate-700">Send candidate SMS/email reminder before scheduled calls</span>
                </label>
                {(draft.notification_enabled) && (
                  <Field label="Reminder Lead Time (minutes)" hint="How many minutes before the call to send the reminder">
                    <TextInput
                      value={draft.notification_lead_minutes ?? 30}
                      onChange={v => setDraft({ ...draft, notification_lead_minutes: parseInt(v) || 30 })}
                      type="number"
                      placeholder="30"
                    />
                  </Field>
                )}
                <p className="text-xs text-slate-400 italic">Notification dispatch requires Twilio SMS / email integration to be configured.</p>
              </div>
            </Section>

            {/* Sticky Save Bar — visible when settings have unsaved changes */}
            {hasChanges && (
              <div className="sticky bottom-0 z-10 bg-white/95 backdrop-blur-md rounded-2xl ring-1 ring-brand-200 shadow-lg px-6 py-4 flex items-center justify-between mt-2">
                <p className="text-sm font-medium text-slate-600">You have unsaved changes</p>
                <div className="flex gap-3">
                  <button
                    onClick={() => setDraft(settings)}
                    className="px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSave}
                    disabled={saving}
                    className="flex items-center gap-2 px-5 py-2 text-sm font-semibold text-white bg-brand-600 hover:bg-brand-700 rounded-xl transition-colors disabled:opacity-50 shadow-sm shadow-brand-200"
                  >
                    {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                    Save Changes
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Session Detail — Split View Panel */}
        {selectedSession && (
          <div className="fixed inset-0 z-50 flex">
            <div className="absolute inset-0 bg-black/20 backdrop-blur-sm" onClick={closeDetail} />
            <div className="relative ml-auto w-full max-w-xl bg-white shadow-2xl overflow-y-auto">
              <div className="sticky top-0 bg-white/95 backdrop-blur-md border-b border-brand-100 px-6 py-4 flex items-center justify-between z-10">
                <div>
                  <h2 className="font-bold text-brand-900">Session #{selectedSession.id}</h2>
                  <div className="flex items-center gap-2 mt-1">
                    <StatusBadge status={selectedSession.status} />
                    <span className="text-xs text-slate-400">
                      {selectedSession.direction === 'inbound' ? 'Inbound' : 'Outbound'}
                    </span>
                    {selectedSession.jd_title && (
                      <span className="text-xs text-slate-400 flex items-center gap-1">
                        <FileText className="w-3 h-3" />
                        {selectedSession.jd_title}
                      </span>
                    )}
                  </div>
                </div>
                <button onClick={closeDetail} aria-label="Close details" className="p-2 rounded-lg hover:bg-slate-100 text-slate-400">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="p-6 space-y-6">
                {detailLoading ? (
                  <div className="flex justify-center py-12">
                    <Loader2 className="w-6 h-6 text-brand-600 animate-spin" />
                  </div>
                ) : sessionDetail ? (
                  <>
                    {/* Session Info */}
                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-3 bg-slate-50 rounded-xl">
                        <p className="text-xs text-slate-400 mb-1">Session ID</p>
                        <p className="text-sm font-mono font-semibold text-brand-600">#{sessionDetail.id}</p>
                      </div>
                      <div className="p-3 bg-slate-50 rounded-xl">
                        <p className="text-xs text-slate-400 mb-1">Phone</p>
                        <p className="text-sm font-semibold text-slate-700">{sessionDetail.phone_number}</p>
                      </div>
                      <div className="p-3 bg-slate-50 rounded-xl">
                        <p className="text-xs text-slate-400 mb-1">Duration</p>
                        <p className="text-sm font-semibold text-slate-700">
                          {sessionDetail.duration_seconds
                            ? `${Math.floor(sessionDetail.duration_seconds / 60)}m ${sessionDetail.duration_seconds % 60}s`
                            : '—'}
                        </p>
                      </div>
                      <div className="p-3 bg-slate-50 rounded-xl">
                        <p className="text-xs text-slate-400 mb-1">Scheduled</p>
                        <p className="text-sm font-semibold text-slate-700">
                          {sessionDetail.scheduled_at
                            ? new Date(sessionDetail.scheduled_at).toLocaleString('en-US', { timeZone: settings?.timezone || undefined })
                            : '—'}
                        </p>
                      </div>
                      <div className="p-3 bg-slate-50 rounded-xl">
                        <p className="text-xs text-slate-400 mb-1">Retries</p>
                        <p className="text-sm font-semibold text-slate-700">{sessionDetail.retry_count}</p>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex flex-wrap gap-2">
                      {['scheduled', 'no_answer', 'failed', 'cancelled'].includes(selectedSession.status) && (
                        <>
                          {!['cancelled', 'completed'].includes(selectedSession.status) && (
                            <button
                              onClick={async () => {
                                try {
                                  await cancelVoiceSession(selectedSession.id)
                                  closeDetail()
                                  fetchSessions()
                                  fetchAnalytics()
                                } catch (err) {
                                  setError(err.message || 'Failed to cancel')
                                }
                              }}
                              className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-red-600 bg-red-50 rounded-xl hover:bg-red-100 transition-colors"
                            >
                              <X className="w-4 h-4" /> Cancel
                            </button>
                          )}
                          <button
                            onClick={() => {
                              setEditingSession(selectedSession)
                              setScheduleModal(true)
                            }}
                            className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-brand-600 bg-brand-50 rounded-xl hover:bg-brand-100 transition-colors"
                          >
                            <RefreshCw className="w-4 h-4" /> Reschedule
                          </button>
                        </>
                      )}
                      {/* Schedule Follow-Up for missed calls */}
                      {['no_answer', 'failed', 'voicemail'].includes(selectedSession.status) && (
                        <button
                          onClick={() => {
                            setFollowUpCandidate({
                              id: selectedSession.candidate_id,
                              name: selectedSession.candidate_name,
                              phone: selectedSession.phone_number,
                            })
                            setScheduleModal(true)
                          }}
                          className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-amber-700 bg-amber-50 rounded-xl hover:bg-amber-100 transition-colors"
                        >
                          <PhoneCall className="w-4 h-4" /> Schedule Follow-Up
                        </button>
                      )}
                      {/* View Report for completed */}
                      {selectedSession.status === 'completed' && selectedSession.candidate_id && (
                        <button
                          onClick={() => navigate(`/candidates/${selectedSession.candidate_id}`)}
                          className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-emerald-700 bg-emerald-50 rounded-xl hover:bg-emerald-100 transition-colors"
                        >
                          <ExternalLink className="w-4 h-4" /> View Candidate Report
                        </button>
                      )}
                    </div>

                    {/* Transcript */}
                    {sessionDetail.transcript && sessionDetail.transcript.length > 0 && (
                      <VoiceTranscriptViewer entries={sessionDetail.transcript} />
                    )}

                    {/* Assessment */}
                    {sessionDetail.assessment_json && (
                      <VoiceAssessmentPanel assessment={
                        typeof sessionDetail.assessment_json === 'string'
                          ? JSON.parse(sessionDetail.assessment_json)
                          : sessionDetail.assessment_json
                      } />
                    )}

                    {/* Quick Notes */}
                    {selectedSession.candidate_id && (
                      <div className="bg-slate-50 rounded-2xl p-4">
                        <h3 className="text-sm font-bold text-slate-700 mb-3 flex items-center gap-2">
                          <StickyNote className="w-4 h-4" />
                          Quick Notes
                        </h3>
                        <div className="flex gap-2 mb-3">
                          <input
                            type="text"
                            value={quickNote}
                            onChange={e => setQuickNote(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && handleAddQuickNote()}
                            placeholder="Add a quick note about this candidate..."
                            className="flex-1 px-3 py-2 bg-white rounded-xl ring-1 ring-slate-200 focus:ring-2 focus:ring-brand-500 text-sm outline-none"
                          />
                          <button
                            onClick={handleAddQuickNote}
                            disabled={notesLoading || !quickNote.trim()}
                            className="px-3 py-2 text-sm font-semibold text-white bg-brand-600 hover:bg-brand-700 rounded-xl transition-colors disabled:opacity-50"
                          >
                            {notesLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Add'}
                          </button>
                        </div>
                        {candidateNotes.length > 0 && (
                          <div className="space-y-2">
                            {candidateNotes.map(note => (
                              <div key={note.id} className="px-3 py-2 bg-white rounded-lg ring-1 ring-slate-100">
                                <p className="text-sm text-slate-700">{note.text}</p>
                                <p className="text-xs text-slate-400 mt-1">
                                  {note.created_at ? new Date(note.created_at).toLocaleString() : ''}
                                </p>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </>
                ) : (
                  <p className="text-center text-slate-400 py-8">Failed to load session details</p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Schedule Modal */}
        {scheduleModal && (
          <VoiceScheduleModal
            editSession={editingSession}
            preselectedCandidate={followUpCandidate}
            onClose={() => {
              setScheduleModal(false)
              setEditingSession(null)
              setFollowUpCandidate(null)
            }}
            onScheduled={() => {
              setScheduleModal(false)
              setEditingSession(null)
              setFollowUpCandidate(null)
              fetchSessions()
              fetchAnalytics()
            }}
          />
        )}
      </div>
    </div>
  )
}
