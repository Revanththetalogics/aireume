import { useState, useEffect } from 'react'
import {
  X, Phone, Calendar, Clock, User, Briefcase, Loader2,
  AlertTriangle, CheckCircle2,
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { scheduleVoiceCall } from '../lib/api'
import { getCandidates } from '../lib/api'

const springTransition = { type: 'spring', stiffness: 300, damping: 28 }

export default function VoiceScheduleModal({ onClose, onScheduled, preselectedCandidate = null, preselectedJdId = null }) {
  const [candidates, setCandidates] = useState([])
  const [loadingCandidates, setLoadingCandidates] = useState(true)
  const [selectedCandidate, setSelectedCandidate] = useState(preselectedCandidate)
  const [phoneNumber, setPhoneNumber] = useState(preselectedCandidate?.phone || preselectedCandidate?.contact_info?.phone || '')
  const [scheduledAt, setScheduledAt] = useState('')
  const [jdId] = useState(preselectedJdId)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)

  const isPreselected = !!preselectedCandidate

  useEffect(() => {
    if (isPreselected) return
    async function loadCandidates() {
      try {
        const data = await getCandidates()
        setCandidates(Array.isArray(data) ? data.slice(0, 100) : [])
      } catch {
        setError('Failed to load candidates')
      } finally {
        setLoadingCandidates(false)
      }
    }
    loadCandidates()
  }, [isPreselected])

  function handleCandidateSelect(candidate) {
    setSelectedCandidate(candidate)
    if (candidate.phone) {
      setPhoneNumber(candidate.phone)
    }
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!selectedCandidate) {
      setError('Please select a candidate')
      return
    }
    if (!phoneNumber.trim()) {
      setError('Please enter a phone number')
      return
    }

    try {
      setSubmitting(true)
      setError(null)
      await scheduleVoiceCall(
        selectedCandidate.id,
        phoneNumber.trim(),
        jdId,
        scheduledAt ? new Date(scheduledAt).toISOString() : null,
      )
      setSuccess(true)
      setTimeout(() => onScheduled(), 1500)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to schedule call')
    } finally {
      setSubmitting(false)
    }
  }

  if (success) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="absolute inset-0 bg-black/30 backdrop-blur-sm"
        />
        <motion.div
          initial={{ opacity: 0, scale: 0.92, y: 16 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={springTransition}
          className="relative bg-white rounded-3xl shadow-2xl p-8 w-full max-w-md text-center"
        >
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', stiffness: 400, damping: 15, delay: 0.1 }}
            className="w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center mx-auto mb-4"
          >
            <CheckCircle2 className="w-8 h-8 text-emerald-600" />
          </motion.div>
          <h3 className="text-xl font-bold text-slate-800 mb-2">Call Scheduled!</h3>
          <p className="text-sm text-slate-500">
            The screening call has been scheduled successfully.
          </p>
        </motion.div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="absolute inset-0 bg-black/30 backdrop-blur-sm"
        onClick={onClose}
      />
      <motion.div
        initial={{ opacity: 0, scale: 0.92, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={springTransition}
        className="relative bg-white rounded-3xl shadow-2xl w-full max-w-lg overflow-hidden"
      >
        {/* Header */}
        <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand-50 flex items-center justify-center">
              <Phone className="w-5 h-5 text-brand-600" />
            </div>
            <h2 className="text-lg font-bold text-slate-800">Schedule Screening Call</h2>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-slate-100 text-slate-400">
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="mx-6 mt-4 p-3 bg-red-50 ring-1 ring-red-200 rounded-xl flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-500 shrink-0" />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {/* Pre-selected candidate info */}
          {isPreselected && (
            <div className="flex items-center gap-3 p-3 bg-brand-50 rounded-xl ring-1 ring-brand-200">
              <div className="w-9 h-9 rounded-full bg-gradient-to-br from-brand-600 to-brand-400 flex items-center justify-center text-white text-sm font-bold shrink-0">
                {(selectedCandidate?.name || selectedCandidate?.email || '?')[0].toUpperCase()}
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-slate-800 truncate">
                  {selectedCandidate?.name || selectedCandidate?.email || `Candidate #${selectedCandidate?.id}`}
                </p>
                <p className="text-xs text-slate-500 truncate">
                  {selectedCandidate?.email || 'No email'}
                </p>
              </div>
            </div>
          )}

          {/* Candidate Selection — only show when not pre-selected */}
          {!isPreselected && (
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                <span className="flex items-center gap-1.5">
                  <User className="w-3.5 h-3.5" /> Candidate
                </span>
              </label>
              {loadingCandidates ? (
                <div className="flex items-center gap-2 py-3 text-sm text-slate-400">
                  <Loader2 className="w-4 h-4 animate-spin" /> Loading candidates...
                </div>
              ) : (
                <div className="relative">
                  <select
                    value={selectedCandidate?.id || ''}
                    onChange={e => {
                      const c = candidates.find(c => c.id === parseInt(e.target.value))
                      if (c) handleCandidateSelect(c)
                    }}
                    className="w-full px-3.5 py-2.5 bg-white rounded-xl ring-1 ring-slate-200 focus:ring-2 focus:ring-brand-500 text-sm outline-none appearance-none"
                  >
                    <option value="">Select a candidate...</option>
                    {candidates.map(c => (
                      <option key={c.id} value={c.id}>
                        {c.name || c.email || `Candidate #${c.id}`}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>
          )}

          {/* Phone Number */}
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              <span className="flex items-center gap-1.5">
                <Phone className="w-3.5 h-3.5" /> Phone Number
              </span>
            </label>
            <input
              type="tel"
              value={phoneNumber}
              onChange={e => setPhoneNumber(e.target.value)}
              placeholder="+14155551234"
              className="w-full px-3.5 py-2.5 bg-white rounded-xl ring-1 ring-slate-200 focus:ring-2 focus:ring-brand-500 text-sm outline-none"
            />
            <p className="text-xs text-slate-400 mt-1">E.164 format (e.g., +14155551234)</p>
          </div>

          {/* Schedule Time */}
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">
              <span className="flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5" /> Schedule Time
              </span>
            </label>
            <input
              type="datetime-local"
              value={scheduledAt}
              onChange={e => setScheduledAt(e.target.value)}
              className="w-full px-3.5 py-2.5 bg-white rounded-xl ring-1 ring-slate-200 focus:ring-2 focus:ring-brand-500 text-sm outline-none"
            />
            <p className="text-xs text-slate-400 mt-1">
              Leave empty to schedule immediately. Calls are adjusted to business hours.
            </p>
          </div>

          {/* Submit */}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2.5 text-sm font-semibold text-slate-600 bg-slate-100 rounded-xl hover:bg-slate-200 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || !selectedCandidate || !phoneNumber.trim()}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-semibold text-white bg-brand-600 rounded-xl hover:bg-brand-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Phone className="w-4 h-4" />
              )}
              Schedule Call
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  )
}
