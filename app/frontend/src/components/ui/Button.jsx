import { motion } from 'framer-motion'
import { Loader2 } from 'lucide-react'

/**
 * Button — Apple-style press/hover micro-interactions.
 *
 * Variants: brand, secondary, ghost, danger
 * Sizes: sm, md, lg
 *
 * Usage:
 *   <Button variant="brand" size="md" loading={false} onClick={...}>
 *     Save Changes
 *   </Button>
 */

const variants = {
  brand: 'bg-brand-600 text-white hover:bg-brand-700 shadow-brand-sm hover:shadow-brand',
  secondary: 'bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-dark-card-elevated dark:text-dark-text-primary dark:hover:bg-dark-card',
  ghost: 'bg-transparent text-slate-600 hover:bg-slate-100 dark:text-dark-text-secondary dark:hover:bg-dark-card-elevated',
  danger: 'bg-red-600 text-white hover:bg-red-700 shadow-sm',
}

const sizes = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-4 py-2.5 text-sm',
  lg: 'px-6 py-3 text-base',
}

export default function Button({
  children,
  variant = 'brand',
  size = 'md',
  loading = false,
  disabled = false,
  className = '',
  ...props
}) {
  return (
    <motion.button
      whileHover={{ scale: disabled || loading ? 1 : 1.01 }}
      whileTap={{ scale: disabled || loading ? 1 : 0.97 }}
      transition={{ type: 'spring', stiffness: 400, damping: 17 }}
      className={`
        inline-flex items-center justify-center gap-2
        font-semibold rounded-xl
        transition-colors
        disabled:opacity-50 disabled:cursor-not-allowed
        ${variants[variant]}
        ${sizes[size]}
        ${className}
      `}
      disabled={disabled || loading}
      aria-disabled={disabled || loading}
      aria-busy={loading}
      {...props}
    >
      {loading && <Loader2 className="w-4 h-4 animate-spin" />}
      {children}
    </motion.button>
  )
}
