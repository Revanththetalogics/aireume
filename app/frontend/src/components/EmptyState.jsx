import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'

/**
 * EmptyState — Animated empty state with staggered entrance.
 *
 * Icon, title, description, and CTA animate in sequence.
 */

export default function EmptyState({
  icon: Icon,
  title,
  description,
  actionLabel,
  onAction,
  actionHref,
  className = '',
}) {
  return (
    <motion.div
      initial="hidden"
      animate="show"
      variants={{
        hidden: {},
        show: { transition: { staggerChildren: 0.08 } },
      }}
      className={`flex flex-col items-center justify-center text-center ${className}`}
    >
      {Icon && (
        <motion.div
          variants={{
            hidden: { opacity: 0, scale: 0.5 },
            show: { opacity: 1, scale: 1, transition: { type: 'spring', stiffness: 300, damping: 15 } },
          }}
          className="w-14 h-14 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center mb-4"
        >
          <Icon className="w-7 h-7 text-brand-500" />
        </motion.div>
      )}
      {title && (
        <motion.h3
          variants={{
            hidden: { opacity: 0, y: 8 },
            show: { opacity: 1, y: 0 },
          }}
          className="text-lg font-bold tracking-tight text-slate-800 dark:text-dark-text-primary mb-1"
        >
          {title}
        </motion.h3>
      )}
      {description && (
        <motion.p
          variants={{
            hidden: { opacity: 0, y: 8 },
            show: { opacity: 1, y: 0 },
          }}
          className="text-sm text-slate-500 dark:text-dark-text-secondary max-w-sm text-center mb-5"
        >
          {description}
        </motion.p>
      )}
      {actionLabel && (onAction || actionHref) && (
        <motion.div
          variants={{
            hidden: { opacity: 0, y: 8 },
            show: { opacity: 1, y: 0 },
          }}
        >
          {actionHref ? (
            <Link
              to={actionHref}
              className="px-5 py-2.5 btn-brand text-white text-sm font-bold rounded-xl shadow-brand-sm"
            >
              {actionLabel}
            </Link>
          ) : (
            <button
              onClick={onAction}
              className="px-5 py-2.5 btn-brand text-white text-sm font-bold rounded-xl shadow-brand-sm"
            >
              {actionLabel}
            </button>
          )}
        </motion.div>
      )}
    </motion.div>
  )
}
