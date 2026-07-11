import { CheckCircle2, Circle, Loader2, AlertTriangle, MinusCircle } from 'lucide-react'
import { ENRICHMENT_PHASES, getEnrichmentPhaseStatus } from '../../lib/enrichmentUtils'

const STREAM_STAGES = [
  { key: 'parsing', label: 'Parsing resume' },
  { key: 'scoring', label: 'Scoring fit' },
  { key: 'complete', label: 'Opening report' },
]

function StageIcon({ state }) {
  if (state === 'complete') return <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
  if (state === 'active') return <Loader2 className="w-4 h-4 text-brand-600 animate-spin shrink-0" />
  if (state === 'fallback') return <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0" />
  if (state === 'skipped') return <MinusCircle className="w-4 h-4 text-slate-400 shrink-0" />
  return <Circle className="w-4 h-4 text-slate-300 shrink-0" />
}

/**
 * Stream-mode tracker for live SSE analysis (single file).
 */
export function StreamStageTracker({ activeStage, className = '' }) {
  const order = ['parsing', 'scoring', 'complete']
  const activeIdx = order.indexOf(activeStage)

  return (
    <div
      className={`rounded-2xl ring-1 ring-brand-100 bg-brand-50/60 p-4 ${className}`}
      role="status"
      aria-live="polite"
    >
      <p className="text-xs font-bold uppercase tracking-wide text-brand-700 mb-3">Analysis progress</p>
      <ol className="space-y-2">
        {STREAM_STAGES.map((stage, idx) => {
          let state = 'pending'
          if (idx < activeIdx) state = 'complete'
          else if (idx === activeIdx) state = 'active'
          return (
            <li key={stage.key} className="flex items-center gap-2.5 text-sm">
              <StageIcon state={state} />
              <span className={state === 'active' ? 'font-semibold text-brand-900' : 'text-slate-600'}>
                {stage.label}
                {state === 'active' && '…'}
              </span>
            </li>
          )
        })}
      </ol>
    </div>
  )
}

/**
 * Enrichment tracker for background narrative / kit / voice phases.
 */
export default function AnalysisStageTracker({ result, showStreamPhases = false, activeStreamStage, className = '' }) {
  if (showStreamPhases) {
    return <StreamStageTracker activeStage={activeStreamStage} className={className} />
  }

  const phases = getEnrichmentPhaseStatus(result || {})
  const items = ENRICHMENT_PHASES.filter((p) => p.key !== 'parsing' && p.key !== 'scoring')

  return (
    <div
      className={`rounded-2xl ring-1 ring-brand-100 bg-white/90 backdrop-blur-md p-4 ${className}`}
      role="status"
      aria-live="polite"
    >
      <p className="text-xs font-bold uppercase tracking-wide text-brand-700 mb-3">AI enrichment</p>
      <ol className="space-y-2">
        {items.map((item) => {
          const state = phases[item.key] || 'waiting'
          return (
            <li key={item.key} className="flex items-center gap-2.5 text-sm">
              <StageIcon state={state === 'waiting' ? 'pending' : state} />
              <span className={state === 'active' ? 'font-semibold text-brand-900' : 'text-slate-600'}>
                {item.label}
                {state === 'active' && '…'}
                {state === 'fallback' && ' (template)'}
                {state === 'skipped' && ' (n/a)'}
              </span>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
