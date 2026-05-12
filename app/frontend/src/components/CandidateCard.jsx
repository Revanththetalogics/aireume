import { Check, AlertTriangle } from 'lucide-react'
import ScoreBadge from './ScoreBadge'
import RecommendationBadge from './RecommendationBadge'
import QuickActions from './QuickActions'

/**
 * Complete candidate card for list display — 30-second review design.
 *
 * Props:
 * - candidate: object { id, name, email, title, fit_score, status, skills, highlights, job_title }
 * - onStatusChange: function(id, newStatus)
 * - onSelect: function(candidate) — for navigation
 * - selected: boolean — show selection ring
 * - onMouseEnter: function
 * - onMouseLeave: function
 * - className: string
 */
export default function CandidateCard({
  candidate,
  onStatusChange,
  onSelect,
  selected = false,
  onMouseEnter,
  onMouseLeave,
  className = '',
}) {
  const {
    id,
    name,
    email,
    title,
    fit_score,
    status,
    skills = [],
    highlights = [],
    job_title,
  } = candidate || {}

  const topSkills = skills.slice(0, 3)
  const topHighlights = highlights.slice(0, 3)

  return (
    <div
      className={`
        bg-white rounded-xl shadow-sm border border-slate-100
        transition-shadow duration-200
        hover:shadow-md
        ${selected ? 'ring-2 ring-brand-500' : ''}
        ${className}
      `}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      {/* Card header */}
      <div
        className="p-4 cursor-pointer"
        onClick={() => onSelect?.(candidate)}
      >
        <div className="flex items-start gap-3">
          <ScoreBadge score={fit_score} size="md" animated />

          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <div>
                <h3 className="text-base font-semibold text-slate-900 truncate">
                  {name || 'Unknown Candidate'}
                </h3>
                {title && (
                  <p className="text-sm text-slate-500 mt-0.5">{title}</p>
                )}
                {job_title && (
                  <p className="text-xs text-slate-400 mt-0.5">
                    Applied: {job_title}
                  </p>
                )}
                {email && !title && !job_title && (
                  <p className="text-sm text-slate-500 mt-0.5">{email}</p>
                )}
              </div>
              <RecommendationBadge score={fit_score} size="sm" />
            </div>
          </div>
        </div>

        {/* Highlights */}
        {topHighlights.length > 0 && (
          <div className="mt-3 space-y-1.5">
            {topHighlights.map((highlight, idx) => {
              const isConcern = highlight.type === 'concern'
              return (
                <div key={idx} className="flex items-start gap-2">
                  {isConcern ? (
                    <AlertTriangle className="w-4 h-4 text-amber-500 mt-0.5 shrink-0" />
                  ) : (
                    <Check className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
                  )}
                  <span
                    className={`text-sm leading-relaxed ${
                      isConcern ? 'text-amber-700' : 'text-slate-600'
                    }`}
                  >
                    {highlight.text}
                  </span>
                </div>
              )
            })}
          </div>
        )}

        {/* Skills */}
        {topSkills.length > 0 && (
          <div className="mt-3 flex flex-wrap items-center gap-4">
            {topSkills.map((skill, idx) => (
              <div key={idx} className="flex items-center gap-2 min-w-0">
                <span className="text-xs font-medium text-slate-600 truncate max-w-[80px]">
                  {skill.name}
                </span>
                <div className="w-20 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-brand"
                    style={{ width: `${Math.min(skill.score || 0, 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick actions footer */}
      <div className="px-4 pb-4 pt-0">
        <QuickActions
          candidateId={id}
          currentStatus={status}
          onStatusChange={onStatusChange}
        />
      </div>
    </div>
  )
}
