import { useState, useEffect } from 'react'
import {
  X, Mic, Loader2, User, FileText, Phone, Brain, Target,
  Clock, Zap, CheckCircle2, Globe,
} from 'lucide-react'
import {
  getCandidates, getTemplates,
  scheduleVoiceCall, initiateRecruiterInterview,
} from '../lib/api'

const DEPTH_OPTIONS = [
  {
    value: 'quick',
    label: 'Quick Screen',
    duration: '3–5 min',
    description: 'Pre-set questions from JD, pass/fail result',
    icon: Phone,
    color: 'ring-blue-300 bg-blue-50',
    activeColor: 'ring-blue-500 bg-blue-50',
    iconBg: 'bg-blue-100 text-blue-600',
  },
  {
    value: 'standard',
    label: 'Standard Interview',
    duration: '10–15 min',
    description: 'AI-generated questions, 3-dimension scorecard',
    icon: Brain,
    color: 'ring-purple-300 bg-purple-50',
    activeColor: 'ring-purple-500 bg-purple-50',
    iconBg: 'bg-purple-100 text-purple-600',
  },
  {
    value: 'deep',
    label: 'Deep Assessment',
    duration: '20–30 min',
    description: 'Full evaluation with fitment verification',
    icon: Target,
    color: 'ring-amber-300 bg-amber-50',
    activeColor: 'ring-amber-500 bg-amber-50',
    iconBg: 'bg-amber-100 text-amber-600',
  },
]

const FOCUS_AREAS = [
  'Technical', 'Behavioral', 'Communication', 'Cultural', 'Motivation',
]

// Common timezone options; default to the browser's local timezone
const TIMEZONE_OPTIONS = [
  'UTC',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'Europe/London',
  'Europe/Paris',
  'Europe/Berlin',
  'Asia/Dubai',
  'Asia/Kolkata',
  'Asia/Singapore',
  'Asia/Shanghai',
  'Asia/Tokyo',
  'Australia/Sydney',
]

function getDefaultTimezone() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone
  } catch {
    return 'UTC'
  }
}

// Convert a datetime-local value (interpreted as the chosen timezone) to a UTC ISO string
function toUtcIso(localValue, timezone) {
  if (!localValue) return null
  try {
    const localDate = new Date(localValue) // browser treats it as local TZ, so we ignore its offset
    const parts = localValue.split('T')
    if (parts.length !== 2) return null
    const [datePart, timePart] = parts
    const [year, month, day] = datePart.split('-').map(Number)
    const [hour, minute] = timePart.split(':').map(Number)
    const tzDate = new Date(Date.UTC(year, month - 1, day, hour, minute))
    const offsetMinutes = -tzDate.getTimezoneOffset()
    const targetOffset = getTargetOffsetMinutes(timezone, tzDate)
    const diffMinutes = targetOffset - offsetMinutes
    const utcMs = tzDate.getTime() - diffMinutes * 60 * 1000
    return new Date(utcMs).toISOString()
  } catch {
    return null
  }
}

function getTargetOffsetMinutes(timezone, date) {
  try {
    const formatter = new Intl.DateTimeFormat('en-US', {
      timeZone: timezone,
      timeZoneName: 'shortOffset',
      year: 'numeric',
      month: 'numeric',
      day: 'numeric',
      hour: 'numeric',
      minute: 'numeric',
      second: 'numeric',
    })
    const parts = formatter.formatToParts(date)
    const tzName = parts.find(p => p.type === 'timeZoneName')?.value || 'GMT+0'
    const match = tzName.match(/GMT([+-]\d{1,2}):?(\d{2})?/)
    if (!match) return 0
    const hours = parseInt(match[1], 10)
    const minutes = parseInt(match[2] || '0', 10)
    return hours * 60 + (hours < 0 ? -minutes : minutes)
  } catch {
    return 0
  }
}

export default function InterviewInitiateModal({ onClose, onSuccess }) {
  const [candidates, setCandidates] = useState([])
  const [templates, setTemplates] = useState([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  const [depth, setDepth] = useState('standard')
  const [candidateId, setCandidateId] = useState('')
  const [candidateSearch, setCandidateSearch] = useState('')
  const [jdId, setJdId] = useState('')
  const [phoneNumber, setPhoneNumber] = useState('')
  const [durationMinutes, setDurationMinutes] = useState(15)
  const [selectedFocusAreas, setSelectedFocusAreas] = useState(['Technical', 'Communication'])
  const [scheduleType, setScheduleType] = useState('now') // 'now' | 'later'
  const [scheduledAt, setScheduledAt] = useState('')
  const [timezone, setTimezone] = useState(getDefaultTimezone)

  useEffect(() => {
    async function load() {
      try {
        const [cands, tpls] = await Promise.all([
          getCandidates({ limit: 200 }).then(d => Array.isArray(d) ? d : d.candidates || []),
          getTemplates().then(d => Array.isArray(d) ? d : []),
        ])
        setCandidates(cands)
        setTemplates(tpls)
      } catch (err) {
        setError('Failed to load candidates/templates')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  // Update default duration when depth changes
  useEffect(() => {
    if (depth === 'quick') setDurationMinutes(5)
    else if (depth === 'standard') setDurationMinutes(15)
    else setDurationMinutes(25)
  }, [depth])

  function toggleFocusArea(area) {
    setSelectedFocusAreas(prev =>
      prev.includes(area) ? prev.filter(a => a !== area) : [...prev, area]
    )
  }

  // Filter candidates by search
  const filteredCandidates = candidates.filter(c => {
    if (!candidateSearch) return true
    const q = candidateSearch.toLowerCase()
    const name = (c.name || c.email || '').toLowerCase()
    return name.includes(q)
  }).slice(0, 20)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!candidateId || !jdId) return
    setSubmitting(true)
    setError(null)

    const scheduledAtUtc = scheduleType === 'later' && scheduledAt
      ? toUtcIso(scheduledAt, timezone)
      : null

    try {
      if (depth === 'quick') {
        // Route to Voice Screening API
        await scheduleVoiceCall(
          parseInt(candidateId),
          phoneNumber,
          parseInt(jdId),
          scheduledAtUtc
        )
      } else {
        // Route to Recruiter API
        await initiateRecruiterInterview({
          candidate_id: parseInt(candidateId),
          jd_id: parseInt(jdId),
          duration_minutes: durationMinutes,
          focus_areas: selectedFocusAreas,
          phone_number: phoneNumber || undefined,
          scheduled_at: scheduledAtUtc,
          timezone,
        })
      }
      onSuccess?.()
      onClose()
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to initiate interview')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-lg bg-white rounded-3xl shadow-2xl overflow-hidden max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between sticky top-0 bg-white z-10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-brand-600 to-brand-400 flex items-center justify-center">
              <Mic className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">New AI Interview</h2>
              <p className="text-xs text-slate-400">Choose depth and configure the interview</p>
            </div>
          </div>
          <button onClick={onClose} aria-label="Close dialog" className="p-2 rounded-lg hover:bg-slate-100 text-slate-400 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {error && (
            <div className="p-3 bg-red-50 ring-1 ring-red-200 rounded-xl">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {loading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-6 h-6 text-brand-600 animate-spin" />
            </div>
          ) : (
            <>
              {/* Depth Selector — Radio Cards */}
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-2">Interview Depth</label>
                <div className="grid grid-cols-3 gap-2">
                  {DEPTH_OPTIONS.map(opt => {
                    const Icon = opt.icon
                    const active = depth === opt.value
                    return (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => setDepth(opt.value)}
                        className={`p-3 rounded-xl ring-2 transition-all text-left ${
                          active ? opt.activeColor : 'ring-slate-200 bg-white hover:ring-slate-300'
                        }`}
                      >
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center mb-2 ${opt.iconBg}`}>
                          <Icon className="w-4 h-4" />
                        </div>
                        <p className="text-xs font-bold text-slate-800">{opt.label}</p>
                        <p className="text-[10px] text-slate-500 mt-0.5 flex items-center gap-1">
                          <Clock className="w-3 h-3" />{opt.duration}
                        </p>
                      </button>
                    )
                  })}
                </div>
                <p className="text-xs text-slate-400 mt-1.5">
                  {DEPTH_OPTIONS.find(o => o.value === depth)?.description}
                </p>
              </div>

              {/* Candidate select */}
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                  <span className="flex items-center gap-1.5"><User className="w-3.5 h-3.5" /> Candidate</span>
                </label>
                <input
                  type="text"
                  value={candidateSearch}
                  onChange={e => setCandidateSearch(e.target.value)}
                  placeholder="Search candidates..."
                  className="w-full px-3.5 py-2 bg-slate-50 rounded-t-xl ring-1 ring-slate-200 focus:ring-2 focus:ring-brand-500 text-sm outline-none transition-all"
                />
                <select
                  value={candidateId}
                  onChange={e => {
                    const id = e.target.value
                    setCandidateId(id)
                    const candidate = candidates.find(c => String(c.id) === id)
                    if (candidate?.phone && !phoneNumber) {
                      setPhoneNumber(candidate.phone)
                    }
                  }}
                  required
                  size={Math.min(filteredCandidates.length + 1, 6)}
                  className="w-full px-3.5 py-1.5 bg-white rounded-b-xl ring-1 ring-slate-200 focus:ring-2 focus:ring-brand-500 text-sm outline-none transition-all"
                >
                  <option value="">Select a candidate...</option>
                  {filteredCandidates.map(c => (
                    <option key={c.id} value={c.id}>
                      {c.name || c.email || `Candidate #${c.id}`}
                    </option>
                  ))}
                </select>
              </div>

              {/* JD select */}
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                  <span className="flex items-center gap-1.5"><FileText className="w-3.5 h-3.5" /> Job Description</span>
                </label>
                <select
                  value={jdId}
                  onChange={e => setJdId(e.target.value)}
                  required
                  className="w-full px-3.5 py-2.5 bg-white rounded-xl ring-1 ring-slate-200 focus:ring-2 focus:ring-brand-500 text-sm outline-none transition-all"
                >
                  <option value="">Select a JD template...</option>
                  {templates.map(t => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
              </div>

              {/* Phone number (optional override for all depths) */}
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                  <span className="flex items-center gap-1.5"><Phone className="w-3.5 h-3.5" /> Phone Number</span>
                </label>
                <input
                  type="tel"
                  value={phoneNumber}
                  onChange={e => setPhoneNumber(e.target.value)}
                  placeholder="+14155551234"
                  required={depth === 'quick'}
                  className="w-full px-3.5 py-2.5 bg-white rounded-xl ring-1 ring-slate-200 focus:ring-2 focus:ring-brand-500 text-sm outline-none transition-all"
                />
                <p className="text-xs text-slate-400 mt-1">E.164 format (optional override; uses candidate profile if left blank)</p>
              </div>

              {/* Schedule (for all depths) */}
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-2">Schedule</label>
                <div className="flex gap-2 mb-2">
                  <button
                    type="button"
                    onClick={() => setScheduleType('now')}
                    className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold transition-all ${
                      scheduleType === 'now'
                        ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    <Zap className="w-3.5 h-3.5" /> Call Now
                  </button>
                  <button
                    type="button"
                    onClick={() => setScheduleType('later')}
                    className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold transition-all ${
                      scheduleType === 'later'
                        ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    <Clock className="w-3.5 h-3.5" /> Schedule Later
                  </button>
                </div>
                {scheduleType === 'later' && (
                  <div className="space-y-2">
                    <input
                      type="datetime-local"
                      value={scheduledAt}
                      onChange={e => setScheduledAt(e.target.value)}
                      required={scheduleType === 'later'}
                      className="w-full px-3.5 py-2.5 bg-white rounded-xl ring-1 ring-slate-200 focus:ring-2 focus:ring-brand-500 text-sm outline-none transition-all"
                    />
                    <div className="flex items-center gap-2">
                      <Globe className="w-3.5 h-3.5 text-slate-400" />
                      <select
                        value={timezone}
                        onChange={e => setTimezone(e.target.value)}
                        className="flex-1 px-3 py-2 bg-white rounded-xl ring-1 ring-slate-200 focus:ring-2 focus:ring-brand-500 text-sm outline-none transition-all"
                      >
                        {TIMEZONE_OPTIONS.map(tz => (
                          <option key={tz} value={tz}>{tz}</option>
                        ))}
                      </select>
                    </div>
                    <p className="text-xs text-slate-400">
                      Time shown in {timezone}. Will be converted to UTC for scheduling.
                    </p>
                  </div>
                )}
              </div>

              {/* Duration (for standard/deep) */}
              {depth !== 'quick' && (
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">Duration (minutes)</label>
                  <input
                    type="number"
                    value={durationMinutes}
                    onChange={e => setDurationMinutes(parseInt(e.target.value) || 15)}
                    min={5}
                    max={60}
                    className="w-full px-3.5 py-2.5 bg-white rounded-xl ring-1 ring-slate-200 focus:ring-2 focus:ring-brand-500 text-sm outline-none transition-all"
                  />
                </div>
              )}

              {/* Focus areas (for standard/deep) */}
              {depth !== 'quick' && (
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-2">Focus Areas</label>
                  <div className="flex flex-wrap gap-2">
                    {FOCUS_AREAS.map(area => {
                      const active = selectedFocusAreas.includes(area)
                      return (
                        <button
                          key={area}
                          type="button"
                          onClick={() => toggleFocusArea(area)}
                          className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                            active
                              ? 'bg-brand-600 text-white'
                              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                          }`}
                        >
                          {active && <CheckCircle2 className="w-3 h-3" />}
                          {area}
                        </button>
                      )
                    })}
                  </div>
                </div>
              )}
            </>
          )}

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 text-sm font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || loading || !candidateId || !jdId || (depth === 'quick' && !phoneNumber)}
              className="flex items-center gap-2 px-5 py-2.5 text-sm font-semibold text-white bg-brand-600 hover:bg-brand-700 rounded-xl transition-colors disabled:opacity-50 shadow-sm shadow-brand-200"
            >
              {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Mic className="w-4 h-4" />}
              {scheduleType === 'later' ? 'Schedule Interview' : (depth === 'quick' ? 'Call Now' : 'Start Interview')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
