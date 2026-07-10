import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Mic, Loader2, Phone, Brain, Target,
  Clock, Zap, CheckCircle2, ChevronDown, ChevronUp,
  AlertTriangle, X,
} from 'lucide-react'
import {
  getCandidates, getTemplates, getNarrative, getScreeningResult,
  createInterviewSession, rescheduleVoiceCall, getNextAvailableSlot,
} from '../lib/api'
import { ModalOverlay } from './motion'
import { Button, Badge, Card, SegmentedControl, SearchSelect, FloatingInput, ScheduleDateTimePicker } from './ui'
import { INTERVIEW } from '../lib/uxLabels'
import { DEPTH_DEFAULT_MINUTES } from '../lib/interviewHubUtils'
import { isKitPending } from '../lib/enrichmentUtils'
import {
  localDatetimeToUtcIso,
  utcIsoToLocalDatetime,
  isLocalDatetimeInPast,
  localDatetimeFromParts,
  defaultScheduleParts,
} from '../lib/datetimeUtils'

const DEPTH_OPTIONS = [
  {
    value: 'quick',
    label: INTERVIEW.quick,
    duration: '3–5 min',
    description: 'Pre-set questions from the role, pass/fail signal',
    icon: Phone,
    activeRing: 'ring-blue-500 bg-blue-50 dark:bg-blue-950/30',
    iconBg: 'bg-blue-100 text-blue-600',
  },
  {
    value: 'standard',
    label: INTERVIEW.standard,
    duration: '10–15 min',
    description: 'AI-generated questions and scorecard',
    icon: Brain,
    activeRing: 'ring-brand-500 bg-brand-50 dark:bg-brand-950/30',
    iconBg: 'bg-brand-100 text-brand-600',
  },
  {
    value: 'deep',
    label: INTERVIEW.deep,
    duration: '20–30 min',
    description: 'Full evaluation with fit verification',
    icon: Target,
    activeRing: 'ring-amber-500 bg-amber-50 dark:bg-amber-950/30',
    iconBg: 'bg-amber-100 text-amber-600',
  },
]

const FOCUS_AREAS = ['Technical', 'Behavioral', 'Communication', 'Cultural', 'Motivation']

function ModalShell({ onClose, title, subtitle, children, footer }) {
  return (
    <ModalOverlay isOpen onClose={onClose} ariaLabel={title}>
      <div className="relative w-full max-w-lg panel-surface rounded-3xl shadow-2xl overflow-hidden max-h-[90vh] flex flex-col">
        <div className="shrink-0 px-6 py-5 border-b border-brand-100 dark:border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-brand-600 to-brand-400 flex items-center justify-center shrink-0">
              <Mic className="w-5 h-5 text-white" />
            </div>
            <div className="min-w-0">
              <h2 className="text-lg font-bold text-brand-900 dark:text-dark-text-primary truncate">{title}</h2>
              {subtitle && <p className="text-xs text-slate-500 dark:text-dark-text-secondary">{subtitle}</p>}
            </div>
          </div>
          <button type="button" onClick={onClose} aria-label="Close dialog" className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-dark-card-elevated text-slate-400">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="flex-1 min-h-0 overflow-y-auto">{children}</div>
        {footer && (
          <div className="shrink-0 px-6 py-4 border-t border-brand-100 dark:border-white/10 bg-white/95 dark:bg-dark-card/95 backdrop-blur-sm">
            {footer}
          </div>
        )}
      </div>
    </ModalOverlay>
  )
}

function ReschedulePanel({ editSession, onClose, onSuccess }) {
  const [phoneNumber, setPhoneNumber] = useState(editSession?.phone_number || '')
  const [scheduledAt, setScheduledAt] = useState(utcIsoToLocalDatetime(editSession?.scheduled_at))
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!phoneNumber.trim()) {
      setError('Enter a phone number for this call.')
      return
    }
    if (scheduledAt && isLocalDatetimeInPast(scheduledAt)) {
      setError('Choose a future date and time.')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      await rescheduleVoiceCall(editSession.id, {
        phone_number: phoneNumber.trim(),
        scheduled_at: scheduledAt ? localDatetimeToUtcIso(scheduledAt) : null,
      })
      setSuccess(true)
      setTimeout(() => onSuccess?.(), 1200)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to reschedule')
    } finally {
      setSubmitting(false)
    }
  }

  if (success) {
    return (
      <ModalShell onClose={onClose} title={INTERVIEW.rescheduleCall} subtitle="Updated successfully">
        <div className="p-8 text-center">
          <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
          <p className="text-sm font-medium text-slate-600">Call rescheduled.</p>
        </div>
      </ModalShell>
    )
  }

  return (
    <ModalShell
      onClose={onClose}
      title={INTERVIEW.rescheduleCall}
      subtitle="Update phone or schedule time"
      footer={
        <div className="flex justify-end gap-3">
          <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
          <Button loading={submitting} onClick={handleSubmit}>Save schedule</Button>
        </div>
      }
    >
      <form onSubmit={handleSubmit} className="p-6 space-y-4">
        {error && (
          <Card className="p-3 flex gap-2 bg-red-50 ring-red-200">
            <AlertTriangle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
            <p className="text-sm text-red-700">{error}</p>
          </Card>
        )}
        <FloatingInput
          label="Phone number"
          type="tel"
          value={phoneNumber}
          onChange={setPhoneNumber}
          placeholder="+14155551234"
        />
        <ScheduleDateTimePicker
          value={scheduledAt}
          onChange={setScheduledAt}
          allowClear
        />
        <p className="text-xs text-slate-400">Clear the schedule to call as soon as possible.</p>
      </form>
    </ModalShell>
  )
}

export default function InterviewInitiateModal({
  onClose,
  onSuccess,
  initialCandidateId = '',
  initialJdId = '',
  initialPhone = '',
  initialDepth = 'standard',
  lockDepth = false,
  screeningResultId = null,
  editSession = null,
  preselectedCandidate = null,
}) {
  if (editSession) {
    return <ReschedulePanel editSession={editSession} onClose={onClose} onSuccess={onSuccess} />
  }

  const prefillCandidateId = initialCandidateId || preselectedCandidate?.id || ''
  const prefillPhone = initialPhone || preselectedCandidate?.phone || preselectedCandidate?.contact_info?.phone || ''

  return (
    <CreateWizard
      onClose={onClose}
      onSuccess={onSuccess}
      initialCandidateId={String(prefillCandidateId || '')}
      initialJdId={String(initialJdId || '')}
      initialPhone={prefillPhone}
      initialDepth={initialDepth}
      lockDepth={lockDepth}
      screeningResultId={screeningResultId}
    />
  )
}

function CreateWizard({
  onClose, onSuccess,
  initialCandidateId, initialJdId, initialPhone,
  initialDepth, lockDepth, screeningResultId,
}) {
  const [step, setStep] = useState(1)
  const [candidates, setCandidates] = useState([])
  const [templates, setTemplates] = useState([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const [advancedOpen, setAdvancedOpen] = useState(false)
  const [contextHint, setContextHint] = useState(null)

  const [depth, setDepth] = useState(initialDepth || 'standard')
  const [candidateId, setCandidateId] = useState(initialCandidateId)
  const [jdId, setJdId] = useState(initialJdId)
  const [phoneNumber, setPhoneNumber] = useState(initialPhone)
  const [durationMinutes, setDurationMinutes] = useState(DEPTH_DEFAULT_MINUTES[initialDepth || 'standard'])
  const [selectedFocusAreas, setSelectedFocusAreas] = useState(['Technical', 'Communication'])
  const [scheduleType, setScheduleType] = useState('now')
  const [scheduledAt, setScheduledAt] = useState('')
  const [interviewKitStatus, setInterviewKitStatus] = useState(null)

  const selectedCandidate = candidates.find((c) => String(c.id) === String(candidateId))
  const selectedJd = templates.find((t) => String(t.id) === String(jdId))

  useEffect(() => {
    async function load() {
      try {
        const [cands, tpls] = await Promise.all([
          getCandidates({ limit: 200 }).then((d) => (Array.isArray(d) ? d : d.candidates || [])),
          getTemplates().then((d) => (Array.isArray(d) ? d : [])),
        ])
        setCandidates(cands)
        setTemplates(tpls)
      } catch {
        setError('Failed to load candidates and roles')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  useEffect(() => {
    if (!screeningResultId) return
    let cancelled = false
    let timerId = null
    let delayMs = 10000

    const poll = async () => {
      if (cancelled) return
      try {
        const data = await getNarrative(screeningResultId)
        if (cancelled) return
        const vs = data.interview_kit_status || null
        setInterviewKitStatus(vs)
        if (vs === 'ready' || vs === 'fallback' || vs === 'skipped' || vs === 'failed') return
        delayMs = 10000
      } catch (err) {
        if (err?.response?.status === 429) {
          const retryAfter = parseInt(err?.response?.headers?.['retry-after'] || '10', 10)
          delayMs = Math.min(Math.max(retryAfter * 1000, 10000), 30000)
        }
      }
      if (!cancelled) timerId = setTimeout(poll, delayMs)
    }

    poll()
    return () => {
      cancelled = true
      if (timerId) clearTimeout(timerId)
    }
  }, [screeningResultId])

  useEffect(() => {
    setDurationMinutes(DEPTH_DEFAULT_MINUTES[depth] || 15)
  }, [depth])

  const loadCandidateContext = useCallback(async (id) => {
    if (!id) return
    const cand = candidates.find((c) => String(c.id) === String(id))
    if (cand?.phone && !phoneNumber) setPhoneNumber(cand.phone)
    if (cand?.latest_result_id && !initialJdId) {
      try {
        const result = await getScreeningResult(cand.latest_result_id)
        if (result?.role_template_id) {
          setJdId(String(result.role_template_id))
          setContextHint({
            jdName: result.jd_name,
            fitScore: result.fit_score,
          })
        }
      } catch { /* ignore */ }
    }
  }, [candidates, initialJdId, phoneNumber])

  useEffect(() => {
    if (candidateId && candidates.length) loadCandidateContext(candidateId)
  }, [candidateId, candidates.length, loadCandidateContext])

  useEffect(() => {
    if (scheduleType !== 'later' || scheduledAt) return
    getNextAvailableSlot()
      .then((data) => {
        if (data?.suggested_at) {
          setScheduledAt(utcIsoToLocalDatetime(data.suggested_at))
        } else {
          setScheduledAt(localDatetimeFromParts(defaultScheduleParts()))
        }
      })
      .catch(() => {
        setScheduledAt(localDatetimeFromParts(defaultScheduleParts()))
      })
  }, [scheduleType, scheduledAt])

  function toggleFocusArea(area) {
    setSelectedFocusAreas((prev) =>
      prev.includes(area) ? prev.filter((a) => a !== area) : [...prev, area],
    )
  }

  const kitBlocked = screeningResultId && isKitPending({ interview_kit_status: interviewKitStatus })

  const step1Valid = candidateId && jdId
  const step2Valid = scheduleType === 'now' || (
    scheduleType === 'later' && scheduledAt && !isLocalDatetimeInPast(scheduledAt)
  )
  const phoneValid = phoneNumber.trim() || selectedCandidate?.phone

  async function handleSubmit() {
    if (!step1Valid || !step2Valid || !phoneValid) return
    if (scheduleType === 'later' && isLocalDatetimeInPast(scheduledAt)) {
      setError('Choose a future date and time.')
      return
    }
    setSubmitting(true)
    setError(null)
    const scheduledAtUtc = scheduleType === 'later' && scheduledAt
      ? localDatetimeToUtcIso(scheduledAt)
      : null
    try {
      await createInterviewSession({
        candidate_id: parseInt(candidateId, 10),
        jd_id: parseInt(jdId, 10),
        depth,
        screening_result_id: screeningResultId || undefined,
        phone_number: phoneNumber.trim() || selectedCandidate?.phone || '',
        scheduled_at: scheduledAtUtc,
        focus_areas: depth === 'quick' ? undefined : selectedFocusAreas,
        duration_minutes: depth === 'quick' ? undefined : durationMinutes,
      })
      onSuccess?.()
      onClose()
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to start screen call')
    } finally {
      setSubmitting(false)
    }
  }

  const footer = step === 1 ? (
    <div className="flex justify-end gap-3">
      <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
      <Button disabled={!step1Valid || loading} onClick={() => setStep(2)}>Continue</Button>
    </div>
  ) : (
    <div className="flex justify-between gap-3">
      <Button type="button" variant="ghost" onClick={() => setStep(1)}>Back</Button>
      <Button
        loading={submitting}
        disabled={submitting || !step2Valid || !phoneValid || kitBlocked}
        onClick={handleSubmit}
      >
        {scheduleType === 'later' ? 'Schedule call' : 'Start call'}
      </Button>
    </div>
  )

  return (
    <ModalShell
      onClose={onClose}
      title={INTERVIEW.newScreenCall}
      subtitle={step === 1 ? 'Step 1 — Who & role' : 'Step 2 — Call setup'}
      footer={!loading ? footer : null}
    >
      <div className="p-6 space-y-5">
        <div className="flex items-center gap-2">
          <Badge color={step === 1 ? 'brand' : 'slate'}>1. Candidate</Badge>
          <span className="text-slate-300">→</span>
          <Badge color={step === 2 ? 'brand' : 'slate'}>2. Call</Badge>
        </div>

        {screeningResultId && interviewKitStatus && (
          <Card className={`p-3 text-xs font-semibold ${
            interviewKitStatus === 'ready'
              ? 'bg-emerald-50 ring-emerald-200 text-emerald-800'
              : kitBlocked
                ? 'bg-brand-50 ring-brand-200 text-brand-800'
                : 'bg-slate-50 ring-slate-200 text-slate-600'
          }`}>
            {interviewKitStatus === 'ready'
              ? 'Interview kit ready — same questions as Live Screen'
              : kitBlocked
                ? 'Preparing interview kit…'
                : interviewKitStatus === 'fallback'
                  ? 'Fallback kit — call allowed with caution'
                  : `Kit status: ${interviewKitStatus}`}
          </Card>
        )}

        {error && (
          <Card className="p-3 flex gap-2 bg-red-50 ring-red-200">
            <AlertTriangle className="w-4 h-4 text-red-500 shrink-0" />
            <p className="text-sm text-red-700">{typeof error === 'string' ? error : JSON.stringify(error)}</p>
          </Card>
        )}

        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="w-7 h-7 text-brand-600 animate-spin" />
          </div>
        ) : step === 1 ? (
          <>
            <SearchSelect
              label="Candidate"
              required
              placeholder="Search by name or email…"
              options={candidates}
              value={candidateId}
              onChange={(id, cand) => {
                setCandidateId(String(id))
                if (cand?.phone) setPhoneNumber(cand.phone)
                setContextHint(null)
                if (!initialJdId) setJdId('')
              }}
              getOptionValue={(c) => c.id}
              getOptionLabel={(c) => c.name || c.email || `Candidate #${c.id}`}
              renderOption={(c) => (
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-slate-800 dark:text-dark-text-primary truncate">
                    {c.name || c.email}
                  </p>
                  <p className="text-xs text-slate-500 truncate">
                    {[c.current_role, c.best_score != null ? `${c.best_score}% fit` : null].filter(Boolean).join(' · ') || c.email}
                  </p>
                </div>
              )}
            />

            {selectedCandidate && (
              <Card className="p-3 bg-brand-50/50 ring-brand-100 flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-gradient-to-br from-brand-600 to-brand-400 flex items-center justify-center text-white text-sm font-bold shrink-0">
                  {(selectedCandidate.name || selectedCandidate.email || '?')[0].toUpperCase()}
                </div>
                <div className="min-w-0 text-xs">
                  <p className="font-semibold text-brand-900 truncate">{selectedCandidate.name || selectedCandidate.email}</p>
                  <p className="text-slate-500">
                    {selectedCandidate.phone ? `Phone on file · ${selectedCandidate.phone}` : 'No phone on profile — add in step 2'}
                  </p>
                </div>
              </Card>
            )}

            <SearchSelect
              label="Role / job description"
              required
              placeholder="Select role…"
              options={templates}
              value={jdId}
              onChange={(id) => setJdId(String(id))}
              getOptionValue={(t) => t.id}
              getOptionLabel={(t) => t.name}
            />

            {contextHint && (
              <p className="text-xs text-brand-600 font-medium">
                Suggested from latest screen
                {contextHint.jdName ? `: ${contextHint.jdName}` : ''}
                {contextHint.fitScore != null ? ` (${contextHint.fitScore}% fit)` : ''}
              </p>
            )}
          </>
        ) : (
          <>
            {(selectedCandidate || selectedJd) && (
              <Card className="p-3 text-sm">
                <p className="font-semibold text-brand-900">{selectedCandidate?.name || selectedCandidate?.email}</p>
                <p className="text-xs text-slate-500 mt-0.5">{selectedJd?.name || 'Role selected'}</p>
              </Card>
            )}

            {!lockDepth && (
              <div>
                <label className="block text-sm font-semibold text-slate-700 dark:text-dark-text-secondary mb-2">Call depth</label>
                <div className="grid grid-cols-3 gap-2">
                  {DEPTH_OPTIONS.map((opt) => {
                    const Icon = opt.icon
                    const active = depth === opt.value
                    return (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => setDepth(opt.value)}
                        className={`p-2.5 rounded-xl ring-2 transition-all text-left ${
                          active ? opt.activeRing : 'ring-slate-200 dark:ring-white/10 bg-white dark:bg-dark-card hover:ring-slate-300'
                        }`}
                      >
                        <div className={`w-7 h-7 rounded-lg flex items-center justify-center mb-1.5 ${opt.iconBg}`}>
                          <Icon className="w-3.5 h-3.5" />
                        </div>
                        <p className="text-[11px] font-bold text-slate-800 dark:text-dark-text-primary leading-tight">{opt.label}</p>
                        <p className="text-[10px] text-slate-500 flex items-center gap-0.5 mt-0.5">
                          <Clock className="w-2.5 h-2.5" />{opt.duration}
                        </p>
                      </button>
                    )
                  })}
                </div>
                <p className="text-xs text-slate-400 mt-1.5">{DEPTH_OPTIONS.find((o) => o.value === depth)?.description}</p>
              </div>
            )}

            <FloatingInput
              label="Phone (uses profile if blank)"
              type="tel"
              value={phoneNumber}
              onChange={setPhoneNumber}
            />

            <div>
              <label className="block text-sm font-semibold text-slate-700 dark:text-dark-text-secondary mb-2">When</label>
              <SegmentedControl
                options={[
                  { label: 'Call now', value: 'now' },
                  { label: 'Schedule', value: 'later' },
                ]}
                value={scheduleType}
                onChange={setScheduleType}
                className="w-full flex"
              />
              {scheduleType === 'later' && (
                <div className="mt-3">
                  <ScheduleDateTimePicker
                    value={scheduledAt}
                    onChange={setScheduledAt}
                    required
                  />
                </div>
              )}
            </div>

            {depth !== 'quick' && (
              <div>
                <button
                  type="button"
                  onClick={() => setAdvancedOpen((v) => !v)}
                  className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-brand-700"
                >
                  {advancedOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  Advanced options
                </button>
                {advancedOpen && (
                  <div className="mt-3 space-y-3 pl-1">
                    <FloatingInput
                      label="Duration (minutes)"
                      type="number"
                      value={String(durationMinutes)}
                      onChange={(v) => setDurationMinutes(parseInt(v, 10) || DEPTH_DEFAULT_MINUTES[depth])}
                    />
                    <div>
                      <span className="text-xs font-semibold text-slate-600 block mb-2">Focus areas</span>
                      <div className="flex flex-wrap gap-2">
                        {FOCUS_AREAS.map((area) => {
                          const active = selectedFocusAreas.includes(area)
                          return (
                            <button
                              key={area}
                              type="button"
                              onClick={() => toggleFocusArea(area)}
                              className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all ${
                                active ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-600 dark:bg-dark-card-elevated'
                              }`}
                            >
                              {area}
                            </button>
                          )
                        })}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </ModalShell>
  )
}
