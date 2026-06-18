import {
  BarChart3, Star, TrendingUp, CheckCircle2, AlertTriangle,
  ThumbsUp, ThumbsDown, Minus, FileText,
} from 'lucide-react'

function RatingBadge({ rating }) {
  const config = {
    strong:    { icon: ThumbsUp,   color: 'bg-emerald-100 text-emerald-700', label: 'Strong' },
    adequate:  { icon: CheckCircle2, color: 'bg-blue-100 text-blue-700',   label: 'Adequate' },
    weak:      { icon: Minus,      color: 'bg-amber-100 text-amber-700',   label: 'Weak' },
    poor:      { icon: ThumbsDown, color: 'bg-red-100 text-red-700',       label: 'Poor' },
  }
  const cfg = config[rating?.toLowerCase()] || config.adequate
  const Icon = cfg.icon
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${cfg.color}`}>
      <Icon className="w-3 h-3" />
      {cfg.label}
    </span>
  )
}

function ScoreBar({ score, max = 10 }) {
  const pct = Math.round((score / max) * 100)
  const color = pct >= 70 ? 'bg-emerald-500' : pct >= 40 ? 'bg-amber-500' : 'bg-red-500'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-slate-100 rounded-full h-2">
        <div className={`h-2 rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-bold text-slate-600 w-8 text-right">{score}/{max}</span>
    </div>
  )
}

export default function VoiceAssessmentPanel({ assessment }) {
  if (!assessment) return null

  // Handle both string and object formats
  const data = typeof assessment === 'string' ? (() => {
    try { return JSON.parse(assessment) } catch { return null }
  })() : assessment

  if (!data) return null

  const {
    overall_score,
    overall_recommendation,
    summary,
    skill_ratings,
    question_assessments,
    strengths,
    concerns,
    follow_up_questions,
  } = data

  return (
    <div>
      <h3 className="flex items-center gap-2 text-sm font-bold text-slate-700 mb-4">
        <BarChart3 className="w-4 h-4" />
        Screening Assessment
      </h3>

      {/* Overall Score */}
      <div className="p-4 bg-gradient-to-br from-brand-50 to-slate-50 rounded-2xl ring-1 ring-brand-100 mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-semibold text-slate-600">Overall Score</span>
          <span className="text-2xl font-extrabold text-brand-700">{overall_score ?? '—'}/10</span>
        </div>
        <ScoreBar score={overall_score || 0} />
        {overall_recommendation && (
          <p className="mt-2 text-sm font-medium text-slate-600">
            Recommendation: <span className="font-bold text-brand-700">{overall_recommendation}</span>
          </p>
        )}
      </div>

      {/* Summary */}
      {summary && (
        <div className="mb-4 p-3 bg-white rounded-xl ring-1 ring-slate-100">
          <p className="text-sm text-slate-600 leading-relaxed">{summary}</p>
        </div>
      )}

      {/* Skill Ratings */}
      {skill_ratings && skill_ratings.length > 0 && (
        <div className="mb-4">
          <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Skill Ratings</h4>
          <div className="space-y-2">
            {skill_ratings.map((sr, idx) => (
              <div key={idx} className="p-3 bg-white rounded-xl ring-1 ring-slate-100">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-sm font-semibold text-slate-700">{sr.skill}</span>
                  <RatingBadge rating={sr.rating} />
                </div>
                <ScoreBar score={sr.score || 0} />
                {sr.evidence && (
                  <p className="text-xs text-slate-400 mt-1.5 italic">"{sr.evidence}"</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Strengths */}
      {strengths && strengths.length > 0 && (
        <div className="mb-4">
          <h4 className="text-xs font-bold text-emerald-600 uppercase tracking-wider mb-2 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" /> Strengths
          </h4>
          <ul className="space-y-1">
            {strengths.map((s, idx) => (
              <li key={idx} className="text-sm text-slate-600 flex items-start gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 mt-1.5 shrink-0" />
                {s}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Concerns */}
      {concerns && concerns.length > 0 && (
        <div className="mb-4">
          <h4 className="text-xs font-bold text-amber-600 uppercase tracking-wider mb-2 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" /> Concerns
          </h4>
          <ul className="space-y-1">
            {concerns.map((c, idx) => (
              <li key={idx} className="text-sm text-slate-600 flex items-start gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 mt-1.5 shrink-0" />
                {c}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Follow-up Questions */}
      {follow_up_questions && follow_up_questions.length > 0 && (
        <div>
          <h4 className="text-xs font-bold text-brand-600 uppercase tracking-wider mb-2 flex items-center gap-1">
            <FileText className="w-3 h-3" /> Suggested Follow-ups
          </h4>
          <ul className="space-y-1.5">
            {follow_up_questions.map((q, idx) => (
              <li key={idx} className="text-sm text-slate-600 p-2 bg-brand-50/50 rounded-lg">
                {q}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Question-by-Question */}
      {question_assessments && question_assessments.length > 0 && (
        <div className="mt-4 border-t border-slate-100 pt-4">
          <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Question Breakdown</h4>
          <div className="space-y-3">
            {question_assessments.map((qa, idx) => (
              <div key={idx} className="p-3 bg-slate-50 rounded-xl">
                <p className="text-sm font-semibold text-slate-700 mb-1">Q{idx + 1}: {qa.question}</p>
                {qa.skill_tested && (
                  <span className="inline-block text-xs bg-brand-100 text-brand-700 rounded-full px-2 py-0.5 mb-2">
                    {qa.skill_tested}
                  </span>
                )}
                <p className="text-sm text-slate-600 mb-2">
                  <span className="font-medium text-slate-500">Answer: </span>
                  {qa.answer_summary || '—'}
                </p>
                <div className="flex items-center gap-2">
                  <RatingBadge rating={qa.rating} />
                  {qa.score != null && <span className="text-xs font-bold text-slate-500">{qa.score}/10</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
