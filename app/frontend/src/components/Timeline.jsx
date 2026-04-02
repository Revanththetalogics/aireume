import { AlertCircle } from 'lucide-react'

export default function Timeline({ workExperience, gaps }) {
  if (!workExperience || workExperience.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <h3 className="text-lg font-semibold text-slate-800 mb-4">Employment Timeline</h3>
        <p className="text-slate-500 text-sm">No work experience data available.</p>
      </div>
    )
  }

  // Sort jobs by start date (newest first)
  const sortedJobs = [...workExperience].sort((a, b) => {
    const dateA = parseDate(a.start_date)
    const dateB = parseDate(b.start_date)
    return dateB - dateA
  })

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
      <h3 className="text-lg font-semibold text-slate-800 mb-6">Employment Timeline</h3>

      <div className="space-y-4">
        {sortedJobs.map((job, index) => {
          const isShortStint = isShortTenure(job.start_date, job.end_date)

          return (
            <div key={index} className="relative">
              {/* Timeline connector */}
              {index < sortedJobs.length - 1 && (
                <div className="absolute left-4 top-10 w-0.5 h-8 bg-slate-200 -translate-x-1/2" />
              )}

              <div className="flex gap-4">
                {/* Timeline dot */}
                <div className={`
                  w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0
                  ${isShortStint ? 'bg-amber-100' : 'bg-blue-100'}
                `}>
                  {isShortStint ? (
                    <AlertCircle className="w-4 h-4 text-amber-600" />
                  ) : (
                    <div className="w-3 h-3 rounded-full bg-blue-500" />
                  )}
                </div>

                {/* Job details */}
                <div className="flex-1 pb-4">
                  <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                    <h4 className="font-semibold text-slate-800">
                      {job.title || 'Unknown Title'}
                    </h4>
                    <span className="text-slate-400">at</span>
                    <span className="font-medium text-slate-700">
                      {job.company || 'Unknown Company'}
                    </span>
                  </div>

                  <p className="text-sm text-slate-500 mt-1">
                    {formatDate(job.start_date)} — {formatDate(job.end_date)}
                  </p>

                  {isShortStint && (
                    <span className="inline-block mt-2 text-xs bg-amber-100 text-amber-700 px-2 py-1 rounded">
                      Short tenure (&lt; 6 months)
                    </span>
                  )}

                  {/* Show gap before this job */}
                  {index < gaps?.length && gaps[index] && (
                    <div className="mt-3 flex items-center gap-2">
                      <div className="flex-1 h-0.5 bg-amber-300" />
                      <span className="text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded">
                        Gap: {gaps[index].duration_months} months
                      </span>
                      <div className="flex-1 h-0.5 bg-amber-300" />
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
  if (!dateStr || dateStr.toLowerCase() === 'present') {
    return new Date()
  }
  const parsed = new Date(dateStr)
  return isNaN(parsed) ? new Date() : parsed
}

function formatDate(dateStr) {
  if (!dateStr || dateStr.toLowerCase() === 'present') {
    return 'Present'
  }
  const date = new Date(dateStr)
  if (isNaN(date)) return dateStr
  return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short' })
}

function isShortTenure(start, end) {
  const startDate = parseDate(start)
  const endDate = parseDate(end)
  const diffMonths = (endDate - startDate) / (1000 * 60 * 60 * 24 * 30)
  return diffMonths < 6
}
