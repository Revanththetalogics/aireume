import { useNavigate } from 'react-router-dom'
import { PIPELINE_STAGES } from '../../lib/constants'
import { Button } from '../ui'
import { ScoreProgression } from '../patterns/InterviewOutcomeBadges'
import { REQUISITIONS } from '../../lib/uxLabels'

const COLUMN_STYLES = {
  pending: { header: 'bg-amber-50 text-amber-800 border-amber-200', badge: 'bg-amber-100 text-amber-700' },
  'in-review': { header: 'bg-blue-50 text-blue-800 border-blue-200', badge: 'bg-blue-100 text-blue-700' },
  shortlisted: { header: 'bg-green-50 text-green-800 border-green-200', badge: 'bg-green-100 text-green-700' },
  rejected: { header: 'bg-red-50 text-red-800 border-red-200', badge: 'bg-red-100 text-red-700' },
  hired: { header: 'bg-indigo-50 text-indigo-800 border-indigo-200', badge: 'bg-indigo-100 text-indigo-700' },
}

export function PipelineCard({ item, onStatusChange, onSubmit, onOutcome, canWritePipeline, isHm, requisitionId }) {
  const navigate = useNavigate()
  return (
    <div className="bg-white rounded-xl ring-1 ring-brand-100 p-3 shadow-sm">
      <button
        type="button"
        onClick={() => navigate(`/candidates/${item.candidate_id}`)}
        className="text-left w-full"
      >
        <p className="font-semibold text-sm text-brand-900 truncate">
          {item.candidate_name || `Candidate #${item.candidate_id}`}
        </p>
        {item.candidate_email && (
          <p className="text-xs text-slate-500 truncate">{item.candidate_email}</p>
        )}
      </button>
      <div className="flex items-center justify-between mt-2 gap-2 flex-wrap">
        {(item.fit_score != null || item.call_fit_score != null) && (
          <ScoreProgression
            analysisScore={item.fit_score}
            callScore={item.call_fit_score}
            callSource={item.call_source}
            compact
          />
        )}
        {item.submission_status === 'submitted' && (
          <span className="text-[10px] font-semibold text-blue-700 bg-blue-50 px-1.5 py-0.5 rounded">Submitted</span>
        )}
        {canWritePipeline && (
          <select
            value={item.pipeline_status}
            onChange={(e) => onStatusChange(item.candidate_id, e.target.value)}
            className="text-xs rounded-lg border border-brand-200 px-2 py-1 ml-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {PIPELINE_STAGES.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        )}
      </div>
      {canWritePipeline && !isHm && item.submission_status !== 'submitted' && (
        <Button
          type="button"
          variant="ghost"
          className="mt-2 w-full text-xs"
          onClick={() => onSubmit(item.candidate_id)}
        >
          {REQUISITIONS.submitToHmCta}
        </Button>
      )}
      {canWritePipeline && !isHm && item.suggested_action === 'ai_interview' && (
        <Button
          type="button"
          variant="secondary"
          className="mt-2 w-full text-xs"
          onClick={() => navigate(`/candidates/${item.candidate_id}?requisition_id=${requisitionId}`)}
        >
          Schedule AI interview
        </Button>
      )}
      {isHm && item.submission_status === 'submitted' && !item.hm_outcome && (
        <div className="flex gap-1 mt-2">
          {['advance', 'hold', 'reject'].map((o) => (
            <button
              key={o}
              type="button"
              onClick={() => onOutcome(item.candidate_id, o)}
              className="flex-1 text-[10px] font-semibold capitalize py-1 rounded-lg ring-1 ring-brand-100 hover:bg-brand-50"
            >
              {o}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}


export default function RequisitionPipelineBoard({
  pipelineSync,
  pipeline,
  requisitionId,
  onStatusChange,
  onSubmit,
  onOutcome,
  canWritePipeline,
  isHiringManager,
}) {
  return (
    <>
      {pipelineSync?.added > 0 && (
        <div className="mb-4 text-sm text-emerald-800 bg-emerald-50 ring-1 ring-emerald-200 rounded-xl px-4 py-3">
          Synced {pipelineSync.added} candidate{pipelineSync.added !== 1 ? 's' : ''} from prior screenings
          {pipelineSync.linked > 0 ? ` (${pipelineSync.linked} requisition links updated)` : ''}.
        </div>
      )}
      <div className="flex gap-4 overflow-x-auto pb-4">
        {PIPELINE_STAGES.map((stage) => {
          const items = pipeline[stage] || []
          const style = COLUMN_STYLES[stage] || COLUMN_STYLES.pending
          return (
            <div key={stage} className="min-w-[220px] flex-1">
              <div className={`rounded-xl border px-3 py-2 mb-3 text-xs font-bold uppercase tracking-wider ${style.header}`}>
                {stage} ({items.length})
              </div>
              <div className="space-y-2">
                {items.map((item) => (
                  <PipelineCard
                    key={item.candidate_id}
                    item={item}
                    requisitionId={requisitionId}
                    onStatusChange={onStatusChange}
                    onSubmit={onSubmit}
                    onOutcome={onOutcome}
                    canWritePipeline={canWritePipeline}
                    isHm={isHiringManager}
                  />
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </>
  )
}
