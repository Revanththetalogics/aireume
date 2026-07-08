import { useState, useEffect, useCallback, useMemo } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Mic, BarChart3, Plus, Search,
  RefreshCw, Loader2,
  AlertTriangle, X, Download, Target,
  Users, CheckCircle2, Clock, Settings as SettingsIcon,
} from 'lucide-react'
import {
  getVoiceSessions,
  cancelVoiceSession, cancelRecruiterSession, exportInterviewSessions,
  getRecruiterSessions,
  getInterviewAnalytics,
} from '../lib/api'
import InterviewInitiateModal from '../components/InterviewInitiateModal'
import { INTERVIEW } from '../lib/uxLabels'
import { PageHeader } from '../components/patterns'
import {
  InterviewSessionSection,
  InterviewEmptyState,
  InterviewSessionRow,
} from '../components/patterns/InterviewSessionList'
import { Button, Card, SegmentedControl } from '../components/ui'
import { bucketSessions, groupSessionsByCandidate, depthLabel } from '../lib/interviewHubUtils'

/* ── Depth config (analytics only) ───────────────────── */
const DEPTH_CONFIG = {
  quick:    { label: INTERVIEW.quick,     color: 'bg-blue-100 text-blue-700' },
  standard: { label: INTERVIEW.standard,  color: 'bg-purple-100 text-purple-700' },
  deep:     { label: INTERVIEW.deep,      color: 'bg-amber-100 text-amber-700' },
}

const RECOMMENDATION_CONFIG = {
  strong_hire:    { label: 'Strong Hire',    color: 'bg-emerald-100 text-emerald-700' },
  hire:           { label: 'Hire',           color: 'bg-green-100 text-green-700' },
  maybe:          { label: 'Maybe',          color: 'bg-amber-100 text-amber-700' },
  no_hire:        { label: 'No Hire',        color: 'bg-red-100 text-red-700' },
  strong_no_hire: { label: 'Strong No Hire', color: 'bg-red-800 text-white' },
}

/* ── Reusable sub-components (analytics) ─────────────── */

function StatCard({ label, value, icon: Icon, color }) {
  return (
    <Card className="px-4 py-3 flex items-center gap-3">
      <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${color}`}>
        <Icon className="w-4 h-4" />
      </div>
      <div>
        <p className="text-xs text-slate-400 font-medium">{label}</p>
        <p className="text-lg font-bold text-slate-800">{value}</p>
      </div>
    </Card>
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
    error_log: s.error_log || null,
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
    voice_session_id: s.voice_session_id,
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
    scheduled_at: s.scheduled_at || null,
    direction: null,
    phone_number: s.phone_number || null,
    error_log: s.error_log || null,
  }
}

/* ── Main component ──────────────────────────────────── */

export default function InterviewPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const initialDepth = searchParams.get('depth') || 'all'

  const [voiceSessions, setVoiceSessions] = useState([])
  const [recruiterSessions, setRecruiterSessions] = useState([])
  const [interviewAnalytics, setInterviewAnalytics] = useState(null)
  const [analyticsLoading, setAnalyticsLoading] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('sessions')
  const [depthFilter, setDepthFilter] = useState(initialDepth)
  const [statusFilter, setStatusFilter] = useState('all')
  const [viewMode, setViewMode] = useState('session')
  const [searchQuery, setSearchQuery] = useState('')
  const [showInitiateModal, setShowInitiateModal] = useState(false)
  const [rescheduleSession, setRescheduleSession] = useState(null)

  // Merge + normalize sessions. Voice sessions that are linked to a recruiter
  // interview are rendered as part of that interview, not as standalone rows.
  const allSessions = useMemo(() => {
    const recruiter = recruiterSessions.map(normalizeRecruiterSession)
    const linkedVoiceIds = new Set(recruiter.map(s => s.voice_session_id).filter(Boolean))
    const voice = voiceSessions
      .filter(s => !linkedVoiceIds.has(s.id))
      .map(normalizeVoiceSession)
    return [...voice, ...recruiter].sort((a, b) =>
      new Date(b.created_at || 0) - new Date(a.created_at || 0)
    )
  }, [voiceSessions, recruiterSessions])

  // Apply filters
  const filteredSessions = useMemo(() => {
    let list = allSessions
    if (depthFilter && depthFilter !== 'all') list = list.filter(s => s.depth === depthFilter)
    if (statusFilter && statusFilter !== 'all') list = list.filter(s => s.status === statusFilter)
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

  const displaySessions = useMemo(() => {
    if (viewMode === 'candidate') return groupSessionsByCandidate(filteredSessions)
    return filteredSessions
  }, [filteredSessions, viewMode])

  const sessionBuckets = useMemo(() => bucketSessions(filteredSessions), [filteredSessions])

  const fetchAll = useCallback(async () => {
    try {
      setLoading(true)
      const [vs, rs] = await Promise.all([
        getVoiceSessions({ limit: 50 }).catch(() => []),
        getRecruiterSessions({ limit: 50 }).catch(() => []),
      ])
      setVoiceSessions(Array.isArray(vs) ? vs : vs.sessions || [])
      setRecruiterSessions(Array.isArray(rs) ? rs : rs.sessions || [])
    } catch (err) {
      setError(err.message || 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchAll() }, [fetchAll])

  const fetchInterviewAnalytics = useCallback(async () => {
    try {
      setAnalyticsLoading(true)
      const data = await getInterviewAnalytics()
      setInterviewAnalytics(data)
    } catch (err) {
      setError(err.message || 'Failed to load analytics')
    } finally {
      setAnalyticsLoading(false)
    }
  }, [])

  useEffect(() => {
    if (activeTab === 'analytics' && !interviewAnalytics && !analyticsLoading) {
      fetchInterviewAnalytics()
    }
  }, [activeTab, interviewAnalytics, analyticsLoading, fetchInterviewAnalytics])

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

  function handleReschedule(session) {
    const voiceSessionId = session.source === 'voice' ? session.rawId : session.voice_session_id
    if (!voiceSessionId) {
      setError('No voice session associated with this interview')
      return
    }
    setRescheduleSession({
      id: voiceSessionId,
      scheduled_at: session.scheduled_at,
      phone_number: session.phone_number,
    })
  }

  async function handleRescheduleComplete() {
    setRescheduleSession(null)
    try {
      const [vs, rs] = await Promise.all([
        getVoiceSessions({ limit: 50 }).catch(() => []),
        getRecruiterSessions({ limit: 50 }).catch(() => []),
      ])
      setVoiceSessions(Array.isArray(vs) ? vs : vs.sessions || [])
      setRecruiterSessions(Array.isArray(rs) ? rs : rs.sessions || [])
    } catch (err) {
      setError(err.message || 'Failed to refresh sessions')
    }
  }

  function handleSessionClick(session) {
    navigate(`/ai-interviews/${session.rawId}?source=${session.source}&depth=${session.depth}`)
  }

  async function handleExportSessions() {
    try {
      setExporting(true)
      const params = {}
      if (depthFilter && depthFilter !== 'all') params.depth = depthFilter
      if (statusFilter && statusFilter !== 'all') params.status = statusFilter
      const blob = await exportInterviewSessions(params)
      const url = window.URL.createObjectURL(new Blob([blob], { type: 'text/csv' }))
      const link = document.createElement('a')
      link.href = url
      link.download = `interview_sessions_${new Date().toISOString().slice(0, 10)}.csv`
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      setError(err.message || 'Failed to export sessions')
    } finally {
      setExporting(false)
    }
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
        <PageHeader
          className="mb-6"
          icon={Mic}
          title={INTERVIEW.hubTitle}
          subtitle={INTERVIEW.hubSubtitle}
          actions={(
            <>
              <Link
                to="/settings?tab=interviews"
                className="hidden sm:inline-flex items-center gap-1.5 px-3 py-2 text-sm font-semibold text-slate-600 hover:text-brand-700 rounded-xl hover:bg-brand-50 transition-colors"
              >
                <SettingsIcon className="w-4 h-4" />
                {INTERVIEW.settingsLink}
              </Link>
              <Button onClick={() => setShowInitiateModal(true)}>
                <Plus className="w-4 h-4 mr-1.5" />
                {INTERVIEW.newScreenCall}
              </Button>
            </>
          )}
        />

        <div className="flex flex-wrap items-center gap-3 mb-6">
          <SegmentedControl
            options={[
              { label: 'Sessions', value: 'sessions' },
              { label: 'Analytics', value: 'analytics' },
            ]}
            value={activeTab}
            onChange={setActiveTab}
          />
          <button
            type="button"
            onClick={fetchAll}
            className="p-2 rounded-xl text-slate-400 hover:text-brand-600 hover:bg-brand-50 transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {error && (
          <Card className="mb-6 p-4 flex items-center gap-3 bg-red-50 ring-red-200">
            <AlertTriangle className="w-5 h-5 text-red-500 shrink-0" />
            <p className="text-sm text-red-700 flex-1">{error}</p>
            <button type="button" onClick={() => setError(null)} aria-label="Dismiss error" className="text-red-400 hover:text-red-600">
              <X className="w-4 h-4" />
            </button>
          </Card>
        )}

        {activeTab === 'sessions' && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
            <Card className="p-3 sm:p-4">
              <div className="flex flex-col lg:flex-row lg:items-center gap-3">
                <div className="relative flex-1 min-w-0">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search candidates or roles…"
                    className="w-full pl-9 pr-3 py-2.5 rounded-xl ring-1 ring-slate-200 dark:ring-white/10 bg-white dark:bg-dark-card text-sm outline-none focus:ring-2 focus:ring-brand-500"
                  />
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <select
                    value={depthFilter}
                    onChange={(e) => setDepthFilter(e.target.value)}
                    className="px-3 py-2 rounded-xl ring-1 ring-slate-200 dark:ring-white/10 bg-white dark:bg-dark-card text-sm font-medium outline-none"
                  >
                    <option value="all">All depths ({depthCounts.all})</option>
                    <option value="quick">{INTERVIEW.quick} ({depthCounts.quick})</option>
                    <option value="standard">{INTERVIEW.standard} ({depthCounts.standard})</option>
                    <option value="deep">{INTERVIEW.deep} ({depthCounts.deep})</option>
                  </select>
                  <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="px-3 py-2 rounded-xl ring-1 ring-slate-200 dark:ring-white/10 bg-white dark:bg-dark-card text-sm font-medium outline-none"
                  >
                    <option value="all">All status</option>
                    <option value="in_progress">In progress</option>
                    <option value="scheduled">Scheduled</option>
                    <option value="completed">Completed</option>
                    <option value="failed">Failed</option>
                    <option value="cancelled">Cancelled</option>
                  </select>
                  <SegmentedControl
                    options={[
                      { label: INTERVIEW.viewBySession, value: 'session' },
                      { label: INTERVIEW.viewByCandidate, value: 'candidate' },
                    ]}
                    value={viewMode}
                    onChange={setViewMode}
                  />
                  <Button variant="secondary" size="sm" loading={exporting} onClick={handleExportSessions}>
                    <Download className="w-3.5 h-3.5 mr-1" />
                    Export
                  </Button>
                </div>
              </div>
            </Card>

            {filteredSessions.length === 0 ? (
              <InterviewEmptyState
                onStart={() => setShowInitiateModal(true)}
                filterLabel={depthFilter !== 'all' ? depthLabel(depthFilter) : null}
              />
            ) : viewMode === 'candidate' ? (
              <Card className="overflow-hidden p-0 divide-y divide-brand-50 dark:divide-white/10">
                {displaySessions.map((session) => (
                  <InterviewSessionRow
                    key={session.id}
                    session={session}
                    showSessionCount={session.sessionCount}
                    onClick={() => handleSessionClick(session)}
                    onReschedule={handleReschedule}
                    onCancel={handleCancelSession}
                  />
                ))}
              </Card>
            ) : (
              <div className="space-y-4">
                <InterviewSessionSection
                  title={INTERVIEW.needsAttention}
                  sessions={sessionBuckets.attention}
                  onClick={handleSessionClick}
                  onReschedule={handleReschedule}
                  onCancel={handleCancelSession}
                />
                <InterviewSessionSection
                  title={INTERVIEW.upcoming}
                  sessions={sessionBuckets.upcoming}
                  onClick={handleSessionClick}
                  onReschedule={handleReschedule}
                  onCancel={handleCancelSession}
                />
                <InterviewSessionSection
                  title={INTERVIEW.recent}
                  sessions={sessionBuckets.recent}
                  onClick={handleSessionClick}
                  onReschedule={handleReschedule}
                  onCancel={handleCancelSession}
                />
              </div>
            )}
          </motion.div>
        )}

        {/* Analytics Tab */}
        {activeTab === 'analytics' && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
            {analyticsLoading && (
              <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 text-brand-600 animate-spin" /></div>
            )}

            {!analyticsLoading && interviewAnalytics && (
              <>
                {/* Overview cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <StatCard label="Total Sessions" value={(interviewAnalytics.voice?.total || 0) + (interviewAnalytics.recruiter?.total || 0)} icon={Users} color="text-brand-600 bg-brand-50" />
                  <StatCard label="Completion Rate" value={(() => {
                    const total = (interviewAnalytics.voice?.total || 0) + (interviewAnalytics.recruiter?.total || 0)
                    const completed = (interviewAnalytics.voice?.completed || 0) + (interviewAnalytics.recruiter?.completed || 0)
                    return total > 0 ? `${Math.round((completed / total) * 100)}%` : '—'
                  })()} icon={CheckCircle2} color="text-emerald-600 bg-emerald-50" />
                  <StatCard label="Avg Duration" value={
                    interviewAnalytics.voice?.average_duration_seconds
                      ? `${Math.floor(interviewAnalytics.voice.average_duration_seconds / 60)}m`
                      : '—'
                  } icon={Clock} color="text-blue-600 bg-blue-50" />
                  <StatCard label="Avg Score" value={(() => {
                    const scored = allSessions.filter(s => s.score != null)
                    if (scored.length === 0) return '—'
                    return Math.round(scored.reduce((a, s) => a + s.score, 0) / scored.length)
                  })()} icon={Target} color="text-amber-600 bg-amber-50" />
                </div>

                {/* Recommendation distribution */}
                <div className="bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 shadow-sm p-6">
                  <h3 className="font-bold text-brand-900 mb-4">Recommendation Distribution</h3>
                  {(() => {
                    const distribution = interviewAnalytics.recruiter?.recommendation_distribution || {}
                    const total = Object.values(distribution).reduce((a, c) => a + c, 0)
                    if (total === 0) {
                      return <p className="text-sm text-slate-400">No recommendation data available yet.</p>
                    }
                    return (
                      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                        {['strong_hire', 'hire', 'maybe', 'no_hire', 'strong_no_hire'].map(key => {
                          const count = distribution[key] || 0
                          const pct = Math.round((count / total) * 100)
                          const cfg = RECOMMENDATION_CONFIG[key]
                          return (
                            <div key={key} className={`p-4 rounded-xl text-center ${cfg.color}`}>
                              <p className="text-xs font-medium opacity-80 mb-1">{cfg.label}</p>
                              <p className="text-2xl font-bold">{count}</p>
                              <p className="text-xs opacity-80">{pct}%</p>
                            </div>
                          )
                        })}
                      </div>
                    )
                  })()}
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
                <Card className="p-6">
                  <h3 className="font-bold text-brand-900 mb-4">Status breakdown</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {Object.entries(interviewAnalytics.voice?.status_breakdown || {}).map(([status, count]) => {
                      if (!count) return null
                      return (
                        <div key={status} className="p-3 bg-slate-50 dark:bg-dark-card-elevated rounded-xl text-center">
                          <p className="text-xs text-slate-400 mb-1 capitalize">{status.replace(/_/g, ' ')}</p>
                          <p className="text-xl font-bold text-slate-800 dark:text-dark-text-primary">{count}</p>
                        </div>
                      )
                    })}
                    {(interviewAnalytics.recruiter?.failed || 0) > 0 && (
                      <div className="p-3 bg-slate-50 rounded-xl text-center">
                        <p className="text-xs text-slate-400 mb-1">Recruiter Failed</p>
                        <p className="text-xl font-bold text-slate-800">{interviewAnalytics.recruiter.failed}</p>
                      </div>
                    )}
                  </div>
                </Card>
              </>
            )}

            {!analyticsLoading && !interviewAnalytics && (
              <div className="text-center py-16">
                <BarChart3 className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                <h3 className="text-lg font-bold text-slate-500 mb-2">Analytics not available</h3>
                <p className="text-sm text-slate-400">Switch to the Analytics tab to load data.</p>
              </div>
            )}
          </motion.div>
        )}

        {(showInitiateModal || rescheduleSession) && (
          <InterviewInitiateModal
            onClose={() => { setShowInitiateModal(false); setRescheduleSession(null) }}
            onSuccess={() => {
              fetchAll()
              if (rescheduleSession) handleRescheduleComplete()
            }}
            editSession={rescheduleSession || undefined}
          />
        )}
      </div>
    </div>
  )
}
