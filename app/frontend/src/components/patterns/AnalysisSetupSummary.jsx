import { ChevronDown, Briefcase, FileText } from 'lucide-react'
import { Card, Badge } from '../ui'

/**
 * Collapsible role + batch context shown during results phase.
 */
export default function AnalysisSetupSummary({
  roleTitle,
  requiredCount,
  fileCount,
  sourceLabel,
  jdText,
  expanded,
  onToggle,
  className = '',
}) {
  return (
    <Card className={`overflow-hidden ring-brand-100 ${className}`}>
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center gap-3 px-4 py-3.5 text-left hover:bg-brand-50/50 transition-colors"
        aria-expanded={expanded}
      >
        <div className="w-9 h-9 rounded-xl bg-brand-100 flex items-center justify-center shrink-0">
          <Briefcase className="w-4 h-4 text-brand-700" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-bold text-brand-900 truncate">{roleTitle}</p>
          <p className="text-xs text-slate-500 mt-0.5">
            {requiredCount} required skill{requiredCount !== 1 ? 's' : ''}
            {' · '}
            {fileCount} resume{fileCount !== 1 ? 's' : ''}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Badge color="brand" className="hidden sm:inline-flex">{sourceLabel}</Badge>
          <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${expanded ? 'rotate-180' : ''}`} />
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 pt-0 border-t border-brand-50">
          <div className="flex items-start gap-2 mt-3">
            <FileText className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
            <p className="text-xs text-slate-600 leading-relaxed line-clamp-4">
              {jdText?.trim() ? jdText.trim().slice(0, 480) + (jdText.length > 480 ? '…' : '') : sourceLabel}
            </p>
          </div>
        </div>
      )}
    </Card>
  )
}
