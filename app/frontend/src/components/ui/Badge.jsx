import { motion, AnimatePresence } from 'framer-motion'

/**
 * Badge — Animated entrance/exit badge.
 *
 * Usage:
 *   <Badge color="green">Active</Badge>
 *   <Badge color="red" show={hasError}>Error</Badge>
 */

const colors = {
  green: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  red: 'bg-red-50 text-red-700 ring-red-200',
  blue: 'bg-blue-50 text-blue-700 ring-blue-200',
  amber: 'bg-amber-50 text-amber-700 ring-amber-200',
  brand: 'bg-brand-50 text-brand-700 ring-brand-200',
  slate: 'bg-slate-100 text-slate-600 ring-slate-200',
}

export default function Badge({ children, color = 'slate', show = true, className = '' }) {
  return (
    <AnimatePresence>
      {show && (
        <motion.span
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.8 }}
          transition={{ type: 'spring', stiffness: 400, damping: 25 }}
          className={`
            inline-flex items-center
            px-2 py-0.5
            text-xs font-semibold
            rounded-full
            ring-1
            ${colors[color]}
            ${className}
          `}
        >
          {children}
        </motion.span>
      )}
    </AnimatePresence>
  )
}
