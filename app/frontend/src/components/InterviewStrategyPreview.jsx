import { Brain, HelpCircle } from 'lucide-react'

const CATEGORY_COLORS = {
  technical:       'bg-blue-50 border-blue-200 text-blue-700',
  behavioral:      'bg-purple-50 border-purple-200 text-purple-700',
  communication:   'bg-green-50 border-green-200 text-green-700',
  cultural_fit:    'bg-amber-50 border-amber-200 text-amber-700',
  risk_validation: 'bg-red-50 border-red-200 text-red-700',
  gap_probe:       'bg-orange-50 border-orange-200 text-orange-700',
  motivation:      'bg-emerald-50 border-emerald-200 text-emerald-700',
}

const CATEGORY_LABELS = {
  technical:       'Technical',
  behavioral:      'Behavioral',
  communication:   'Communication',
  cultural_fit:    'Cultural Fit',
  risk_validation: 'Risk Validation',
  gap_probe:       'Gap Probe',
  motivation:      'Motivation',
}

// Stable display order for known categories; unknown ones append at the end.
const CATEGORY_ORDER = [
  'technical', 'behavioral', 'communication', 'cultural_fit',
  'risk_validation', 'gap_probe', 'motivation',
]

export default function InterviewStrategyPreview({ questions }) {
  if (!questions || !Array.isArray(questions) || questions.length === 0) {
    return (
      <div className="text-center py-16 text-slate-400">
        <Brain className="w-12 h-12 mx-auto mb-4 opacity-40" />
        <p className="text-sm">No interview strategy available</p>
      </div>
    )
  }

  // Group questions by category while preserving first-seen order.
  const grouped = {}
  const order = []
  for (const q of questions) {
    const cat = q.category || 'technical'
    if (!grouped[cat]) {
      grouped[cat] = []
      order.push(cat)
    }
    grouped[cat].push(q)
  }

  // Sort categories by the defined order, unknown categories go last.
  const sortedCats = [...order].sort((a, b) => {
    const ia = CATEGORY_ORDER.indexOf(a)
    const ib = CATEGORY_ORDER.indexOf(b)
    if (ia === -1 && ib === -1) return 0
    if (ia === -1) return 1
    if (ib === -1) return -1
    return ia - ib
  })

  return (
    <div className="space-y-5">
      {sortedCats.map(cat => {
        const color = CATEGORY_COLORS[cat] || 'bg-slate-50 border-slate-200 text-slate-700'
        const label = CATEGORY_LABELS[cat] || cat.replace(/_/g, ' ')
        const items = grouped[cat]

        return (
          <div key={cat} className="bg-white rounded-2xl ring-1 ring-slate-200 p-5">
            <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${color} mb-4`}>
              <HelpCircle className="w-3.5 h-3.5" />
              {label}
              <span className="ml-0.5 px-1.5 py-0.5 rounded-full bg-white/70 text-[10px] font-bold">
                {items.length}
              </span>
            </div>

            <div className="space-y-3">
              {items.map((q, i) => {
                const seq = q.sequence_number ?? i + 1
                return (
                  <div key={`${cat}-${seq}-${i}`} className="flex items-start gap-3 p-3 bg-slate-50/60 rounded-xl">
                    <span className="shrink-0 w-7 h-7 rounded-lg bg-brand-100 text-brand-700 flex items-center justify-center text-xs font-bold">
                      Q{seq}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-800 leading-relaxed">
                        {q.question_text || q.spoken_text || '—'}
                      </p>
                      {q.intent && (
                        <p className="text-xs text-brand-700/80 mt-1">
                          Intent: {q.intent}
                        </p>
                      )}
                      {q.question_context && (
                        <p className="text-xs text-slate-500 italic mt-1.5">Listen for: {q.question_context}</p>
                      )}
                      {Array.isArray(q.what_to_listen_for) && q.what_to_listen_for.length > 0 && (
                        <ul className="text-xs text-slate-500 mt-1.5 list-disc list-inside space-y-0.5">
                          {q.what_to_listen_for.map((item, j) => (
                            <li key={j}>{item}</li>
                          ))}
                        </ul>
                      )}
                      {Array.isArray(q.follow_up_intents) && q.follow_up_intents[0] && (
                        <p className="text-xs text-amber-700/90 mt-1.5">
                          If vague: {q.follow_up_intents[0]}
                        </p>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )
      })}
    </div>
  )
}
