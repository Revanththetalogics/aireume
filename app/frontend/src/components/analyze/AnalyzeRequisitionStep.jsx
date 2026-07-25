import { Link } from 'react-router-dom'
import {
  Briefcase, ChevronUp, ExternalLink, FileText, Loader2, Search, X,
} from 'lucide-react'
import { Button } from '../ui'
import { ANALYZE } from '../../lib/uxLabels'
import { countJdWords } from '../../lib/analyzeRequisitionUtils'

export function RequisitionContextBar({
  requisition,
  intakeGate,
  remainingAnalyses,
  onChangeRole,
  onViewFullJd,
}) {
  if (!requisition) return null

  const wordCount = countJdWords(requisition.jd_text)
  const statusLabel = requisition.status?.replace(/_/g, ' ') || 'draft'
  const intakeLabel = requisition.intake_status?.replace(/_/g, ' ') || 'draft'

  return (
    <div className="mb-6 rounded-2xl ring-1 ring-brand-200 bg-brand-50/60 p-4 space-y-3">
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[10px] font-bold uppercase tracking-wider text-brand-700">
            {ANALYZE.screeningFor}
          </p>
          <h3 className="text-lg font-bold text-brand-900 truncate">{requisition.title || requisition.name}</h3>
          <p className="text-xs text-slate-600 mt-1 capitalize">
            {statusLabel}
            {requisition.is_calibrated ? ' · Calibrated' : ''}
            {requisition.client_name ? ` · ${requisition.client_name}` : ''}
            {requisition.location ? ` · ${requisition.location}` : ''}
          </p>
          <p className="text-xs text-slate-500 mt-0.5 capitalize">
            Intake: {intakeLabel}
            {requisition.current_criteria_version
              ? ` · Criteria v${requisition.current_criteria_version}`
              : ''}
          </p>
        </div>
        <div className="flex flex-wrap gap-2 shrink-0">
          {remainingAnalyses !== undefined && remainingAnalyses !== Infinity && (
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-white ring-1 ring-brand-200 text-brand-800">
              {remainingAnalyses} analyses left
            </span>
          )}
          <Button variant="ghost" size="sm" onClick={onChangeRole}>
            {ANALYZE.changeRequisition}
          </Button>
          <Link
            to={`/requisitions/${requisition.id}`}
            className="inline-flex items-center gap-1 text-xs font-semibold text-brand-700 hover:text-brand-900 px-2 py-1"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            {ANALYZE.openRequisition}
          </Link>
        </div>
      </div>

      {intakeGate?.warning && (
        <div className={`text-sm rounded-xl px-3 py-2 ring-1 ${
          intakeGate.blocks
            ? 'bg-amber-50 text-amber-900 ring-amber-200'
            : 'bg-white text-amber-800 ring-amber-100'
        }`}>
          {intakeGate.warning}
        </div>
      )}

      {requisition.jd_text?.trim() && (
        <div className="rounded-xl bg-white ring-1 ring-brand-100 p-3">
          <div className="flex items-center justify-between gap-2 mb-2">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              {ANALYZE.jdReferenceLabel}
            </p>
            <button
              type="button"
              onClick={onViewFullJd}
              className="text-xs font-semibold text-brand-600 hover:text-brand-800"
            >
              {ANALYZE.viewFullJd(wordCount)}
            </button>
          </div>
          <p className="text-sm text-slate-700 whitespace-pre-wrap line-clamp-4 leading-relaxed">
            {requisition.jd_text}
          </p>
        </div>
      )}
    </div>
  )
}

export function RequisitionPickerPanel({
  requisitions,
  loading,
  search,
  onSearchChange,
  onSelect,
  onCreateNew,
}) {
  const query = search.trim().toLowerCase()
  const filtered = query
    ? requisitions.filter((r) => {
        const title = (r.title || r.name || '').toLowerCase()
        const client = (r.client_name || '').toLowerCase()
        return title.includes(query) || client.includes(query)
      })
    : requisitions

  return (
    <div className="space-y-4">
      <div className="rounded-2xl ring-1 ring-brand-100 bg-brand-50/40 p-5">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl bg-brand-100 flex items-center justify-center shrink-0">
            <Briefcase className="w-5 h-5 text-brand-700" />
          </div>
          <div>
            <p className="text-sm font-bold text-brand-900">{ANALYZE.selectOpeningTitle}</p>
            <p className="text-xs text-slate-600 mt-1 leading-relaxed">{ANALYZE.selectOpeningHint}</p>
          </div>
        </div>
      </div>

      <div className="relative">
        <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
        <input
          type="search"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder={ANALYZE.searchRequisitions}
          className="w-full pl-9 pr-3 py-2.5 rounded-xl border border-brand-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
      </div>

      {loading ? (
        <div className="flex justify-center py-10">
          <Loader2 className="w-6 h-6 animate-spin text-brand-500" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-10 px-4 rounded-2xl ring-1 ring-dashed ring-brand-200 bg-white">
          <FileText className="w-8 h-8 text-brand-300 mx-auto mb-2" />
          <p className="text-sm font-semibold text-slate-700">{ANALYZE.noRequisitionsTitle}</p>
          <p className="text-xs text-slate-500 mt-1 mb-4">{ANALYZE.noRequisitionsHint}</p>
          <Button size="sm" onClick={onCreateNew}>{ANALYZE.createRequisitionCta}</Button>
        </div>
      ) : (
        <div className="grid gap-2 max-h-80 overflow-y-auto pr-1">
          {filtered.map((req) => (
            <button
              key={req.id}
              type="button"
              onClick={() => onSelect(req)}
              className="w-full text-left p-4 rounded-2xl bg-white ring-1 ring-brand-100 hover:ring-brand-300 hover:bg-brand-50/40 transition-all"
            >
              <p className="text-sm font-semibold text-brand-900 truncate">{req.title || req.name}</p>
              <p className="text-xs text-slate-500 mt-1 capitalize">
                {(req.status || 'draft').replace(/_/g, ' ')}
                {req.is_calibrated ? ' · Calibrated' : ''}
                {req.client_name ? ` · ${req.client_name}` : ''}
              </p>
              {req.intake_gate_warning && (
                <p className="text-xs text-amber-700 mt-2 line-clamp-2">{req.intake_gate_warning}</p>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export function JdFullModal({ title, jdText, onClose }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl ring-1 ring-brand-100 shadow-brand-xl w-full max-w-3xl max-h-[85vh] flex flex-col">
        <div className="flex items-center justify-between gap-3 px-5 py-4 border-b border-brand-50">
          <div className="flex items-center gap-2 min-w-0">
            <FileText className="w-5 h-5 text-brand-600 shrink-0" />
            <h3 className="font-bold text-brand-900 truncate">{title}</h3>
          </div>
          <button type="button" onClick={onClose} aria-label="Close" className="p-1.5 hover:bg-brand-50 rounded-lg">
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>
        <div className="overflow-y-auto px-5 py-4 flex-1">
          <p className="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">{jdText}</p>
        </div>
        <div className="px-5 py-3 border-t border-brand-50 flex justify-end">
          <Button variant="ghost" onClick={onClose}>Close</Button>
        </div>
      </div>
    </div>
  )
}

export function AdHocModeToggle({ onEnable, onDisable, active }) {
  if (active) {
    return (
      <button
        type="button"
        onClick={onDisable}
        className="text-xs font-semibold text-brand-600 hover:text-brand-800 inline-flex items-center gap-1"
      >
        <ChevronUp className="w-3.5 h-3.5" />
        {ANALYZE.backToRequisitions}
      </button>
    )
  }
  return (
    <button
      type="button"
      onClick={onEnable}
      className="text-xs font-semibold text-slate-500 hover:text-brand-700 underline underline-offset-2"
    >
      {ANALYZE.quickScreenLink}
    </button>
  )
}
