export default function ScoreGauge({ score }) {
  // score === null means the pipeline is in "Pending" state (analysis unavailable)
  const isPending = score === null || score === undefined

  let arcColor  = '#7C3AED'
  let bgColor   = 'bg-brand-600'
  let label     = 'Low Fit'
  let ringColor = 'shadow-brand-lg'

  if (!isPending) {
    // Thresholds aligned with backend: Shortlist ≥ 72, Consider ≥ 45, else Reject
    if (score >= 72) {
      arcColor  = '#22c55e'
      bgColor   = 'bg-green-500'
      label     = 'Strong Fit'
      ringColor = 'shadow-lg shadow-green-200'
    } else if (score >= 45) {
      arcColor  = '#f59e0b'
      bgColor   = 'bg-amber-500'
      label     = 'Moderate Fit'
      ringColor = 'shadow-lg shadow-amber-200'
    }
  }

  const size         = 160
  const strokeWidth  = 12
  const radius       = (size - strokeWidth) / 2
  const circumference = radius * 2 * Math.PI
  const effectiveScore = isPending ? 0 : score
  const offset       = circumference - (effectiveScore / 100) * circumference

  if (isPending) {
    return (
      <div className="flex flex-col items-center">
        <div
          className="relative rounded-full p-3 shadow-lg shadow-slate-200"
          style={{ width: size, height: size }}
        >
          <svg className="transform -rotate-90" width={size} height={size}>
            <circle
              cx={size / 2} cy={size / 2} r={radius}
              fill="none" stroke="#F1F5F9" strokeWidth={strokeWidth}
            />
            <circle
              cx={size / 2} cy={size / 2} r={radius}
              fill="none" stroke="#CBD5E1" strokeWidth={strokeWidth}
              strokeDasharray={`${circumference * 0.2} ${circumference * 0.8}`}
              strokeLinecap="round"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-2xl font-bold text-slate-400">—</span>
            <span className="text-xs text-slate-400 uppercase tracking-wider font-medium">Pending</span>
          </div>
        </div>
        <div className="mt-4 px-4 py-1.5 rounded-full bg-slate-400 text-white font-bold text-sm shadow-sm">
          Manual Review
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center">
      <div className={`relative rounded-full p-3 ${ringColor}`} style={{ width: size, height: size }}>
        <svg
          className="transform -rotate-90"
          width={size}
          height={size}
        >
          <circle
            cx={size / 2} cy={size / 2} r={radius}
            fill="none" stroke="#EDE9FE" strokeWidth={strokeWidth}
          />
          <circle
            cx={size / 2} cy={size / 2} r={radius}
            fill="none" stroke={arcColor} strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            style={{ transition: 'stroke-dashoffset 1s ease-out' }}
          />
        </svg>

        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-4xl font-extrabold text-brand-900 tracking-tight">{score}</span>
          <span className="text-xs text-slate-400 uppercase tracking-wider font-medium">/ 100</span>
        </div>
      </div>

      <div className={`mt-4 px-4 py-1.5 rounded-full ${bgColor} text-white font-bold text-sm shadow-sm`}>
        {label}
      </div>
    </div>
  )
}
