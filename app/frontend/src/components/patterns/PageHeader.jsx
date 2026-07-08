import { Card } from '../ui'

/**
 * Consistent page header — icon, title, subtitle, optional actions.
 */
export default function PageHeader({
  title,
  subtitle,
  icon: Icon,
  actions,
  className = '',
  compact = false,
}) {
  return (
    <div className={`flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${className}`}>
      <div className="flex items-start gap-3 min-w-0">
        {Icon && (
          <div
            className={`shrink-0 rounded-2xl bg-gradient-to-br from-brand-600 to-brand-400 flex items-center justify-center shadow-brand-sm ${
              compact ? 'w-10 h-10' : 'w-12 h-12'
            }`}
          >
            <Icon className={`text-white ${compact ? 'w-5 h-5' : 'w-6 h-6'}`} />
          </div>
        )}
        <div className="min-w-0">
          <h1
            className={`font-extrabold text-brand-900 tracking-tight ${
              compact ? 'text-2xl' : 'text-3xl'
            }`}
          >
            {title}
          </h1>
          {subtitle && (
            <p className="text-sm text-slate-500 font-medium mt-0.5 max-w-2xl">{subtitle}</p>
          )}
        </div>
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2 shrink-0">{actions}</div>}
    </div>
  )
}

export function PageHeaderCard(props) {
  return (
    <Card className="p-5 mb-6">
      <PageHeader {...props} />
    </Card>
  )
}
