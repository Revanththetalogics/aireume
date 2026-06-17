import { useState, useEffect } from 'react'
import { CheckCircle, Clock, Loader2, ShieldCheck, PhoneCall, Users, Gavel } from 'lucide-react'
import { getScorecard } from '../lib/api'

const STAGES = [
  {
    key: 'initial_screening',
    label: 'Initial Screening',
    description: 'AI-powered skills & experience analysis',
    icon: ShieldCheck,
  },
  {
    key: 'technical_interview',
    label: 'Technical Interview',
    description: 'Phone screen kit evaluation',
    icon: PhoneCall,
  },
  {
    key: 'cultural_fit',
    label: 'Cultural Fit Assessment',
    description: 'Culture & behavioral evaluation',
    icon: Users,
  },
  {
    key: 'final_decision',
    label: 'Final Decision',
    description: 'Recruiter recommendation submitted',
    icon: Gavel,
  },
]

const STATUS_STYLES = {
  completed: {
    badge: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
    dot: 'bg-emerald-500',
    label: 'Completed',
  },
  in_progress: {
    badge: 'bg-blue-50 text-blue-700 ring-blue-200',
    dot: 'bg-blue-500 animate-pulse',
    label: 'In Progress',
  },
  pending: {
    badge: 'bg-amber-50 text-amber-700 ring-amber-200',
    dot: 'bg-amber-400',
    label: 'Pending',
  },
}

/**
 * EvaluationChecklist — shows the pipeline status for a candidate's evaluation.
 *
 * Determines each stage status from:
 *   - result data (fit_score → Initial Screening)
 *   - scorecard data (evaluations, debrief, recommendation)
 */
export default function EvaluationChecklist({ result }) {
  const [scorecard, setScorecard] = useState(null)
  const [loading, setLoading] = useState(true)

  const resultId = result?.result_id || result?.id

  useEffect(() => {
    if (!resultId) { setLoading(false); return }
    const load = async () => {
      try {
        const data = await getScorecard(resultId)
        setScorecard(data)
      } catch (err) {
        console.debug('EvaluationChecklist: scorecard not available', err)
      }
      setLoading(false)
    }
    load()
  }, [resultId])

  /** Derive the status for each stage from result + scorecard data */
  const getStageStatus = (stageKey) => {
    switch (stageKey) {
      case 'initial_screening':
        // Completed if AI analysis has been done (fit_score exists)
        return result?.fit_score != null ? 'completed' : 'pending'

      case 'technical_interview': {
        // Completed if technical/behavioral evaluations were submitted
        const techEval = scorecard?.technical_summary?.evaluated_count || 0
        const behEval = scorecard?.behavioral_summary?.evaluated_count || 0
        const techTotal = scorecard?.technical_summary?.total_questions || 0
        const behTotal = scorecard?.behavioral_summary?.total_questions || 0
        const evalCount = techEval + behEval
        const totalCount = techTotal + behTotal
        if (evalCount > 0 && evalCount >= totalCount && totalCount > 0) return 'completed'
        if (evalCount > 0) return 'in_progress'
        // Also consider "completed" if debrief exists (recruiter submitted evaluation)
        if (scorecard?.debrief) return 'completed'
        return 'pending'
      }

      case 'cultural_fit': {
        // Completed if culture fit questions were rated
        const cultEval = scorecard?.culture_fit_summary?.evaluated_count || 0
        const cultTotal = scorecard?.culture_fit_summary?.total_questions || 0
        if (cultEval > 0 && cultEval >= cultTotal && cultTotal > 0) return 'completed'
        if (cultEval > 0) return 'in_progress'
        // Also consider "completed" if debrief exists
        if (scorecard?.debrief) return 'completed'
        return 'pending'
      }

      case 'final_decision': {
        // Completed if a recommendation was submitted or debrief generated
        if (scorecard?.recruiter_recommendation) return 'completed'
        if (scorecard?.debrief) return 'completed'
        if (scorecard?.overall_assessment) return 'in_progress'
        return 'pending'
      }

      default:
        return 'pending'
    }
  }

  const completedCount = STAGES.filter(s => getStageStatus(s.key) === 'completed').length

  if (loading) {
    return (
      <div className="bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 shadow-brand-sm p-5">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-5 h-5 rounded-md bg-brand-50 flex items-center justify-center">
            <Loader2 className="w-3.5 h-3.5 text-brand-600 animate-spin" />
          </div>
          <h3 className="text-sm font-bold text-slate-800">Evaluation Checklist</h3>
        </div>
        <div className="space-y-3">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="h-10 bg-slate-50 rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white/90 backdrop-blur-md rounded-2xl ring-1 ring-brand-100 shadow-brand-sm p-5">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded-md bg-brand-50 flex items-center justify-center">
            <CheckCircle className="w-3.5 h-3.5 text-brand-600" />
          </div>
          <h3 className="text-sm font-bold text-slate-800">Evaluation Checklist</h3>
        </div>
        <span className="text-xs font-semibold text-slate-500">
          {completedCount}/{STAGES.length} complete
        </span>
      </div>

      {/* Progress bar */}
      <div className="w-full h-1.5 bg-slate-100 rounded-full mb-4 overflow-hidden">
        <div
          className="h-full bg-brand-500 rounded-full transition-all duration-500"
          style={{ width: `${(completedCount / STAGES.length) * 100}%` }}
        />
      </div>

      {/* Stage list */}
      <div className="space-y-2">
        {STAGES.map((stage) => {
          const status = getStageStatus(stage.key)
          const style = STATUS_STYLES[status]
          const Icon = stage.icon
          const isLast = stage.key === STAGES[STAGES.length - 1].key

          return (
            <div key={stage.key} className="relative">
              <div className="flex items-center gap-3 p-2.5 rounded-xl hover:bg-slate-50/50 transition-colors">
                {/* Icon + connector line */}
                <div className="relative flex flex-col items-center">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                    status === 'completed' ? 'bg-emerald-50' :
                    status === 'in_progress' ? 'bg-blue-50' : 'bg-slate-50'
                  }`}>
                    {status === 'completed' ? (
                      <CheckCircle className="w-4 h-4 text-emerald-600" />
                    ) : (
                      <Icon className={`w-4 h-4 ${
                        status === 'in_progress' ? 'text-blue-600' : 'text-slate-400'
                      }`} />
                    )}
                  </div>
                  {/* Connector line */}
                  {!isLast && (
                    <div className={`w-0.5 h-3 mt-1 ${
                      status === 'completed' ? 'bg-emerald-200' : 'bg-slate-200'
                    }`} />
                  )}
                </div>

                {/* Stage info */}
                <div className="flex-1 min-w-0">
                  <p className={`text-sm font-semibold ${
                    status === 'completed' ? 'text-slate-800' :
                    status === 'in_progress' ? 'text-blue-800' : 'text-slate-500'
                  }`}>
                    {stage.label}
                  </p>
                  <p className="text-xs text-slate-400 truncate">{stage.description}</p>
                </div>

                {/* Status badge */}
                <span className={`shrink-0 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ring-1 ${style.badge}`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
                  {style.label}
                </span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
