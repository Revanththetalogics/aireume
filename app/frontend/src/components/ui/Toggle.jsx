import { motion } from 'framer-motion'

/**
 * Toggle — Spring-based toggle switch.
 *
 * Usage:
 *   <Toggle checked={isEnabled} onChange={setEnabled} label="Enable notifications" />
 */

export default function Toggle({ checked, onChange, label, disabled = false }) {
  return (
    <label className={`inline-flex items-center gap-3 cursor-pointer ${disabled ? 'opacity-50' : ''}`}>
      <motion.button
        role="switch"
        aria-checked={checked}
        onClick={() => !disabled && onChange?.(!checked)}
        disabled={disabled}
        className={`
          relative inline-flex h-6 w-11 shrink-0
          rounded-full
          transition-colors
          ${checked ? 'bg-brand-600' : 'bg-slate-200 dark:bg-dark-card-elevated'}
          ${disabled ? 'cursor-not-allowed' : 'cursor-pointer'}
        `}
        whileTap={{ scale: 0.95 }}
      >
        <motion.span
          layout
          transition={{ type: 'spring', stiffness: 500, damping: 30 }}
          className={`
            inline-block h-5 w-5
            rounded-full
            bg-white shadow-sm
            ${checked ? 'translate-x-5.5' : 'translate-x-0.5'}
            mt-0.5
          `}
          style={{ x: checked ? 22 : 2 }}
        />
      </motion.button>
      {label && (
        <span className="text-sm font-medium text-slate-700 dark:text-dark-text-primary">
          {label}
        </span>
      )}
    </label>
  )
}
