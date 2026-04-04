import { useLocation, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { ArrowLeft, Share2, Download, CheckCircle, Check, ThumbsUp, ThumbsDown, Loader2 } from 'lucide-react'
import ScoreGauge from '../components/ScoreGauge'
import ResultCard from '../components/ResultCard'
import Timeline from '../components/Timeline'
import NavBar from '../components/NavBar'
import { labelTrainingExample, updateResultStatus } from '../lib/api'

export default function ReportPage() {
  const location = useLocation()
  const navigate  = useNavigate()
  const [copied, setCopied]         = useState(false)
  const [result, setResult]         = useState(location.state?.result || null)
  const [labelStatus, setLabelStatus]   = useState(null)
  const [labelLoading, setLabelLoading] = useState(false)
  const [labelDone, setLabelDone]       = useState(false)

  useEffect(() => {
    if (result) return
    const params = new URLSearchParams(location.search)
    const id = params.get('id')
    if (id) {
      try {
        const stored = sessionStorage.getItem(`report_${id}`)
        if (stored) { setResult(JSON.parse(stored)); return }
      } catch { /* ignore */ }
    }
    navigate('/', { replace: true })
  }, [result, location.search, navigate])

  if (!result) return null

  const handleShare = () => {
    const id = crypto.randomUUID()
    sessionStorage.setItem(`report_${id}`, JSON.stringify(result))
    const shareUrl = `${window.location.origin}/report?id=${id}`
    navigator.clipboard.writeText(shareUrl).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2500)
    }).catch(() => window.prompt('Copy this report link:', shareUrl))
  }

  const handleDownload = () => window.print()

  const handleLabel = async (outcome) => {
    const resultId = result?.result_id
    if (!resultId || labelLoading) return
    setLabelLoading(true)
    try {
      await labelTrainingExample(resultId, outcome)
      await updateResultStatus(resultId, outcome)
      setLabelStatus(outcome)
      setLabelDone(true)
    } catch { /* Silently fail */ } finally {
      setLabelLoading(false)
    }
  }

  const candidate = result.candidate_name || result.contact_info?.name || 'Candidate'
  const role      = result.job_role || ''
  const timestamp = result.analyzed_at
    ? new Date(result.analyzed_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
    : new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })

  return (
    <div className="min-h-screen bg-surface">
      <NavBar />

      {/* Action bar */}
      <div className="bg-white/80 backdrop-blur-xl border-b border-brand-100/60 sticky top-16 z-20 print:hidden">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between gap-3">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-brand-700 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Analyze Another
          </button>

          <div className="flex items-center gap-2">
            <button
              onClick={handleShare}
              className="flex items-center gap-2 px-4 py-2 rounded-xl ring-1 ring-brand-200 text-sm font-semibold text-brand-700 hover:bg-brand-50 transition-colors"
            >
              {copied ? <Check className="w-4 h-4 text-green-600" /> : <Share2 className="w-4 h-4" />}
              {copied ? 'Link Copied!' : 'Share'}
            </button>
            <button
              onClick={handleDownload}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold text-white btn-brand shadow-brand-sm"
            >
              <Download className="w-4 h-4" />
              Download PDF
            </button>
          </div>
        </div>
      </div>

      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6 print:py-4 print:px-0">

        {/* Report header */}
        <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6 card-animate print:shadow-none">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <span className="inline-block text-xs font-bold text-brand-600 uppercase tracking-widest mb-2 bg-brand-50 px-3 py-1 rounded-full ring-1 ring-brand-200">
                Screening Report
              </span>
              <h1 className="text-2xl font-extrabold text-brand-900 tracking-tight">{candidate}</h1>
              {role && <p className="text-slate-500 mt-0.5 font-medium">{role}</p>}
            </div>
            <div className="text-right">
              <p className="text-xs text-slate-400 font-medium">Analyzed on</p>
              <p className="text-sm font-bold text-brand-900">{timestamp}</p>
              <p className="text-xs text-slate-400 mt-1">Powered by ARIA · ThetaLogics</p>
            </div>
          </div>
        </div>

        {/* Score + result card */}
        <div className="grid md:grid-cols-3 gap-6 print:grid-cols-3">
          <div className="md:col-span-1 bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6 flex flex-col items-center justify-center print:shadow-none card-animate">
            <ScoreGauge score={result.fit_score} />
            {result.final_recommendation && (
              <div className="mt-4 flex items-center gap-2 px-4 py-2 rounded-full bg-brand-50 ring-1 ring-brand-200 text-brand-700 text-sm font-bold">
                <CheckCircle className="w-4 h-4" />
                {result.final_recommendation}
              </div>
            )}
          </div>
          <div className="md:col-span-2 card-animate">
            <ResultCard result={result} defaultExpandEducation />
          </div>
        </div>

        {/* Employment Timeline */}
        <div className="print:break-before-page card-animate">
          <Timeline
            workExperience={result.work_experience || []}
            gaps={result.employment_gaps || []}
          />
        </div>

        {/* Training label */}
        {result.result_id && (
          <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-5 print:hidden card-animate">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div>
                <p className="text-sm font-bold text-brand-900">Help ARIA Learn</p>
                <p className="text-xs text-slate-400 mt-0.5">
                  Label this outcome to improve ARIA's accuracy for your company.
                </p>
              </div>
              {labelDone ? (
                <div className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-bold ring-1 ${
                  labelStatus === 'hired'
                    ? 'bg-green-100 text-green-700 ring-green-200'
                    : 'bg-red-100 text-red-700 ring-red-200'
                }`}>
                  <Check className="w-4 h-4" />
                  Marked as {labelStatus === 'hired' ? 'Hired' : 'Rejected'}
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleLabel('hired')}
                    disabled={labelLoading}
                    className="flex items-center gap-2 px-4 py-2 rounded-xl bg-green-50 ring-1 ring-green-200 text-green-700 text-sm font-bold hover:bg-green-100 disabled:opacity-50 transition-colors"
                  >
                    {labelLoading && labelStatus !== 'rejected'
                      ? <Loader2 className="w-4 h-4 animate-spin" />
                      : <ThumbsUp className="w-4 h-4" />}
                    Hired
                  </button>
                  <button
                    onClick={() => handleLabel('rejected')}
                    disabled={labelLoading}
                    className="flex items-center gap-2 px-4 py-2 rounded-xl bg-red-50 ring-1 ring-red-200 text-red-700 text-sm font-bold hover:bg-red-100 disabled:opacity-50 transition-colors"
                  >
                    {labelLoading && labelStatus !== 'hired'
                      ? <Loader2 className="w-4 h-4 animate-spin" />
                      : <ThumbsDown className="w-4 h-4" />}
                    Rejected
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

      </main>

      <footer className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6 text-center print:hidden">
        <div className="inline-flex items-center gap-2 text-xs text-slate-400">
          <span className="w-1.5 h-1.5 rounded-full bg-green-400 inline-block" />
          ARIA · Enterprise Agent Pipeline · 3-Agent Architecture · Powered by llama3 on-prem · No data leaves your VPS
        </div>
      </footer>
    </div>
  )
}
