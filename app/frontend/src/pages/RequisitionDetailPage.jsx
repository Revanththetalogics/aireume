import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate, Link, useSearchParams } from 'react-router-dom'
import {
  ArrowLeft, Briefcase, Loader2, Users, CheckCircle2, Sparkles,
  ListChecks, Columns3,
} from 'lucide-react'
import {
  getRequisition,
  getRequisitionPipeline,
  updateRequisitionIntake,
  calibrateRequisition,
  hmApproveRequisition,
  updateRequisitionCandidateStatus,
  submitCandidateToHm,
  recordHmOutcome,
  getRequisitionAnalytics,
  addCandidatesToRequisition,
  getCandidates,
  getRequisitionCriteriaVersions,
} from '../lib/api'
import { PIPELINE_STAGES } from '../lib/constants'
import { Button, Card } from '../components/ui'
import usePermissions from '../hooks/usePermissions'
import { ViewerReadOnlyBanner } from '../components/RequireWriteAccess'
import { REQUISITIONS } from '../lib/uxLabels'

const TABS = [
  { id: 'overview', label: REQUISITIONS.overviewTab, icon: Briefcase },
  { id: 'intake', label: REQUISITIONS.intakeTab, icon: ListChecks },
  { id: 'criteria', label: REQUISITIONS.criteriaTab, icon: Sparkles },
  { id: 'pipeline', label: REQUISITIONS.pipelineTab, icon: Columns3 },
]

const COLUMN_STYLES = {
  pending: { header: 'bg-amber-50 text-amber-800 border-amber-200', badge: 'bg-amber-100 text-amber-700' },
  'in-review': { header: 'bg-blue-50 text-blue-800 border-blue-200', badge: 'bg-blue-100 text-blue-700' },
  shortlisted: { header: 'bg-green-50 text-green-800 border-green-200', badge: 'bg-green-100 text-green-700' },
  rejected: { header: 'bg-red-50 text-red-800 border-red-200', badge: 'bg-red-100 text-red-700' },
  hired: { header: 'bg-indigo-50 text-indigo-800 border-indigo-200', badge: 'bg-indigo-100 text-indigo-700' },
}

function IntakeForm({ intake, onChange, readOnly }) {
  const fields = [
    { key: 'must_haves', label: 'Must-haves (one per line)', rows: 4 },
    { key: 'good_to_haves', label: 'Good-to-haves (one per line)', rows: 3 },
    { key: 'deal_breakers', label: 'Deal-breakers (one per line)', rows: 2 },
    { key: 'environment', label: 'Work environment', rows: 2 },
    { key: 'seniority_bar', label: 'Seniority bar', rows: 1 },
    { key: 'team_context', label: 'Team context', rows: 2 },
    { key: 'success_criteria_90d', label: '90-day success criteria', rows: 2 },
    { key: 'hm_notes', label: 'HM notes', rows: 3 },
  ]

  const getValue = (key) => {
    const v = intake[key]
    if (Array.isArray(v)) return v.join('\n')
    return v || ''
  }

  const setValue = (key, raw) => {
    const listKeys = ['must_haves', 'good_to_haves', 'deal_breakers']
    if (listKeys.includes(key)) {
      onChange({
        ...intake,
        [key]: raw.split('\n').map((s) => s.trim()).filter(Boolean),
      })
    } else {
      onChange({ ...intake, [key]: raw })
    }
  }

  return (
    <div className="space-y-4">
      {fields.map(({ key, label, rows }) => (
        <label key={key} className="block text-sm">
          <span className="font-semibold text-slate-700">{label}</span>
          <textarea
            value={getValue(key)}
            onChange={(e) => setValue(key, e.target.value)}
            rows={rows}
            disabled={readOnly}
            className="mt-1 w-full rounded-xl border border-brand-200 px-3 py-2 text-sm resize-none disabled:opacity-60"
          />
        </label>
      ))}
    </div>
  )
}

function PipelineCard({ item, onStatusChange, onSubmit, onOutcome, canWritePipeline, isHm }) {
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
        {item.fit_score != null && (
          <span className="text-xs font-bold text-brand-700">{item.fit_score}</span>
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

export default function RequisitionDetailPage() {
  const { id } = useParams()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { canWrite, isHiringManager } = usePermissions()
  const [req, setReq] = useState(null)
  const [intake, setIntake] = useState({})
  const [pipeline, setPipeline] = useState({})
  const [analytics, setAnalytics] = useState(null)
  const [criteriaVersions, setCriteriaVersions] = useState([])
  const [tab, setTab] = useState(searchParams.get('tab') || 'overview')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [showAddCandidates, setShowAddCandidates] = useState(false)
  const [allCandidates, setAllCandidates] = useState([])
  const [selectedCandidateIds, setSelectedCandidateIds] = useState([])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [r, pipe, stats, versions] = await Promise.all([
        getRequisition(id),
        getRequisitionPipeline(id),
        getRequisitionAnalytics(id).catch(() => null),
        getRequisitionCriteriaVersions(id).catch(() => []),
      ])
      setReq(r)
      setIntake(r.intake_json || {})
      setPipeline(pipe.pipeline || {})
      setAnalytics(stats)
      setCriteriaVersions(Array.isArray(versions) ? versions : [])
    } catch {
      setReq(null)
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    load()
  }, [load])

  const saveIntake = async () => {
    setSaving(true)
    try {
      const updated = await updateRequisitionIntake(id, intake, 'pending_hm')
      setReq(updated)
      setIntake(updated.intake_json || {})
    } catch {
      window.alert('Failed to save intake')
    } finally {
      setSaving(false)
    }
  }

  const handleCalibrate = async () => {
    setSaving(true)
    try {
      const updated = await calibrateRequisition(id)
      setReq(updated)
      setTab('criteria')
      await load()
    } catch {
      window.alert('Calibration failed')
    } finally {
      setSaving(false)
    }
  }

  const handleHmApproval = async (approved) => {
    setSaving(true)
    try {
      const updated = await hmApproveRequisition(id, approved)
      setReq(updated)
    } catch {
      window.alert('Approval failed')
    } finally {
      setSaving(false)
    }
  }

  const handleStatusChange = async (candidateId, status) => {
    try {
      await updateRequisitionCandidateStatus(id, candidateId, status)
      await load()
    } catch {
      window.alert('Failed to update status')
    }
  }

  const handleSubmit = async (candidateId) => {
    try {
      await submitCandidateToHm(id, candidateId, {})
      await load()
    } catch {
      window.alert('Submit failed')
    }
  }

  const handleOutcome = async (candidateId, outcome) => {
    try {
      await recordHmOutcome(id, candidateId, outcome)
      await load()
    } catch {
      window.alert('Failed to record outcome')
    }
  }

  useEffect(() => {
    const t = searchParams.get('tab')
    if (t) setTab(t)
  }, [searchParams])

  const openAddCandidates = async () => {
    try {
      const data = await getCandidates()
      setAllCandidates(Array.isArray(data) ? data : data?.candidates || [])
      setShowAddCandidates(true)
    } catch {
      setAllCandidates([])
      setShowAddCandidates(true)
    }
  }

  const handleAddCandidates = async () => {
    if (!selectedCandidateIds.length) return
    try {
      await addCandidatesToRequisition(id, selectedCandidateIds)
      setShowAddCandidates(false)
      setSelectedCandidateIds([])
      await load()
    } catch {
      window.alert('Failed to add candidates')
    }
  }

  const canEditIntake = canWrite || isHiringManager
  const canWritePipeline = canWrite || isHiringManager

  if (loading) {
    return (
      <div className="flex justify-center py-24">
        <Loader2 className="w-8 h-8 animate-spin text-brand-500" />
      </div>
    )
  }

  if (!req) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center">
        <p className="text-slate-500">Requisition not found</p>
        <Link to="/requisitions" className="text-brand-600 text-sm font-semibold mt-2 inline-block">Back</Link>
      </div>
    )
  }

  const criteria = req.calibrated_criteria_json || {}

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {!canWrite && !isHiringManager && <ViewerReadOnlyBanner />}

      <button
        type="button"
        onClick={() => navigate(isHiringManager ? '/requisitions' : '/requisitions')}
        className="inline-flex items-center gap-1 text-sm font-semibold text-brand-600 mb-4 hover:text-brand-800"
      >
        <ArrowLeft className="w-4 h-4" />
        All requisitions
      </button>

      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-extrabold text-brand-900 tracking-tight">{req.title}</h1>
          <p className="text-sm text-slate-500 mt-1 capitalize">
            {req.status?.replace(/_/g, ' ')}
            {req.client_name ? ` · ${req.client_name}` : ''}
            {req.location ? ` · ${req.location}` : ''}
          </p>
          {req.intake_gate_warning && (
            <p className="mt-2 text-sm text-amber-700 bg-amber-50 ring-1 ring-amber-200 rounded-xl px-3 py-2">
              {req.intake_gate_warning}
            </p>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          {canWrite && tab === 'intake' && (
            <Button onClick={saveIntake} disabled={saving}>Save intake</Button>
          )}
          {canWrite && (
            <Button variant="secondary" onClick={handleCalibrate} disabled={saving}>
              <Sparkles className="w-4 h-4" />
              {REQUISITIONS.calibrateCta}
            </Button>
          )}
          {isHiringManager && req.intake_status === 'pending_hm' && (
            <>
              <Button onClick={() => handleHmApproval(true)} disabled={saving}>
                <CheckCircle2 className="w-4 h-4" />
                {REQUISITIONS.approveIntakeCta}
              </Button>
              <Button variant="ghost" onClick={() => handleHmApproval(false)} disabled={saving}>
                {REQUISITIONS.requestChangesCta}
              </Button>
            </>
          )}
          {canWrite && (
            <Button variant="ghost" onClick={() => navigate(`/requisitions/${id}/handoff`)}>
              HM handoff
            </Button>
          )}
          {canWrite && (
            <Button variant="ghost" onClick={openAddCandidates}>
              Add candidates
            </Button>
          )}
          {canWrite && (
            <Button variant="ghost" onClick={() => navigate(`/analyze?requisition_id=${id}`)}>
              Screen candidate
            </Button>
          )}
        </div>
      </div>

      <div className="flex gap-1 mb-6 p-1 bg-brand-50/80 rounded-xl ring-1 ring-brand-100 w-fit flex-wrap">
        {TABS.map(({ id: tabId, label, icon: Icon }) => (
          <button
            key={tabId}
            type="button"
            onClick={() => setTab(tabId)}
            className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-semibold transition-colors ${
              tab === tabId ? 'bg-white text-brand-800 shadow-sm' : 'text-slate-600 hover:text-brand-700'
            }`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      {tab === 'overview' && (
        <Card className="p-6 space-y-4">
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
          <div className="pt-4 border-t border-brand-50">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">JD preview</p>
            <p className="text-sm text-slate-600 whitespace-pre-wrap line-clamp-6">{req.jd_text}</p>
          </div>
        </Card>
      )}

      {tab === 'intake' && (
        <Card className="p-6">
          <IntakeForm intake={intake} onChange={setIntake} readOnly={!canEditIntake} />
        </Card>
      )}

      {tab === 'criteria' && (
        <Card className="p-6 space-y-4">
          {req.is_calibrated ? (
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
          ) : (
            <p className="text-slate-500 text-sm">{REQUISITIONS.notCalibratedWarning}</p>
          )}
          {criteriaVersions.length > 0 && (
            <div className="pt-4 border-t border-brand-50">
              <p className="text-xs font-semibold text-slate-500 uppercase mb-2">Version history</p>
              <ul className="space-y-1 text-sm text-slate-600">
                {criteriaVersions.map((v) => (
                  <li key={v.id}>v{v.version} — {v.source} ({v.created_at ? new Date(v.created_at).toLocaleDateString() : ''})</li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      )}

      {tab === 'pipeline' && (
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
                      onStatusChange={handleStatusChange}
                      onSubmit={handleSubmit}
                      onOutcome={handleOutcome}
                      canWritePipeline={canWritePipeline}
                      isHm={isHiringManager}
                    />
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {showAddCandidates && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
          <Card className="w-full max-w-lg max-h-[80vh] overflow-hidden flex flex-col p-5">
            <h3 className="font-bold text-brand-900 mb-3">Add candidates to pipeline</h3>
            <div className="overflow-y-auto flex-1 space-y-2 mb-4">
              {allCandidates.length === 0 ? (
                <p className="text-sm text-slate-500">No candidates in your tenant yet.</p>
              ) : (
                allCandidates.map((c) => (
                  <label key={c.id} className="flex items-center gap-2 text-sm p-2 rounded-lg hover:bg-brand-50">
                    <input
                      type="checkbox"
                      checked={selectedCandidateIds.includes(c.id)}
                      onChange={(e) => {
                        setSelectedCandidateIds((prev) =>
                          e.target.checked ? [...prev, c.id] : prev.filter((x) => x !== c.id),
                        )
                      }}
                    />
                    <span>{c.name || c.email || `Candidate #${c.id}`}</span>
                  </label>
                ))
              )}
            </div>
            <div className="flex gap-2 justify-end">
              <Button variant="ghost" onClick={() => setShowAddCandidates(false)}>Cancel</Button>
              <Button onClick={handleAddCandidates} disabled={!selectedCandidateIds.length}>Add</Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}
