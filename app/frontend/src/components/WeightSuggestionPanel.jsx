import { useState } from 'react'
import { Sparkles, TrendingUp, AlertCircle, Check, Loader2, ChevronDown, ChevronUp } from 'lucide-react'
import api from '../lib/api'

export default function WeightSuggestionPanel({ 
  jobDescription, 
  onWeightsAccepted, 
  currentWeights,
  className = '' 
}) {
  const [suggestion, setSuggestion] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [expanded, setExpanded] = useState(true)

  const fetchSuggestion = async () => {
    if (!jobDescription || jobDescription.trim().length < 50) {
      setError('Job description is too short for AI analysis')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append('job_description', jobDescription)

      const response = await api.post('/analyze/suggest-weights', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })

      setSuggestion(response.data)
      setExpanded(true)
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to get weight suggestions'
      setError(errorMsg)
    } finally {
      setLoading(false)
    }
  }

  const handleAcceptWeights = () => {
    if (suggestion?.suggested_weights) {
      onWeightsAccepted(suggestion.suggested_weights)
    }
  }

  const getRoleBadgeColor = (category) => {
    const colors = {
      technical: 'bg-blue-100 text-blue-700 ring-blue-200',
      sales: 'bg-green-100 text-green-700 ring-green-200',
      hr: 'bg-purple-100 text-purple-700 ring-purple-200',
      marketing: 'bg-pink-100 text-pink-700 ring-pink-200',
      operations: 'bg-orange-100 text-orange-700 ring-orange-200',
      leadership: 'bg-indigo-100 text-indigo-700 ring-indigo-200',
    }
    return colors[category?.toLowerCase()] || 'bg-slate-100 text-slate-700 ring-slate-200'
  }

  const getSeniorityBadgeColor = (level) => {
    const colors = {
      junior: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
      mid: 'bg-sky-50 text-sky-700 ring-sky-200',
      senior: 'bg-violet-50 text-violet-700 ring-violet-200',
      lead: 'bg-amber-50 text-amber-700 ring-amber-200',
      executive: 'bg-rose-50 text-rose-700 ring-rose-200',
    }
    return colors[level?.toLowerCase()] || 'bg-slate-50 text-slate-700 ring-slate-200'
  }

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.8) return 'text-green-600'
    if (confidence >= 0.6) return 'text-yellow-600'
    return 'text-orange-600'
  }

  const formatWeightLabel = (key) => {
    const labels = {
      core_competencies: 'Core Competencies',
      experience: 'Experience Level',
      domain_fit: 'Domain/Industry Fit',
      education: 'Education & Credentials',
      career_trajectory: 'Career Progression',
      role_excellence: 'Role Excellence',
      risk: 'Risk Assessment'
    }
    return labels[key] || key
  }

  return (
    <div className={`bg-gradient-to-br from-indigo-50 via-purple-50 to-pink-50 border border-indigo-200 rounded-2xl shadow-lg ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-indigo-200 bg-white/50 backdrop-blur-sm rounded-t-2xl">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-2 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-800">AI Weight Suggestions</h3>
              <p className="text-xs text-slate-500">Intelligent scoring based on job requirements</p>
            </div>
          </div>
          <button
            onClick={fetchSuggestion}
            disabled={loading || !jobDescription}
            className="px-4 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 text-white text-sm font-semibold rounded-lg hover:from-indigo-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md hover:shadow-lg flex items-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                Get AI Suggestion
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="p-4 bg-red-50 border-b border-red-200">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red-600 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-sm font-medium text-red-800">Failed to get suggestions</p>
              <p className="text-xs text-red-600 mt-1">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Suggestion Content */}
      {suggestion && (
        <div className="p-4 space-y-4">
          {/* Role Detection */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-medium text-slate-600">Detected:</span>
            <span className={`px-2.5 py-1 text-xs font-semibold rounded-lg ring-1 ${getRoleBadgeColor(suggestion.role_category)}`}>
              {suggestion.role_category?.toUpperCase() || 'UNKNOWN'} ROLE
            </span>
            {suggestion.seniority_level && suggestion.seniority_level !== 'unknown' && (
              <span className={`px-2.5 py-1 text-xs font-semibold rounded-lg ring-1 ${getSeniorityBadgeColor(suggestion.seniority_level)}`}>
                {suggestion.seniority_level?.toUpperCase()}
              </span>
            )}
            {suggestion.confidence && (
              <span className={`text-xs font-medium ${getConfidenceColor(suggestion.confidence)}`}>
                {Math.round(suggestion.confidence * 100)}% confidence
              </span>
            )}
          </div>

          {/* Reasoning */}
          {suggestion.reasoning && (
            <div className="p-3 bg-white/70 backdrop-blur-sm rounded-xl border border-indigo-100">
              <div className="flex items-start gap-2">
                <TrendingUp className="w-4 h-4 text-indigo-600 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-xs font-semibold text-slate-700 mb-1">AI Reasoning</p>
                  <p className="text-xs text-slate-600 leading-relaxed">{suggestion.reasoning}</p>
                </div>
              </div>
            </div>
          )}

          {/* Weights Visualization */}
          {suggestion.suggested_weights && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <button
                  onClick={() => setExpanded(!expanded)}
                  className="flex items-center gap-1 text-xs font-semibold text-slate-700 hover:text-indigo-600 transition-colors"
                >
                  Suggested Weights
                  {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                </button>
              </div>

              {expanded && (
                <div className="space-y-2.5">
                  {Object.entries(suggestion.suggested_weights)
                    .filter(([key]) => key !== 'risk')
                    .sort(([, a], [, b]) => b - a)
                    .map(([key, value]) => (
                      <div key={key} className="space-y-1">
                        <div className="flex justify-between items-center text-xs">
                          <span className="font-medium text-slate-700">
                            {key === 'role_excellence' && suggestion.role_excellence_label
                              ? suggestion.role_excellence_label
                              : formatWeightLabel(key)}
                          </span>
                          <span className="font-bold text-indigo-700">{Math.round(value * 100)}%</span>
                        </div>
                        <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-indigo-500 to-purple-600 rounded-full transition-all duration-500"
                            style={{ width: `${value * 100}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  
                  {/* Risk Penalty */}
                  {suggestion.suggested_weights.risk && (
                    <div className="space-y-1 pt-2 border-t border-indigo-100">
                      <div className="flex justify-between items-center text-xs">
                        <span className="font-medium text-slate-700">Risk Assessment (Penalty)</span>
                        <span className="font-bold text-red-600">{Math.round(Math.abs(suggestion.suggested_weights.risk) * 100)}%</span>
                      </div>
                      <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-red-500 to-orange-600 rounded-full transition-all duration-500"
                          style={{ width: `${Math.abs(suggestion.suggested_weights.risk) * 100}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-2 pt-2">
            <button
              onClick={handleAcceptWeights}
              className="flex-1 px-4 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 text-white text-sm font-semibold rounded-lg hover:from-indigo-700 hover:to-purple-700 transition-all shadow-md hover:shadow-lg flex items-center justify-center gap-2"
            >
              <Check className="w-4 h-4" />
              Use AI Weights
            </button>
            <button
              onClick={() => setSuggestion(null)}
              className="px-4 py-2.5 bg-white text-slate-700 text-sm font-medium rounded-lg hover:bg-slate-50 transition-all border border-slate-200 hover:border-slate-300"
            >
              Dismiss
            </button>
          </div>

          {/* Fallback Notice */}
          {suggestion.fallback && (
            <div className="p-2 bg-yellow-50 border border-yellow-200 rounded-lg">
              <p className="text-xs text-yellow-800">
                <AlertCircle className="w-3 h-3 inline mr-1" />
                Using default weights (AI unavailable)
              </p>
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {!suggestion && !error && !loading && (
        <div className="p-6 text-center">
          <div className="w-12 h-12 bg-gradient-to-br from-indigo-100 to-purple-100 rounded-full flex items-center justify-center mx-auto mb-3">
            <Sparkles className="w-6 h-6 text-indigo-600" />
          </div>
          <p className="text-sm font-medium text-slate-700 mb-1">No suggestions yet</p>
          <p className="text-xs text-slate-500">
            Click "Get AI Suggestion" to analyze the job description and get optimal weights
          </p>
        </div>
      )}
    </div>
  )
}
