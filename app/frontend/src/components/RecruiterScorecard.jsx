import { Brain, TrendingUp, ArrowRight, CheckCircle2, XCircle, AlertCircle } from 'lucide-react'

const RECOMMENDATION_CONFIG = {
  strong_hire: { label: 'Strong Hire', color: 'bg-emerald-100 text-emerald-800', icon: CheckCircle2 },
  hire:        { label: 'Hire',        color: 'bg-green-100 text-green-700',     icon: CheckCircle2 },
  maybe:       { label: 'Maybe',       color: 'bg-amber-100 text-amber-700',     icon: AlertCircle },
  no_hire:     { label: 'No Hire',     color: 'bg-red-100 text-red-700',         icon: XCircle },
  strong_no_hire: { label: 'Strong No Hire', color: 'bg-red-200 text-red-800',   icon: XCircle },
}

const DIMENSION_LABELS = {
  technical:      'Technical',
  communication:  'Communication',
  experience:     'Experience',
  culture_fit:    'Culture Fit',
  problem_solving:'Problem Solving',
}

function ScoreBar({ label, score, max = 100 }) {
  const pct = Math.min(100, Math.max(0, (score / max) * 100))
  const color =
    pct >= 80 ? 'bg-emerald-500' :
    pct >= 60 ? 'bg-green-500' :
    pct >= 40 ? 'bg-amber-500' :
    'bg-red-500'
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-semibold text-slate-600">{label}</span>
        <span className="text-xs font-bold text-slate-700">{score}/{max}</span>
      </div>
      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-500 ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function ScoreGauge({ score, max = 100 }) {
  const pct = Math.min(100, Math.max(0, (score / max) * 100))
  const color =
    pct >= 80 ? 'text-emerald-600' :
    pct >= 60 ? 'text-green-600' :
    pct >= 40 ? 'text-amber-600' :
    'text-red-600'
  const ringColor =
    pct >= 80 ? 'stroke-emerald-500' :
    pct >= 60 ? 'stroke-green-500' :
    pct >= 40 ? 'stroke-amber-500' :
    'stroke-red-500'
  const circumference = 2 * Math.PI * 44
  const offset = circumference - (pct / 100) * circumference
  return (
    <div className="relative w-28 h-28 mx-auto">
      <svg className="w-28 h-28 -rotate-90" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="44" fill="none" strokeWidth="8" className="stroke-slate-100" />
        <circle
          cx="50" cy="50" r="44" fill="none" strokeWidth="8"
          className={ringColor}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 0.8s ease' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`text-2xl font-bold ${color}`}>{score}</span>
        <span className="text-xs text-slate-400">/ {max}</span>
      </div>
    </div>
  )
}

export default function RecruiterScorecard({ scorecard }) {
  if (!scorecard) return null

  const dimensions = scorecard.dimensions || {}
  const recommendation = scorecard.recommendation || null
  const recConfig = RECOMMENDATION_CONFIG[recommendation] || null
  const RecIcon = recConfig?.icon || null

  const fitment = scorecard.fitment_adjustment || null

  return (
    <div className="space-y-6">
      {/* Overall Score + Recommendation */}
      <div className="bg-white rounded-2xl ring-1 ring-slate-200 p-6">
        <div className="flex flex-col md:flex-row items-center gap-6">
          <ScoreGauge score={scorecard.overall_score || 0} />
          <div className="flex-1 text-center md:text-left">
            <h3 className="text-lg font-bold text-slate-900">Overall Score</h3>
            {recConfig && (
              <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold mt-2 ${recConfig.color}`}>
                {RecIcon && <RecIcon className="w-4 h-4" />}
                {recConfig.label}
              </div>
            )}
            {scorecard.confidence != null && (
              <p className="text-xs text-slate-400 mt-2">
                Confidence: <span className="font-semibold text-slate-600">{Math.round(scorecard.confidence * 100)}%</span>
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Dimension Bars */}
      <div className="bg-white rounded-2xl ring-1 ring-slate-200 p-6">
        <h3 className="text-sm font-bold text-slate-800 mb-4 flex items-center gap-2">
          <Brain className="w-4 h-4 text-brand-600" />
          Dimension Scores
        </h3>
        <div className="space-y-4">
          {Object.entries(DIMENSION_LABELS).map(([key, label]) => {
            const val = dimensions[key]
            if (val == null) return null
            return <ScoreBar key={key} label={label} score={typeof val === 'object' ? val.score || 0 : val} />
          })}
        </div>
      </div>

      {/* Fitment Adjustment */}
      {fitment && (
        <div className="bg-white rounded-2xl ring-1 ring-slate-200 p-6">
          <h3 className="text-sm font-bold text-slate-800 mb-4 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-brand-600" />
            Fitment Adjustment
          </h3>
          <div className="flex items-center justify-center gap-4">
            <div className="text-center">
              <p className="text-xs text-slate-400 mb-1">Original</p>
              <p className="text-2xl font-bold text-slate-600">{fitment.original_score ?? '—'}</p>
            </div>
            <ArrowRight className="w-5 h-5 text-slate-300" />
            <div className="text-center">
              <p className="text-xs text-slate-400 mb-1">Adjusted</p>
              <p className={`text-2xl font-bold ${
                (fitment.adjusted_score || 0) >= (fitment.original_score || 0)
                  ? 'text-emerald-600' : 'text-amber-600'
              }`}>{fitment.adjusted_score ?? '—'}</p>
            </div>
            {fitment.delta != null && (
              <div className="text-center">
                <p className="text-xs text-slate-400 mb-1">Delta</p>
                <p className={`text-lg font-bold ${fitment.delta >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                  {fitment.delta > 0 ? '+' : ''}{fitment.delta}
                </p>
              </div>
            )}
          </div>
          {fitment.rationale && (
            <p className="text-xs text-slate-500 mt-4 text-center italic">{fitment.rationale}</p>
          )}
        </div>
      )}

      {/* Dimension Detail Cards */}
      {Object.entries(dimensions).length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Object.entries(dimensions).map(([key, val]) => {
            if (typeof val !== 'object') return null
            const label = DIMENSION_LABELS[key] || key.replace(/_/g, ' ')
            return (
              <div key={key} className="bg-white rounded-2xl ring-1 ring-slate-200 p-5">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-bold text-slate-800">{label}</h4>
                  <span className="text-sm font-bold text-brand-600">{val.score ?? '—'}</span>
                </div>
                {val.highlights && val.highlights.length > 0 && (
                  <ul className="space-y-1 mt-2">
                    {val.highlights.map((h, i) => (
                      <li key={i} className="text-xs text-slate-500 pl-3 border-l-2 border-brand-100">{h}</li>
                    ))}
                  </ul>
                )}
                {val.notes && <p className="text-xs text-slate-500 mt-2">{val.notes}</p>}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
