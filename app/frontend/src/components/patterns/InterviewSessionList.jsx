import {
  Phone, Brain, Clock, FileText, ChevronRight, CalendarClock, X,
  AlertTriangle,
} from 'lucide-react'
import { Badge, Card } from '../ui'
import { INTERVIEW } from '../../lib/uxLabels'
import {
  formatSessionWhen, recommendationLabel, depthLabel,
} from '../../lib/interviewHubUtils'

const DEPTH_BADGE = {
  quick: 'blue',
  standard: 'brand',
  deep: 'amber',
}

const STATUS_BADGE = {
  scheduled: 'slate',
  ringing: 'amber',
  in_progress: 'blue',
  pending_strategy: 'slate',
  strategy_ready: 'blue',
  completed: 'green',
  failed: 'red',
  no_answer: 'amber',
  cancelled: 'slate',
  expired: 'amber',
}

const STATUS_LABEL = {
  scheduled: 'Scheduled',
  ringing: 'Ringing',
  in_progress: 'In Progress',
  pending_strategy: 'Preparing',
  strategy_ready: 'Ready',
  completed: 'Completed',
  failed: 'Failed',
  no_answer: 'No Answer',
  cancelled: 'Cancelled',
  expired: 'Expired',
}

export function InterviewSessionRow({
  session,
  onClick,
  onReschedule,
  onCancel,
  showSessionCount,
}) {
  const DepthIcon = session.depth === 'quick' ? Phone : Brain

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => e.key === 'Enter' && onClick?.()}
      className="flex items-center gap-3 px-4 sm:px-5 py-3.5 hover:bg-brand-50/50 dark:hover:bg-dark-card-elevated transition-colors cursor-pointer"
    >
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
        session.status === 'completed' ? 'bg-emerald-100 dark:bg-emerald-950/40' :
        session.status === 'failed' ? 'bg-red-100 dark:bg-red-950/40' :
        session.status === 'in_progress' ? 'bg-blue-100 dark:bg-blue-950/40' :
        'bg-slate-100 dark:bg-dark-card-elevated'
      }`}>
        <DepthIcon className={`w-5 h-5 ${
          session.status === 'completed' ? 'text-emerald-600' :
          session.status === 'failed' ? 'text-red-600' :
          session.status === 'in_progress' ? 'text-blue-600' :
          'text-slate-500'
        }`} />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap mb-0.5">
          <span className="text-sm font-semibold text-brand-800 dark:text-dark-text-primary truncate">
            {session.candidate_name}
          </span>
          <Badge color={DEPTH_BADGE[session.depth] || 'slate'}>{depthLabel(session.depth)}</Badge>
          <Badge color={STATUS_BADGE[session.status] || 'slate'}>
            {STATUS_LABEL[session.status] || session.status}
          </Badge>
          {showSessionCount > 1 && (
            <Badge color="slate">{showSessionCount} calls</Badge>
          )}
          {session.recommendation && (
            <Badge color={
              session.recommendation.includes('hire') && !session.recommendation.includes('no')
                ? 'green' : session.recommendation.includes('no') ? 'red' : 'amber'
            }>
              {recommendationLabel(session.recommendation)}
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-3 text-xs text-slate-500 dark:text-dark-text-secondary flex-wrap">
          {session.jd_title && (
            <span className="flex items-center gap-1 truncate max-w-[200px]">
              <FileText className="w-3 h-3 shrink-0" />{session.jd_title}
            </span>
          )}
          {session.duration_seconds != null && (
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {Math.floor(session.duration_seconds / 60)}m {session.duration_seconds % 60}s
            </span>
          )}
          {session.score != null && (
            <span className={`font-bold ${session.score >= 70 ? 'text-emerald-600' : session.score >= 40 ? 'text-amber-600' : 'text-red-600'}`}>
              {session.score}% score
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center gap-1.5 shrink-0">
        <span className="text-xs text-slate-400 hidden sm:inline">{formatSessionWhen(session)}</span>
        {session.status === 'scheduled' && (session.source === 'voice' || session.voice_session_id) && onReschedule && (
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onReschedule(session) }}
            className="p-1.5 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-950/40 text-blue-500"
            title="Reschedule"
          >
            <CalendarClock className="w-3.5 h-3.5" />
          </button>
        )}
        {['scheduled', 'pending_strategy', 'strategy_ready', 'failed', 'no_answer'].includes(session.status) && onCancel && (
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onCancel(session) }}
            className="p-1.5 rounded-lg hover:bg-red-100 dark:hover:bg-red-950/40 text-red-400"
            aria-label="Cancel session"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
        {session.status === 'failed' && session.error_log && (
          <span className="hidden md:inline-flex" title={session.error_log}>
            <AlertTriangle className="w-3.5 h-3.5 text-red-500" />
          </span>
        )}
        <ChevronRight className="w-4 h-4 text-slate-300" />
      </div>
    </div>
  )
}

export function InterviewSessionSection({ title, sessions, onClick, onReschedule, onCancel }) {
  if (!sessions.length) return null
  const rowProps = { onClick, onReschedule, onCancel }
  return (
    <Card className="overflow-hidden p-0">
      <div className="px-4 sm:px-5 py-3 border-b border-brand-50 dark:border-white/10 bg-brand-50/30 dark:bg-dark-card-elevated/50">
        <h3 className="text-xs font-bold uppercase tracking-wider text-brand-700 dark:text-brand-300">
          {title}
          <span className="ml-2 text-slate-400 font-semibold normal-case">({sessions.length})</span>
        </h3>
      </div>
      <div className="divide-y divide-brand-50 dark:divide-white/10">
        {sessions.map((session) => (
          <InterviewSessionRow
            key={session.id}
            session={session}
            onClick={() => rowProps.onClick?.(session)}
            onReschedule={rowProps.onReschedule}
            onCancel={rowProps.onCancel}
            showSessionCount={rowProps.showSessionCount}
          />
        ))}
      </div>
    </Card>
  )
}

export function InterviewEmptyState({ onStart, filterLabel }) {
  return (
    <Card className="p-12 text-center">
      <Phone className="w-12 h-12 text-slate-300 mx-auto mb-4" />
      <h3 className="text-lg font-bold text-slate-600 dark:text-dark-text-primary mb-2">No screen calls yet</h3>
      <p className="text-sm text-slate-400 mb-6 max-w-sm mx-auto">
        {filterLabel ? `No ${filterLabel} sessions match your filters.` : 'Start an AI screen call from a candidate report or here.'}
      </p>
      {onStart && (
        <button
          type="button"
          onClick={onStart}
          className="px-5 py-2.5 bg-brand-600 text-white rounded-xl font-semibold text-sm hover:bg-brand-700 transition-all"
        >
          {INTERVIEW.newScreenCall}
        </button>
      )}
    </Card>
  )
}
