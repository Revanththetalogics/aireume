export default function ScoreGauge({ score }) {
  // Calculate color based on score
  let color = '#ef4444' // red-500
  let bgColor = 'bg-red-500'
  let label = 'Low Fit'

  if (score >= 70) {
    color = '#22c55e' // green-500
    bgColor = 'bg-green-500'
    label = 'Strong Fit'
  } else if (score >= 40) {
    color = '#eab308' // yellow-500
    bgColor = 'bg-yellow-500'
    label = 'Moderate Fit'
  }

  // Calculate circle properties
  const size = 160
  const strokeWidth = 12
  const radius = (size - strokeWidth) / 2
  const circumference = radius * 2 * Math.PI
  const offset = circumference - (score / 100) * circumference

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size }}>
        {/* Background circle */}
        <svg
          className="transform -rotate-90"
          width={size}
          height={size}
        >
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="#e2e8f0"
            strokeWidth={strokeWidth}
          />
          {/* Progress circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            style={{
              transition: 'stroke-dashoffset 1s ease-out'
            }}
          />
        </svg>

        {/* Score text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-4xl font-bold text-slate-800">{score}</span>
          <span className="text-xs text-slate-500 uppercase tracking-wider">out of 100</span>
        </div>
      </div>

      {/* Label */}
      <div className={`mt-4 px-4 py-1.5 rounded-full ${bgColor} text-white font-semibold text-sm`}>
        {label}
      </div>
    </div>
  )
}
