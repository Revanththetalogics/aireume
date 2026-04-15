import { useState } from 'react'
import { History, TrendingUp, TrendingDown, Minus, Eye, RotateCcw, Trash2, GitCompare, CheckCircle, Circle } from 'lucide-react'

export default function VersionHistory({ 
  candidateId, 
  versions = [], 
  onVersionSelect,
  onVersionRestore,
  onVersionDelete,
  onCompare,
  className = '' 
}) {
  const [selectedVersions, setSelectedVersions] = useState([])

  const handleVersionClick = (version) => {
    if (onVersionSelect) {
      onVersionSelect(version)
    }
  }

  const handleCompareToggle = (versionId) => {
    setSelectedVersions(prev => {
      if (prev.includes(versionId)) {
        return prev.filter(id => id !== versionId)
      } else if (prev.length < 2) {
        return [...prev, versionId]
      }
      return prev
    })
  }

  const handleCompare = () => {
    if (selectedVersions.length === 2 && onCompare) {
      const v1 = versions.find(v => v.id === selectedVersions[0])
      const v2 = versions.find(v => v.id === selectedVersions[1])
      onCompare(v1, v2)
    }
  }

  const getScoreDiff = (current, previous) => {
    if (!previous) return null
    const diff = current - previous
    if (Math.abs(diff) < 1) return null
    return diff
  }

  const formatDate = (dateString) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now - date
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
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

  if (!versions || versions.length === 0) {
    return (
      <div className={`bg-white border border-slate-200 rounded-2xl p-6 ${className}`}>
        <div className="text-center">
          <History className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <p className="text-sm font-medium text-slate-600">No version history</p>
          <p className="text-xs text-slate-500 mt-1">
            Re-analyze with different weights to create versions
          </p>
        </div>
      </div>
    )
  }

  const activeVersion = versions.find(v => v.is_active)
  const sortedVersions = [...versions].sort((a, b) => b.version_number - a.version_number)

  return (
    <div className={`bg-white border border-slate-200 rounded-2xl shadow-sm ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-slate-200 bg-slate-50 rounded-t-2xl">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <History className="w-4 h-4 text-slate-600" />
            <h3 className="text-sm font-bold text-slate-800">Version History</h3>
            <span className="px-2 py-0.5 bg-slate-200 text-slate-700 text-xs font-semibold rounded">
              {versions.length} {versions.length === 1 ? 'version' : 'versions'}
            </span>
          </div>
          {selectedVersions.length === 2 && (
            <button
              onClick={handleCompare}
              className="px-3 py-1.5 bg-indigo-600 text-white text-xs font-semibold rounded-lg hover:bg-indigo-700 transition-all flex items-center gap-1.5"
            >
              <GitCompare className="w-3.5 h-3.5" />
              Compare Selected
            </button>
          )}
        </div>
      </div>

      {/* Version List */}
      <div className="divide-y divide-slate-100">
        {sortedVersions.map((version, index) => {
          const previousVersion = sortedVersions[index + 1]
          const scoreDiff = getScoreDiff(
            version.analysis_result?.fit_score,
            previousVersion?.analysis_result?.fit_score
          )
          const isSelected = selectedVersions.includes(version.id)

          return (
            <div
              key={version.id}
              className={`p-4 hover:bg-slate-50 transition-colors ${
                version.is_active ? 'bg-indigo-50/50' : ''
              }`}
            >
              <div className="flex items-start gap-3">
                {/* Compare Checkbox */}
                <button
                  onClick={() => handleCompareToggle(version.id)}
                  className={`mt-1 p-1 rounded transition-colors ${
                    isSelected 
                      ? 'text-indigo-600 bg-indigo-100' 
                      : 'text-slate-400 hover:text-indigo-600 hover:bg-indigo-50'
                  }`}
                  title="Select for comparison"
                >
                  {isSelected ? (
                    <CheckCircle className="w-4 h-4" />
                  ) : (
                    <Circle className="w-4 h-4" />
                  )}
                </button>

                {/* Version Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-2">
                    <span className="text-sm font-bold text-slate-800">
                      Version {version.version_number}
                    </span>
                    {version.is_active && (
                      <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-semibold rounded">
                        ACTIVE
                      </span>
                    )}
                    {version.role_category && (
                      <span className={`px-2 py-0.5 text-xs font-semibold rounded ${getRoleBadgeColor(version.role_category)}`}>
                        {version.role_category.toUpperCase()}
                      </span>
                    )}
                    <span className="text-xs text-slate-500">
                      {formatDate(version.created_at)}
                    </span>
                  </div>

                  {/* Score */}
                  <div className="flex items-center gap-3 mb-2">
                    <div className="flex items-baseline gap-1">
                      <span className="text-2xl font-bold text-slate-800">
                        {version.analysis_result?.fit_score || 0}
                      </span>
                      <span className="text-xs text-slate-500">/ 100</span>
                    </div>
                    {scoreDiff !== null && (
                      <div className={`flex items-center gap-1 text-xs font-semibold ${
                        scoreDiff > 0 ? 'text-green-600' : scoreDiff < 0 ? 'text-red-600' : 'text-slate-500'
                      }`}>
                        {scoreDiff > 0 ? (
                          <TrendingUp className="w-3.5 h-3.5" />
                        ) : scoreDiff < 0 ? (
                          <TrendingDown className="w-3.5 h-3.5" />
                        ) : (
                          <Minus className="w-3.5 h-3.5" />
                        )}
                        {scoreDiff > 0 ? '+' : ''}{scoreDiff}
                      </div>
                    )}
                  </div>

                  {/* Weight Reasoning */}
                  {version.weight_reasoning && (
                    <p className="text-xs text-slate-600 mb-2 line-clamp-2">
                      {version.weight_reasoning}
                    </p>
                  )}

                  {/* Recommendation */}
                  {version.analysis_result?.final_recommendation && (
                    <span className={`inline-block px-2 py-0.5 text-xs font-semibold rounded ${
                      version.analysis_result.final_recommendation === 'Shortlist'
                        ? 'bg-green-100 text-green-700'
                        : version.analysis_result.final_recommendation === 'Consider'
                        ? 'bg-yellow-100 text-yellow-700'
                        : 'bg-red-100 text-red-700'
                    }`}>
                      {version.analysis_result.final_recommendation}
                    </span>
                  )}
                </div>

                {/* Actions */}
                <div className="flex flex-col gap-1">
                  <button
                    onClick={() => handleVersionClick(version)}
                    className="p-1.5 text-slate-600 hover:text-indigo-600 hover:bg-indigo-50 rounded transition-all"
                    title="View details"
                  >
                    <Eye className="w-4 h-4" />
                  </button>
                  {!version.is_active && onVersionRestore && (
                    <button
                      onClick={() => onVersionRestore(version)}
                      className="p-1.5 text-slate-600 hover:text-green-600 hover:bg-green-50 rounded transition-all"
                      title="Restore this version"
                    >
                      <RotateCcw className="w-4 h-4" />
                    </button>
                  )}
                  {!version.is_active && onVersionDelete && (
                    <button
                      onClick={() => onVersionDelete(version)}
                      className="p-1.5 text-slate-600 hover:text-red-600 hover:bg-red-50 rounded transition-all"
                      title="Delete this version"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Comparison Hint */}
      {selectedVersions.length === 1 && (
        <div className="p-3 bg-indigo-50 border-t border-indigo-100">
          <p className="text-xs text-indigo-700">
            Select one more version to compare side-by-side
          </p>
        </div>
      )}
    </div>
  )
}
