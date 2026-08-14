import {
  Phone, Calendar, PhoneCall, PhoneOff, CheckCircle2, XCircle, AlertTriangle, X,
} from 'lucide-react'

export const OPENING_PLACEHOLDERS = '{candidate_first_name}, {role_title}, {company_name}, {bot_name}'

const STATUS_CONFIG = {
  scheduled:  { label: 'Scheduled',  color: 'bg-blue-100 text-blue-700',   icon: Calendar },
  ringing:    { label: 'Ringing',    color: 'bg-amber-100 text-amber-700', icon: Phone },
  in_progress:{ label: 'In Progress',color: 'bg-green-100 text-green-700', icon: PhoneCall },
  completed:  { label: 'Completed',  color: 'bg-emerald-100 text-emerald-700', icon: CheckCircle2 },
  failed:     { label: 'Failed',     color: 'bg-red-100 text-red-700',     icon: XCircle },
  no_answer:  { label: 'No Answer',  color: 'bg-orange-100 text-orange-700', icon: PhoneOff },
  escalated:  { label: 'Escalated',  color: 'bg-purple-100 text-purple-700', icon: AlertTriangle },
  cancelled:  { label: 'Cancelled',  color: 'bg-slate-100 text-slate-600', icon: X },
}

const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
export const VOICE_OPTIONS = [
  { value: 'female', label: 'Female' },
  { value: 'male', label: 'Male' },
]
export const GREETING_OPTIONS = [
  { value: 'professional', label: 'Professional' },
  { value: 'casual', label: 'Casual' },
  { value: 'friendly', label: 'Friendly' },
]
export const DETAIL_OPTIONS = [
  { value: 'brief', label: 'Brief Summary' },
  { value: 'full', label: 'Full Detail' },
]
export const FOLLOW_UP_OPTIONS = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
]
export const TIMEZONE_OPTIONS = [
  { value: 'UTC', label: 'UTC (Coordinated Universal Time)' },
  { value: 'America/New_York', label: 'US Eastern (ET)' },
  { value: 'America/Chicago', label: 'US Central (CT)' },
  { value: 'America/Denver', label: 'US Mountain (MT)' },
  { value: 'America/Los_Angeles', label: 'US Pacific (PT)' },
  { value: 'America/Anchorage', label: 'US Alaska (AKT)' },
  { value: 'Pacific/Honolulu', label: 'US Hawaii (HST)' },
  { value: 'Europe/London', label: 'UK (GMT/BST)' },
  { value: 'Europe/Berlin', label: 'Central Europe (CET)' },
  { value: 'Europe/Paris', label: 'France (CET)' },
  { value: 'Europe/Helsinki', label: 'Eastern Europe (EET)' },
  { value: 'Asia/Dubai', label: 'UAE (GST)' },
  { value: 'Asia/Kolkata', label: 'India (IST)' },
  { value: 'Asia/Bangkok', label: 'Thailand (ICT)' },
  { value: 'Asia/Singapore', label: 'Singapore (SGT)' },
  { value: 'Asia/Shanghai', label: 'China (CST)' },
  { value: 'Asia/Tokyo', label: 'Japan (JST)' },
  { value: 'Australia/Sydney', label: 'Australia Eastern (AEST)' },
  { value: 'Pacific/Auckland', label: 'New Zealand (NZST)' },
]

export function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.scheduled
  const Icon = cfg.icon
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold ${cfg.color}`}>
      <Icon className="w-3 h-3" />
      {cfg.label}
    </span>
  )
}

export function Section({ title, icon: Icon, children, description, action }) {
  return (
    <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6 card-animate">
      <div className="flex items-start justify-between mb-5">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 rounded-2xl bg-brand-50 ring-1 ring-brand-100 flex items-center justify-center shrink-0">
            <Icon className="w-5 h-5 text-brand-600" />
          </div>
          <div>
            <h3 className="font-extrabold text-brand-900 text-lg tracking-tight">{title}</h3>
            {description && <p className="text-sm text-slate-500 mt-0.5">{description}</p>}
          </div>
        </div>
        {action}
      </div>
      {children}
    </div>
  )
}

export function Field({ label, children, hint }) {
  return (
    <div>
      <label htmlFor="voicescreeningpage-field-1" className="block text-sm font-semibold text-slate-700 mb-1.5">{label}</label>
      {children}
      {hint && <p className="text-xs text-slate-400 mt-1">{hint}</p>}
    </div>
  )
}

export function TextInput({ value, onChange, placeholder, type = 'text' }) {
  return (
    <input id="voicescreeningpage-field-1"
      type={type}
      value={value ?? ''}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full px-3.5 py-2.5 bg-white rounded-xl ring-1 ring-slate-200 focus:ring-2 focus:ring-brand-500 focus:border-transparent text-sm transition-all outline-none"
    />
  )
}

export function Select({ value, onChange, options }) {
  return (
    <select
      value={value ?? ''}
      onChange={e => onChange(e.target.value)}
      className="w-full px-3.5 py-2.5 bg-white rounded-xl ring-1 ring-slate-200 focus:ring-2 focus:ring-brand-500 focus:border-transparent text-sm transition-all outline-none appearance-none"
    >
      {options.map(o => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  )
}

export function DayPicker({ value, onChange }) {
  const days = value || [1, 2, 3, 4, 5]
  function toggle(dayIdx) {
    const next = days.includes(dayIdx)
      ? days.filter(d => d !== dayIdx)
      : [...days, dayIdx].sort()
    onChange(next)
  }
  return (
    <div className="flex gap-1.5">
      {DAY_NAMES.map((name, idx) => {
        const dayNum = idx + 1
        const active = days.includes(dayNum)
        return (
          <button
            key={idx}
            onClick={() => toggle(dayNum)}
            className={`w-9 h-9 rounded-lg text-xs font-bold transition-all ${
              active
                ? 'bg-brand-600 text-white shadow-sm'
                : 'bg-slate-100 text-slate-400 hover:bg-slate-200'
            }`}
          >
            {name}
          </button>
        )
      })}
    </div>
  )
}
