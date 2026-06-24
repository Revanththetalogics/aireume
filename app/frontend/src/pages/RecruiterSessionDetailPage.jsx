import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Brain, ArrowLeft, Clock, FileText, Calendar, User, Loader2,
  XCircle, RefreshCw, Download, CheckCircle2, AlertTriangle,
  MessageSquare, ClipboardList, Target,
} from 'lucide-react'
import {
  getRecruiterSession, getRecruiterTranscript, getRecruiterScorecard,
  cancelRecruiterSession, retryRecruiterSession,
} from '../lib/api'
import RecruiterScorecard from '../components/RecruiterScorecard'
import RecruiterTranscript from '../components/RecruiterTranscript'

const STATUS_CONFIG = {
  pending_strategy: { label: 'Preparing',   color: 'bg-slate-100 text-slate-700' },
  strategy_ready:   { label: 'Ready',       color: 'bg-blue-100 text-blue-700' },
  scheduled:        { label: 'Scheduled',   color: 'bg-amber-100 text-amber-700' },
  in_progress:      { label: 'In Progress', color: 'bg-indigo-100 text-indigo-700' },
  completed:        { label: 'Completed',   color: 'bg-green-100 text-green-700' },
  failed:           { label: 'Failed',      color: 'bg-red-100 text-red-700' },
  cancelled:        { label: 'Cancelled',   color: 'bg-gray-100 text-gray-500' },
  expired:          { label: 'Expired',     color: 'bg-orange-100 text-orange-600' },
}

const RECOMMENDATION_COLORS = {
  strong_hire:    'bg-emerald-100 text-emerald-800',
  hire:           'bg-green-100 text-green-700',
  maybe:          'bg-amber-100 text-amber-700',
  no_hire:        'bg-red-100 text-red-700',
  strong_no_hire: 'bg-red-200 text-red-800',
}

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.pending_strategy
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${cfg.color}`}>
      {cfg.label}
    </span>
  )
}

function InfoField({ label, value, className = '' }) {
  return (
    <div className={`p-3 bg-slate-50 rounded-xl ${className}`}>
      <p className="text-xs text-slate-400 mb-1">{label}</p>
      <p className="text-sm font-semibold text-slate-700">{value ?? '—'}</p>
    </div>
  )
}

export default function RecruiterSessionDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [session, setSession] = useState(null)
  const [transcript, setTranscript] = useState(null)
  const [scorecard, setScorecard] = useState(null)
  const [loading, setLoading] = useState(true)
  const [tabLoading, setTabLoading] = useState(false)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('scorecard')

  useEffect(() => {
    async function load() {
      try {
        setLoading(true)
        const sessionData = await getRecruiterSession(id)
        setSession(sessionData)
        // Pre-load scorecard for completed sessions
        if (sessionData.status === 'completed') {
          const [sc, tr] = await Promise.all([
            getRecruiterScorecard(id).catch(() => null),
            getRecruiterTranscript(id).catch(() => null),
          ])
          setScorecard(sc)
          setTranscript(tr)
        }
      } catch (err) {
        setError(err.message || 'Failed to load session')
      } finally {
        setLoading(false)
      }
    }
    if (id) load()
  }, [id])

  async function loadTab(tab) {
    setActiveTab(tab)
    if (tab === 'transcript' && !transcript) {
      try {
        setTabLoading(true)
        const tr = await getRecruiterTranscript(id)
        setTranscript(tr)
      } catch { /* ignore */ }
      finally { setTabLoading(false) }
    }
    if (tab === 'scorecard' && !scorecard) {
      try {
        setTabLoading(true)
        const sc = await getRecruiterScorecard(id)
        setScorecard(sc)
      } catch { /* ignore */ }
      finally { setTabLoading(false) }
    }
  }

  async function handleCancel() {
    if (!confirm('Cancel this interview session?')) return
    try {
      await cancelRecruiterSession(id)
      const updated = await getRecruiterSession(id)
      setSession(updated)
    } catch (err) {
      setError(err.message || 'Failed to cancel')
    }
  }

  async function handleRetry() {
    try {
      await retryRecruiterSession(id)
      const updated = await getRecruiterSession(id)
      setSession(updated)
    } catch (err) {
      setError(err.message || 'Failed to retry')
    }
  }

  function formatDuration(seconds) {
    if (!seconds) return '—'
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return `${m}m ${s}s`
  }

  if (loading) {
    return (
      <div className="h-screen bg-surface flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-brand-600 animate-spin" />
      </div>
    )
  }

  if (error || !session) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-red-300 mx-auto mb-4" />
          <p className="text-sm text-red-600 mb-4">{error || 'Session not found'}</p>
          <button onClick={() => navigate('/recruiter-interviews')} className="px-4 py-2 bg-brand-600 text-white rounded-xl text-sm font-semibold hover:bg-brand-700">
            Back to Sessions
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-surface">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
        {/* Back button */}
        <button
          onClick={() => navigate('/recruiter-interviews')}
          className="flex items-center gap-2 text-sm text-slate-500 hover:text-brand-600 mb-6 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Sessions
        </button>

        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-4">
              <div className={`w-14 h-14 rounded-2xl flex items-center justify-center ${
                session.status === 'completed' ? 'bg-gradient-to-br from-emerald-500 to-green-400' :
                session.status === 'in_progress' ? 'bg-gradient-to-br from-indigo-500 to-blue-400' :
                session.status === 'failed' ? 'bg-gradient-to-br from-red-500 to-orange-400' :
                'bg-gradient-to-br from-brand-600 to-brand-400'
              } shadow-lg`}>
                <Brain className="w-7 h-7 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-extrabold text-brand-900 tracking-tight">
                  {session.candidate_name || `Candidate #${session.candidate_id}`}
                </h1>
                <div className="flex items-center gap-2 mt-1 flex-wrap">
                  <StatusBadge status={session.status} />
                  {session.jd_title && (
                    <span className="text-sm text-slate-500 flex items-center gap-1">
                      <FileText className="w-3.5 h-3.5" />
                      {session.jd_title}
                    </span>
                  )}
                  {session.recommendation && (
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${RECOMMENDATION_COLORS[session.recommendation] || 'bg-slate-100 text-slate-600'}`}>
                      {session.recommendation.replace(/_/g, ' ')}
                    </span>
                  )}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {['pending_strategy', 'strategy_ready', 'scheduled', 'failed'].includes(session.status) && (
                <button
                  onClick={handleCancel}
                  className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-red-600 bg-red-50 rounded-xl hover:bg-red-100 transition-colors"
                >
                  <XCircle className="w-4 h-4" /> Cancel
                </button>
              )}
              {['failed', 'expired'].includes(session.status) && (
                <button
                  onClick={handleRetry}
                  className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-brand-600 bg-brand-50 rounded-xl hover:bg-brand-100 transition-colors"
                >
                  <RefreshCw className="w-4 h-4" /> Retry
                </button>
              )}
            </div>
          </div>
        </motion.div>

        {/* Info grid */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
          <InfoField label="Session ID" value={`#${session.id}`} />
          <InfoField label="Duration" value={formatDuration(session.duration_seconds)} />
          <InfoField label="Created" value={session.created_at ? new Date(session.created_at).toLocaleDateString('en-US') : '—'} />
          <InfoField label="Completed" value={session.completed_at ? new Date(session.completed_at).toLocaleDateString('en-US') : '—'} />
          {session.overall_score != null && (
            <InfoField label="Overall Score" value={session.overall_score} />
          )}
          {session.trigger_type && (
            <InfoField label="Trigger" value={session.trigger_type.replace(/_/g, ' ')} />
          )}
          {session.question_count != null && (
            <InfoField label="Questions" value={session.question_count} />
          )}
          {session.candidate_email && (
            <InfoField label="Email" value={session.candidate_email} />
          )}
        </motion.div>

        {/* Tabs */}
        <div className="flex gap-1 mb-6 bg-white/60 backdrop-blur rounded-2xl p-1 ring-1 ring-brand-100 w-fit">
          {[
            { key: 'scorecard', label: 'Scorecard', icon: Target },
            { key: 'transcript', label: 'Transcript', icon: MessageSquare },
            { key: 'strategy', label: 'Strategy', icon: ClipboardList },
          ].map(tab => (
            <button
              key={tab.key}
              onClick={() => loadTab(tab.key)}
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

        {tabLoading && (
          <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 text-brand-600 animate-spin" /></div>
        )}

        {/* Scorecard Tab */}
        {!tabLoading && activeTab === 'scorecard' && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            {scorecard ? (
              <RecruiterScorecard scorecard={scorecard} />
            ) : (
              <div className="text-center py-16 text-slate-400">
                <Target className="w-12 h-12 mx-auto mb-4 opacity-40" />
                <p className="text-sm">
                  {session.status === 'completed' ? 'No scorecard available' : 'Scorecard available after interview completion'}
                </p>
              </div>
            )}
          </motion.div>
        )}

        {/* Transcript Tab */}
        {!tabLoading && activeTab === 'transcript' && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <RecruiterTranscript transcript={transcript} />
          </motion.div>
        )}

        {/* Strategy Tab */}
        {!tabLoading && activeTab === 'strategy' && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            {session.strategy ? (
              <div className="bg-white rounded-2xl ring-1 ring-slate-200 p-6">
                <h3 className="text-sm font-bold text-slate-800 mb-4 flex items-center gap-2">
                  <ClipboardList className="w-4 h-4 text-brand-600" />
                  Interview Strategy
                </h3>
                <div className="prose prose-sm max-w-none">
                  {typeof session.strategy === 'string' ? (
                    <div className="text-sm text-slate-700 whitespace-pre-wrap">{session.strategy}</div>
                  ) : (
                    <div className="space-y-4">
                      {session.strategy.objective && (
                        <div>
                          <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Objective</h4>
                          <p className="text-sm text-slate-700">{session.strategy.objective}</p>
                        </div>
                      )}
                      {session.strategy.focus_areas && (
                        <div>
                          <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Focus Areas</h4>
                          <div className="flex flex-wrap gap-2">
                            {session.strategy.focus_areas.map((area, i) => (
                              <span key={i} className="px-2.5 py-1 bg-brand-50 text-brand-700 rounded-lg text-xs font-semibold">{area}</span>
                            ))}
                          </div>
                        </div>
                      )}
                      {session.strategy.planned_questions && (
                        <div>
                          <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Planned Questions</h4>
                          <div className="space-y-2">
                            {session.strategy.planned_questions.map((q, i) => (
                              <div key={i} className="flex items-start gap-2 p-3 bg-slate-50 rounded-xl">
                                <span className="text-xs font-bold text-brand-600 mt-0.5">{i + 1}</span>
                                <div>
                                  <p className="text-sm text-slate-700">{q.question || q}</p>
                                  {q.category && (
                                    <span className="text-xs text-slate-400 mt-1">{q.category}</span>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="text-center py-16 text-slate-400">
                <ClipboardList className="w-12 h-12 mx-auto mb-4 opacity-40" />
                <p className="text-sm">
                  {['pending_strategy', 'strategy_ready'].includes(session.status)
                    ? 'Strategy is being generated...'
                    : 'No strategy available'}
                </p>
              </div>
            )}
          </motion.div>
        )}
      </div>
    </div>
  )
}
