import { useState, useEffect } from 'react'
import { Sheet, Button } from '../ui'
import { getTemplates, analyzeCandidateJd } from '../../lib/api'
import { showSuccess, showError } from '../../lib/toast'

export default function AnalyzeJdSheet({ isOpen, onClose, candidateId, onComplete }) {
  const [templates, setTemplates] = useState([])
  const [templateId, setTemplateId] = useState('')
  const [jdText, setJdText] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingTemplates, setLoadingTemplates] = useState(true)

  useEffect(() => {
    if (!isOpen) return
    setLoadingTemplates(true)
    getTemplates()
      .then((data) => setTemplates(Array.isArray(data) ? data : data?.items || []))
      .catch(() => setTemplates([]))
      .finally(() => setLoadingTemplates(false))
  }, [isOpen])

  useEffect(() => {
    const tpl = templates.find((t) => String(t.id) === String(templateId))
    if (tpl?.jd_text) setJdText(tpl.jd_text)
  }, [templateId, templates])

  async function handleSubmit(e) {
    e.preventDefault()
    if (!candidateId || !jdText.trim()) return
    setLoading(true)
    try {
      const result = await analyzeCandidateJd(candidateId, {
        job_description: jdText.trim(),
        requisition_id: templateId ? Number(templateId) : null,
      })
      showSuccess('Analysis complete — no re-upload needed')
      onComplete?.(result)
      onClose()
    } catch (err) {
      showError(err.response?.data?.detail || 'Analysis failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Sheet isOpen={isOpen} onClose={onClose} maxWidth="max-w-xl">
      <form onSubmit={handleSubmit} className="p-6">
        <h2 className="text-xl font-bold text-brand-900 mb-1">Analyze against new role</h2>
        <p className="text-sm text-slate-500 mb-6">
          Re-score this candidate using stored resume data — typically 3× faster than a fresh upload.
        </p>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-1.5">Requisition</label>
            <select
              value={templateId}
              onChange={(e) => setTemplateId(e.target.value)}
              disabled={loadingTemplates}
              className="w-full px-3.5 py-2.5 bg-white rounded-xl ring-1 ring-brand-200 focus:ring-2 focus:ring-brand-500 text-sm outline-none"
            >
              <option value="">Custom JD text below…</option>
              {templates.map((t) => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          </div>

          <label className="block text-sm font-semibold text-slate-700 mb-1.5">Job description</label>
          <textarea
            value={jdText}
            onChange={(e) => setJdText(e.target.value)}
            rows={8}
            required
            className="w-full px-4 py-3 border border-brand-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none text-sm"
            placeholder="Paste job description or select a template above…"
          />
        </div>

        <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-brand-100">
          <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="brand" loading={loading} disabled={!jdText.trim()}>
            Analyze
          </Button>
        </div>
      </form>
    </Sheet>
  )
}
