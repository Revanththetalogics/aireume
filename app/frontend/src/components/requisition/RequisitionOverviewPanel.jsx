import { UserPlus } from 'lucide-react'
import { Button, Card } from '../ui'
import { REQUISITIONS } from '../../lib/uxLabels'
import { RequisitionNextActionBanner, JdPreviewSection } from './RequisitionDetailPanels'

export default function RequisitionOverviewPanel({
  nextAction,
  onNextAction,
  canWrite,
  canAssign,
  isAdmin,
  req,
  hmSelectId,
  setHmSelectId,
  hmCandidates,
  saveHiringManager,
  savingHm,
  onShowHmRequest,
  onShowHmInvite,
  assignSelfAsHm,
  onApproveHmRequest,
  onRejectHmRequest,
  assignRecruiterId,
  setAssignRecruiterId,
  recruiterCandidates,
  onAssignRecruiter,
  saving,
  pendingFeedback,
  onApplyFeedback,
  analytics,
  resumeWeight,
  setResumeWeight,
  interviewWeight,
  setInterviewWeight,
  saveHiringWeights,
  savingWeights,
  onViewFullJd,
}) {
  return (
        <Card className="p-6 space-y-4">
          <RequisitionNextActionBanner action={nextAction} onAction={onNextAction} />
          {canWrite && (
            <div id="hm-assignment" className="pb-4 border-b border-brand-50">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                {REQUISITIONS.hmAssignOverview}
              </p>
              <p className="text-xs text-slate-500 mb-3">{REQUISITIONS.hmAssignHint}</p>
              {req.hm_request_status === 'pending' && req.hm_request_email && (
                <div className="mb-3 rounded-xl bg-amber-50 ring-1 ring-amber-200 px-3 py-2 text-sm text-amber-900">
                  <p className="font-semibold">{REQUISITIONS.hmRequestPending}</p>
                  <p className="mt-1">
                    <span className="font-medium">{req.hm_request_email}</span>
                    {req.hm_requested_by_email ? ` · requested by ${req.hm_requested_by_email}` : ''}
                  </p>
                  {req.hm_request_notes && (
                    <p className="mt-1 text-xs text-amber-800">{req.hm_request_notes}</p>
                  )}
                  {isAdmin && (
                    <div className="flex flex-wrap gap-2 mt-3">
                      <Button size="sm" onClick={onApproveHmRequest} disabled={savingHm}>
                        {REQUISITIONS.hmRequestApproveCta}
                      </Button>
                      <Button size="sm" variant="ghost" onClick={onRejectHmRequest} disabled={savingHm}>
                        {REQUISITIONS.hmRequestRejectCta}
                      </Button>
                    </div>
                  )}
                </div>
              )}
              <div className="flex flex-wrap items-end gap-3">
                <label className="text-sm flex-1 min-w-[14rem]">
                  <span className="font-semibold text-slate-700">Primary hiring manager</span>
                  <select
                    value={hmSelectId}
                    onChange={(e) => setHmSelectId(e.target.value)}
                    className="mt-1 w-full rounded-xl border border-brand-200 px-3 py-2 text-sm bg-white"
                  >
                    <option value="">Select hiring manager…</option>
                    {hmCandidates.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.email} ({m.role.replace(/_/g, ' ')})
                      </option>
                    ))}
                  </select>
                </label>
                <Button
                  onClick={() => saveHiringManager()}
                  disabled={savingHm || !hmSelectId}
                  size="sm"
                  className="shrink-0"
                >
                  {savingHm ? 'Saving…' : REQUISITIONS.hmAssignCta}
                </Button>
                {canWrite && !isAdmin && req.hm_request_status !== 'pending' && (
                  <Button
                    variant="secondary"
                    onClick={onShowHmRequest}
                    disabled={savingHm}
                    size="sm"
                    className="shrink-0"
                  >
                    <UserPlus className="w-4 h-4" />
                    {REQUISITIONS.hmRequestCta}
                  </Button>
                )}
                {isAdmin && (
                  <Button
                    variant="secondary"
                    onClick={onShowHmInvite}
                    disabled={savingHm}
                    size="sm"
                    className="shrink-0"
                  >
                    <UserPlus className="w-4 h-4" />
                    {REQUISITIONS.hmInviteCta}
                  </Button>
                )}
                {isAdmin && (
                  <Button
                    variant="secondary"
                    onClick={assignSelfAsHm}
                    disabled={savingHm}
                    size="sm"
                    className="shrink-0"
                  >
                    {REQUISITIONS.hmAssignSelfCta}
                  </Button>
                )}
              </div>
              {canWrite && hmCandidates.length === 0 && req.hm_request_status !== 'pending' && (
                <p className="text-xs text-amber-700 mt-2">
                  {isAdmin
                    ? 'No hiring managers on your team yet — invite one or approve a recruiter request.'
                    : 'No hiring managers on your team yet — request HM access and an admin will approve.'}
                </p>
              )}
              {req.primary_hiring_manager_email && (
                <p className="text-xs text-slate-500 mt-2">
                  Current: <span className="font-semibold text-slate-700">{req.primary_hiring_manager_email}</span>
                </p>
              )}
              {req.opened_on_behalf_of_hm_email && (
                <p className="text-xs text-slate-500 mt-1">
                  {REQUISITIONS.openedOnBehalfOf}: <span className="font-semibold">{req.opened_on_behalf_of_hm_email}</span>
                </p>
              )}
            </div>
          )}
          {canAssign && (
            <div className="pt-4 border-t border-brand-50">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">{REQUISITIONS.assignRecruiter}</p>
              <p className="text-xs text-slate-500 mb-2">{REQUISITIONS.assignRecruiterHint}</p>
              <div className="flex flex-wrap gap-2 items-end">
                <select
                  value={assignRecruiterId}
                  onChange={(e) => setAssignRecruiterId(e.target.value)}
                  className="rounded-xl border border-brand-200 px-3 py-2 text-sm min-w-[12rem]"
                >
                  <option value="">Select recruiter…</option>
                  {recruiterCandidates.map((m) => (
                    <option key={m.id} value={m.id}>{m.email}</option>
                  ))}
                </select>
                <Button size="sm" onClick={onAssignRecruiter} disabled={!assignRecruiterId || saving}>
                  {REQUISITIONS.assignRecruiter}
                </Button>
              </div>
              {req.assigned_recruiter_email && (
                <p className="text-xs text-slate-500 mt-2">Assigned: <span className="font-semibold">{req.assigned_recruiter_email}</span></p>
              )}
            </div>
          )}
          {req.intake_status === 'changes_requested' && canWrite && (
            <div className="rounded-xl bg-amber-50 ring-1 ring-amber-200 px-4 py-3 text-sm text-amber-900">
              {REQUISITIONS.intakeChangesRequested}
            </div>
          )}
          {pendingFeedback && canWrite && (
            <div className="rounded-xl bg-blue-50 ring-1 ring-blue-200 px-4 py-3 space-y-2">
              <p className="text-sm font-bold text-blue-900">{REQUISITIONS.hmRejectFeedbackTitle}</p>
              <ul className="text-xs text-blue-800 list-disc pl-4">
                {(pendingFeedback.search_brief_additions || []).map((line, i) => (
                  <li key={i}>{line}</li>
                ))}
              </ul>
              <Button size="sm" onClick={onApplyFeedback} disabled={saving}>{REQUISITIONS.applyFeedbackCta}</Button>
            </div>
          )}
          <div className="grid sm:grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-slate-500 font-medium">Candidates</p>
              <p className="text-2xl font-bold text-brand-900">{req.candidate_count ?? 0}</p>
            </div>
            <div>
              <p className="text-slate-500 font-medium">Intake</p>
              <p className="font-semibold capitalize">{req.intake_status?.replace(/_/g, ' ')}</p>
            </div>
            <div>
              <p className="text-slate-500 font-medium">Criteria version</p>
              <p className="font-semibold">{req.current_criteria_version || 0}</p>
            </div>
          </div>
          {analytics && (
            <div className="pt-4 border-t border-brand-50">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Funnel</p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(analytics.funnel || {}).map(([stage, count]) => (
                  <span key={stage} className="text-xs font-semibold px-2 py-1 rounded-lg bg-brand-50 text-brand-800 capitalize">
                    {stage}: {count}
                  </span>
                ))}
              </div>
            </div>
          )}
          {canWrite && (
            <div className="pt-4 border-t border-brand-50">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Hiring signal weights</p>
              <p className="text-xs text-slate-500 mb-3">Override tenant defaults for combined resume + interview score on this requisition.</p>
              <div className="flex flex-wrap items-end gap-4">
                <label className="text-sm">
                  Resume %
                  <input
                    type="number"
                    min={0}
                    max={100}
                    value={resumeWeight}
                    onChange={(e) => setResumeWeight(Number(e.target.value))}
                    className="mt-1 block w-24 rounded-xl border border-brand-200 px-3 py-2 text-sm"
                  />
                </label>
                <label className="text-sm">
                  Interview %
                  <input
                    type="number"
                    min={0}
                    max={100}
                    value={interviewWeight}
                    onChange={(e) => setInterviewWeight(Number(e.target.value))}
                    className="mt-1 block w-24 rounded-xl border border-brand-200 px-3 py-2 text-sm"
                  />
                </label>
                <Button onClick={saveHiringWeights} disabled={savingWeights} size="sm">
                  {savingWeights ? 'Saving…' : 'Save weights'}
                </Button>
              </div>
            </div>
          )}
          <div className="pt-4 border-t border-brand-50">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
              {REQUISITIONS.jdPreviewLabel}
            </p>
            <JdPreviewSection jdText={req.jd_text} onViewFull={onViewFullJd} />
          </div>
        </Card>

  )
}
