import {
  Loader2, CheckCircle2, AlertCircle, Hourglass, FileCheck, XCircle,
} from 'lucide-react'
import { Card, Button } from '../ui'
import {
  formatBatchProgressTitle,
  formatBatchProgressSubtitle,
  getBatchProgressPercent,
  getEffectiveBatchTotal,
  estimateBatchEtaMs,
} from '../../lib/analyzeBatchUtils'

function FileStatusCard({ fs }) {
  const isQueued = fs.status === 'queued'
  const isProcessing = fs.status === 'processing'
  const isCompleted = fs.status === 'completed'
  const isFailed = fs.status === 'failed'

  return (
    <div
      className={`flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-xs font-medium transition-all duration-300 ${
        isQueued ? 'bg-slate-100 text-slate-500 ring-1 ring-slate-200' :
        isProcessing ? 'bg-brand-50 text-brand-800 ring-1 ring-brand-200 shadow-sm' :
        isCompleted ? 'bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200' :
        'bg-red-50 text-red-700 ring-1 ring-red-200'
      }`}
    >
      <div className="shrink-0">
        {isQueued && <Hourglass className="w-4 h-4" />}
        {isProcessing && <Loader2 className="w-4 h-4 animate-spin" />}
        {isCompleted && <FileCheck className="w-4 h-4 text-emerald-600" />}
        {isFailed && <XCircle className="w-4 h-4 text-red-600" />}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate">{fs.filename}</p>
        {isCompleted && fs.result?.fit_score != null && (
          <p className="text-[10px] opacity-80">
            Score: <span className="font-bold">{fs.result.fit_score}</span>
            {' · '}
            {fs.result.final_recommendation || '—'}
          </p>
        )}
        {isFailed && fs.error && (
          <p className="text-[10px] opacity-80 truncate">{fs.error}</p>
        )}
      </div>
    </div>
  )
}

/**
 * Batch analysis progress — design-system card with progress bar and per-file status.
 */
export default function BatchAnalysisProgress({
  analysisDone,
  analysisProgress,
  batchStartTime,
  fileStatuses = [],
  successfulCount = 0,
  failedCount = 0,
  preparing = false,
  stuck = false,
  stuckMessage,
  onRetry,
  className = '',
}) {
  const completed = analysisProgress?.completed || 0
  const total = getEffectiveBatchTotal(analysisProgress, fileStatuses)
  const percent = getBatchProgressPercent(completed, total)
  const etaMs = estimateBatchEtaMs(batchStartTime, completed, total)

  const title = formatBatchProgressTitle({
    analysisDone,
    completed,
    total,
    successful: successfulCount,
    failed: failedCount,
    preparing,
    stuck,
  })

  const subtitle = stuck
    ? (stuckMessage || 'The batch did not receive a response. Check your connection and try again.')
    : formatBatchProgressSubtitle({
        analysisDone,
        completed,
        total,
        etaMs,
        successful: successfulCount,
      })

  return (
    <Card className={`p-5 ring-brand-100 bg-brand-50/40 space-y-4 ${className}`} role="status" aria-live="polite">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-sm font-bold text-brand-900">{title}</h3>
          <p className="text-xs text-slate-600 mt-0.5">{subtitle}</p>
        </div>
        {stuck ? (
          <AlertCircle className="w-5 h-5 text-amber-500 shrink-0" />
        ) : analysisDone ? (
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
        ) : (
          <Loader2 className="w-5 h-5 text-brand-600 animate-spin shrink-0" />
        )}
      </div>

      {!analysisDone && !stuck && total > 0 && (
        <div className="space-y-1.5">
          <div className="w-full bg-brand-100 rounded-full h-2 overflow-hidden">
            <div
              className="bg-brand-600 h-full transition-all duration-500 ease-out"
              style={{ width: `${percent}%` }}
            />
          </div>
          <p className="text-[10px] font-semibold text-brand-700 uppercase tracking-wide">{percent}% complete</p>
        </div>
      )}

      {stuck && onRetry && (
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="brand" onClick={onRetry}>
            Retry analysis
          </Button>
        </div>
      )}

      {fileStatuses.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
          {fileStatuses.map((fs) => (
            <FileStatusCard key={fs.filename} fs={fs} />
          ))}
        </div>
      )}
    </Card>
  )
}
