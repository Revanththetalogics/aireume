import { AlertCircle, ArrowLeft, Eye, FileText, Loader2, Trophy } from 'lucide-react'
import { AnalysisSetupSummary, BatchAnalysisProgress } from '../patterns'
import EmptyState from '../EmptyState'
import { Button, Card } from '../ui'
import { FitBadge, RecommendBadge, EnrichmentStatusBadges } from '../Badges'

export default function AnalyzeResultsPanel(props) {
  const {
    setupSummary,
    jdMode,
    jdText,
    setupSummaryExpanded,
    setSetupSummaryExpanded,
    handleNewBatch,
    analysisDone,
    topCandidate,
    streamingResults,
    streamingFailed,
    analysisProgress,
    navigate,
    isAnalyzing,
    fileStatuses,
    batchStartTime,
    batchPreparing,
    batchStuckError,
    handleRetryBatch,
    streamingResultsRef,
    streamingFailedRef,
    skillOverrides,
    skillsConfirmed,
    jdParseResult,
    weights,
    roleCategory,
  } = props

  return (
        <div className="space-y-5 card-animate">
          <AnalysisSetupSummary
            roleTitle={setupSummary.roleTitle}
            requiredCount={setupSummary.requiredCount}
            fileCount={setupSummary.fileCount}
            sourceLabel={setupSummary.sourceLabel}
            jdText={jdMode === 'text' ? jdText : ''}
            expanded={setupSummaryExpanded}
            onToggle={() => setSetupSummaryExpanded((v) => !v)}
          />

          {/* Results toolbar */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <Button variant="secondary" size="sm" onClick={handleNewBatch}>
                <ArrowLeft className="w-4 h-4" />
                New batch
              </Button>
            </div>
            {analysisDone && topCandidate && (
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  size="sm"
                  onClick={() => {
                    const id = topCandidate.screeningResultId
                    const r = topCandidate.result
                    if (!id) return
                    try {
                      sessionStorage.setItem('aria_batch_results', JSON.stringify({
                        results: streamingResults,
                        failed: streamingFailed,
                        progress: analysisProgress,
                        timestamp: Date.now(),
                      }))
                    } catch {}
                    navigate(`/report?id=${id}&from=analyze`, { state: { from: '/analyze', result: r } })
                  }}
                >
                  <Trophy className="w-4 h-4" />
                  View top candidate
                </Button>
                <Button variant="secondary" size="sm" onClick={() => navigate('/candidates')}>
                  <Eye className="w-4 h-4" />
                  All candidates
                </Button>
              </div>
            )}
          </div>

          {/* Analysis Progress */}
          {(isAnalyzing || analysisDone || fileStatuses.length > 0 || batchStuckError) && (
            <BatchAnalysisProgress
              analysisDone={analysisDone}
              analysisProgress={analysisProgress}
              batchStartTime={batchStartTime}
              fileStatuses={fileStatuses}
              successfulCount={streamingResults.length}
              failedCount={streamingFailed.length}
              preparing={batchPreparing}
              stuck={Boolean(batchStuckError)}
              stuckMessage={batchStuckError}
              onRetry={handleRetryBatch}
            />
          )}

          {/* Waiting for first result */}
          {!analysisDone && streamingResults.length === 0 && !batchStuckError && (
            <Card className="p-8">
              <div className="flex flex-col items-center text-center py-4">
                <Loader2 className="w-10 h-10 text-brand-600 animate-spin mb-4" />
                <h3 className="text-lg font-bold text-brand-900 mb-1">Waiting for first result</h3>
                <p className="text-sm text-slate-500 max-w-sm">
                  {analysisProgress.total > 0
                    ? `Scoring ${analysisProgress.total} resume${analysisProgress.total !== 1 ? 's' : ''}. Results will appear here as each completes.`
                    : 'Connecting to the analysis service…'}
                </p>
              </div>
            </Card>
          )}

          {/* Results header + table */}
          {streamingResults.length > 0 && (
            <>
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div>
                  <h3 className="text-xl font-extrabold text-brand-900 tracking-tight">Ranked Shortlist</h3>
                  <p className="text-sm text-slate-500 font-medium">
                    {streamingResults.length} scored
                    {!analysisDone && analysisProgress.total > streamingResults.length
                      ? ` · ${analysisProgress.total - streamingResults.length} still processing`
                      : ''}
                    {streamingFailed.length ? ` · ${streamingFailed.length} failed` : ''}
                  </p>
                </div>
              </div>
            <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-brand-50 border-b border-brand-100">
                  <tr>
                    <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Rank</th>
                    <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">File</th>
                    <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Score</th>
                    <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Recommendation</th>
                    <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Risk</th>
                    <th className="px-4 py-3.5 text-left text-xs font-bold text-brand-700 uppercase tracking-wide">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {streamingResults.map((item, idx) => {
                    const r   = item.result
                    const id  = item.screeningResultId
                    const rank = idx + 1
                    return (
                      <tr key={id || idx} className="border-b border-brand-50 hover:bg-brand-50/40 transition-all duration-300">
                        <td className="px-4 py-3.5">
                          <div className="flex items-center gap-1.5">
                            {rank === 1 && <Trophy className="w-4 h-4 text-amber-500" />}
                            <span className="font-extrabold text-brand-900">#{rank}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3.5 text-brand-900 font-medium max-w-[200px] truncate">{item.filename}</td>
                        <td className="px-4 py-3.5"><FitBadge score={r?.fit_score} /></td>
                        <td className="px-4 py-3.5"><RecommendBadge rec={r?.final_recommendation} /></td>
                        <td className="px-4 py-3.5">
                          <span className={`text-xs font-bold ${
                            !r?.risk_level       ? 'text-slate-400' :
                            r.risk_level === 'Low'  ? 'text-green-700' :
                            r.risk_level === 'High' ? 'text-red-700'   : 'text-amber-700'
                          }`}>{r?.risk_level || '—'}</span>
                        </td>
                        <td className="px-4 py-3.5">
                          <div className="flex items-center gap-2">
                            <EnrichmentStatusBadges result={r} />
                            <button
                              onClick={() => {
                                // Persist batch results before navigating to report
                                try {
                                  sessionStorage.setItem('aria_batch_results', JSON.stringify({
                                    results: streamingResultsRef.current,
                                    failed: streamingFailedRef.current,
                                    progress: analysisProgress,
                                    timestamp: Date.now()
                                  }))
                                  // Also persist batch context for back-navigation
                                  sessionStorage.setItem('aria_batch_context', JSON.stringify({
                                    jdText,
                                    skillOverrides,
                                    skillsConfirmed,
                                    jdParseResult,
                                    jdMode,
                                    weights,
                                    roleCategory,
                                    fileNames: streamingResults.map(r => r.filename),
                                    timestamp: Date.now()
                                  }))
                                } catch {}
                                navigate(`/report?id=${id}&from=analyze`, { state: { from: '/analyze', result: r } })
                              }}
                              className="flex items-center gap-1 text-xs text-brand-600 hover:text-brand-700 font-bold hover:underline"
                            >
                              <Eye className="w-3.5 h-3.5" />
                              View Report
                            </button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            </>
          )}

          {/* All failed / zero scored */}
          {analysisDone && streamingResults.length === 0 && !batchStuckError && (
            <Card className="p-8">
              <EmptyState
                icon={AlertCircle}
                title="No resumes were scored"
                description={
                  streamingFailed.length > 0
                    ? `${streamingFailed.length} file${streamingFailed.length !== 1 ? 's' : ''} could not be processed. Review errors below or upload again.`
                    : 'The batch finished without any successful results. Try uploading again or check your job description.'
                }
                actionLabel="Start new batch"
                onAction={handleNewBatch}
              />
            </Card>
          )}

          {/* Failed Resumes Section */}
          {streamingFailed.length > 0 && (
            <div className="bg-red-50/80 backdrop-blur-md rounded-3xl ring-1 ring-red-200 shadow-sm overflow-hidden">
              <div className="px-5 py-4 border-b border-red-200 bg-red-100/50">
                <div className="flex items-center gap-2.5">
                  <AlertCircle className="w-5 h-5 text-red-600" />
                  <h4 className="text-base font-bold text-red-800">
                    Failed Resumes ({streamingFailed.length})
                  </h4>
                </div>
                <p className="text-sm text-red-600 mt-1 ml-8">
                  The following resumes could not be processed:
                </p>
              </div>
              <div className="divide-y divide-red-100">
                {streamingFailed.map((item, idx) => (
                  <div key={idx} className="px-5 py-3.5 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-xl bg-red-100 flex items-center justify-center shrink-0">
                        <FileText className="w-4 h-4 text-red-600" />
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-red-900">{item.filename}</p>
                        <p className="text-xs text-red-600 mt-0.5">{item.error || 'Unknown error'}</p>
                      </div>
                    </div>
                    <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-red-100 text-red-700 ring-1 ring-red-200">
                      Failed
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

  )
}
