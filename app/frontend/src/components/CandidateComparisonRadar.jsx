import { useMemo, useState } from 'react'
import { Users, BarChart3, FileText } from 'lucide-react'

const CANDIDATE_COLORS = [
  { name: 'blue', bg: 'bg-blue-500', light: 'bg-blue-50', text: 'text-blue-700', ring: 'ring-blue-200', border: 'border-blue-200' },
  { name: 'green', bg: 'bg-emerald-500', light: 'bg-emerald-50', text: 'text-emerald-700', ring: 'ring-emerald-200', border: 'border-emerald-200' },
  { name: 'amber', bg: 'bg-amber-500', light: 'bg-amber-50', text: 'text-amber-700', ring: 'ring-amber-200', border: 'border-amber-200' },
  { name: 'red', bg: 'bg-red-500', light: 'bg-red-50', text: 'text-red-700', ring: 'ring-red-200', border: 'border-red-200' },
  { name: 'purple', bg: 'bg-purple-500', light: 'bg-purple-50', text: 'text-purple-700', ring: 'ring-purple-200', border: 'border-purple-200' },
]

const RECOMMENDATION_COLORS = {
  strong_hire: 'bg-emerald-100 text-emerald-800 ring-emerald-200',
  hire: 'bg-green-100 text-green-700 ring-green-200',
  maybe: 'bg-amber-100 text-amber-700 ring-amber-200',
  no_hire: 'bg-red-100 text-red-700 ring-red-200',
  strong_no_hire: 'bg-red-200 text-red-800 ring-red-200',
}

const DIMENSIONS = [
  { key: 'technical_score', label: 'Technical' },
  { key: 'behavioral_score', label: 'Behavioral' },
  { key: 'communication_score', label: 'Communication' },
  { key: 'cultural_fit_score', label: 'Cultural Fit' },
  { key: 'motivation_score', label: 'Motivation' },
]

function formatRecommendation(value) {
  if (!value) return '—'
  return value.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function ScoreBar({ score, colorClass, max = 100 }) {
  const pct = Math.min(Math.max((score ?? 0) / max, 0), 1) * 100
  return (
    <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
      <div
        className={`h-full ${colorClass} transition-all duration-500`}
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}

export default function CandidateComparisonRadar({ scorecards }) {
  const [selectedIds, setSelectedIds] = useState(() =>
    scorecards.map((s) => s.candidate_id)
  )

  const selectedScorecards = useMemo(
    () => scorecards.filter((s) => selectedIds.includes(s.candidate_id)),
    [scorecards, selectedIds]
  )

  function toggleCandidate(id) {
    setSelectedIds((prev) => {
      if (prev.includes(id)) {
        // Keep at least one selected so the table never empties
        if (prev.length === 1) return prev
        return prev.filter((x) => x !== id)
      }
      // Cap at 5
      if (prev.length >= 5) return prev
      return [...prev, id]
    })
  }

  if (!scorecards || scorecards.length === 0) {
    return (
      <div className="text-center py-12 text-slate-400">
        <BarChart3 className="w-12 h-12 mx-auto mb-4 opacity-40" />
        <p className="text-sm">No scorecards available to compare.</p>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Candidate selector */}
      <div className="bg-white rounded-2xl ring-1 ring-slate-200 p-4">
        <div className="flex items-center gap-2 mb-3">
          <Users className="w-4 h-4 text-slate-400" />
          <span className="text-sm font-semibold text-slate-700">
            Select candidates to compare ({selectedIds.length}/5)
          </span>
        </div>
        <div className="flex flex-wrap gap-2">
          {scorecards.map((sc, idx) => {
            const color = CANDIDATE_COLORS[idx % CANDIDATE_COLORS.length]
            const isSelected = selectedIds.includes(sc.candidate_id)
            return (
              <button
                key={sc.candidate_id}
                onClick={() => toggleCandidate(sc.candidate_id)}
                className={`flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium transition-all ring-1 ${
                  isSelected
                    ? `${color.light} ${color.text} ${color.ring}`
                    : 'bg-slate-50 text-slate-500 ring-slate-200 hover:bg-slate-100'
                }`}
              >
                <span className={`w-3 h-3 rounded-full ${isSelected ? color.bg : 'bg-slate-300'}`} />
                <span className="truncate max-w-[160px]">
                  {sc.candidate_name || `Candidate #${sc.candidate_id}`}
                </span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Comparison table */}
      <div className="bg-white rounded-2xl ring-1 ring-slate-200 overflow-hidden">
        <div className="px-4 py-4 border-b border-slate-100 flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-brand-600" />
          <h3 className="font-bold text-slate-800">Scorecard Comparison</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50/70">
                <th className="text-left px-4 py-3 font-semibold text-slate-500 sticky left-0 bg-slate-50/70 min-w-[140px]">
                  Metric
                </th>
                {selectedScorecards.map((sc, idx) => {
                  const color = CANDIDATE_COLORS[idx % CANDIDATE_COLORS.length]
                  return (
                    <th key={sc.candidate_id} className="px-4 py-3 min-w-[180px]">
                      <div className="flex items-center gap-2">
                        <span className={`w-2.5 h-2.5 rounded-full ${color.bg}`} />
                        <span className="font-bold text-slate-700 truncate max-w-[180px]">
                          {sc.candidate_name || `Candidate #${sc.candidate_id}`}
                        </span>
                      </div>
                    </th>
                  )
                })}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {/* Overall score */}
              <tr>
                <td className="px-4 py-3 font-semibold text-slate-700 sticky left-0 bg-white">
                  Overall Score
                </td>
                {selectedScorecards.map((sc) => (
                  <td key={sc.candidate_id} className="px-4 py-3">
                    <span className="text-xl font-extrabold text-slate-900">
                      {sc.overall_score ?? '—'}
                    </span>
                    <span className="text-xs text-slate-400 font-medium">/100</span>
                  </td>
                ))}
              </tr>

              {/* Recommendation */}
              <tr>
                <td className="px-4 py-3 font-semibold text-slate-700 sticky left-0 bg-white">
                  Recommendation
                </td>
                {selectedScorecards.map((sc) => (
                  <td key={sc.candidate_id} className="px-4 py-3">
                    {sc.recommendation ? (
                      <span
                        className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold capitalize ring-1 ${
                          RECOMMENDATION_COLORS[sc.recommendation] || 'bg-slate-100 text-slate-700 ring-slate-200'
                        }`}
                      >
                        {formatRecommendation(sc.recommendation)}
                      </span>
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </td>
                ))}
              </tr>

              {/* Confidence */}
              <tr>
                <td className="px-4 py-3 font-semibold text-slate-700 sticky left-0 bg-white">
                  Confidence
                </td>
                {selectedScorecards.map((sc) => (
                  <td key={sc.candidate_id} className="px-4 py-3">
                    <span className="capitalize text-slate-600">
                      {sc.confidence_level || '—'}
                    </span>
                  </td>
                ))}
              </tr>

              {/* Dimension rows */}
              {DIMENSIONS.map((dim) => (
                <tr key={dim.key}>
                  <td className="px-4 py-3 font-semibold text-slate-700 sticky left-0 bg-white">
                    {dim.label}
                  </td>
                  {selectedScorecards.map((sc, idx) => {
                    const color = CANDIDATE_COLORS[idx % CANDIDATE_COLORS.length]
                    const score = sc[dim.key]
                    return (
                      <td key={sc.candidate_id} className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className="flex-1 min-w-[80px]">
                            <ScoreBar score={score} colorClass={color.bg} />
                          </div>
                          <span className="text-sm font-bold text-slate-700 w-8 text-right">
                            {score ?? '—'}
                          </span>
                        </div>
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Executive summary cards */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <FileText className="w-5 h-5 text-brand-600" />
          <h3 className="font-bold text-slate-800">Executive Summaries</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {selectedScorecards.map((sc, idx) => {
            const color = CANDIDATE_COLORS[idx % CANDIDATE_COLORS.length]
            return (
              <div
                key={sc.candidate_id}
                className={`bg-white rounded-2xl ring-1 ${color.border} p-5`}
              >
                <div className="flex items-center gap-2 mb-3">
                  <span className={`w-3 h-3 rounded-full ${color.bg}`} />
                  <h4 className="font-bold text-slate-800 truncate">
                    {sc.candidate_name || `Candidate #${sc.candidate_id}`}
                  </h4>
                </div>
                {sc.executive_summary ? (
                  <p className="text-sm text-slate-600 leading-relaxed whitespace-pre-line">
                    {sc.executive_summary}
                  </p>
                ) : (
                  <p className="text-sm text-slate-400 italic">No summary available.</p>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
