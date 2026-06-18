import { motion } from 'framer-motion'

/**
 * SegmentedControl — Apple-style animated segmented control.
 *
 * The active pill indicator slides between segments using layoutId.
 *
 * Usage:
 *   <SegmentedControl
 *     options={[{ label: 'Sessions', value: 'sessions' }, { label: 'Settings', value: 'settings' }]}
 *     value={activeTab}
 *     onChange={setActiveTab}
 *   />
 */

export default function SegmentedControl({ options, value, onChange, className = '' }) {
  return (
    <div className={`relative inline-flex items-center bg-slate-100 dark:bg-dark-card-elevated rounded-xl p-1 ${className}`}>
      {options.map(option => {
        const isActive = option.value === value
        return (
          <button
            key={option.value}
            onClick={() => onChange(option.value)}
            className={`
              relative z-10 px-4 py-2 text-sm font-semibold rounded-lg
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
