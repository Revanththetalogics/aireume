import { ThumbsUp, ThumbsDown, AlertTriangle, ChevronDown, ChevronUp, CheckCircle, XCircle, Target, TrendingUp, Shield } from 'lucide-react'
import { useState } from 'react'

function ScoreBar({ label, value, color }) {
  const barColor = {
    green: 'bg-green-500',
    blue: 'bg-blue-500',
    amber: 'bg-amber-500',
    purple: 'bg-purple-500'
  }[color] || 'bg-slate-400'

  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <span className="text-xs font-medium text-slate-600">{label}</span>
        <span className="text-xs font-bold text-slate-700">{value}%</span>
      </div>
      <div className="w-full bg-slate-100 rounded-full h-2">
        <div
          className={`h-2 rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
        />
      </div>
    </div>
  )
}

function RiskBadge({ level }) {
  const styles = {
    Low: 'bg-green-100 text-green-700 border-green-200',
    Medium: 'bg-amber-100 text-amber-700 border-amber-200',
    High: 'bg-red-100 text-red-700 border-red-200'
  }
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold border ${styles[level] || styles.Medium}`}>
      {level} Risk
    </span>
  )
}

export default function ResultCard({ result }) {
  const [showEducation, setShowEducation] = useState(false)

  const {
    fit_score,
    strengths,
    weaknesses,
    education_analysis,
    risk_signals,
    final_recommendation,
    score_breakdown,
    matched_skills,
    missing_skills,
    risk_level
  } = result

  let badgeColor = 'bg-yellow-100 text-yellow-800 border-yellow-200'
  let BadgeIcon = Target
  if (final_recommendation === 'Shortlist') {
    badgeColor = 'bg-green-100 text-green-800 border-green-200'
    BadgeIcon = CheckCircle
  } else if (final_recommendation === 'Reject') {
    badgeColor = 'bg-red-100 text-red-800 border-red-200'
    BadgeIcon = XCircle
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 md:p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold text-slate-800">Analysis Results</h2>
        <div className="flex items-center gap-2">
          {risk_level && <RiskBadge level={risk_level} />}
          <span className={`flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-semibold border ${badgeColor}`}>
            <BadgeIcon className="w-4 h-4" />
            {final_recommendation}
          </span>
        </div>
      </div>

      {/* Score Breakdown (enterprise) */}
      {score_breakdown && Object.keys(score_breakdown).length > 0 && (
        <div className="bg-slate-50 rounded-lg p-5 border border-slate-200">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="w-4 h-4 text-slate-500" />
            <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">Score Breakdown</h3>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <ScoreBar label="Skill Match" value={score_breakdown.skill_match || 0} color="blue" />
            <ScoreBar label="Experience" value={score_breakdown.experience_match || 0} color="green" />
            <ScoreBar label="Stability" value={score_breakdown.stability || 0} color="purple" />
            <ScoreBar label="Education" value={score_breakdown.education || 0} color="amber" />
          </div>
        </div>
      )}

      {/* Skills Intel */}
      {((matched_skills && matched_skills.length > 0) || (missing_skills && missing_skills.length > 0)) && (
        <div className="grid grid-cols-2 gap-4">
          {matched_skills && matched_skills.length > 0 && (
            <div className="bg-green-50 rounded-lg p-4 border border-green-100">
              <div className="flex items-center gap-1.5 mb-2">
                <CheckCircle className="w-4 h-4 text-green-600" />
                <span className="text-xs font-semibold text-green-700 uppercase tracking-wide">Matched Skills</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {matched_skills.slice(0, 8).map((s, i) => (
                  <span key={i} className="px-2 py-0.5 bg-green-100 text-green-800 text-xs rounded-full font-medium">{s}</span>
                ))}
              </div>
            </div>
          )}
          {missing_skills && missing_skills.length > 0 && (
            <div className="bg-red-50 rounded-lg p-4 border border-red-100">
              <div className="flex items-center gap-1.5 mb-2">
                <XCircle className="w-4 h-4 text-red-600" />
                <span className="text-xs font-semibold text-red-700 uppercase tracking-wide">Missing Skills</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {missing_skills.slice(0, 6).map((s, i) => (
                  <span key={i} className="px-2 py-0.5 bg-red-100 text-red-800 text-xs rounded-full font-medium">{s}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Strengths / Weaknesses / Risks */}
      <div className="grid md:grid-cols-3 gap-4">
        <div className="bg-green-50 rounded-lg p-4 border-l-4 border-green-500">
          <div className="flex items-center gap-2 mb-3">
            <ThumbsUp className="w-5 h-5 text-green-600" />
            <h3 className="font-semibold text-green-800">Strengths</h3>
          </div>
          <ul className="space-y-2">
            {strengths && strengths.length > 0 ? (
              strengths.slice(0, 5).map((s, i) => (
                <li key={i} className="text-sm text-green-700 flex items-start gap-2">
                  <span className="text-green-500 mt-1">•</span>{s}
                </li>
              ))
            ) : (
              <li className="text-sm text-green-600 italic">No specific strengths identified</li>
            )}
          </ul>
        </div>

        <div className="bg-red-50 rounded-lg p-4 border-l-4 border-red-500">
          <div className="flex items-center gap-2 mb-3">
            <ThumbsDown className="w-5 h-5 text-red-600" />
            <h3 className="font-semibold text-red-800">Weaknesses</h3>
          </div>
          <ul className="space-y-2">
            {weaknesses && weaknesses.length > 0 ? (
              weaknesses.slice(0, 5).map((w, i) => (
                <li key={i} className="text-sm text-red-700 flex items-start gap-2">
                  <span className="text-red-500 mt-1">•</span>{w}
                </li>
              ))
            ) : (
              <li className="text-sm text-red-600 italic">No significant weaknesses</li>
            )}
          </ul>
        </div>

        <div className="bg-amber-50 rounded-lg p-4 border-l-4 border-amber-500">
          <div className="flex items-center gap-2 mb-3">
            <Shield className="w-5 h-5 text-amber-600" />
            <h3 className="font-semibold text-amber-800">Risk Signals</h3>
          </div>
          <ul className="space-y-2">
            {risk_signals && risk_signals.length > 0 ? (
              risk_signals.map((risk, i) => (
                <li key={i} className="text-sm text-amber-700 flex items-start gap-2">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-500 mt-0.5 shrink-0" />
                  {typeof risk === 'string' ? risk : risk.description}
                </li>
              ))
            ) : (
              <li className="text-sm text-amber-600 italic">No risk signals detected</li>
            )}
          </ul>
        </div>
      </div>

      {/* Education (collapsible) */}
      <div className="border border-slate-200 rounded-lg">
        <button
          onClick={() => setShowEducation(!showEducation)}
          className="w-full flex items-center justify-between p-4 hover:bg-slate-50 transition-colors"
        >
          <span className="font-semibold text-slate-700">Education Analysis</span>
          {showEducation
            ? <ChevronUp className="w-5 h-5 text-slate-500" />
            : <ChevronDown className="w-5 h-5 text-slate-500" />
          }
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
