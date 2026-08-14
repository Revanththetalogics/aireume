import { Button, Card } from '../ui'
import { REQUISITIONS } from '../../lib/uxLabels'
import { CriteriaEditForm, CriteriaVersionDiff } from './RequisitionDetailPanels'

export default function RequisitionCriteriaPanel({
  req,
  canWrite,
  editCriteria,
  setEditCriteria,
  saveCriteria,
  saving,
  criteria,
  criteriaVersions,
  routingPolicy,
  setRoutingPolicy,
  saveRoutingPolicy,
  savingRouting,
}) {
  return (
        <Card className="p-6 space-y-4">
          {req.is_calibrated ? (
            <>
              {canWrite && (
                <div className="flex flex-wrap gap-2 justify-end">
                  {editCriteria == null ? (
                    <Button
                      variant="secondary"
                      onClick={() => setEditCriteria({ ...(req.calibrated_criteria_json || {}) })}
                    >
                      Edit criteria
                    </Button>
                  ) : (
                    <>
                      <Button variant="ghost" onClick={() => setEditCriteria(null)}>Cancel</Button>
                      <Button onClick={saveCriteria} disabled={saving}>Save criteria</Button>
                    </>
                  )}
                </div>
              )}
              {editCriteria != null ? (
                <CriteriaEditForm
                  criteria={editCriteria}
                  onChange={setEditCriteria}
                  readOnly={!canWrite}
                />
              ) : (
                <>
                  <div>
                    <p className="text-xs font-semibold text-slate-500 uppercase mb-2">Must-haves</p>
                    <ul className="list-disc list-inside text-sm text-slate-700">
                      {(criteria.must_haves || []).map((s) => <li key={s}>{s}</li>)}
                    </ul>
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-slate-500 uppercase mb-2">Good-to-haves</p>
                    <ul className="list-disc list-inside text-sm text-slate-700">
                      {(criteria.good_to_haves || []).map((s) => <li key={s}>{s}</li>)}
                    </ul>
                  </div>
                  {(criteria.deal_breakers || []).length > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-slate-500 uppercase mb-2">Deal-breakers</p>
                      <ul className="list-disc list-inside text-sm text-red-700">
                        {criteria.deal_breakers.map((s) => <li key={s}>{s}</li>)}
                      </ul>
                    </div>
                  )}
                </>
              )}
            </>
          ) : (
            <p className="text-slate-500 text-sm">{REQUISITIONS.notCalibratedWarning}</p>
          )}
          {criteriaVersions.length > 0 && (
            <div className="pt-4 border-t border-brand-50 space-y-3">
              <CriteriaVersionDiff versions={criteriaVersions} />
              <p className="text-xs font-semibold text-slate-500 uppercase mb-2">Version history</p>
              <ul className="space-y-1 text-sm text-slate-600">
                {criteriaVersions.map((v) => (
                  <li key={v.id}>v{v.version} — {v.source} ({v.created_at ? new Date(v.created_at).toLocaleDateString() : ''})</li>
                ))}
              </ul>
            </div>
          )}
          <div className="pt-4 border-t border-brand-50 space-y-3">
            <p className="text-xs font-semibold text-slate-500 uppercase">{REQUISITIONS.routingPolicyLabel}</p>
            <p className="text-xs text-slate-500">
              Fit-score bands that suggest submit to HM vs AI interview vs pass. Pipeline CTAs use these thresholds.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <label className="text-xs text-slate-600 space-y-1">
                <span>Submit to HM min</span>
                <input
                  type="number"
                  min={0}
                  max={100}
                  disabled={!canWrite}
                  className="w-full rounded-xl border border-brand-100 px-3 py-2 text-sm"
                  value={routingPolicy.submit_to_hm_min_score}
                  onChange={(e) => setRoutingPolicy((p) => ({ ...p, submit_to_hm_min_score: Number(e.target.value) }))}
                />
              </label>
              <label className="text-xs text-slate-600 space-y-1">
                <span>AI interview min</span>
                <input
                  type="number"
                  min={0}
                  max={100}
                  disabled={!canWrite}
                  className="w-full rounded-xl border border-brand-100 px-3 py-2 text-sm"
                  value={routingPolicy.ai_interview_min_score}
                  onChange={(e) => setRoutingPolicy((p) => ({ ...p, ai_interview_min_score: Number(e.target.value) }))}
                />
              </label>
              <label className="text-xs text-slate-600 space-y-1">
                <span>AI interview max</span>
                <input
                  type="number"
                  min={0}
                  max={100}
                  disabled={!canWrite}
                  className="w-full rounded-xl border border-brand-100 px-3 py-2 text-sm"
                  value={routingPolicy.ai_interview_max_score}
                  onChange={(e) => setRoutingPolicy((p) => ({ ...p, ai_interview_max_score: Number(e.target.value) }))}
                />
              </label>
            </div>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                disabled={!canWrite}
                checked={!!routingPolicy.auto_suggest}
                onChange={(e) => setRoutingPolicy((p) => ({ ...p, auto_suggest: e.target.checked }))}
              />
              Auto-suggest next action on pipeline cards
            </label>
            {canWrite && (
              <Button size="sm" onClick={saveRoutingPolicy} disabled={savingRouting}>
                {savingRouting ? 'Saving…' : 'Save routing thresholds'}
              </Button>
            )}
          </div>
        </Card>

  )
}
