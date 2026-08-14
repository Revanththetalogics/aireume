import { CheckCircle, ChevronRight, Loader2 } from 'lucide-react'
import { ANALYZE_STEPS, isAnalyzeStepComplete, canNavigateToAnalyzeStep } from '../../lib/analyzeBatchUtils'

export default function AnalyzeProgressSteps({
  isStep1Complete,
  isStep2Complete,
  showResults,
  analysisDone,
  activeStep,
  isAnalyzing,
  hasRequisitions,
  onSelectStep,
}) {
  return (
      <div className="mb-8 flex items-center justify-between gap-2">
        {ANALYZE_STEPS.map((step, idx) => {
          const isComplete = isAnalyzeStepComplete(step.num, {
            isStep1Complete,
            isStep2Complete,
            showResults,
            analysisDone,
          })
          const isActive = activeStep === step.num
          const canNavigate = canNavigateToAnalyzeStep(step.num, { isAnalyzing, showResults })

          return (
            <div key={step.num} className="flex items-center flex-1 min-w-0">
              <button
                type="button"
                disabled={!canNavigate}
                onClick={() => {
                  if (!canNavigate) return
                  if (step.num === 3) return
                  onSelectStep(step.num)
                }}
                className={`flex items-center gap-2 sm:gap-3 min-w-0 ${
                  isActive ? 'opacity-100' : 'opacity-60 hover:opacity-80'
                } ${canNavigate ? '' : 'cursor-default'} transition-opacity`}
              >
                <div className={`w-9 h-9 sm:w-10 sm:h-10 rounded-full flex items-center justify-center font-bold text-sm transition-all shrink-0 ${
                  isComplete
                    ? 'bg-emerald-500 text-white ring-4 ring-emerald-100'
                    : isActive
                    ? 'bg-brand-600 text-white ring-4 ring-brand-100'
                    : 'bg-slate-200 text-slate-600'
                }`}>
                  {isComplete && step.num !== 3 ? (
                    <CheckCircle className="w-5 h-5" />
                  ) : isActive && step.num === 3 && !analysisDone ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : isComplete && step.num === 3 ? (
                    <CheckCircle className="w-5 h-5" />
                  ) : (
                    step.num
                  )}
                </div>
                <span className={`text-xs sm:text-sm font-semibold truncate ${isActive ? 'text-brand-900' : 'text-slate-600'}`}>
                  {step.num === 1 && hasRequisitions ? 'Opening & skills' : step.label}
                </span>
              </button>
              {idx < ANALYZE_STEPS.length - 1 && (
                <ChevronRight className="w-4 h-4 sm:w-5 sm:h-5 text-slate-300 mx-1 sm:mx-2 flex-shrink-0" />
              )}
            </div>
          )
        })}
      </div>

  )
}
