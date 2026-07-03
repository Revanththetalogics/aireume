import { motion } from 'framer-motion'

export function Skeleton({ className = '', variant = 'text', width, height, count = 1 }) {
  const baseStyles = 'bg-gray-200 dark:bg-gray-700 rounded'

  const variantStyles = {
    text: 'h-4 w-full',
    title: 'h-6 w-3/4',
    avatar: 'h-12 w-12 rounded-full',
    thumbnail: 'h-32 w-full rounded-lg',
    card: 'h-48 w-full rounded-xl',
    button: 'h-10 w-24 rounded-lg',
    input: 'h-10 w-full rounded-lg',
  }

  const style = {
    width: width || undefined,
    height: height || undefined,
  }

  return (
    <div className="space-y-2">
      {Array.from({ length: count }).map((_, i) => (
        <motion.div
          key={i}
          className={`${baseStyles} ${variantStyles[variant] || variantStyles.text} ${className}`}
          style={style}
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{
            duration: 1.5,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      ))}
    </div>
  )
}

export function SkeletonCard() {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-100 dark:border-gray-700">
      <Skeleton variant="title" className="mb-3" />
      <Skeleton variant="text" className="mb-2" />
      <Skeleton variant="text" width="75%" />
    </div>
  )
}

export function SkeletonTable({ rows = 5, cols = 4 }) {
  return (
    <div className="space-y-3">
      <div className="flex gap-4">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} variant="text" height="h-4" className="flex-1" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="flex gap-4">
          {Array.from({ length: cols }).map((_, colIndex) => (
            <Skeleton key={colIndex} variant="text" height="h-8" className="flex-1" />
          ))}
        </div>
      ))}
    </div>
  )
}

export function SkeletonList({ count = 3 }) {
  return (
    <div className="space-y-4">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="flex items-center gap-3">
          <Skeleton variant="avatar" />
          <div className="flex-1 space-y-2">
            <Skeleton variant="text" width="40%" />
            <Skeleton variant="text" width="60%" />
          </div>
        </div>
      ))}
    </div>
  )
}

export default Skeleton
