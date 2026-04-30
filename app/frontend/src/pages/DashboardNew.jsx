import { useState, useEffect, useCallback } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  Clock, CheckCircle, Users, FileText, ArrowRight, RefreshCw,
  Zap, GitCompareArrows, LayoutTemplate, AlertCircle, Loader2,
  ChevronRight, UserCheck, HourglassIcon
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { getDashboardSummary, getDashboardActivity } from '../lib/api'

/** Coerce any value to a render-safe string. Objects become JSON; null/undefined → '' */
function safeStr(v) {
  if (v == null) return ''
  if (typeof v === 'string') return v
  if (typeof v === 'number' || typeof v === 'boolean') return String(v)
  try { return JSON.stringify(v) } catch { return String(v) }
}

/** Convert ISO timestamp to relative time string */
function timeAgo(timestamp) {
  if (!timestamp) return ''
  const now = Date.now()
  const then = new Date(timestamp).getTime()
  if (isNaN(then)) return ''
  const diffMs = now - then
  const seconds = Math.floor(diffMs / 1000)
  if (seconds < 60) return 'just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ago`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days} day${days > 1 ? 's' : ''} ago`
  return new Date(timestamp).toLocaleDateString()
}

/** Score badge color classes (aligned with ScoreGauge thresholds) */
function scoreBadgeClasses(score) {
  if (score == null) return 'bg-slate-100 text-slate-500 ring-slate-200'
  if (score >= 72) return 'bg-green-50 text-green-700 ring-green-200'
  if (score >= 45) return 'bg-amber-50 text-amber-700 ring-amber-200'
  return 'bg-red-50 text-red-700 ring-red-200'
}

/** Status bar segment colors */
const STATUS_COLORS = {
  shortlisted: '#22c55e',
  pending: '#f59e0b',
  rejected: '#ef4444',
  'in-review': '#3b82f6',
  hired: '#8b5cf6',
}

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function SkeletonCard({ className = '' }) {
  return (
    <div className={`bg-white rounded-xl shadow-sm border border-slate-100 p-6 animate-pulse ${className}`}>
      <div className="h-4 bg-slate-200 rounded w-1/2 mb-3" />
      <div className="h-8 bg-slate-200 rounded w-1/3" />
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <div className="h-8 bg-slate-200 rounded w-64 mb-2 animate-pulse" />
        <div className="h-4 bg-slate-200 rounded w-96 animate-pulse" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
        <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6 animate-pulse h-80" />
        <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6 animate-pulse h-80" />
      </div>
    </div>
  )
}

// ─── Stacked Status Bar ───────────────────────────────────────────────────────

function StackedStatusBar({ breakdown = {}, total = 0 }) {
  if (!total) return null
  const segments = Object.entries(breakdown).filter(([, count]) => count > 0)
  if (!segments.length) return null

  return (
    <div className="flex w-full h-2.5 rounded-full overflow-hidden bg-slate-100">
      {segments.map(([status, count]) => (
        <div
          key={status}
          className="h-full transition-all duration-500"
          style={{
            width: `${(count / total) * 100}%`,
            backgroundColor: STATUS_COLORS[status] || '#94a3b8',
          }}
          title={`${status}: ${count}`}
        />
      ))}
    </div>
  )
}

// ─── Recommendation Tag ───────────────────────────────────────────────────────

function RecommendationTag({ recommendation }) {
  const rec = safeStr(recommendation)?.toLowerCase() || ''
  let bg = 'bg-slate-100 text-slate-600 ring-slate-200'
  if (rec.includes('shortlist') || rec.includes('strong') || rec.includes('recommend')) {
    bg = 'bg-green-50 text-green-700 ring-green-200'
  } else if (rec.includes('consider') || rec.includes('moderate')) {
    bg = 'bg-amber-50 text-amber-700 ring-amber-200'
  } else if (rec.includes('reject') || rec.includes('not recommend') || rec.includes('weak')) {
    bg = 'bg-red-50 text-red-700 ring-red-200'
  }
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ring-1 ${bg}`}>
      {safeStr(recommendation) || '—'}
    </span>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function DashboardNew() {
  const navigate = useNavigate()
  const { user } = useAuth()

  const [summary, setSummary] = useState(null)
  const [activity, setActivity] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [summaryData, activityData] = await Promise.all([
        getDashboardSummary(),
        getDashboardActivity(),
      ])
      setSummary(summaryData)
      setActivity(activityData)
    } catch (err) {
      setError(err.message || 'Failed to load dashboard data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  // ─── Early returns ────────────────────────────────────────────────────────
  if (loading && !summary) return <LoadingSkeleton />

  if (error && !summary) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-xl shadow-sm border border-red-100 p-12 text-center">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <h2 className="text-lg font-bold text-slate-900 mb-2">Failed to load dashboard</h2>
          <p className="text-sm text-slate-500 mb-6">{safeStr(error)}</p>
          <button
            onClick={fetchData}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-brand-600 text-white rounded-xl text-sm font-semibold hover:bg-brand-700 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Retry
          </button>
        </div>
      </div>
    )
  }

  // ─── Derived data ─────────────────────────────────────────────────────────
  const actionItems = summary?.action_items || {}
  const pipelineByJd = summary?.pipeline_by_jd || []
  const weeklyMetrics = summary?.weekly_metrics || {}
  const activities = activity?.activities || []

  const pendingCount = actionItems.pending_review ?? 0
  const shortlistedCount = actionItems.shortlisted_count ?? 0
  const inProgressCount = actionItems.in_progress_analyses ?? 0

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-extrabold text-brand-900 tracking-tight">
            Welcome back{user?.email ? `, ${user.email.split('@')[0]}` : ''}
          </h1>
          <p className="text-slate-500 text-sm mt-0.5 font-medium">
            Your recruiting command center
          </p>
        </div>
        {loading && (
          <Loader2 className="w-5 h-5 text-brand-500 animate-spin" />
        )}
      </div>

      {/* ── Action Items Bar ───────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        {/* Pending Review */}
        <button
          onClick={() => navigate('/candidates?status=pending')}
          className="bg-amber-50 hover:bg-amber-100 border border-amber-200 rounded-xl shadow-sm p-5 text-left transition-colors group"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-3xl font-extrabold text-amber-700">{pendingCount}</p>
              <p className="text-sm font-semibold text-amber-600 mt-1">Pending Review</p>
            </div>
            <div className="w-11 h-11 rounded-xl bg-amber-200/60 flex items-center justify-center">
              <Clock className="w-5 h-5 text-amber-700" />
            </div>
          </div>
          <div className="flex items-center gap-1 mt-3 text-xs text-amber-600 font-medium">
            View candidates
            <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
          </div>
        </button>

        {/* Shortlisted */}
        <button
          onClick={() => navigate('/candidates?status=shortlisted')}
          className="bg-green-50 hover:bg-green-100 border border-green-200 rounded-xl shadow-sm p-5 text-left transition-colors group"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-3xl font-extrabold text-green-700">{shortlistedCount}</p>
              <p className="text-sm font-semibold text-green-600 mt-1">Shortlisted</p>
            </div>
            <div className="w-11 h-11 rounded-xl bg-green-200/60 flex items-center justify-center">
              <UserCheck className="w-5 h-5 text-green-700" />
            </div>
          </div>
          <div className="flex items-center gap-1 mt-3 text-xs text-green-600 font-medium">
            View candidates
            <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
          </div>
        </button>

        {/* In Progress */}
        <div className="bg-blue-50 border border-blue-200 rounded-xl shadow-sm p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-3xl font-extrabold text-blue-700">{inProgressCount}</p>
              <p className="text-sm font-semibold text-blue-600 mt-1">In Progress</p>
            </div>
            <div className="w-11 h-11 rounded-xl bg-blue-200/60 flex items-center justify-center">
              <HourglassIcon className="w-5 h-5 text-blue-700" />
            </div>
          </div>
          <p className="text-xs text-blue-500 mt-3 font-medium">Analyses currently running</p>
        </div>
      </div>

      {/* ── Pipeline Summary ───────────────────────────────────────────────── */}
      <div className="mb-8">
        <h2 className="text-lg font-bold text-brand-900 mb-4">Pipeline Summary</h2>
        {pipelineByJd.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {pipelineByJd.map((jd) => {
              const total = jd.total_candidates ?? 0
              const breakdown = jd.status_breakdown || {}
              const avgScore = jd.avg_fit_score
              return (
                <div
                  key={jd.jd_id}
                  className="bg-white rounded-xl shadow-sm border border-slate-100 p-5 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start justify-between mb-3">
                    <h3 className="text-sm font-bold text-slate-900 leading-snug line-clamp-2 flex-1 mr-2">
                      {safeStr(jd.jd_name) || 'Untitled JD'}
                    </h3>
                    {avgScore != null && (
                      <span className={`shrink-0 px-2.5 py-1 rounded-full text-xs font-bold ring-1 ${scoreBadgeClasses(avgScore)}`}>
                        {avgScore}
                      </span>
                    )}
                  </div>

                  <p className="text-xs text-slate-500 mb-3">
                    {total} candidate{total !== 1 ? 's' : ''}
                  </p>

                  {/* Stacked status bar */}
                  <StackedStatusBar breakdown={breakdown} total={total} />

                  {/* Status legend */}
                  <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2.5">
                    {Object.entries(breakdown).filter(([, c]) => c > 0).map(([status, count]) => (
                      <span key={status} className="flex items-center gap-1 text-xs text-slate-500">
                        <span
                          className="w-2 h-2 rounded-full inline-block"
                          style={{ backgroundColor: STATUS_COLORS[status] || '#94a3b8' }}
                        />
                        {count} {status.replace('-', ' ')}
                      </span>
                    ))}
                  </div>

                  <Link
                    to={`/jd-library/${jd.jd_id}/candidates`}
                    className="inline-flex items-center gap-1 mt-4 text-xs font-semibold text-brand-600 hover:text-brand-700"
                  >
                    View Candidates
                    <ChevronRight className="w-3 h-3" />
                  </Link>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-10 text-center">
            <LayoutTemplate className="w-10 h-10 text-slate-300 mx-auto mb-3" />
            <p className="text-sm font-medium text-slate-500">No active job descriptions.</p>
            <p className="text-xs text-slate-400 mt-1 mb-4">Create one in JD Library to start screening candidates.</p>
            <Link
              to="/jd-library"
              className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-xl text-sm font-medium hover:bg-brand-700 transition-colors"
            >
              <LayoutTemplate className="w-4 h-4" />
              JD Library
            </Link>
          </div>
        )}
      </div>

      {/* ── Two-Column Layout: Activity + Metrics ──────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Left — Activity Feed */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-brand-900">Recent Activity</h2>
            <Link
              to="/candidates"
              className="text-xs font-semibold text-brand-600 hover:text-brand-700 flex items-center gap-1"
            >
              View all
              <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          {activities.length > 0 ? (
            <div className="space-y-1 max-h-96 overflow-y-auto pr-1">
              {activities.map((item, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    if (item.result_id) {
                      navigate(`/report?id=${item.result_id}`)
                    }
                  }}
                  className={`w-full text-left flex items-center gap-3 p-3 rounded-xl transition-colors ${
                    item.result_id
                      ? 'hover:bg-slate-50 cursor-pointer'
                      : 'cursor-default'
                  }`}
                >
                  {/* Icon */}
                  <div className="w-9 h-9 rounded-lg bg-brand-50 flex items-center justify-center shrink-0">
                    <FileText className="w-4 h-4 text-brand-600" />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-slate-900 truncate">
                        {safeStr(item.candidate_name) || 'Candidate'}
                      </span>
                      {item.fit_score != null && (
                        <span className={`shrink-0 px-2 py-0.5 rounded-full text-xs font-bold ring-1 ${scoreBadgeClasses(item.fit_score)}`}>
                          {item.fit_score}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-xs text-slate-400 truncate">{safeStr(item.jd_name) || 'JD'}</span>
                      <span className="text-xs text-slate-300">•</span>
                      <span className="text-xs text-slate-400 shrink-0">{timeAgo(item.timestamp)}</span>
                    </div>
                  </div>

                  {/* Recommendation tag */}
                  {item.recommendation && (
                    <RecommendationTag recommendation={item.recommendation} />
                  )}
                </button>
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <Clock className="w-10 h-10 text-slate-300 mx-auto mb-3" />
              <p className="text-sm font-medium text-slate-500">No recent activity</p>
              <p className="text-xs text-slate-400 mt-1">Analyses will appear here as they complete</p>
            </div>
          )}
        </div>

        {/* Right — Weekly Metrics */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
          <h2 className="text-lg font-bold text-brand-900 mb-5">Weekly Metrics</h2>

          <div className="grid grid-cols-2 gap-4 mb-6">
            {/* Analyses This Week */}
            <div className="bg-slate-50 rounded-xl p-4">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Analyses This Week</p>
              <p className="text-3xl font-extrabold text-brand-900">
                {weeklyMetrics.analyses_this_week ?? 0}
              </p>
            </div>

            {/* Avg Fit Score */}
            <div className="bg-slate-50 rounded-xl p-4">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Avg Fit Score</p>
              <div className="flex items-baseline gap-2">
                <p className="text-3xl font-extrabold text-brand-900">
                  {weeklyMetrics.avg_fit_score != null ? Math.round(weeklyMetrics.avg_fit_score) : '—'}
                </p>
                {weeklyMetrics.avg_fit_score != null && (
                  <span className={`text-sm font-bold ${
                    weeklyMetrics.avg_fit_score >= 72
                      ? 'text-green-600'
                      : weeklyMetrics.avg_fit_score >= 45
                      ? 'text-amber-600'
                      : 'text-red-600'
                  }`}>
                    {weeklyMetrics.avg_fit_score >= 72 ? '●' : weeklyMetrics.avg_fit_score >= 45 ? '●' : '●'}
                  </span>
                )}
              </div>
            </div>

            {/* Shortlist Rate */}
            <div className="bg-slate-50 rounded-xl p-4">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Shortlist Rate</p>
              <p className="text-3xl font-extrabold text-brand-900">
                {weeklyMetrics.shortlist_rate != null
                  ? `${Math.round(weeklyMetrics.shortlist_rate)}%`
                  : '—'}
              </p>
            </div>

            {/* Placeholder for balance */}
            <div className="bg-slate-50 rounded-xl p-4 flex items-center justify-center">
              <div className="text-center">
                <Users className="w-6 h-6 text-slate-300 mx-auto mb-1" />
                <p className="text-xs text-slate-400 font-medium">Active Pipeline</p>
              </div>
            </div>
          </div>

          {/* Top Skill Gaps */}
          {weeklyMetrics.top_skill_gaps && weeklyMetrics.top_skill_gaps.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Top Skill Gaps</p>
              <div className="flex flex-wrap gap-2">
                {weeklyMetrics.top_skill_gaps.map((skill, i) => (
                  <span
                    key={i}
                    className={`px-3 py-1 rounded-full text-xs font-semibold ring-1 ${
                      i < 2
                        ? 'bg-red-50 text-red-700 ring-red-200'
                        : 'bg-orange-50 text-orange-700 ring-orange-200'
                    }`}
                  >
                    {safeStr(skill)}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Quick Actions ──────────────────────────────────────────────────── */}
      <div className="flex flex-wrap gap-3">
        <button
          onClick={() => navigate('/analyze')}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold border-2 border-brand-200 text-brand-700 hover:bg-brand-50 hover:border-brand-300 transition-colors"
        >
          <Zap className="w-4 h-4" />
          New Analysis
        </button>
        <button
          onClick={() => navigate('/compare')}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold border-2 border-brand-200 text-brand-700 hover:bg-brand-50 hover:border-brand-300 transition-colors"
        >
          <GitCompareArrows className="w-4 h-4" />
          Compare Candidates
        </button>
        <Link
          to="/jd-library"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold border-2 border-brand-200 text-brand-700 hover:bg-brand-50 hover:border-brand-300 transition-colors"
        >
          <LayoutTemplate className="w-4 h-4" />
          JD Library
        </Link>
      </div>
    </div>
  )
}
