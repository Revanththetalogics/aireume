/** Helpers for batch analysis progress copy and step state on AnalyzePage. */

export const ANALYZE_STEPS = [
  { num: 1, label: 'JD & Skills', shortLabel: 'JD' },
  { num: 2, label: 'Upload', shortLabel: 'Upload' },
  { num: 3, label: 'Results', shortLabel: 'Results' },
]

export function getEffectiveBatchTotal(analysisProgress, fileStatuses) {
  const total = analysisProgress?.total || 0
  if (total > 0) return total
  return fileStatuses?.length || 0
}

export function getBatchProgressPercent(completed, total) {
  if (!total || total <= 0) return 0
  return Math.min(100, Math.round((completed / total) * 100))
}

export function formatBatchProgressTitle({
  analysisDone,
  completed,
  total,
  successful,
  failed,
  preparing,
  stuck,
}) {
  if (stuck) return 'Analysis did not start'
  if (preparing) return 'Preparing batch…'
  if (analysisDone) {
    const failedSuffix = failed > 0 ? `, ${failed} failed` : ''
    if (successful === 0) return `No resumes were scored${failedSuffix}`
    return `Analysis complete — ${successful} scored${failedSuffix}`
  }
  if (total <= 0) return 'Starting analysis…'
  if (completed >= total) return `Finishing up — ${completed} of ${total} processed`
  const next = Math.min(completed + 1, total)
  return `Scoring resume ${next} of ${total}`
}

export function formatBatchProgressSubtitle({
  analysisDone,
  completed,
  total,
  etaMs,
  successful,
}) {
  if (analysisDone) {
    if (successful === 0) return 'Review failed files below or start a new batch.'
    return `${successful} candidate${successful !== 1 ? 's' : ''} ranked by fit score.`
  }
  if (total <= 0) return 'Connecting to the analysis service…'
  if (completed === 0) return `First result usually arrives within ~30s · ${total} in queue`
  if (etaMs != null && etaMs > 0) {
    if (etaMs < 5000) return 'Almost done…'
    if (etaMs < 60000) return `~${Math.ceil(etaMs / 1000)}s remaining · ${completed} of ${total} complete`
    return `~${Math.ceil(etaMs / 60000)} min remaining · ${completed} of ${total} complete`
  }
  return `${completed} of ${total} complete`
}

export function estimateBatchEtaMs(batchStartTime, completed, total) {
  if (!batchStartTime || completed <= 0 || total <= 0) return null
  const elapsed = Date.now() - batchStartTime
  const avgPerFile = elapsed / completed
  const remaining = total - completed
  return avgPerFile * remaining
}

export function buildSetupSummary({
  roleCategory,
  jdParseResult,
  skillOverrides,
  fileCount,
  jdMode,
  jdFile,
}) {
  const roleTitle =
    jdParseResult?.role_title ||
    jdParseResult?.title ||
    (roleCategory && roleCategory !== 'general' ? roleCategory : null)

  const requiredCount =
    skillOverrides?.required_skills?.length ??
    jdParseResult?.required_skills?.length ??
    jdParseResult?.skills?.required?.length ??
    0

  const sourceLabel =
    jdMode === 'file' && jdFile?.name
      ? jdFile.name
      : jdMode === 'text'
        ? 'Pasted job description'
        : 'Job description'

  return {
    roleTitle: roleTitle || 'Role',
    requiredCount,
    fileCount,
    sourceLabel,
  }
}

export function getActiveAnalyzeStep(showResults, currentStep) {
  return showResults ? 3 : currentStep
}

export function isAnalyzeStepComplete(stepNum, { isStep1Complete, isStep2Complete, showResults, analysisDone }) {
  if (stepNum === 1) return isStep1Complete
  if (stepNum === 2) return isStep2Complete || showResults
  if (stepNum === 3) return analysisDone
  return false
}

export function canNavigateToAnalyzeStep(stepNum, { isAnalyzing, showResults }) {
  if (isAnalyzing) return stepNum === 3
  if (stepNum === 3) return showResults
  return true
}
