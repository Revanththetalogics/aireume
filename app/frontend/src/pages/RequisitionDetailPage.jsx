import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate, Link, useSearchParams } from 'react-router-dom'
import {
  ArrowLeft, Briefcase, Loader2, Users, CheckCircle2, Sparkles,
  ListChecks, Columns3, Wand2, UserPlus, X,
} from 'lucide-react'
import {
  getRequisition,
  getRequisitionPipeline,
  updateRequisitionIntake,
  suggestRequisitionIntake,
  calibrateRequisition,
  hmApproveRequisition,
  updateRequisitionCandidateStatus,
  submitCandidateToHm,
  recordHmOutcome,
  getRequisitionAnalytics,
  addCandidatesToRequisition,
  getCandidates,
  getRequisitionCriteriaVersions,
  updateRequisitionCriteria,
  updateRequisition,
  checkRequisitionIntakeGate,
  getTeamMembers,
  inviteTeamMember,
  requestRequisitionHm,
  approveRequisitionHmRequest,
  rejectRequisitionHmRequest,
} from '../lib/api'
import { PIPELINE_STAGES } from '../lib/constants'
import { Button, Card } from '../components/ui'
import { ScoreProgression } from '../components/patterns/InterviewOutcomeBadges'
import usePermissions from '../hooks/usePermissions'
import { ViewerReadOnlyBanner } from '../components/RequireWriteAccess'
import { REQUISITIONS } from '../lib/uxLabels'
import { showSuccess, showError } from '../lib/toast'
import { useAuth } from '../contexts/AuthContext'

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

function HmRequestModal({ onClose, onSubmitted }) {
  const [email, setEmail] = useState('')
  const [notes, setNotes] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async () => {
    if (!email.trim()) return
    setLoading(true)
    setError('')
    try {
      await onSubmitted({ email: email.trim(), notes: notes.trim() || null })
    } catch (err) {
      setError(err.response?.data?.detail || 'Request failed')
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl ring-1 ring-brand-100 shadow-brand-xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-brand-900">{REQUISITIONS.hmRequestTitle}</h3>
          <button type="button" onClick={onClose} aria-label="Close" className="p-1 hover:bg-brand-50 rounded-lg">
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>
        <p className="text-sm text-slate-500 mb-4">{REQUISITIONS.hmRequestHint}</p>
        <label className="block text-sm mb-3">
          <span className="font-semibold text-slate-700">HM email</span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="hiring.manager@company.com"
            className="mt-1 w-full rounded-xl border border-brand-200 px-3 py-2 text-sm"
            autoFocus
          />
        </label>
        <label className="block text-sm mb-4">
          <span className="font-semibold text-slate-700">Notes for admin (optional)</span>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            placeholder="e.g. Finance director for this FP&A opening"
            className="mt-1 w-full rounded-xl border border-brand-200 px-3 py-2 text-sm resize-none"
          />
        </label>
        {error && <p className="text-sm text-red-600 mb-3">{error}</p>}
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSubmit} disabled={loading || !email.trim()}>
            {loading ? 'Submitting…' : REQUISITIONS.hmRequestCta}
          </Button>
        </div>
      </div>
    </div>
  )
}

function HmInviteModal({ onClose, onInvited }) {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleInvite = async () => {
    if (!email.trim()) return
    setLoading(true)
    setError('')
    try {
      const data = await inviteTeamMember(email.trim(), 'hiring_manager')
      await onInvited(data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Invitation failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl ring-1 ring-brand-100 shadow-brand-xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-brand-900">{REQUISITIONS.hmInviteTitle}</h3>
          <button type="button" onClick={onClose} aria-label="Close" className="p-1 hover:bg-brand-50 rounded-lg">
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>
        <p className="text-sm text-slate-500 mb-4">{REQUISITIONS.hmInviteHint}</p>
        <label className="block text-sm mb-4">
          <span className="font-semibold text-slate-700">Email</span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="hiring.manager@company.com"
            className="mt-1 w-full rounded-xl border border-brand-200 px-3 py-2 text-sm"
            autoFocus
          />
        </label>
        {error && <p className="text-sm text-red-600 mb-3">{error}</p>}
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button onClick={handleInvite} disabled={loading || !email.trim()}>
            {loading ? 'Inviting…' : REQUISITIONS.hmInviteCta}
          </Button>
        </div>
      </div>
    </div>
  )
}

function CriteriaVersionDiff({ versions }) {
  if (versions.length < 2) return null
  const [newer, older] = versions
  const newerCriteria = newer.criteria_json || {}
  const olderCriteria = older.criteria_json || {}
  const listKeys = ['must_haves', 'good_to_haves', 'deal_breakers']

  const diffFor = (key) => {
    const a = new Set(olderCriteria[key] || [])
    const b = new Set(newerCriteria[key] || [])
    return {
      added: [...b].filter((x) => !a.has(x)),
      removed: [...a].filter((x) => !b.has(x)),
    }
  }

  const hasChanges = listKeys.some((k) => {
    const d = diffFor(k)
    return d.added.length > 0 || d.removed.length > 0
  })
  if (!hasChanges) return null

  return (
    <div className="rounded-xl bg-brand-50/60 ring-1 ring-brand-100 p-4 space-y-3">
      <p className="text-xs font-semibold text-slate-500 uppercase">
        Changes v{older.version} → v{newer.version}
      </p>
      {listKeys.map((key) => {
        const { added, removed } = diffFor(key)
        if (!added.length && !removed.length) return null
        return (
          <div key={key} className="text-sm">
            <p className="font-semibold text-slate-700 capitalize">{key.replace(/_/g, ' ')}</p>
            {added.map((item) => (
              <p key={`add-${item}`} className="text-emerald-700">+ {item}</p>
            ))}
            {removed.map((item) => (
              <p key={`rem-${item}`} className="text-red-600">− {item}</p>
            ))}
          </div>
        )
      })}
    </div>
  )
}

function parseScoringWeights(sw) {
  if (!sw) return { resume: 40, interview: 60 }
  try {
    const obj = typeof sw === 'string' ? JSON.parse(sw) : sw
    return {
      resume: Math.round((obj.resume_weight ?? 0.4) * 100),
      interview: Math.round((obj.interview_weight ?? 0.6) * 100),
    }
  } catch {
    return { resume: 40, interview: 60 }
  }
}

function CriteriaEditForm({ criteria, onChange, readOnly }) {
  const fields = [
    { key: 'must_haves', label: 'Must-haves (one per line)', rows: 6 },
    { key: 'good_to_haves', label: 'Good-to-haves (one per line)', rows: 4 },
    { key: 'deal_breakers', label: 'Deal-breakers (one per line)', rows: 2 },
  ]
  const getValue = (key) => {
    const v = criteria[key]
    if (Array.isArray(v)) return v.join('\n')
    return v || ''
  }
  const setValue = (key, raw) => {
    onChange({
      ...criteria,
      [key]: raw.split('\n').map((s) => s.trim()).filter(Boolean),
    })
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
            className="mt-1 w-full rounded-xl border border-brand-200 px-3 py-2 text-sm resize-none disabled:opacity-60 font-mono"
          />
        </label>
      ))}
    </div>
  )
}

function IntakeWorkflowBar({ intakeGate, req }) {
  const intakeDone = intakeGate?.intake_has_minimum_content && intakeGate?.hm_assigned
  const canScreen = intakeGate?.intake_screening_ready && !intakeGate?.blocks
  const refined = (req?.current_criteria_version || 0) > 1
  const steps = [
    {
      key: 'intake',
      label: REQUISITIONS.intakeStepIntake,
      done: intakeDone,
      active: !intakeDone,
    },
    {
      key: 'screen',
      label: REQUISITIONS.intakeStepScreen,
      done: canScreen,
      active: intakeDone && !canScreen,
    },
    {
      key: 'refine',
      label: REQUISITIONS.intakeStepRefine,
      done: refined,
      active: canScreen && !refined,
    },
  ]
  return (
    <div className="flex flex-wrap gap-2 mb-4">
      {steps.map((step) => (
        <span
          key={step.key}
          className={`inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-full ring-1 ${
            step.done
              ? 'bg-emerald-50 text-emerald-800 ring-emerald-200'
              : step.active
                ? 'bg-brand-50 text-brand-800 ring-brand-200'
                : 'bg-slate-50 text-slate-500 ring-slate-200'
          }`}
        >
          {step.done ? <CheckCircle2 className="w-3.5 h-3.5" /> : null}
          {step.label}
          {step.key === 'screen' && canScreen && !intakeGate?.intake_approved && intakeGate?.requires_hm_approval === false && (
            <span className="text-[10px] font-normal opacity-70">(approval optional)</span>
          )}
        </span>
      ))}
    </div>
  )
}

function IntakeForm({ intake, onChange, readOnly, onSuggest, suggesting }) {
  const fields = [
    { key: 'screen_focus_topics', label: 'What should the screen focus on? (one topic per line)', rows: 4, list: true },
    { key: 'must_haves', label: 'Must-have skills (one per line)', rows: 4 },
    { key: 'good_to_haves', label: 'Nice-to-have skills (one per line)', rows: 3 },
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
    const listKeys = ['must_haves', 'good_to_haves', 'deal_breakers', 'screen_focus_topics']
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
      {!readOnly && onSuggest && (
        <div className="rounded-xl bg-brand-50/80 ring-1 ring-brand-100 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-brand-900">Start from the job description</p>
            <p className="text-xs text-slate-600 mt-0.5">{REQUISITIONS.intakeSaveHint}</p>
          </div>
          <Button type="button" variant="secondary" onClick={onSuggest} disabled={suggesting}>
            {suggesting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wand2 className="w-4 h-4" />}
            {REQUISITIONS.intakeSuggestCta}
          </Button>
        </div>
      )}
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
  const { user } = useAuth()
  const { canWrite, isHiringManager, isAdmin } = usePermissions()
  const [req, setReq] = useState(null)
  const [intake, setIntake] = useState({})
  const [pipeline, setPipeline] = useState({})
  const [analytics, setAnalytics] = useState(null)
  const [criteriaVersions, setCriteriaVersions] = useState([])
  const [editCriteria, setEditCriteria] = useState(null)
  const [pipelineSync, setPipelineSync] = useState(null)
  const [tab, setTab] = useState(searchParams.get('tab') || 'overview')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [showAddCandidates, setShowAddCandidates] = useState(false)
  const [allCandidates, setAllCandidates] = useState([])
  const [selectedCandidateIds, setSelectedCandidateIds] = useState([])
  const [resumeWeight, setResumeWeight] = useState(40)
  const [interviewWeight, setInterviewWeight] = useState(60)
  const [savingWeights, setSavingWeights] = useState(false)
  const [intakeGate, setIntakeGate] = useState(null)
  const [savedIntakeSnapshot, setSavedIntakeSnapshot] = useState('')
  const [intakeSavedAt, setIntakeSavedAt] = useState(null)
  const [suggestingIntake, setSuggestingIntake] = useState(false)
  const [teamMembers, setTeamMembers] = useState([])
  const [hmSelectId, setHmSelectId] = useState('')
  const [savingHm, setSavingHm] = useState(false)
  const [showHmInvite, setShowHmInvite] = useState(false)
  const [showHmRequest, setShowHmRequest] = useState(false)

  const hmCandidates = teamMembers.filter(
    (m) => m.role === 'hiring_manager' || m.role === 'admin' || m.role === 'recruiter',
  )

  const intakeDirty = savedIntakeSnapshot !== JSON.stringify(intake || {})

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [r, pipe, stats, versions, gate] = await Promise.all([
        getRequisition(id),
        getRequisitionPipeline(id),
        getRequisitionAnalytics(id).catch(() => null),
        getRequisitionCriteriaVersions(id).catch(() => []),
        checkRequisitionIntakeGate(id).catch(() => null),
      ])
      setReq(r)
      setIntakeGate(gate)
      setHmSelectId(r.primary_hiring_manager_id ? String(r.primary_hiring_manager_id) : '')
      const loadedIntake = r.intake_json || {}
      setIntake(loadedIntake)
      setSavedIntakeSnapshot(JSON.stringify(loadedIntake))
      const weights = parseScoringWeights(r.scoring_weights)
      setResumeWeight(weights.resume)
      setInterviewWeight(weights.interview)
      setPipeline(pipe.pipeline || {})
      setPipelineSync(pipe.sync || null)
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

  const refreshTeamMembers = async () => {
    try {
      const data = await getTeamMembers()
      setTeamMembers(Array.isArray(data) ? data : [])
      return Array.isArray(data) ? data : []
    } catch {
      setTeamMembers([])
      return []
    }
  }

  useEffect(() => {
    if (!canWrite) return
    refreshTeamMembers()
  }, [canWrite])

  const saveHiringManager = async (managerId) => {
    const selectedId = managerId ?? (hmSelectId ? Number(hmSelectId) : null)
    if (!selectedId) return
    setSavingHm(true)
    try {
      const updated = await updateRequisition(id, { primary_hiring_manager_id: selectedId })
      setReq(updated)
      setHmSelectId(String(selectedId))
      const gate = await checkRequisitionIntakeGate(id).catch(() => null)
      setIntakeGate(gate)
      showSuccess('Hiring manager assigned')
    } catch {
      showError('Failed to assign hiring manager')
    } finally {
      setSavingHm(false)
    }
  }

  const assignSelfAsHm = () => {
    if (!user?.id) return
    setHmSelectId(String(user.id))
    saveHiringManager(user.id)
  }

  const handleHmInvited = async (inviteResult) => {
    const members = await refreshTeamMembers()
    const invitedId = inviteResult?.user_id
      || members.find((m) => m.email === inviteResult?.email)?.id
    setShowHmInvite(false)
    if (invitedId) {
      await saveHiringManager(invitedId)
      showSuccess(REQUISITIONS.hmInviteSuccess)
    } else {
      showSuccess('Hiring manager invited — select them from the dropdown and save.')
    }
  }

  const handleHmRequested = async ({ email, notes }) => {
    const updated = await requestRequisitionHm(id, { email, notes })
    setReq(updated)
    const gate = await checkRequisitionIntakeGate(id).catch(() => null)
    setIntakeGate(gate)
    setShowHmRequest(false)
    showSuccess(REQUISITIONS.hmRequestSuccess)
  }

  const handleApproveHmRequest = async () => {
    setSavingHm(true)
    try {
      const updated = await approveRequisitionHmRequest(id)
      setReq(updated)
      setHmSelectId(updated.primary_hiring_manager_id ? String(updated.primary_hiring_manager_id) : '')
      await refreshTeamMembers()
      const gate = await checkRequisitionIntakeGate(id).catch(() => null)
      setIntakeGate(gate)
      showSuccess('Hiring manager approved and assigned')
    } catch {
      showError('Failed to approve HM request')
    } finally {
      setSavingHm(false)
    }
  }

  const handleRejectHmRequest = async () => {
    const notes = window.prompt('Optional reason for rejection:') || null
    setSavingHm(true)
    try {
      const updated = await rejectRequisitionHmRequest(id, notes)
      setReq(updated)
      const gate = await checkRequisitionIntakeGate(id).catch(() => null)
      setIntakeGate(gate)
      showSuccess('HM request rejected')
    } catch {
      showError('Failed to reject HM request')
    } finally {
      setSavingHm(false)
    }
  }

  const focusHmAssignment = () => {
    setTab('overview')
    requestAnimationFrame(() => {
      document.getElementById('hm-assignment')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    })
  }

  const saveHiringWeights = async () => {
    setSavingWeights(true)
    try {
      const updated = await updateRequisition(id, {
        scoring_weights: {
          resume_weight: resumeWeight / 100,
          interview_weight: interviewWeight / 100,
        },
      })
      setReq(updated)
      const weights = parseScoringWeights(updated.scoring_weights)
      setResumeWeight(weights.resume)
      setInterviewWeight(weights.interview)
    } catch {
      window.alert('Failed to save hiring signal weights')
    } finally {
      setSavingWeights(false)
    }
  }

  const saveIntake = async () => {
    setSaving(true)
    try {
      const updated = await updateRequisitionIntake(id, intake, 'pending_hm')
      setReq(updated)
      const saved = updated.intake_json || {}
      setIntake(saved)
      setSavedIntakeSnapshot(JSON.stringify(saved))
      setIntakeSavedAt(Date.now())
      const gate = await checkRequisitionIntakeGate(id).catch(() => null)
      setIntakeGate(gate)
      showSuccess(
        gate?.intake_has_minimum_content
          ? (gate?.blocks && gate?.requires_hm_approval
            ? `${REQUISITIONS.intakeSaved} — HM approval required before screening (tenant policy).`
            : `${REQUISITIONS.intakeSaved} — you can screen candidates. HM approval locks criteria v1.`)
          : `${REQUISITIONS.intakeSaved} — add screen-focus topics or must-haves to unlock screening.`,
      )
    } catch {
      showError('Failed to save intake')
    } finally {
      setSaving(false)
    }
  }

  const suggestIntake = async () => {
    setSuggestingIntake(true)
    try {
      const { intake_json: suggested } = await suggestRequisitionIntake(id)
      setIntake(suggested || {})
      showSuccess(REQUISITIONS.intakeSuggestDone)
    } catch {
      showError('Could not suggest intake from job description')
    } finally {
      setSuggestingIntake(false)
    }
  }

  const handleCalibrate = async () => {
    setSaving(true)
    try {
      const updated = await calibrateRequisition(id)
      setReq(updated)
      setTab('criteria')
      showSuccess('Criteria calibrated — you can screen candidates')
      await load()
    } catch {
      showError('Calibration failed')
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

  const saveCriteria = async () => {
    if (!editCriteria) return
    setSaving(true)
    try {
      const updated = await updateRequisitionCriteria(id, editCriteria)
      setReq(updated)
      setEditCriteria(null)
      await load()
    } catch {
      window.alert('Failed to save criteria')
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
            <div className="mt-2 text-sm text-amber-700 bg-amber-50 ring-1 ring-amber-200 rounded-xl px-3 py-2 flex flex-wrap items-center gap-2">
              <span className="flex-1 min-w-[12rem]">{req.intake_gate_warning}</span>
              {canWrite && !intakeGate?.hm_assigned && (
                <button
                  type="button"
                  onClick={focusHmAssignment}
                  className="shrink-0 text-xs font-semibold text-amber-900 underline hover:no-underline"
                >
                  Assign hiring manager
                </button>
              )}
            </div>
          )}
        </div>
        <div className="flex flex-nowrap items-center gap-2 overflow-x-auto max-w-full pb-1 shrink-0">
          {canWrite && tab === 'intake' && (
            <Button onClick={saveIntake} disabled={saving || !intakeDirty}>
              {saving ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Saving…
                </>
              ) : intakeSavedAt && !intakeDirty ? (
                <>
                  <CheckCircle2 className="w-4 h-4" />
                  Saved
                </>
              ) : (
                'Save intake'
              )}
            </Button>
          )}
          {canWrite && tab === 'intake' && intakeDirty && (
            <span className="text-xs font-semibold text-amber-700 self-center">{REQUISITIONS.intakeUnsaved}</span>
          )}
          {canWrite && (
            <Button variant="secondary" onClick={handleCalibrate} disabled={saving} className="shrink-0 whitespace-nowrap">
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
            <Button
              variant="ghost"
              onClick={() => navigate(`/requisitions/${id}/handoff`)}
              title={REQUISITIONS.hmReviewPackHint}
              className="shrink-0 whitespace-nowrap"
            >
              {REQUISITIONS.hmReviewPackCta}
            </Button>
          )}
          {canWrite && (
            <Button variant="ghost" onClick={openAddCandidates} className="shrink-0 whitespace-nowrap">
              Add candidates
            </Button>
          )}
          {canWrite && (
            <Button
              variant="ghost"
              disabled={intakeGate?.blocks}
              title={intakeGate?.blocks ? (intakeGate.warning || 'Save intake before screening') : undefined}
              className="shrink-0 whitespace-nowrap"
              onClick={() => {
                if (intakeGate?.blocks) {
                  window.alert(intakeGate.warning || 'Save HM intake and calibrate before screening candidates.')
                  return
                }
                navigate(`/analyze?requisition_id=${id}`)
              }}
            >
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
                      <Button size="sm" onClick={handleApproveHmRequest} disabled={savingHm}>
                        {REQUISITIONS.hmRequestApproveCta}
                      </Button>
                      <Button size="sm" variant="ghost" onClick={handleRejectHmRequest} disabled={savingHm}>
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
                    onClick={() => setShowHmRequest(true)}
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
                    onClick={() => setShowHmInvite(true)}
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
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">JD preview</p>
            <p className="text-sm text-slate-600 whitespace-pre-wrap line-clamp-6">{req.jd_text}</p>
          </div>
        </Card>
      )}

      {tab === 'intake' && (
        <Card className="p-6">
          <IntakeWorkflowBar intakeGate={intakeGate} req={req} />
          <IntakeForm
            intake={intake}
            onChange={setIntake}
            readOnly={!canEditIntake}
            onSuggest={canEditIntake ? suggestIntake : null}
            suggesting={suggestingIntake}
          />
        </Card>
      )}

      {tab === 'criteria' && (
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
        </Card>
      )}

      {tab === 'pipeline' && (
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
        </>
      )}

      {showHmRequest && (
        <HmRequestModal
          onClose={() => setShowHmRequest(false)}
          onSubmitted={handleHmRequested}
        />
      )}

      {showHmInvite && (
        <HmInviteModal
          onClose={() => setShowHmInvite(false)}
          onInvited={handleHmInvited}
        />
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
