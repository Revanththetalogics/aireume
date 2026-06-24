import { useState, useEffect } from 'react'
import { X, Brain, Loader2, User, FileText } from 'lucide-react'
import { getCandidates, getTemplates, initiateRecruiterInterview } from '../lib/api'

export default function InterviewInitiateModal({ onClose, onSuccess }) {
  const [candidates, setCandidates] = useState([])
  const [templates, setTemplates] = useState([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  const [candidateId, setCandidateId] = useState('')
  const [jdId, setJdId] = useState('')
  const [durationMinutes, setDurationMinutes] = useState(30)
  const [focusAreas, setFocusAreas] = useState('')

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

  async function handleSubmit(e) {
    e.preventDefault()
    if (!candidateId || !jdId) return
    setSubmitting(true)
    setError(null)
    try {
      await initiateRecruiterInterview({
        candidate_id: parseInt(candidateId),
        jd_id: parseInt(jdId),
        duration_minutes: durationMinutes,
        focus_areas: focusAreas ? focusAreas.split(',').map(s => s.trim()).filter(Boolean) : [],
      })
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
      <div className="relative w-full max-w-lg bg-white rounded-3xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-brand-600 to-brand-400 flex items-center justify-center">
              <Brain className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">Initiate AI Interview</h2>
              <p className="text-xs text-slate-400">Start a new AI recruiter interview session</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-slate-100 text-slate-400 transition-colors">
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
              {/* Candidate select */}
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                  <span className="flex items-center gap-1.5"><User className="w-3.5 h-3.5" /> Candidate</span>
                </label>
                <select
                  value={candidateId}
                  onChange={e => setCandidateId(e.target.value)}
                  required
                  className="w-full px-3.5 py-2.5 bg-white rounded-xl ring-1 ring-slate-200 focus:ring-2 focus:ring-brand-500 text-sm outline-none transition-all"
                >
                  <option value="">Select a candidate...</option>
                  {candidates.map(c => (
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

              {/* Duration */}
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">Duration (minutes)</label>
                <input
                  type="number"
                  value={durationMinutes}
                  onChange={e => setDurationMinutes(parseInt(e.target.value) || 30)}
                  min={10}
                  max={60}
                  className="w-full px-3.5 py-2.5 bg-white rounded-xl ring-1 ring-slate-200 focus:ring-2 focus:ring-brand-500 text-sm outline-none transition-all"
                />
              </div>

              {/* Focus areas */}
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">Focus Areas (optional)</label>
                <input
                  type="text"
                  value={focusAreas}
                  onChange={e => setFocusAreas(e.target.value)}
                  placeholder="e.g. system design, leadership, teamwork"
                  className="w-full px-3.5 py-2.5 bg-white rounded-xl ring-1 ring-slate-200 focus:ring-2 focus:ring-brand-500 text-sm outline-none transition-all"
                />
                <p className="text-xs text-slate-400 mt-1">Comma-separated list of areas to focus on</p>
              </div>
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
              disabled={submitting || loading || !candidateId || !jdId}
              className="flex items-center gap-2 px-5 py-2.5 text-sm font-semibold text-white bg-brand-600 hover:bg-brand-700 rounded-xl transition-colors disabled:opacity-50 shadow-sm shadow-brand-200"
            >
              {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Brain className="w-4 h-4" />}
              Start Interview
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
