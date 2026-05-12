import { getScoreColor } from '../lib/constants'
import AnimatedScore from './AnimatedScore'

/**
 * Circular score badge with color coding.
 *
 * Props:
 * - score: number (0-100)
 * - size: 'sm' (32px) | 'md' (48px) | 'lg' (64px) — default 'md'
 * - animated: boolean (default true) — use AnimatedScore for count-up
 * - className: string
 */
export default function ScoreBadge({
  score,
  size = 'md',
  animated = true,
  className = '',
}) {
  const colorConfig = getScoreColor(score)

  const sizeClasses = {
    sm: 'w-8 h-8 text-xs',
    md: 'w-12 h-12 text-sm',
    lg: 'w-16 h-16 text-lg',
  }

  const borderClass = colorConfig?.border || 'border-slate-200'
  const bgClass = colorConfig?.bg || 'bg-slate-50'

  return (
    <div
      className={`
        inline-flex items-center justify-center rounded-full
        ${borderClass.replace('border-', 'border-')}
        border-2
        ${bgClass}
        ${sizeClasses[size] || sizeClasses.md}
        ${className}
      `}
    >
      {animated ? (
        <AnimatedScore
          score={score}
          size={size}
          animate={animated}
          showColor
        />
      ) : (
        <span
          className={`font-bold ${colorConfig?.text || 'text-slate-700'}`}
        >
          {score}
        </span>
      )}
    </div>
  )
}
