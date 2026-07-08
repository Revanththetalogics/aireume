import { useState, useEffect, useMemo } from 'react'
import { Sheet, Button } from '../ui'
import SkillClassificationEditor from '../SkillClassificationEditor'
import { rescoreAnalysis } from '../../lib/api'
import { extractRescoreSkillClassification } from '../../lib/rescoreUtils'
import { showSuccess, showError } from '../../lib/toast'

export default function RescoreSheet({ isOpen, onClose, result, onRescoreComplete }) {
  const [loading, setLoading] = useState(false)
  const [overrides, setOverrides] = useState(null)

  const resultId = result?.result_id || result?.id

  const classificationData = useMemo(
    () => extractRescoreSkillClassification(result),
    [result],
  )

  useEffect(() => {
    if (isOpen) setOverrides(null)
  }, [isOpen, resultId])

  async function handleRescore(payload = overrides) {
    if (!resultId || !payload) return
    setLoading(true)
    try {
      const updated = await rescoreAnalysis(resultId, {
        required_skills: payload.required_skills,
        nice_to_have_skills: payload.nice_to_have_skills,
      })
      showSuccess('Fit score recalculated')
      onRescoreComplete?.(updated)
      onClose()
    } catch (err) {
      showError(err.response?.data?.detail || 'Recalculation failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Sheet isOpen={isOpen} onClose={onClose} maxWidth="max-w-xl">
      <div className="p-6">
        <h2 className="text-xl font-bold text-brand-900 mb-1">Recalculate fit score</h2>
        <p className="text-sm text-slate-500 mb-6">
          Adjust must-have and nice-to-have skills. Scoring updates instantly — no re-upload or AI call.
        </p>

        {isOpen && (
          <SkillClassificationEditor
            key={resultId}
            data={classificationData}
            onConfirm={setOverrides}
          />
        )}

        <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-brand-100">
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button
            variant="brand"
            onClick={() => {
              if (overrides) handleRescore()
            }}
            loading={loading}
            disabled={!overrides}
          >
            Recalculate
          </Button>
        </div>
      </div>
    </Sheet>
  )
}
