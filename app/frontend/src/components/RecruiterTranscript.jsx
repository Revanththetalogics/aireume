import { useState } from 'react'
import { MessageSquare, Bot, User, Clock, ChevronDown, ChevronUp, CheckCircle2, XCircle } from 'lucide-react'

const CATEGORY_COLORS = {
  technical:      'bg-blue-100 text-blue-700',
  behavioral:     'bg-purple-100 text-purple-700',
  culture_fit:    'bg-amber-100 text-amber-700',
  experience:     'bg-emerald-100 text-emerald-700',
  problem_solving:'bg-indigo-100 text-indigo-700',
  general:        'bg-slate-100 text-slate-700',
}

function EvalBadge({ score }) {
  if (score == null) return null
  if (score >= 70) return (
    <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-xs font-semibold bg-emerald-100 text-emerald-700">
      <CheckCircle2 className="w-3 h-3" /> Pass
    </span>
  )
  if (score >= 40) return (
    <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-xs font-semibold bg-amber-100 text-amber-700">
      <Clock className="w-3 h-3" /> Partial
    </span>
  )
  return (
    <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-xs font-semibold bg-red-100 text-red-700">
      <XCircle className="w-3 h-3" /> Fail
    </span>
  )
}

export default function RecruiterTranscript({ transcript }) {
  const [expandedIdx, setExpandedIdx] = useState(null)

  // Guard against non-array data (e.g. backend returning an object)
  const items = Array.isArray(transcript) ? transcript : []

  if (items.length === 0) {
    return (
      <div className="text-center py-12 text-slate-400">
        <MessageSquare className="w-10 h-10 mx-auto mb-3 opacity-40" />
        <p className="text-sm">No transcript available</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {items.map((item, idx) => {
        const isExpanded = expandedIdx === idx
        const followUps = item.follow_ups || []
        const category = item.category || 'general'
        const catColor = CATEGORY_COLORS[category] || CATEGORY_COLORS.general

        return (
          <div
            key={item.id || idx}
            className="bg-white rounded-2xl ring-1 ring-slate-200 overflow-hidden"
          >
            {/* Question header */}
            <div
              className="px-5 py-4 cursor-pointer hover:bg-slate-50 transition-colors"
              onClick={() => setExpandedIdx(isExpanded ? null : idx)}
            >
              <div className="flex items-start gap-3">
                <div className="w-7 h-7 rounded-lg bg-brand-100 text-brand-600 flex items-center justify-center shrink-0 mt-0.5">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`px-2 py-0.5 rounded text-xs font-semibold ${catColor}`}>
                      {category.replace(/_/g, ' ')}
                    </span>
                    <EvalBadge score={item.evaluation_score} />
                    {item.duration_seconds != null && (
                      <span className="text-xs text-slate-400 flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {item.duration_seconds}s
                      </span>
                    )}
                  </div>
                  <p className="text-sm font-semibold text-slate-800">{item.question}</p>
                </div>
                <div className="shrink-0 text-slate-400">
                  {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </div>
              </div>
            </div>

            {/* Response (expanded) */}
            {isExpanded && (
              <div className="px-5 pb-4 border-t border-slate-100">
                <div className="flex items-start gap-3 mt-4">
                  <div className="w-7 h-7 rounded-lg bg-slate-100 text-slate-600 flex items-center justify-center shrink-0 mt-0.5">
                    <User className="w-4 h-4" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm text-slate-700 leading-relaxed">{item.response || 'No response recorded'}</p>
                    {item.evaluation_notes && (
                      <div className="mt-3 p-3 bg-slate-50 rounded-xl">
                        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Evaluation</p>
                        <p className="text-xs text-slate-600">{item.evaluation_notes}</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Follow-up questions */}
                {followUps.length > 0 && (
                  <div className="mt-4 ml-10 space-y-2">
                    <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Follow-ups</p>
                    {followUps.map((fu, fIdx) => (
                      <div key={fIdx} className="pl-3 border-l-2 border-brand-100">
                        <p className="text-xs font-semibold text-brand-600 mb-1">{fu.question}</p>
                        <p className="text-xs text-slate-600">{fu.response}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
