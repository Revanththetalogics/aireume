import { Loader2, Sparkles } from 'lucide-react'

export function FitBadge({ score }) {
  if (score == null)
    return <span className="px-2.5 py-0.5 rounded-full text-xs font-bold ring-1 bg-slate-50 text-slate-500 ring-slate-200">—</span>
  let color = 'bg-red-50 text-red-700 ring-red-200'
  if (score >= 72) color = 'bg-green-50 text-green-700 ring-green-200'
  else if (score >= 45) color = 'bg-amber-50 text-amber-700 ring-amber-200'
  return <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ring-1 ${color}`}>{score}</span>
}

export function RecommendBadge({ rec }) {
  const styles = {
    Shortlist: 'bg-green-50 text-green-700 ring-green-200',
    Consider:  'bg-amber-50 text-amber-700 ring-amber-200',
    Reject:    'bg-red-50 text-red-700 ring-red-200',
    Pending:   'bg-slate-50 text-slate-600 ring-slate-200',
  }
  return <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ring-1 ${styles[rec] || 'bg-slate-50 text-slate-600 ring-slate-200'}`}>{rec || '—'}</span>
}

export function NarrativeStatusBadge({ result }) {
  const status = result?.narrative_status
  const isPending = status === 'pending' || status === 'processing' || result?.narrative_pending === true

  if (isPending) {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-brand-600 bg-brand-50 px-1.5 py-0.5 rounded-md ring-1 ring-brand-200">
        <Loader2 className="w-3 h-3 animate-spin" />
        AI…
      </span>
    )
  }

  if (status === 'ready' && result?.ai_enhanced) {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-green-700 bg-green-50 px-1.5 py-0.5 rounded-md ring-1 ring-green-200" title="AI-enhanced narrative">
        <Sparkles className="w-3 h-3" />
        AI
      </span>
    )
  }

  if (status === 'failed') {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded-md ring-1 ring-amber-200" title="Standard analysis (AI enhancement unavailable)">
        Std
      </span>
    )
  }

  return null
}
