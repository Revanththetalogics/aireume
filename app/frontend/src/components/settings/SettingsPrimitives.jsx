import { Sparkles } from 'lucide-react'

export function Section({ title, icon: Icon, children, description }) {
  return (
    <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6 card-animate">
      <div className="flex items-start gap-4 mb-5">
        <div className="w-10 h-10 rounded-2xl bg-brand-50 ring-1 ring-brand-100 flex items-center justify-center shrink-0">
          <Icon className="w-5 h-5 text-brand-600" />
        </div>
        <div>
          <h3 className="font-extrabold text-brand-900 text-lg tracking-tight">{title}</h3>
          {description && <p className="text-sm text-slate-500 mt-0.5">{description}</p>}
        </div>
      </div>
      {children}
    </div>
  )
}

export function ProgressBar({ value, max, color = 'brand' }) {
  const percentage = Math.min(100, Math.round((value / max) * 100))
  const colorClasses = {
    brand: 'bg-brand-500',
    green: 'bg-green-500',
    amber: 'bg-amber-500',
    red: 'bg-red-500'
  }
  return (
    <div className="w-full bg-slate-100 rounded-full h-2">
      <div
        className={`h-2 rounded-full transition-all duration-500 ${colorClasses[color] || colorClasses.brand}`}
        style={{ width: `${percentage}%` }}
      />
    </div>
  )
}

export function UsageCard({ label, used, limit, unit = '' }) {
  const isUnlimited = limit === -1
  const percentage = isUnlimited ? 0 : Math.round((used / limit) * 100)
  const color = percentage > 90 ? 'red' : percentage > 70 ? 'amber' : 'brand'

  return (
    <div className="p-4 bg-brand-50/50 rounded-2xl ring-1 ring-brand-100">
      <div className="flex justify-between items-center mb-2">
        <span className="text-sm font-medium text-slate-700">{label}</span>
        <span className={`text-xs font-bold ${percentage > 90 ? 'text-red-600' : 'text-brand-700'}`}>
          {isUnlimited ? `${used.toLocaleString()} / ∞` : `${used.toLocaleString()} / ${limit.toLocaleString()} ${unit}`}
        </span>
      </div>
      {!isUnlimited && <ProgressBar value={used} max={limit} color={color} />}
      {isUnlimited && (
        <div className="flex items-center gap-1 text-xs text-green-600 font-medium">
          <Sparkles className="w-3.5 h-3.5" />
          Unlimited
        </div>
      )}
    </div>
  )
}
