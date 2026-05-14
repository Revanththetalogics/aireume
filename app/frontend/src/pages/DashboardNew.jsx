import { useState, useEffect, useCallback } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  Clock, FileText, ArrowRight, RefreshCw,
  LayoutTemplate, AlertCircle, Loader2,
  ChevronRight, UserCheck, HourglassIcon, XCircle, Award, Columns,
  Plus, AlertTriangle, Sparkles, GitCompare, Download
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

import { getDashboardSummary, getDashboardActivity } from '../lib/api'
import { safeStr } from '../lib/utils'
import { getScoreColor } from '../lib/constants'
import Skeleton from '../components/Skeleton'
import GettingStarted from '../components/GettingStarted'

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

/** Score badge color classes — delegates to shared getScoreColor from constants */
function scoreBadgeClasses(score) {
  const c = getScoreColor(score)
  if (!c) return 'bg-slate-100 text-slate-500 ring-slate-200'
  return `${c.bg} ${c.text} ${c.ring}`
}

/** Status bar segment Tailwind bg classes (Improvement #1) */
const STATUS_BG = {
  pending: 'bg-slate-300',
  'in-review': 'bg-blue-400',
  shortlisted: 'bg-green-400',
  rejected: 'bg-red-400',
  hired: 'bg-brand-400',
}

/** Human-readable status labels */
const STATUS_LABELS = {
  pending: 'Pending',
  'in-review': 'In Review',
  shortlisted: 'Shortlisted',
  rejected: 'Rejected',
  hired: 'Hired',
}

// ─── Stacked Status Bar (Improvement #1 — Tailwind classes) ──────────────────

function StackedStatusBar({ breakdown = {}, total = 0 }) {
  if (!total) return null
  const segments = Object.entries(breakdown).filter(([, count]) => count > 0)
  if (!segments.length) return null

  return (
    <div className="flex w-full h-2.5 rounded-full overflow-hidden bg-slate-100">
      {segments.map(([status, count]) => (
        <div
          key={status}
          className={`h-full transition-all duration-500 ${STATUS_BG[status] || 'bg-slate-300'}`}
          style={{ width: `${(count / total) * 100}%` }}
          title={`${STATUS_LABELS[status] || status}: ${count}`}
        />
      ))}
    </div>
  )
}

// ─── Score Ring Gauge (Improvement #3 — SVG circle) ──────────────────────────

function ScoreRingGauge({ score, size = 80, strokeWidth = 6 }) {
  if (score == null) return <span className="text-3xl font-extrabold text-slate-400">—</span>

  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference * (1 - Math.min(score, 100) / 100)

  let strokeColor = '#ef4444' // red-500 (Poor <30)
  if (score >= 70) strokeColor = '#22c55e'       // green-500 (Strong)
  else if (score >= 50) strokeColor = '#f59e0b'   // amber-500 (Good)
  else if (score >= 30) strokeColor = '#fca5a5'   // red-300 (Weak)

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none" stroke="#e2e8f0" strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2} cy={size / 2} r={radius}
          fill="none" stroke={strokeColor} strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-700"
        />
      </svg>
      <span className="absolute text-lg font-extrabold text-slate-900">
        {Math.round(score)}
      </span>
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

// ─── Activity Helpers (Improvement #5) ────────────────────────────────────────

/** Derive action label and icon from an activity item */
function getActionInfo(item) {
  const rec = (item.recommendation || '').toLowerCase()
  if (rec.includes('shortlist') || rec.includes('strong') || rec.includes('recommend')) {
    return { label: 'Shortlisted', Icon: UserCheck, colorCls: 'text-green-600 bg-green-50' }
  }
  if (rec.includes('reject') || rec.includes('not recommend') || rec.includes('weak')) {
    return { label: 'Rejected', Icon: XCircle, colorCls: 'text-red-600 bg-red-50' }
  }
  return { label: 'Analyzed', Icon: FileText, colorCls: 'text-brand-600 bg-brand-50' }
}

/** Group activities by time period: Today / Yesterday / This Week / Earlier */
function groupActivitiesByTime(activities) {
  const now = new Date()
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const startOfYesterday = new Date(startOfToday)
  startOfYesterday.setDate(startOfYesterday.getDate() - 1)
  const startOfWeek = new Date(startOfToday)
  startOfWeek.setDate(startOfWeek.getDate() - 7)

  const today = [], yesterday = [], thisWeek = [], earlier = []

  for (const item of activities) {
    const ts = new Date(item.timestamp)
    if (isNaN(ts.getTime())) { earlier.push(item); continue }
    if (ts >= startOfToday) today.push(item)
    else if (ts >= startOfYesterday) yesterday.push(item)
    else if (ts >= startOfWeek) thisWeek.push(item)
    else earlier.push(item)
  }

  const groups = []
  if (today.length) groups.push({ label: 'Today', items: today })
  if (yesterday.length) groups.push({ label: 'Yesterday', items: yesterday })
  if (thisWeek.length) groups.push({ label: 'This Week', items: thisWeek })
  if (earlier.length) groups.push({ label: 'Earlier', items: earlier })

  return groups
}

// ─── Main Component ───────────────────────────────────────────────────────────

function DashboardContent() {
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
  if (loading && !summary) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header skeleton */}
        <div className="mb-6 space-y-2">
          <Skeleton variant="text" width="16rem" className="h-8" />
          <Skeleton variant="text" width="24rem" />
        </div>
        {/* KPI cards skeleton */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <Skeleton variant="card" count={3} />
        </div>
        {/* Activity + Metrics skeleton */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          <Skeleton variant="card" height="20rem" />
          <Skeleton variant="card" height="20rem" />
        </div>
      </div>
    )
  }

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

  // Sum rejected & hired across all JDs in pipeline
  const rejectedCount = pipelineByJd.reduce(
    (sum, jd) => sum + ((jd.status_breakdown || {}).rejected ?? 0), 0
  )
  const hiredCount = pipelineByJd.reduce(
    (sum, jd) => sum + ((jd.status_breakdown || {}).hired ?? 0), 0
  )

  // Improvement #2: Sort JDs by urgency — most pending first, then most candidates
  const sortedPipelineByJd = [...pipelineByJd].sort((a, b) => {
    const aPending = (a.status_breakdown || {}).pending ?? 0
    const bPending = (b.status_breakdown || {}).pending ?? 0
    if (bPending !== aPending) return bPending - aPending
    return (b.total_candidates ?? 0) - (a.total_candidates ?? 0)
  })

  // Improvement #5: Group activities by time period
  const activityGroups = groupActivitiesByTime(activities)

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* ── Getting Started Checklist ───────────────────────────────────── */}
      <div className="mb-8">
        <GettingStarted />
      </div>

      {/* ── Improvement #4 & #6: Compact Header + Quick Actions ──────────── */}
      <div className="flex items-center justify-between mb-6 gap-4 flex-wrap">
        <h1 className="text-lg font-semibold text-brand-900 whitespace-nowrap">
          Welcome back{user?.email ? `, ${user.email.split('@')[0]}` : ''}
        </h1>
        <div className="grid grid-cols-2 sm:flex items-center gap-2 sm:gap-3 w-full sm:w-auto">
          {/* Primary CTA - filled */}
          <button
            onClick={() => navigate('/analyze')}
            className="flex items-center justify-center gap-2 px-4 py-2.5 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors shadow-sm font-medium text-sm"
          >
            <Sparkles className="w-4 h-4" />
            Screen Resumes
          </button>

          {/* Secondary actions - outlined */}
          <button
            onClick={() => navigate('/jd-library')}
            className="flex items-center justify-center gap-2 px-4 py-2.5 border border-slate-200 bg-white text-slate-700 rounded-lg hover:bg-slate-50 hover:border-brand-300 transition-colors font-medium text-sm"
          >
            <Plus className="w-4 h-4" />
            Create New JD
          </button>

          <button
            onClick={() => navigate('/compare')}
            className="flex items-center justify-center gap-2 px-4 py-2.5 border border-slate-200 bg-white text-slate-700 rounded-lg hover:bg-slate-50 hover:border-brand-300 transition-colors font-medium text-sm"
          >
            <GitCompare className="w-4 h-4" />
            Compare Candidates
          </button>
        </div>
        {loading && <Loader2 className="w-5 h-5 text-brand-500 animate-spin shrink-0" />}
      </div>

      {/* ── Action Items Bar (Improvement #2 — ring on Pending > 50) ─────── */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
        {/* Pending Review */}
        <button
          onClick={() => navigate('/candidates?status=pending')}
          className={`bg-amber-50 hover:bg-amber-100 border rounded-xl shadow-sm p-5 text-left transition-colors group ${
            pendingCount > 50
              ? 'border-amber-300 ring-2 ring-orange-400'
              : 'border-amber-200'
          }`}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-3xl font-extrabold text-amber-700">{pendingCount}</p>
              <p className="text-sm font-semibold text-amber-600 mt-1">Pending Review</p>
            </div>
            <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${
              pendingCount > 50 ? 'bg-orange-200/60' : 'bg-amber-200/60'
            }`}>
              <Clock className={`w-5 h-5 ${pendingCount > 50 ? 'text-orange-700' : 'text-amber-700'}`} />
            </div>
          </div>
          {pendingCount > 50 && (
            <p className="text-xs font-semibold text-orange-600 mt-2 flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" />
              Needs attention
            </p>
          )}
          <div className="flex items-center gap-1 mt-3 text-xs text-amber-600 font-medium">
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

        {/* Hired */}
        <button
          onClick={() => navigate('/candidates?status=hired')}
          className="bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 rounded-xl shadow-sm p-5 text-left transition-colors group"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-3xl font-extrabold text-indigo-700">{hiredCount}</p>
              <p className="text-sm font-semibold text-indigo-600 mt-1">Hired</p>
            </div>
            <div className="w-11 h-11 rounded-xl bg-indigo-200/60 flex items-center justify-center">
              <Award className="w-5 h-5 text-indigo-700" />
            </div>
          </div>
          <div className="flex items-center gap-1 mt-3 text-xs text-indigo-600 font-medium">
            View candidates
            <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
          </div>
        </button>

        {/* Rejected */}
        <button
          onClick={() => navigate('/candidates?status=rejected')}
          className="bg-red-50 hover:bg-red-100 border border-red-200 rounded-xl shadow-sm p-5 text-left transition-colors group"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-3xl font-extrabold text-red-700">{rejectedCount}</p>
              <p className="text-sm font-semibold text-red-600 mt-1">Rejected</p>
            </div>
            <div className="w-11 h-11 rounded-xl bg-red-200/60 flex items-center justify-center">
              <XCircle className="w-5 h-5 text-red-700" />
            </div>
          </div>
          <div className="flex items-center gap-1 mt-3 text-xs text-red-600 font-medium">
            View candidates
            <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
          </div>
        </button>
      </div>

      {/* ── Pipeline Summary (Improvements #1 & #2 — progress bars, urgency, sorting) */}
      <div className="mb-8">
        <h2 className="text-lg font-bold text-brand-900 mb-4">Pipeline Summary</h2>
        {sortedPipelineByJd.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {sortedPipelineByJd.map((jd) => {
              const total = jd.total_candidates ?? 0
              const breakdown = jd.status_breakdown || {}
              const avgScore = jd.avg_fit_score
              const pendingInJd = breakdown.pending ?? 0
              const segments = Object.entries(breakdown).filter(([, c]) => c > 0)

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

                  {/* Improvement #1: Compact legend with · separator */}
                  <div className="mt-2 text-xs text-slate-500 flex flex-wrap items-center">
                    {segments.flatMap(([status, count], i) => {
                      const el = (
                        <span key={status} className="inline-flex items-center gap-1">
                          <span className={`w-1.5 h-1.5 rounded-full ${STATUS_BG[status] || 'bg-slate-300'}`} />
                          {count} {STATUS_LABELS[status] || status}
                        </span>
                      )
                      return i < segments.length - 1
                        ? [el, <span key={`sep-${i}`} className="mx-1 text-slate-300">·</span>]
                        : [el]
                    })}
                  </div>

                  {/* Improvement #2: Urgency indicator */}
                  {pendingInJd > 0 && (
                    <p className="text-xs font-medium text-orange-600 mt-2 flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3" />
                      {pendingInJd} pending review
                    </p>
                  )}

                  <div className="flex items-center gap-4 mt-4">
                    <Link
                      to={`/jd-library/${jd.jd_id}/candidates`}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-brand-600 hover:text-brand-700"
                    >
                      View Candidates
                      <ChevronRight className="w-3 h-3" />
                    </Link>
                    <Link
                      to={`/jd-library/${jd.jd_id}/candidates?view=kanban`}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-700"
                    >
                      <Columns className="w-3 h-3" />
                      View Pipeline
                    </Link>
                  </div>
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
        {/* Left — Activity Feed (Improvement #5 — time groupings, clickable, action type) */}
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
            <div className="space-y-0 max-h-96 overflow-y-auto pr-1">
              {activityGroups.map(group => (
                <div key={group.label}>
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest px-3 pt-3 pb-1 sticky top-0 bg-white z-10">
                    {group.label}
                  </p>
                  {group.items.map((item, idx) => {
                    const { label: actionLabel, Icon: ActionIcon, colorCls } = getActionInfo(item)
                    const hasLink = !!(item.candidate_id || item.result_id)
                    return (
                      <button
                        key={`${group.label}-${idx}`}
                        onClick={() => {
                          if (item.candidate_id) {
                            navigate(`/candidates/${item.candidate_id}`)
                          } else if (item.result_id) {
                            navigate(`/report?id=${item.result_id}`)
                          }
                        }}
                        className={`w-full text-left flex items-center gap-3 p-3 rounded-xl transition-colors ${
                          hasLink ? 'hover:bg-slate-50 cursor-pointer' : 'cursor-default'
                        }`}
                      >
                        {/* Icon with action-based color */}
                        <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${colorCls}`}>
                          <ActionIcon className="w-4 h-4" />
                        </div>

                        {/* Content */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] font-bold uppercase tracking-wide text-slate-400">
                              {actionLabel}
                            </span>
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
                            <span className="text-xs text-slate-300">·</span>
                            <span className="text-xs text-slate-400 shrink-0">{timeAgo(item.timestamp)}</span>
                          </div>
                        </div>

                        {/* Recommendation tag */}
                        {item.recommendation && (
                          <RecommendationTag recommendation={item.recommendation} />
                        )}
                      </button>
                    )
                  })}
                </div>
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

        {/* Right — Weekly Metrics (Improvements #3 & #7 — ring gauge, trend indicators) */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
          <h2 className="text-lg font-bold text-brand-900 mb-5">Weekly Metrics</h2>

          <div className="grid grid-cols-2 gap-4 mb-6">
            {/* Analyses This Week — Improvement #7: color-coded */}
            <div className="bg-slate-50 rounded-xl p-4">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Analyses This Week</p>
              <p className={`text-3xl font-extrabold ${
                (weeklyMetrics.analyses_this_week ?? 0) > 0 ? 'text-green-700' : 'text-slate-400'
              }`}>
                {weeklyMetrics.analyses_this_week ?? 0}
              </p>
            </div>

            {/* Improvement #3: Avg Fit Score — Ring Gauge */}
            <div className="bg-slate-50 rounded-xl p-4 flex flex-col items-center justify-center">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Avg Fit Score</p>
              <ScoreRingGauge score={weeklyMetrics.avg_fit_score} />
            </div>

            {/* Improvement #7: Shortlist Rate — color-coded */}
            <div className="bg-slate-50 rounded-xl p-4">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Shortlist Rate</p>
              <p className={`text-3xl font-extrabold ${
                weeklyMetrics.shortlist_rate == null ? 'text-slate-400' :
                weeklyMetrics.shortlist_rate >= 40 ? 'text-green-700' :
                weeklyMetrics.shortlist_rate >= 20 ? 'text-amber-700' :
                'text-red-700'
              }`}>
                {weeklyMetrics.shortlist_rate != null
                  ? `${Math.round(weeklyMetrics.shortlist_rate)}%`
                  : '—'}
              </p>
            </div>

            {/* Active Pipeline mini-summary */}
            <div className="bg-slate-50 rounded-xl p-4">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
                Active Pipeline
              </p>
              {(() => {
                const totals = pipelineByJd.reduce(
                  (acc, jd) => {
                    const b = jd.status_breakdown || {}
                    acc.pending += b.pending ?? 0
                    acc['in-review'] += b['in-review'] ?? 0
                    acc.shortlisted += b.shortlisted ?? 0
                    acc.rejected += b.rejected ?? 0
                    acc.hired += b.hired ?? 0
                    return acc
                  },
                  { pending: 0, 'in-review': 0, shortlisted: 0, rejected: 0, hired: 0 }
                )
                const grandTotal = Object.values(totals).reduce((s, c) => s + c, 0)
                const pipelineSegments = Object.entries(totals).filter(([, c]) => c > 0)
                return (
                  <>
                    <p className="text-2xl font-extrabold text-brand-900 mb-2">
                      {grandTotal} <span className="text-sm font-semibold text-slate-400">candidates</span>
                    </p>
                    {grandTotal > 0 && (
                      <div className="flex w-full h-3 rounded-full overflow-hidden bg-slate-200 mb-2">
                        {pipelineSegments.map(([status, count]) => (
                          <div
                            key={status}
                            className={`h-full transition-all duration-500 ${STATUS_BG[status] || 'bg-slate-300'}`}
                            style={{ width: `${(count / grandTotal) * 100}%` }}
                            title={`${STATUS_LABELS[status] || status}: ${count}`}
                          />
                        ))}
                      </div>
                    )}
                    <div className="flex flex-wrap gap-x-2.5 gap-y-0.5">
                      {Object.entries(totals).map(([status, count]) => (
                        <span key={status} className="flex items-center gap-1 text-[10px] text-slate-500">
                          <span className={`w-1.5 h-1.5 rounded-full inline-block ${STATUS_BG[status] || 'bg-slate-300'}`} />
                          {STATUS_LABELS[status] || status} {count}
                        </span>
                      ))}
                    </div>
                    <Link
                      to="/pipeline"
                      className="inline-flex items-center gap-1 mt-2 text-[10px] font-semibold text-indigo-600 hover:text-indigo-700"
                    >
                      View Full Pipeline <ArrowRight className="w-2.5 h-2.5" />
                    </Link>
                  </>
                )
              })()}
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
    </div>
  )
}

export default DashboardContent
