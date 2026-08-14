import { AlertCircle, Clock, Sparkles } from 'lucide-react'
import { ANALYZE } from '../lib/uxLabels'
import FeatureGuideModal from '../components/onboarding/FeatureGuideModal'
import { PageHeader } from '../components/patterns'
import { Badge } from '../components/ui'
import { JdFullModal } from '../components/analyze/AnalyzeRequisitionStep'
import AnalyzeProgressSteps from '../components/analyze/AnalyzeProgressSteps'
import AnalyzeJdStep from '../components/analyze/AnalyzeJdStep'
import AnalyzeUploadStep from '../components/analyze/AnalyzeUploadStep'
import AnalyzeResultsPanel from '../components/analyze/AnalyzeResultsPanel'
import useAnalyzePage from '../components/analyze/useAnalyzePage'

export default function AnalyzePage() {
  const {
    hasRequisitions, remainingAnalyses, isStep1Complete, isStep2Complete, showResults,
    analysisDone, activeStep, isAnalyzing, setCurrentStep, draftSaved, error, setError,
    currentStep, screeningMode, showRequisitionFirst, adHocMode, enableAdHocMode,
    clearRequisitionSelection, requisitions, requisitionsLoading, requisitionSearch,
    setRequisitionSearch, handleLoadRequisition, navigate, requisitionRequired,
    showLoadedRequisition, loadedRequisition, intakeGateStatus, setShowJdModal,
    showAdHocInput, jdMode, setJdMode, hasLoadedRequisition, jdText, setJdText,
    skillsConfirmed, setSkillsConfirmed, setSkillOverrides, jdParseResult, setJdParseResult,
    showAiSuggestion, setShowAiSuggestion, roleName, setRoleName, roleNameTouchedRef,
    roleCategory, parsingJd, setParsingJd, parseError, setParseError, jdFile, setJdFile,
    getJdRootProps, getJdInputProps, isJdDragActive, urlInput, setUrlInput, handleExtractUrl,
    urlLoading, urlError, loadedRequisitionId, skillOverrides, queuedBatchInfo, setQueuedBatchInfo,
    files, getResumeRootProps, getResumeInputProps, isResumeDragActive, planBatchLimit, removeFile,
    weightPreset, weightsManuallySet, hasCustomWeights, showAdvanced, setShowAdvanced,
    handleWeightsAccepted, weights, handleWeightsChange, streamStage, singleFileName,
    runInBackground, setRunInBackground, handleAnalyze, setupSummary, setupSummaryExpanded,
    setSetupSummaryExpanded, handleNewBatch, topCandidate, streamingResults, streamingFailed,
    analysisProgress, fileStatuses, batchStartTime, batchPreparing, batchStuckError,
    handleRetryBatch, streamingResultsRef, streamingFailedRef, analyzeGuide, showJdModal,
  } = useAnalyzePage()

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader
        className="mb-8"
        title={hasRequisitions ? ANALYZE.pageTitleRequisition : ANALYZE.pageTitle}
        subtitle={hasRequisitions ? ANALYZE.subtitleRequisition : ANALYZE.subtitle}
        icon={Sparkles}
        actions={
          remainingAnalyses !== undefined && remainingAnalyses !== Infinity ? (
            <Badge color="brand">{remainingAnalyses} analyses left</Badge>
          ) : null
        }
      />

      {/* Progress Steps */}
      <AnalyzeProgressSteps
        isStep1Complete={isStep1Complete}
        isStep2Complete={isStep2Complete}
        showResults={showResults}
        analysisDone={analysisDone}
        activeStep={activeStep}
        isAnalyzing={isAnalyzing}
        hasRequisitions={hasRequisitions}
        onSelectStep={setCurrentStep}
      />

      {/* Draft saved indicator */}
      {draftSaved && (
        <div className="mb-4 flex items-center gap-2 text-sm text-green-600 bg-green-50 px-4 py-2 rounded-xl ring-1 ring-green-200">
          <Clock className="w-4 h-4" />
          Draft saved locally
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="mb-6 flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-2xl">
          <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-semibold text-red-900">Error</p>
            <p className="text-sm text-red-700 mt-1">{error}</p>
          </div>
          <button
            onClick={() => { setError('') }}
            className="ml-4 px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Step 1: Job Description */}
      {currentStep === 1 && !showResults && (
        <AnalyzeJdStep
          hasRequisitions={hasRequisitions}
          screeningMode={screeningMode}
          showRequisitionFirst={showRequisitionFirst}
          adHocMode={adHocMode}
          enableAdHocMode={enableAdHocMode}
          clearRequisitionSelection={clearRequisitionSelection}
          requisitions={requisitions}
          requisitionsLoading={requisitionsLoading}
          requisitionSearch={requisitionSearch}
          setRequisitionSearch={setRequisitionSearch}
          handleLoadRequisition={handleLoadRequisition}
          navigate={navigate}
          requisitionRequired={requisitionRequired}
          showLoadedRequisition={showLoadedRequisition}
          loadedRequisition={loadedRequisition}
          intakeGateStatus={intakeGateStatus}
          remainingAnalyses={remainingAnalyses}
          setShowJdModal={setShowJdModal}
          showAdHocInput={showAdHocInput}
          jdMode={jdMode}
          setJdMode={setJdMode}
          hasLoadedRequisition={hasLoadedRequisition}
          jdText={jdText}
          setJdText={setJdText}
          skillsConfirmed={skillsConfirmed}
          setSkillsConfirmed={setSkillsConfirmed}
          setSkillOverrides={setSkillOverrides}
          jdParseResult={jdParseResult}
          setJdParseResult={setJdParseResult}
          showAiSuggestion={showAiSuggestion}
          setShowAiSuggestion={setShowAiSuggestion}
          roleName={roleName}
          setRoleName={setRoleName}
          roleNameTouchedRef={roleNameTouchedRef}
          roleCategory={roleCategory}
          parsingJd={parsingJd}
          setParsingJd={setParsingJd}
          parseError={parseError}
          setParseError={setParseError}
          jdFile={jdFile}
          setJdFile={setJdFile}
          getJdRootProps={getJdRootProps}
          getJdInputProps={getJdInputProps}
          isJdDragActive={isJdDragActive}
          urlInput={urlInput}
          setUrlInput={setUrlInput}
          handleExtractUrl={handleExtractUrl}
          urlLoading={urlLoading}
          urlError={urlError}
          loadedRequisitionId={loadedRequisitionId}
          skillOverrides={skillOverrides}
        />
      )}

      {/* Step 2: Upload & Analyze */}
      {currentStep === 2 && !showResults && (
        <AnalyzeUploadStep
          queuedBatchInfo={queuedBatchInfo}
          setQueuedBatchInfo={setQueuedBatchInfo}
          files={files}
          getResumeRootProps={getResumeRootProps}
          getResumeInputProps={getResumeInputProps}
          isResumeDragActive={isResumeDragActive}
          planBatchLimit={planBatchLimit}
          removeFile={removeFile}
          weightPreset={weightPreset}
          weightsManuallySet={weightsManuallySet}
          hasCustomWeights={hasCustomWeights}
          showAdvanced={showAdvanced}
          setShowAdvanced={setShowAdvanced}
          showAiSuggestion={showAiSuggestion}
          jdText={jdText}
          handleWeightsAccepted={handleWeightsAccepted}
          weights={weights}
          handleWeightsChange={handleWeightsChange}
          roleCategory={roleCategory}
          skillsConfirmed={skillsConfirmed}
          streamStage={streamStage}
          singleFileName={singleFileName}
          runInBackground={runInBackground}
          setRunInBackground={setRunInBackground}
          setCurrentStep={setCurrentStep}
          handleAnalyze={handleAnalyze}
          isStep2Complete={isStep2Complete}
          isAnalyzing={isAnalyzing}
        />
      )}

      {/* Step 3: Batch Analysis Results */}
      {showResults && (
        <AnalyzeResultsPanel
          setupSummary={setupSummary}
          jdMode={jdMode}
          jdText={jdText}
          setupSummaryExpanded={setupSummaryExpanded}
          setSetupSummaryExpanded={setSetupSummaryExpanded}
          handleNewBatch={handleNewBatch}
          analysisDone={analysisDone}
          topCandidate={topCandidate}
          streamingResults={streamingResults}
          streamingFailed={streamingFailed}
          analysisProgress={analysisProgress}
          navigate={navigate}
          isAnalyzing={isAnalyzing}
          fileStatuses={fileStatuses}
          batchStartTime={batchStartTime}
          batchPreparing={batchPreparing}
          batchStuckError={batchStuckError}
          handleRetryBatch={handleRetryBatch}
          streamingResultsRef={streamingResultsRef}
          streamingFailedRef={streamingFailedRef}
          skillOverrides={skillOverrides}
          skillsConfirmed={skillsConfirmed}
          jdParseResult={jdParseResult}
          weights={weights}
          roleCategory={roleCategory}
        />
      )}

      <FeatureGuideModal
        open={analyzeGuide.open}
        guide={analyzeGuide.guide}
        onDismiss={analyzeGuide.dismiss}
      />
      {showJdModal && loadedRequisition?.jd_text && (
        <JdFullModal
          title={`${ANALYZE.jdReferenceLabel} · ${loadedRequisition.title || loadedRequisition.name}`}
          jdText={loadedRequisition.jd_text}
          onClose={() => setShowJdModal(false)}
        />
      )}
    </div>
  )
}
