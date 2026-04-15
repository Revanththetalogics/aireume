import { useState, useEffect } from 'react'
import { X, Sparkles, Play, AlertCircle, Loader2 } from 'lucide-react'
import UniversalWeightsPanel from './UniversalWeightsPanel'
import WeightSuggestionPanel from './WeightSuggestionPanel'

export default function ReanalyzeModal({ 
  isOpen, 
  onClose, 
  candidate,
  jobDescription,
  currentWeights,
  onReanalyze,
  isLoading = false 
}) {
  const [weights, setWeights] = useState(currentWeights || {
    core_competencies: 0.30,
    experience: 0.20,
    domain_fit: 0.20,
    education: 0.10,
    career_trajectory: 0.10,
    role_excellence: 0.10,
    risk: -0.10,
  })
  const [showAiSuggestion, setShowAiSuggestion] = useState(false)
  const [weightMetadata, setWeightMetadata] = useState(null)

  useEffect(() => {
    if (currentWeights) {
      setWeights(currentWeights)
    }
  }, [currentWeights])

  const handleReanalyze = () => {
    if (onReanalyze) {
      onReanalyze(weights, weightMetadata)
    }
  }

  const handleWeightsAccepted = (suggestedWeights, metadata) => {
    setWeights(suggestedWeights)
    setWeightMetadata(metadata)
    setShowAiSuggestion(false)
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-slate-200 bg-gradient-to-r from-indigo-50 to-purple-50">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-xl font-bold text-slate-800 mb-1">
                Re-analyze with Different Weights
              </h2>
              <p className="text-sm text-slate-600">
                Try different scoring weights to see how they affect the candidate's score
              </p>
              {candidate && (
                <p className="text-xs text-slate-500 mt-2">
                  Candidate: <span className="font-semibold">{candidate.name || 'Unknown'}</span>
                </p>
              )}
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
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* AI Suggestion Toggle */}
          {jobDescription && (
            <div>
              <button
                onClick={() => setShowAiSuggestion(!showAiSuggestion)}
                className="flex items-center gap-2 text-sm font-semibold text-indigo-600 hover:text-indigo-700 transition-colors mb-3"
              >
                <Sparkles className="w-4 h-4" />
                {showAiSuggestion ? 'Hide' : 'Show'} AI Weight Suggestions
              </button>

              {showAiSuggestion && (
                <WeightSuggestionPanel
                  jobDescription={jobDescription}
                  currentWeights={weights}
                  onWeightsAccepted={(suggestedWeights) => {
                    setWeights(suggestedWeights)
                    setShowAiSuggestion(false)
                  }}
                />
              )}
            </div>
          )}

          {/* Weight Controls */}
          <div>
            <h3 className="text-sm font-semibold text-slate-700 mb-3">
              Adjust Scoring Weights
            </h3>
            <UniversalWeightsPanel
              weights={weights}
              onChange={setWeights}
              roleCategory={weightMetadata?.role_category}
              roleExcellenceLabel={weightMetadata?.role_excellence_label}
            />
          </div>

          {/* Info Notice */}
          <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm font-semibold text-blue-800 mb-1">
                  Version Management
                </p>
                <p className="text-xs text-blue-700 leading-relaxed">
                  Re-analyzing will create a new version of the analysis. The current version 
                  will be archived, allowing you to compare different weight scenarios and 
                  restore previous versions if needed.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-slate-200 bg-slate-50">
          <div className="flex items-center justify-between gap-4">
            <button
              onClick={onClose}
              disabled={isLoading}
              className="px-6 py-2.5 text-sm font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cancel
            </button>
            <button
              onClick={handleReanalyze}
              disabled={isLoading}
              className="px-6 py-2.5 text-sm font-semibold text-white bg-gradient-to-r from-indigo-600 to-purple-600 rounded-lg hover:from-indigo-700 hover:to-purple-700 transition-all shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Re-analyzing...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  Re-analyze with New Weights
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
