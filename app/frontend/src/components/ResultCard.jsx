import { ThumbsUp, ThumbsDown, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react'
import { useState } from 'react'

export default function ResultCard({ result }) {
  const [showEducation, setShowEducation] = useState(false)

  const {
    fit_score,
    strengths,
    weaknesses,
    education_analysis,
    risk_signals,
    final_recommendation
  } = result

  // Determine badge color based on recommendation
  let badgeColor = 'bg-yellow-100 text-yellow-800 border-yellow-200'
  if (final_recommendation === 'Shortlist') {
    badgeColor = 'bg-green-100 text-green-800 border-green-200'
  } else if (final_recommendation === 'Reject') {
    badgeColor = 'bg-red-100 text-red-800 border-red-200'
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 md:p-8">
      {/* Header with recommendation badge */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-semibold text-slate-800">Analysis Results</h2>
        <span className={`px-4 py-2 rounded-full text-sm font-semibold border ${badgeColor}`}>
          {final_recommendation}
        </span>
      </div>

      {/* Three column layout for Strengths, Weaknesses, Risks */}
      <div className="grid md:grid-cols-3 gap-4 mb-6">
        {/* Strengths */}
        <div className="bg-green-50 rounded-lg p-4 border-l-4 border-green-500">
          <div className="flex items-center gap-2 mb-3">
            <ThumbsUp className="w-5 h-5 text-green-600" />
            <h3 className="font-semibold text-green-800">Strengths</h3>
          </div>
          <ul className="space-y-2">
            {strengths && strengths.length > 0 ? (
              strengths.slice(0, 5).map((strength, i) => (
                <li key={i} className="text-sm text-green-700 flex items-start gap-2">
                  <span className="text-green-500 mt-1">•</span>
                  {strength}
                </li>
              ))
            ) : (
              <li className="text-sm text-green-600 italic">No specific strengths identified</li>
            )}
          </ul>
        </div>

        {/* Weaknesses */}
        <div className="bg-red-50 rounded-lg p-4 border-l-4 border-red-500">
          <div className="flex items-center gap-2 mb-3">
            <ThumbsDown className="w-5 h-5 text-red-600" />
            <h3 className="font-semibold text-red-800">Weaknesses</h3>
          </div>
          <ul className="space-y-2">
            {weaknesses && weaknesses.length > 0 ? (
              weaknesses.slice(0, 5).map((weakness, i) => (
                <li key={i} className="text-sm text-red-700 flex items-start gap-2">
                  <span className="text-red-500 mt-1">•</span>
                  {weakness}
                </li>
              ))
            ) : (
              <li className="text-sm text-red-600 italic">No significant weaknesses</li>
            )}
          </ul>
        </div>

        {/* Risk Signals */}
        <div className="bg-amber-50 rounded-lg p-4 border-l-4 border-amber-500">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-5 h-5 text-amber-600" />
            <h3 className="font-semibold text-amber-800">Risk Signals</h3>
          </div>
          <ul className="space-y-2">
            {risk_signals && risk_signals.length > 0 ? (
              risk_signals.map((risk, i) => (
                <li key={i} className="text-sm text-amber-700 flex items-start gap-2">
                  <span className="text-amber-500 mt-1">!</span>
                  {typeof risk === 'string' ? risk : risk.description}
                </li>
              ))
            ) : (
              <li className="text-sm text-amber-600 italic">No risk signals detected</li>
            )}
          </ul>
        </div>
      </div>

      {/* Education Analysis (collapsible) */}
      <div className="border border-slate-200 rounded-lg">
        <button
          onClick={() => setShowEducation(!showEducation)}
          className="w-full flex items-center justify-between p-4 hover:bg-slate-50 transition-colors"
        >
          <span className="font-semibold text-slate-700">Education Analysis</span>
          {showEducation ? (
            <ChevronUp className="w-5 h-5 text-slate-500" />
          ) : (
            <ChevronDown className="w-5 h-5 text-slate-500" />
          )}
        </button>
        {showEducation && (
          <div className="px-4 pb-4">
            <p className="text-sm text-slate-600 leading-relaxed">
              {education_analysis || 'No education analysis available.'}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
