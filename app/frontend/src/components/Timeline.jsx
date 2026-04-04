import { AlertCircle, Briefcase } from 'lucide-react'

export default function Timeline({ workExperience, gaps }) {
  if (!workExperience || workExperience.length === 0) {
    return (
      <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6">
        <h3 className="text-lg font-bold text-brand-900 mb-4 tracking-tight">Employment Timeline</h3>
        <p className="text-slate-500 text-sm">No work experience data available.</p>
      </div>
    )
  }

  const sortedJobs = [...workExperience].sort((a, b) => {
    const dateA = parseDate(a.start_date)
    const dateB = parseDate(b.start_date)
    return dateB - dateA
  })

  return (
    <div className="bg-white/90 backdrop-blur-md rounded-3xl ring-1 ring-brand-100 shadow-brand p-6">
      <h3 className="text-lg font-bold text-brand-900 mb-6 tracking-tight">Employment Timeline</h3>

      <div className="space-y-4">
        {sortedJobs.map((job, index) => {
          const isShortStint = isShortTenure(job.start_date, job.end_date)

          return (
            <div key={index} className="relative">
              {index < sortedJobs.length - 1 && (
                <div className="absolute left-4 top-10 w-0.5 h-8 bg-brand-200 -translate-x-1/2" />
              )}

              <div className="flex gap-4">
                <div className={`
                  w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 ring-2
                  ${isShortStint
                    ? 'bg-amber-50 ring-amber-200'
                    : 'bg-brand-50 ring-brand-200'}
                `}>
                  {isShortStint ? (
                    <AlertCircle className="w-4 h-4 text-amber-600" />
                  ) : (
                    <Briefcase className="w-4 h-4 text-brand-600" />
                  )}
                </div>

                <div className="flex-1 pb-4">
                  <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                    <h4 className="font-bold text-brand-900">
                      {job.title || 'Unknown Title'}
                    </h4>
                    <span className="text-slate-400 text-sm">at</span>
                    <span className="font-semibold text-slate-700">
                      {job.company || 'Unknown Company'}
                    </span>
                  </div>

                  <p className="text-sm text-slate-500 mt-1">
                    {formatDate(job.start_date)} — {formatDate(job.end_date)}
                  </p>

                  {isShortStint && (
                    <span className="inline-block mt-2 text-xs bg-amber-100 text-amber-700 px-2.5 py-1 rounded-lg font-medium">
                      Short tenure (&lt; 6 months)
                    </span>
                  )}

                  {index < gaps?.length && gaps[index] && (
                    <div className="mt-3 flex items-center gap-2">
                      <div className="flex-1 h-px bg-amber-200" />
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs text-amber-700 bg-amber-50 ring-1 ring-amber-200 px-2.5 py-1 rounded-lg font-medium">
                          Gap: {gaps[index].duration_months ?? gaps[index].gap_after_months ?? 0} months
                        </span>
                        {gaps[index].severity && gaps[index].severity !== 'negligible' && (
                          <span className={`text-xs px-2 py-0.5 rounded-full font-bold ring-1 ${
                            gaps[index].severity === 'critical' ? 'bg-red-100 text-red-700 ring-red-200' :
                            gaps[index].severity === 'moderate' ? 'bg-amber-100 text-amber-700 ring-amber-200' :
                                                                  'bg-yellow-100 text-yellow-700 ring-yellow-200'
                          }`}>{gaps[index].severity}</span>
                        )}
                      </div>
                      <div className="flex-1 h-px bg-amber-200" />
                    </div>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function parseDate(dateStr) {
  if (!dateStr || dateStr.toLowerCase() === 'present') return new Date()
  const parsed = new Date(dateStr)
  return isNaN(parsed) ? new Date() : parsed
}

function formatDate(dateStr) {
  if (!dateStr || dateStr.toLowerCase() === 'present') return 'Present'
  const date = new Date(dateStr)
  if (isNaN(date)) return dateStr
  return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short' })
}

function isShortTenure(start, end) {
  const startDate = parseDate(start)
  const endDate   = parseDate(end)
  const diffMonths = (endDate - startDate) / (1000 * 60 * 60 * 24 * 30)
  return diffMonths < 6
}
