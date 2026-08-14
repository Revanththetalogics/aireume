import {
  AlertCircle, ChevronDown, ChevronRight, FileText, Loader2, Settings, Sparkles, Upload, X, CheckCircle2,
} from 'lucide-react'
import EmptyState from '../EmptyState'
import { Card } from '../ui'
import WeightSuggestionPanel from '../WeightSuggestionPanel'
import UniversalWeightsPanel from '../UniversalWeightsPanel'
import { StreamStageTracker } from '../patterns'
import { PRESET_LABELS, BACKGROUND_BATCH_MIN, BACKGROUND_BATCH_AUTO } from './analyzeConstants'

export default function AnalyzeUploadStep(props) {
  const {
    queuedBatchInfo,
    setQueuedBatchInfo,
    files,
    getResumeRootProps,
    getResumeInputProps,
    isResumeDragActive,
    planBatchLimit,
    removeFile,
    weightPreset,
    weightsManuallySet,
    hasCustomWeights,
    showAdvanced,
    setShowAdvanced,
    showAiSuggestion,
    jdText,
    handleWeightsAccepted,
    weights,
    handleWeightsChange,
    roleCategory,
    skillsConfirmed,
    streamStage,
    singleFileName,
    runInBackground,
    setRunInBackground,
    setCurrentStep,
    handleAnalyze,
    isStep2Complete,
    isAnalyzing,
  } = props

  return (
        <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand-xl p-6 md:p-8 card-animate">
          <h2 className="text-xl font-bold text-brand-900 mb-6">Step 2: Upload & Analyze</h2>

          {queuedBatchInfo && (
            <Card className="mb-6 p-6 ring-emerald-100 bg-emerald-50/40">
              <EmptyState
                icon={CheckCircle2}
                title={`${queuedBatchInfo.count} resume${queuedBatchInfo.count !== 1 ? 's' : ''} queued`}
                description="Scoring runs in the background. Open Activity in the top navigation to track progress."
                actionLabel="Upload another batch"
                onAction={() => setQueuedBatchInfo(null)}
              />
            </Card>
          )}

          {/* Analysis Type Indicator */}
          <div className="mb-6 p-4 bg-brand-50 rounded-2xl ring-1 ring-brand-200">
            <div className="flex items-center gap-3">
              <Sparkles className="w-5 h-5 text-brand-600" />
              <div>
                <p className="text-sm font-semibold text-brand-900">
                  {files.length === 0 ? 'Ready for Analysis' : files.length === 1 ? 'Single Analysis' : `Batch Analysis (${files.length} resumes)`}
                </p>
                <p className="text-xs text-slate-600 mt-0.5">
                  {files.length === 0 
                    ? 'Upload 1 resume for detailed analysis or multiple for batch processing'
                    : files.length === 1
                    ? 'Detailed report with full analysis and interview questions'
                    : 'Ranked shortlist with comparative scoring'
                  }
                </p>
              </div>
            </div>
          </div>

          {/* Resume Upload */}
          <div
            {...getResumeRootProps()}
            className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all mb-4 ${
              isResumeDragActive
                ? 'border-brand-500 bg-brand-50'
                : files.length > 0
                ? 'border-brand-200 bg-brand-50/40'
                : 'border-brand-200 hover:border-brand-400 hover:bg-brand-50/40'
            }`}
          >
            <input {...getResumeInputProps()} />
            <Upload className="w-12 h-12 text-brand-400 mx-auto mb-3" />
            <p className="text-sm font-medium text-slate-700">
              {files.length > 0 ? 'Drop more resumes or click to add' : 'Drop resumes here or click to browse'}
            </p>
            <p className="text-xs text-slate-500 mt-1">PDF or DOCX (max 10MB each, up to {planBatchLimit} files on your plan)</p>
          </div>

          {/* File List */}
          {files.length > 0 && (
            <div className="space-y-2 mb-6">
              <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
                {files.length} Resume{files.length > 1 ? 's' : ''} Ready
              </p>
              <div className="max-h-64 overflow-y-auto space-y-2">
                {files.map((file, idx) => (
                  <div key={idx} className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl ring-1 ring-slate-200">
                    <FileText className="w-5 h-5 text-brand-600 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-900 truncate">{file.name}</p>
                      <p className="text-xs text-slate-500">{(file.size / 1024).toFixed(1)} KB</p>
                    </div>
                    <button
                      onClick={() => removeFile(idx)}
                      aria-label="Remove file"
                      className="p-2 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      <X className="w-4 h-4 text-red-600" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Weight preset indicator */}
          <p className="text-xs text-slate-400 mt-1 mb-4">
            Scoring: {PRESET_LABELS[weightPreset] || 'Balanced'} weights
            {!weightsManuallySet && ' (auto-detected)'}
          </p>

          {/* Advanced: Scoring Weights (Business+) */}
          {hasCustomWeights ? (
          <div className="mt-6">
            <button 
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-700 transition-colors"
            >
              <Settings className="w-4 h-4" />
              <span>Advanced: Scoring Weights</span>
              <ChevronDown className={`w-4 h-4 transition-transform ${showAdvanced ? 'rotate-180' : ''}`} />
            </button>
            
            {showAdvanced && (
              <div className="mt-4 p-4 bg-slate-50 rounded-xl border border-slate-200">
                {showAiSuggestion && jdText && (
                  <div className="mb-6">
                    <WeightSuggestionPanel
                      jobDescription={jdText}
                      onWeightsAccepted={handleWeightsAccepted}
                      currentWeights={weights}
                    />
                  </div>
                )}
                <UniversalWeightsPanel
                  weights={weights}
                  onChange={handleWeightsChange}
                  roleCategory={roleCategory}
                />
              </div>
            )}
          </div>
          ) : (
            <p className="mt-4 text-xs text-slate-400">
              Custom scoring weights are available on Business and above.
            </p>
          )}

          {/* Skill confirmation required message */}
          {!skillsConfirmed && files.length > 0 && (
            <div className="mb-6 p-4 bg-amber-50 ring-1 ring-amber-200 rounded-2xl flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
              <p className="text-sm text-amber-700">Please go back to Step 1 and confirm the extracted skills before analysis</p>
            </div>
          )}

          {streamStage && singleFileName && (
            <div className="mb-6">
              <p className="text-xs text-slate-500 mb-2 font-medium">Analyzing {singleFileName}</p>
              <StreamStageTracker activeStage={streamStage} />
            </div>
          )}

          {files.length > 1 && files.length >= BACKGROUND_BATCH_MIN && (
            <label htmlFor="analyze-run-in-background" className="mb-4 flex items-start gap-3 p-4 bg-indigo-50 ring-1 ring-indigo-200 rounded-2xl cursor-pointer">
              <input
                id="analyze-run-in-background"
                type="checkbox"
                checked={runInBackground}
                onChange={(e) => setRunInBackground(e.target.checked)}
                className="mt-1 rounded border-indigo-300 text-indigo-600 focus:ring-indigo-500"
              />
              <span className="text-sm font-semibold text-indigo-900">
                Run in background
                <span className="block text-xs font-normal text-indigo-700 mt-0.5">
                  Queue {files.length} resumes for server-side processing. Track progress in Activity Center.
                  {files.length >= BACKGROUND_BATCH_AUTO && ' (Recommended for 50+ files)'}
                </span>
              </span>
            </label>
          )}

          {/* Navigation */}
          <div className="flex justify-between">
            <button
              onClick={() => setCurrentStep(1)}
              className="flex items-center gap-2 px-6 py-3 bg-slate-100 text-slate-700 rounded-2xl font-semibold hover:bg-slate-200 transition-colors"
            >
              <ChevronRight className="w-4 h-4 rotate-180" />
              Back
            </button>
            <button
              onClick={handleAnalyze}
              disabled={!isStep2Complete || isAnalyzing || !skillsConfirmed}
              className="flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-brand-600 to-brand-500 text-white rounded-2xl font-bold hover:shadow-brand-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-brand-sm"
            >
              {isAnalyzing && files.length === 1 ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5" />
                  Analyze {files.length} Resume{files.length > 1 ? 's' : ''}
                </>
              )}
            </button>
          </div>
        </div>

  )
}
