import { ArrowRight, TrendingUp, TrendingDown, Minus, X } from 'lucide-react'

export default function ComparisonView({ 
  version1, 
  version2, 
  onClose,
  className = '' 
}) {
  if (!version1 || !version2) return null

  const getScoreDiff = (score1, score2) => {
    return score1 - score2
  }

  const formatWeight = (value) => {
    return Math.round(Math.abs(value) * 100) + '%'
  }

  const getWeightDiff = (w1, w2) => {
    const diff = (w1 - w2) * 100
    if (Math.abs(diff) < 1) return null
    return diff
  }

  const getRoleBadgeColor = (category) => {
    const colors = {
      technical: 'bg-blue-100 text-blue-700',
      sales: 'bg-green-100 text-green-700',
      hr: 'bg-purple-100 text-purple-700',
      marketing: 'bg-pink-100 text-pink-700',
      operations: 'bg-orange-100 text-orange-700',
      leadership: 'bg-indigo-100 text-indigo-700',
    }
    return colors[category?.toLowerCase()] || 'bg-slate-100 text-slate-700'
  }

  const v1Result = version1.analysis_result || {}
  const v2Result = version2.analysis_result || {}
  const v1Weights = version1.suggested_weights_json ? JSON.parse(version1.suggested_weights_json) : {}
  const v2Weights = version2.suggested_weights_json ? JSON.parse(version2.suggested_weights_json) : {}

  const scoreDiff = getScoreDiff(v1Result.fit_score || 0, v2Result.fit_score || 0)

  const allWeightKeys = new Set([
    ...Object.keys(v1Weights),
    ...Object.keys(v2Weights)
  ])

  return (
    <div className={`fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm ${className}`}>
      <div className="bg-white rounded-2xl shadow-2xl max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-slate-200 bg-gradient-to-r from-indigo-50 to-purple-50">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-xl font-bold text-slate-800 mb-1">
                Version Comparison
              </h2>
              <p className="text-sm text-slate-600">
                Compare scoring weights and results side-by-side
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-all"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="grid grid-cols-2 gap-6">
            {/* Version 1 */}
            <div className="space-y-4">
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-sm font-bold text-slate-800">
                    Version {version1.version_number}
                  </span>
                  {version1.is_active && (
                    <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-semibold rounded">
                      ACTIVE
                    </span>
                  )}
                  {version1.role_category && (
                    <span className={`px-2 py-0.5 text-xs font-semibold rounded ${getRoleBadgeColor(version1.role_category)}`}>
                      {version1.role_category.toUpperCase()}
                    </span>
                  )}
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-bold text-slate-800">
                    {v1Result.fit_score || 0}
                  </span>
                  <span className="text-sm text-slate-500">/ 100</span>
                </div>
                {v1Result.final_recommendation && (
                  <span className={`inline-block mt-2 px-2 py-0.5 text-xs font-semibold rounded ${
                    v1Result.final_recommendation === 'Shortlist'
                      ? 'bg-green-100 text-green-700'
                      : v1Result.final_recommendation === 'Consider'
                      ? 'bg-yellow-100 text-yellow-700'
                      : 'bg-red-100 text-red-700'
                  }`}>
                    {v1Result.final_recommendation}
                  </span>
                )}
              </div>

              {/* Weights */}
              <div className="space-y-2">
                <h3 className="text-sm font-semibold text-slate-700">Scoring Weights</h3>
                {Array.from(allWeightKeys).map(key => (
                  <div key={key} className="flex justify-between items-center text-sm">
                    <span className="text-slate-600 capitalize">
                      {key.replace(/_/g, ' ')}
                    </span>
                    <span className="font-semibold text-slate-800">
                      {formatWeight(v1Weights[key] || 0)}
                    </span>
                  </div>
                ))}
              </div>

              {/* Reasoning */}
              {version1.weight_reasoning && (
                <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <p className="text-xs font-semibold text-blue-800 mb-1">Reasoning</p>
                  <p className="text-xs text-blue-700 leading-relaxed">
                    {version1.weight_reasoning}
                  </p>
                </div>
              )}
            </div>

            {/* Version 2 */}
            <div className="space-y-4">
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-sm font-bold text-slate-800">
                    Version {version2.version_number}
                  </span>
                  {version2.is_active && (
                    <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-semibold rounded">
                      ACTIVE
                    </span>
                  )}
                  {version2.role_category && (
                    <span className={`px-2 py-0.5 text-xs font-semibold rounded ${getRoleBadgeColor(version2.role_category)}`}>
                      {version2.role_category.toUpperCase()}
                    </span>
                  )}
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-bold text-slate-800">
                    {v2Result.fit_score || 0}
                  </span>
                  <span className="text-sm text-slate-500">/ 100</span>
                </div>
                {v2Result.final_recommendation && (
                  <span className={`inline-block mt-2 px-2 py-0.5 text-xs font-semibold rounded ${
                    v2Result.final_recommendation === 'Shortlist'
                      ? 'bg-green-100 text-green-700'
                      : v2Result.final_recommendation === 'Consider'
                      ? 'bg-yellow-100 text-yellow-700'
                      : 'bg-red-100 text-red-700'
                  }`}>
                    {v2Result.final_recommendation}
                  </span>
                )}
              </div>

              {/* Weights */}
              <div className="space-y-2">
                <h3 className="text-sm font-semibold text-slate-700">Scoring Weights</h3>
                {Array.from(allWeightKeys).map(key => {
                  const diff = getWeightDiff(v2Weights[key] || 0, v1Weights[key] || 0)
                  return (
                    <div key={key} className="flex justify-between items-center text-sm">
                      <span className="text-slate-600 capitalize">
                        {key.replace(/_/g, ' ')}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-slate-800">
                          {formatWeight(v2Weights[key] || 0)}
                        </span>
                        {diff !== null && (
                          <span className={`text-xs font-semibold ${
                            diff > 0 ? 'text-green-600' : diff < 0 ? 'text-red-600' : 'text-slate-500'
                          }`}>
                            {diff > 0 ? '+' : ''}{diff.toFixed(0)}%
                          </span>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>

              {/* Reasoning */}
              {version2.weight_reasoning && (
                <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <p className="text-xs font-semibold text-blue-800 mb-1">Reasoning</p>
                  <p className="text-xs text-blue-700 leading-relaxed">
                    {version2.weight_reasoning}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Impact Summary */}
          <div className="mt-6 p-4 bg-gradient-to-r from-indigo-50 to-purple-50 border border-indigo-200 rounded-xl">
            <h3 className="text-sm font-bold text-slate-800 mb-3">Impact Summary</h3>
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center">
                <p className="text-xs text-slate-600 mb-1">Score Change</p>
                <div className={`flex items-center justify-center gap-1 text-lg font-bold ${
                  scoreDiff > 0 ? 'text-green-600' : scoreDiff < 0 ? 'text-red-600' : 'text-slate-600'
                }`}>
                  {scoreDiff > 0 ? (
                    <TrendingUp className="w-5 h-5" />
                  ) : scoreDiff < 0 ? (
                    <TrendingDown className="w-5 h-5" />
                  ) : (
                    <Minus className="w-5 h-5" />
                  )}
                  {scoreDiff > 0 ? '+' : ''}{scoreDiff}
                </div>
              </div>
              <div className="text-center">
                <p className="text-xs text-slate-600 mb-1">Recommendation</p>
                <div className="flex items-center justify-center gap-2">
                  <span className={`px-2 py-0.5 text-xs font-semibold rounded ${
                    v1Result.final_recommendation === 'Shortlist'
                      ? 'bg-green-100 text-green-700'
                      : v1Result.final_recommendation === 'Consider'
                      ? 'bg-yellow-100 text-yellow-700'
                      : 'bg-red-100 text-red-700'
                  }`}>
                    {v1Result.final_recommendation || 'N/A'}
                  </span>
                  <ArrowRight className="w-4 h-4 text-slate-400" />
                  <span className={`px-2 py-0.5 text-xs font-semibold rounded ${
                    v2Result.final_recommendation === 'Shortlist'
                      ? 'bg-green-100 text-green-700'
                      : v2Result.final_recommendation === 'Consider'
                      ? 'bg-yellow-100 text-yellow-700'
                      : 'bg-red-100 text-red-700'
                  }`}>
                    {v2Result.final_recommendation || 'N/A'}
                  </span>
                </div>
              </div>
              <div className="text-center">
                <p className="text-xs text-slate-600 mb-1">Risk Level</p>
                <div className="flex items-center justify-center gap-2">
                  <span className={`px-2 py-0.5 text-xs font-semibold rounded ${
                    v1Result.risk_level === 'Low'
                      ? 'bg-green-100 text-green-700'
                      : v1Result.risk_level === 'Medium'
                      ? 'bg-yellow-100 text-yellow-700'
                      : 'bg-red-100 text-red-700'
                  }`}>
                    {v1Result.risk_level || 'N/A'}
                  </span>
                  <ArrowRight className="w-4 h-4 text-slate-400" />
                  <span className={`px-2 py-0.5 text-xs font-semibold rounded ${
                    v2Result.risk_level === 'Low'
                      ? 'bg-green-100 text-green-700'
                      : v2Result.risk_level === 'Medium'
                      ? 'bg-yellow-100 text-yellow-700'
                      : 'bg-red-100 text-red-700'
                  }`}>
                    {v2Result.risk_level || 'N/A'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-slate-200 bg-slate-50">
          <button
            onClick={onClose}
            className="w-full px-6 py-2.5 text-sm font-semibold text-white bg-gradient-to-r from-indigo-600 to-purple-600 rounded-lg hover:from-indigo-700 hover:to-purple-700 transition-all shadow-md hover:shadow-lg"
          >
            Close Comparison
          </button>
        </div>
      </div>
    </div>
  )
}
