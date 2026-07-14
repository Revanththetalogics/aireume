import { motion } from 'framer-motion'

export default function SegmentedControl({
  options, value, onChange, className = '', role, ariaLabel,
}) {
  const isTablist = role === 'tablist'
  return (
    <div
      className={`relative inline-flex items-center bg-slate-100 dark:bg-dark-card-elevated rounded-xl p-1 ${className}`}
      role={role}
      aria-label={ariaLabel}
    >
      {options.map((option) => {
        const isActive = option.value === value
        return (
          <button
            key={option.value}
            type="button"
            role={isTablist ? 'tab' : undefined}
            aria-selected={isTablist ? isActive : undefined}
            onClick={() => onChange(option.value)}
            className={`
              relative z-10 px-4 py-2 text-sm font-semibold rounded-lg whitespace-nowrap
              transition-colors duration-200
              ${isActive
                ? 'text-brand-700 dark:text-brand-400'
                : 'text-slate-500 hover:text-slate-700 dark:hover:text-dark-text-secondary'
              }
            `}
          >
            {isActive && (
              <motion.div
                layoutId="segmented-control-pill"
                className="absolute inset-0 bg-white dark:bg-dark-card rounded-lg shadow-sm"
                transition={{ type: 'spring', stiffness: 400, damping: 30 }}
              />
            )}
            <span className="relative z-10">{option.label}</span>
          </button>
        )
      })}
    </div>
  )
}
