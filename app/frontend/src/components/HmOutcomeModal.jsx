import { useState } from 'react'
import { Button } from './ui'

const REJECT_REASONS = [
  { code: 'too_junior', label: 'Too junior for the role' },
  { code: 'wrong_skills', label: 'Missing or wrong must-have skills' },
  { code: 'wrong_seniority', label: 'Seniority level mismatch' },
  { code: 'culture_mismatch', label: 'Culture or team fit concern' },
  { code: 'compensation', label: 'Compensation or level mismatch' },
  { code: 'other', label: 'Other' },
]

export default function HmOutcomeModal({ open, outcome, onClose, onConfirm, saving }) {
  const [reasonCode, setReasonCode] = useState('wrong_skills')
  const [notes, setNotes] = useState('')

  if (!open) return null

  const isReject = outcome === 'reject'

  const handleConfirm = () => {
    if (isReject && !reasonCode) return
    onConfirm({
      outcome,
      reasonCode: isReject ? reasonCode : null,
      notes: notes.trim() || null,
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-2xl ring-1 ring-brand-100 shadow-brand-xl w-full max-w-md p-5 space-y-4">
        <h3 className="text-lg font-bold text-brand-900 capitalize">
          Confirm {outcome}
        </h3>
        {isReject && (
          <>
            <label className="block text-sm">
              <span className="font-semibold text-slate-700">Reason (required)</span>
              <select
                value={reasonCode}
                onChange={(e) => setReasonCode(e.target.value)}
                className="mt-1 w-full rounded-xl border border-brand-200 px-3 py-2 text-sm"
              >
                {REJECT_REASONS.map((r) => (
                  <option key={r.code} value={r.code}>{r.label}</option>
                ))}
              </select>
            </label>
            <p className="text-xs text-slate-500">
              Your feedback helps the recruiter adjust sourcing strategy and criteria.
            </p>
          </>
        )}
        <label className="block text-sm">
          <span className="font-semibold text-slate-700">Notes {isReject ? '(recommended)' : '(optional)'}</span>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
            className="mt-1 w-full rounded-xl border border-brand-200 px-3 py-2 text-sm resize-none"
            placeholder={isReject ? 'What should change in sourcing or the bar?' : 'Optional note for the recruiter'}
          />
        </label>
        <div className="flex gap-2 justify-end">
          <Button variant="ghost" onClick={onClose} disabled={saving}>Cancel</Button>
          <Button onClick={handleConfirm} disabled={saving || (isReject && !reasonCode)}>
            {saving ? 'Saving…' : 'Confirm'}
          </Button>
        </div>
      </div>
    </div>
  )
}

export { REJECT_REASONS }
