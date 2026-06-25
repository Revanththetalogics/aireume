import { useState, useEffect, useCallback, useMemo } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Mic, Brain, BarChart3, Settings as SettingsIcon, Plus, Search,
  RefreshCw, Clock, CheckCircle2, XCircle, AlertTriangle, Loader2,
  Calendar, FileText, ChevronRight, Download, Save, X, TrendingUp,
  Users, Target, Zap, Phone, PhoneCall, Volume2, Shield, Bell,
} from 'lucide-react'
import {
  getVoiceSessions, getVoiceSettings, updateVoiceSettings,
  getVoiceAnalytics, cancelVoiceSession, exportVoiceSessions,
  getRecruiterSessions, getRecruiterAnalytics, getRecruiterConfig,
  updateRecruiterConfig, cancelRecruiterSession, exportRecruiterSessions,
} from '../lib/api'
import InterviewInitiateModal from '../components/InterviewInitiateModal'

/* ── Depth config ────────────────────────────────────── */
const DEPTH_CONFIG = {
  quick:    { label: 'Quick Screen',     color: 'bg-blue-100 text-blue-700',     icon: Phone },
  standard: { label: 'Standard Interview', color: 'bg-purple-100 text-purple-700', icon: Brain },
  deep:     { label: 'Deep Assessment',  color: 'bg-amber-100 text-amber-700',   icon: Target },
}

/* ── Unified status config ───────────────────────────── */
const STATUS_CONFIG = {
  scheduled:        { label: 'Scheduled',   color: 'bg-neutral-100 text-neutral-700' },
  ringing:          { label: 'Ringing',     color: 'bg-amber-100 text-amber-700' },
  in_progress:      { label: 'In Progress', color: 'bg-blue-100 text-blue-700' },
  pending_strategy: { label: 'Preparing',   color: 'bg-neutral-100 text-neutral-700' },
  strategy_ready:   { label: 'Ready',       color: 'bg-blue-100 text-blue-700' },
  completed:        { label: 'Completed',   color: 'bg-emerald-100 text-emerald-700' },
  failed:           { label: 'Failed',      color: 'bg-red-100 text-red-700' },
  no_answer:        { label: 'No Answer',   color: 'bg-orange-100 text-orange-700' },
  cancelled:        { label: 'Cancelled',   color: 'bg-gray-100 text-gray-500' },
  expired:          { label: 'Expired',     color: 'bg-orange-100 text-orange-600' },
}

/* ── Reusable sub-components ─────────────────────────── */

function DepthBadge({ depth }) {
  const cfg = DEPTH_CONFIG[depth] || DEPTH_CONFIG.standard
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${cfg.color}`}>
      {cfg.label}
    </span>
  )
}

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.scheduled
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${cfg.color}`}>
      {cfg.label}
    </span>
  )
}

function StatCard({ label, value, icon: Icon, color }) {
  return (
    <div className="bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 shadow-sm px-4 py-3 flex items-center gap-3">
      <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${color}`}>
        <Icon className="w-4 h-4" />
      </div>
      <div>
        <p className="text-xs text-slate-400 font-medium">{label}</p>
        <p className="text-lg font-bold text-slate-800">{value}</p>
      </div>
    </div>
  )
}

function Section({ title, icon: Icon, children, description, action }) {
  return (
    <div className="bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 shadow-sm p-6">
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

/* ── Session normalization ───────────────────────────── */

function normalizeVoiceSession(s) {
  return {
    id: `v-${s.id}`,
    rawId: s.id,
    source: 'voice',
    depth: 'quick',
    candidate_id: s.candidate_id,
    candidate_name: s.candidate_name || s.candidate_email || `Candidate #${s.candidate_id}`,
    jd_title: s.jd_title || null,
    status: s.status,
    duration_seconds: s.duration_seconds || null,
    score: s.match_score ?? null,
    recommendation: null,
    created_at: s.created_at,
    scheduled_at: s.scheduled_at,
    direction: s.direction,
    phone_number: s.phone_number,
  }
}

function normalizeRecruiterSession(s) {
  const isDeep = (s.duration_seconds || 0) > 900 ||
    (s.overall_score != null) ||
    s.recommendation ||
    s.status === 'completed'
  return {
    id: `r-${s.id}`,
    rawId: s.id,
    source: 'recruiter',
    depth: isDeep ? 'deep' : 'standard',
    candidate_id: s.candidate_id,
    candidate_name: s.candidate_name || `Candidate #${s.candidate_id}`,
    jd_title: s.jd_title || null,
    status: s.status,
    duration_seconds: s.duration_seconds || null,
    score: s.overall_score ?? null,
    recommendation: s.recommendation || null,
    created_at: s.created_at,
    scheduled_at: null,
    direction: null,
    phone_number: null,
  }
}

/* ── Main component ──────────────────────────────────── */

export default function InterviewPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const initialDepth = searchParams.get('depth') || 'all'

  const [voiceSessions, setVoiceSessions] = useState([])
  const [recruiterSessions, setRecruiterSessions] = useState([])
  const [voiceAnalytics, setVoiceAnalytics] = useState(null)
  const [recruiterAnalytics, setRecruiterAnalytics] = useState(null)
  const [config, setConfig] = useState(null)
  const [configDraft, setConfigDraft] = useState(null)
  const [loading, setLoading] = useState(true)
  const [sessionsLoading, setSessionsLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('sessions')
  const [depthFilter, setDepthFilter] = useState(initialDepth)
  const [statusFilter, setStatusFilter] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [showInitiateModal, setShowInitiateModal] = useState(false)

  const configDirty = config && configDraft && JSON.stringify(config) !== JSON.stringify(configDraft)

  // Merge + normalize sessions
  const allSessions = useMemo(() => {
    const voice = voiceSessions.map(normalizeVoiceSession)
    const recruiter = recruiterSessions.map(normalizeRecruiterSession)
    return [...voice, ...recruiter].sort((a, b) =>
      new Date(b.created_at || 0) - new Date(a.created_at || 0)
    )
  }, [voiceSessions, recruiterSessions])

  // Apply filters
  const filteredSessions = useMemo(() => {
    let list = allSessions
    if (depthFilter && depthFilter !== 'all') list = list.filter(s => s.depth === depthFilter)
    if (statusFilter) list = list.filter(s => s.status === statusFilter)
    if (searchQuery.length >= 2) {
      const q = searchQuery.toLowerCase()
      list = list.filter(s =>
        s.candidate_name?.toLowerCase().includes(q) ||
        s.jd_title?.toLowerCase().includes(q)
      )
    }
    return list
  }, [allSessions, depthFilter, statusFilter, searchQuery])

  // Depth counts
  const depthCounts = useMemo(() => ({
    all: allSessions.length,
    quick: allSessions.filter(s => s.depth === 'quick').length,
    standard: allSessions.filter(s => s.depth === 'standard').length,
    deep: allSessions.filter(s => s.depth === 'deep').length,
  }), [allSessions])

  const fetchAll = useCallback(async () => {
    try {
      setLoading(true)
      const [vs, rs, va, ra, cfg] = await Promise.all([
        getVoiceSessions({ limit: 50 }).catch(() => []),
        getRecruiterSessions({ limit: 50 }).catch(() => []),
        getVoiceAnalytics().catch(() => null),
        getRecruiterAnalytics().catch(() => null),
        Promise.all([getVoiceSettings().catch(() => null), getRecruiterConfig().catch(() => null)]),
      ])
      setVoiceSessions(Array.isArray(vs) ? vs : vs.sessions || [])
      setRecruiterSessions(Array.isArray(rs) ? rs : rs.sessions || [])
      setVoiceAnalytics(va)
      setRecruiterAnalytics(ra)
      const mergedCfg = { voice: cfg[0], recruiter: cfg[1] }
      setConfig(mergedCfg)
      setConfigDraft(mergedCfg)
    } catch (err) {
      setError(err.message || 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchAll() }, [fetchAll])

  async function handleSaveConfig() {
    try {
      setSaving(true)
      const results = {}
      if (configDraft.voice) {
        results.voice = await updateVoiceSettings(configDraft.voice)
      }
      if (configDraft.recruiter) {
        results.recruiter = await updateRecruiterConfig(configDraft.recruiter)
      }
      const updated = { voice: results.voice || configDraft.voice, recruiter: results.recruiter || configDraft.recruiter }
      setConfig(updated)
      setConfigDraft(updated)
    } catch (err) {
      setError(err.message || 'Failed to save config')
    } finally {
      setSaving(false)
    }
  }

  async function handleCancelSession(session) {
    if (!confirm('Cancel this interview session?')) return
    try {
      if (session.source === 'voice') {
        await cancelVoiceSession(session.rawId)
      } else {
        await cancelRecruiterSession(session.rawId)
      }
      // Refresh sessions
      const [vs, rs] = await Promise.all([
        getVoiceSessions({ limit: 50 }).catch(() => []),
        getRecruiterSessions({ limit: 50 }).catch(() => []),
      ])
      setVoiceSessions(Array.isArray(vs) ? vs : vs.sessions || [])
      setRecruiterSessions(Array.isArray(rs) ? rs : rs.sessions || [])
    } catch (err) {
      setError(err.message || 'Failed to cancel')
    }
  }

  function handleSessionClick(session) {
    navigate(`/ai-interviews/${session.rawId}?source=${session.source}&depth=${session.depth}`)
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
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-brand-600 to-brand-400 flex items-center justify-center shadow-lg shadow-brand-200">
              <Mic className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-extrabold text-brand-900 tracking-tight">AI Interview</h1>
              <p className="text-sm text-slate-500">Unified AI-powered screening &amp; interviews</p>
            </div>
          </div>
          <button
            onClick={() => setShowInitiateModal(true)}
            className="flex items-center gap-2 px-5 py-2.5 bg-brand-600 text-white rounded-xl font-semibold text-sm hover:bg-brand-700 transition-all shadow-sm shadow-brand-200"
          >
            <Plus className="w-4 h-4" />
            New Interview
          </button>
        </div>

        {/* Depth filter tabs */}
        <div className="flex items-center gap-2 mb-4">
          <div className="flex gap-1 bg-white/60 backdrop-blur rounded-2xl p-1 ring-1 ring-brand-100">
            {[
              { key: 'all', label: 'All' },
              { key: 'quick', label: 'Quick' },
              { key: 'standard', label: 'Standard' },
              { key: 'deep', label: 'Deep' },
            ].map(tab => (
              <button
                key={tab.key}
                onClick={() => setDepthFilter(tab.key)}
                className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-sm font-semibold transition-all ${
                  depthFilter === tab.key
                    ? 'bg-brand-600 text-white shadow-sm'
                    : 'text-slate-500 hover:text-brand-700 hover:bg-brand-50'
                }`}
              >
                {tab.label}
                <span className={`text-xs font-bold px-1.5 py-0.5 rounded-full ${
                  depthFilter === tab.key ? 'bg-white/20 text-white' : 'bg-slate-100 text-slate-500'
                }`}>
                  {depthCounts[tab.key]}
                </span>
              </button>
            ))}
          </div>
          <div className="relative flex-1 max-w-xs ml-auto">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search candidates..."
              className="w-full pl-9 pr-3 py-2 bg-white rounded-xl ring-1 ring-slate-200 focus:ring-2 focus:ring-brand-500 text-sm outline-none transition-all"
            />
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-6 bg-white/60 backdrop-blur rounded-2xl p-1 ring-1 ring-brand-100 w-fit">
          {[
            { key: 'sessions', label: 'Sessions', icon: Users },
            { key: 'analytics', label: 'Analytics', icon: BarChart3 },
            { key: 'config', label: 'Configuration', icon: SettingsIcon },
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
            <button onClick={() => setError(null)} className="ml-auto text-red-400 hover:text-red-600">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Sessions Tab */}
        {activeTab === 'sessions' && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
            {/* Quick stats */}
            {(voiceAnalytics || recruiterAnalytics) && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <StatCard label="Total Sessions" value={depthCounts.all} icon={Users} color="text-brand-600 bg-brand-50" />
                <StatCard label="Quick Screens" value={depthCounts.quick} icon={Phone} color="text-blue-600 bg-blue-50" />
                <StatCard label="Interviews" value={depthCounts.standard + depthCounts.deep} icon={Brain} color="text-purple-600 bg-purple-50" />
                <StatCard label="Completed" value={allSessions.filter(s => s.status === 'completed').length} icon={CheckCircle2} color="text-emerald-600 bg-emerald-50" />
              </div>
            )}

            {sessionsLoading && (
              <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 text-brand-600 animate-spin" /></div>
            )}

            {!sessionsLoading && filteredSessions.length === 0 && (
              <div className="text-center py-16">
                <Mic className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                <h3 className="text-lg font-bold text-slate-500 mb-2">No interview sessions</h3>
                <p className="text-sm text-slate-400 mb-6">
                  {depthFilter !== 'all' ? `No ${depthFilter} sessions found` : 'Start a new AI interview to get started'}
                </p>
                <button
                  onClick={() => setShowInitiateModal(true)}
                  className="px-5 py-2.5 bg-brand-600 text-white rounded-xl font-semibold text-sm hover:bg-brand-700 transition-all"
                >
                  Start First Interview
                </button>
              </div>
            )}

            {!sessionsLoading && filteredSessions.length > 0 && (
              <div className="bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-brand-50 flex items-center justify-between">
                  <h3 className="font-bold text-brand-900">
                    {filteredSessions.length} session{filteredSessions.length !== 1 ? 's' : ''}
                  </h3>
                  <div className="flex items-center gap-2">
                    <div className="flex gap-1">
                      {[null, 'in_progress', 'completed', 'failed', 'cancelled'].map(s => (
                        <button
                          key={s || 'all'}
                          onClick={() => setStatusFilter(s)}
                          className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                            statusFilter === s
                              ? 'bg-brand-600 text-white shadow-sm'
                              : 'text-slate-500 hover:bg-slate-100'
                          }`}
                        >
                          {s ? STATUS_CONFIG[s]?.label || s : 'All Status'}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="divide-y divide-brand-50">
                  {filteredSessions.map(session => (
                    <div
                      key={session.id}
                      className="flex items-center gap-3 px-6 py-4 hover:bg-brand-50/50 transition-colors cursor-pointer"
                      onClick={() => handleSessionClick(session)}
                    >
                      <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
                        session.status === 'completed' ? 'bg-emerald-100' :
                        session.status === 'in_progress' ? 'bg-blue-100' :
                        session.status === 'failed' ? 'bg-red-100' :
                        'bg-slate-100'
                      }`}>
                        {session.depth === 'quick' ? (
                          <Phone className={`w-5 h-5 ${
                            session.status === 'completed' ? 'text-emerald-600' :
                            session.status === 'in_progress' ? 'text-blue-600' :
                            session.status === 'failed' ? 'text-red-600' : 'text-slate-500'
                          }`} />
                        ) : (
                          <Brain className={`w-5 h-5 ${
                            session.status === 'completed' ? 'text-emerald-600' :
                            session.status === 'in_progress' ? 'text-blue-600' :
                            session.status === 'failed' ? 'text-red-600' : 'text-slate-500'
                          }`} />
                        )}
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                          <span className="text-sm font-semibold text-brand-700">
                            {session.candidate_name}
                          </span>
                          <DepthBadge depth={session.depth} />
                          <StatusBadge status={session.status} />
                          {session.recommendation && (
                            <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                              session.recommendation === 'strong_hire' || session.recommendation === 'hire'
                                ? 'bg-emerald-100 text-emerald-700' :
                              session.recommendation === 'maybe' ? 'bg-amber-100 text-amber-700' :
                              'bg-red-100 text-red-700'
                            }`}>
                              {session.recommendation.replace(/_/g, ' ')}
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-3 text-xs text-slate-400">
                          {session.jd_title && (
                            <span className="flex items-center gap-1">
                              <FileText className="w-3 h-3" />{session.jd_title}
                            </span>
                          )}
                          {session.duration_seconds != null && (
                            <span className="flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              {Math.floor(session.duration_seconds / 60)}m {session.duration_seconds % 60}s
                            </span>
                          )}
                          {session.score != null && (
                            <span className={`font-bold ${
                              session.score >= 70 ? 'text-emerald-600' :
                              session.score >= 40 ? 'text-amber-600' : 'text-red-600'
                            }`}>
                              Score: {session.score}
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <span className="text-xs text-slate-400">
                          {session.created_at ? new Date(session.created_at).toLocaleDateString('en-US') : ''}
                        </span>
                        {['scheduled', 'pending_strategy', 'strategy_ready', 'failed', 'no_answer'].includes(session.status) && (
                          <button
                            onClick={(e) => { e.stopPropagation(); handleCancelSession(session) }}
                            className="p-1.5 rounded-lg hover:bg-red-100 text-red-400 transition-colors"
                            title="Cancel"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        )}
                        <ChevronRight className="w-4 h-4 text-slate-300" />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        )}

        {/* Analytics Tab */}
        {activeTab === 'analytics' && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
            {/* Overview cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <StatCard label="Total Sessions" value={depthCounts.all} icon={Users} color="text-brand-600 bg-brand-50" />
              <StatCard label="Completion Rate" value={
                depthCounts.all > 0
                  ? `${Math.round((allSessions.filter(s => s.status === 'completed').length / depthCounts.all) * 100)}%`
                  : '—'
              } icon={CheckCircle2} color="text-emerald-600 bg-emerald-50" />
              <StatCard label="Avg Duration" value={(() => {
                const completed = allSessions.filter(s => s.status === 'completed' && s.duration_seconds)
                if (completed.length === 0) return '—'
                const avg = completed.reduce((a, s) => a + s.duration_seconds, 0) / completed.length
                return `${Math.floor(avg / 60)}m`
              })()} icon={Clock} color="text-blue-600 bg-blue-50" />
              <StatCard label="Avg Score" value={(() => {
                const scored = allSessions.filter(s => s.score != null)
                if (scored.length === 0) return '—'
                return Math.round(scored.reduce((a, s) => a + s.score, 0) / scored.length)
              })()} icon={Target} color="text-amber-600 bg-amber-50" />
            </div>

            {/* Per-depth breakdown */}
            <div className="bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 shadow-sm p-6">
              <h3 className="font-bold text-brand-900 mb-4">Sessions by Depth</h3>
              <div className="grid grid-cols-3 gap-4">
                {['quick', 'standard', 'deep'].map(depth => {
                  const count = depthCounts[depth]
                  const pct = depthCounts.all > 0 ? Math.round((count / depthCounts.all) * 100) : 0
                  const cfg = DEPTH_CONFIG[depth]
                  return (
                    <div key={depth} className="p-4 bg-slate-50 rounded-xl text-center">
                      <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold mb-2 ${cfg.color}`}>
                        {cfg.label}
                      </span>
                      <p className="text-2xl font-bold text-slate-800">{count}</p>
                      <p className="text-xs text-slate-400">{pct}%</p>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Status breakdown */}
            <div className="bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 shadow-sm p-6">
              <h3 className="font-bold text-brand-900 mb-4">Status Breakdown</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {Object.entries(STATUS_CONFIG).map(([status, cfg]) => {
                  const count = allSessions.filter(s => s.status === status).length
                  if (count === 0) return null
                  return (
                    <div key={status} className="p-3 bg-slate-50 rounded-xl text-center">
                      <p className="text-xs text-slate-400 mb-1">{cfg.label}</p>
                      <p className="text-xl font-bold text-slate-800">{count}</p>
                    </div>
                  )
                })}
              </div>
            </div>
          </motion.div>
        )}

        {/* Configuration Tab */}
        {activeTab === 'config' && configDraft && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
            {/* Bot Identity (from voice settings) */}
            {configDraft.voice && (
              <Section title="Bot Identity" icon={Volume2} description="How the AI bot presents to candidates (Quick Screen)">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Bot Name</label>
                    <input
                      value={configDraft.voice.bot_name ?? ''}
                      onChange={e => setConfigDraft({ ...configDraft, voice: { ...configDraft.voice, bot_name: e.target.value } })}
                      className="w-full px-3.5 py-2.5 bg-white rounded-xl ring-1 ring-slate-200 focus:ring-2 focus:ring-brand-500 text-sm outline-none transition-all"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Caller ID Name</label>
                    <input
                      value={configDraft.voice.caller_id_name ?? ''}
                      onChange={e => setConfigDraft({ ...configDraft, voice: { ...configDraft.voice, caller_id_name: e.target.value } })}
                      className="w-full px-3.5 py-2.5 bg-white rounded-xl ring-1 ring-slate-200 focus:ring-2 focus:ring-brand-500 text-sm outline-none transition-all"
                    />
                  </div>
                </div>
              </Section>
            )}

            {/* Auto-trigger settings (from recruiter config) */}
            {configDraft.recruiter && (
              <Section title="Auto-Trigger Settings" icon={Zap} description="When AI interviews are automatically triggered (Standard/Deep)">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      id="auto_trigger"
                      checked={configDraft.recruiter.auto_trigger_enabled ?? false}
                      onChange={e => setConfigDraft({ ...configDraft, recruiter: { ...configDraft.recruiter, auto_trigger_enabled: e.target.checked } })}
                      className="w-4 h-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                    />
                    <label htmlFor="auto_trigger" className="text-sm font-medium text-slate-700">
                      Enable auto-trigger on shortlist
                    </label>
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Min fit score for auto-trigger</label>
                    <input
                      type="number"
                      value={configDraft.recruiter.min_score_threshold ?? 60}
                      onChange={e => setConfigDraft({ ...configDraft, recruiter: { ...configDraft.recruiter, min_score_threshold: parseInt(e.target.value) || 60 } })}
                      min={0} max={100}
                      className="w-full px-3.5 py-2.5 bg-white rounded-xl ring-1 ring-slate-200 focus:ring-2 focus:ring-brand-500 text-sm outline-none transition-all"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Default duration (minutes)</label>
                    <input
                      type="number"
                      value={configDraft.recruiter.default_duration_minutes ?? 30}
                      onChange={e => setConfigDraft({ ...configDraft, recruiter: { ...configDraft.recruiter, default_duration_minutes: parseInt(e.target.value) || 30 } })}
                      min={10} max={60}
                      className="w-full px-3.5 py-2.5 bg-white rounded-xl ring-1 ring-slate-200 focus:ring-2 focus:ring-brand-500 text-sm outline-none transition-all"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1.5">Max concurrent sessions</label>
                    <input
                      type="number"
                      value={configDraft.recruiter.max_concurrent ?? 3}
                      onChange={e => setConfigDraft({ ...configDraft, recruiter: { ...configDraft.recruiter, max_concurrent: parseInt(e.target.value) || 3 } })}
                      min={1} max={10}
                      className="w-full px-3.5 py-2.5 bg-white rounded-xl ring-1 ring-slate-200 focus:ring-2 focus:ring-brand-500 text-sm outline-none transition-all"
                    />
                  </div>
                </div>
              </Section>
            )}

            {/* Sticky save bar */}
            {configDirty && (
              <div className="sticky bottom-0 z-10 bg-white/95 backdrop-blur-md rounded-2xl ring-1 ring-brand-200 shadow-lg px-6 py-4 flex items-center justify-between mt-2">
                <p className="text-sm font-medium text-slate-600">You have unsaved changes</p>
                <div className="flex gap-3">
                  <button
                    onClick={() => setConfigDraft(config)}
                    className="px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSaveConfig}
                    disabled={saving}
                    className="flex items-center gap-2 px-5 py-2 text-sm font-semibold text-white bg-brand-600 hover:bg-brand-700 rounded-xl transition-colors disabled:opacity-50 shadow-sm shadow-brand-200"
                  >
                    {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                    Save Changes
                  </button>
                </div>
              </div>
            )}
          </motion.div>
        )}

        {/* Initiate Modal */}
        {showInitiateModal && (
          <InterviewInitiateModal
            onClose={() => setShowInitiateModal(false)}
            onSuccess={() => fetchAll()}
          />
        )}
      </div>
    </div>
  )
}
