import { useEffect, useState } from 'react'
import { useSearchParams, useNavigate, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  ArrowLeft,
  BarChart3,
  Loader2,
  AlertTriangle,
  Users,
  FileText,
} from 'lucide-react'
import { compareInterviewScores } from '../lib/api'
import CandidateComparisonRadar from '../components/CandidateComparisonRadar'

export default function InterviewComparisonPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  const jdIdParam = searchParams.get('jd_id')
  const candidatesParam = searchParams.get('candidates')

  const [scorecards, setScorecards] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function load() {
      setLoading(true)
      setError(null)

      if (!jdIdParam || !candidatesParam) {
        setError('Missing required parameters: jd_id and candidates')
        setLoading(false)
        return
      }

      const jdId = parseInt(jdIdParam, 10)
      const candidateIds = candidatesParam
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean)
        .map((s) => parseInt(s, 10))

      if (Number.isNaN(jdId) || candidateIds.length === 0 || candidateIds.some(Number.isNaN)) {
        setError('Invalid parameters: jd_id must be a number and candidates must be comma-separated IDs')
        setLoading(false)
        return
      }

      try {
        const data = await compareInterviewScores(jdId, candidateIds)
        const items = data?.scorecards || []
        if (items.length === 0) {
          setError('No completed interviews found for the selected candidates and JD.')
        } else {
          setScorecards(items)
        }
      } catch (err) {
        const message = err?.response?.data?.detail || err.message || 'Failed to load comparison'
        setError(message)
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [jdIdParam, candidatesParam])

  if (loading) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-brand-600 animate-spin" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-surface">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
          <button
            onClick={() => navigate('/ai-interviews')}
            className="flex items-center gap-2 text-sm text-slate-500 hover:text-brand-600 mb-6 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Sessions
          </button>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white rounded-2xl ring-1 ring-slate-200 p-8 text-center"
          >
            <AlertTriangle className="w-12 h-12 text-red-300 mx-auto mb-4" />
            <h2 className="text-lg font-bold text-slate-800 mb-2">Unable to compare</h2>
            <p className="text-sm text-slate-500 mb-6">{error}</p>
            <div className="flex items-center justify-center gap-3">
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 bg-brand-600 text-white rounded-xl text-sm font-semibold hover:bg-brand-700 transition-colors"
              >
                Try Again
              </button>
              <Link
                to="/ai-interviews"
                className="px-4 py-2 text-slate-600 bg-slate-100 rounded-xl text-sm font-semibold hover:bg-slate-200 transition-colors"
              >
                View Interviews
              </Link>
            </div>
          </motion.div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-surface">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        {/* Back button */}
        <button
          onClick={() => navigate('/ai-interviews')}
          className="flex items-center gap-2 text-sm text-slate-500 hover:text-brand-600 mb-6 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Sessions
        </button>

        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-brand-600 to-indigo-500 shadow-lg flex items-center justify-center">
              <BarChart3 className="w-7 h-7 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-extrabold text-brand-900 tracking-tight">
                Candidate Comparison
              </h1>
              <div className="flex items-center gap-3 mt-2 flex-wrap text-sm text-slate-500">
                <span className="flex items-center gap-1">
                  <FileText className="w-3.5 h-3.5" />
                  JD #{jdIdParam}
                </span>
                <span className="flex items-center gap-1">
                  <Users className="w-3.5 h-3.5" />
                  {scorecards.length} candidate{scorecards.length !== 1 ? 's' : ''}
                </span>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Comparison content */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <CandidateComparisonRadar scorecards={scorecards} />
        </motion.div>
      </div>
    </div>
  )
}
