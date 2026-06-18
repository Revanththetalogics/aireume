import { useState, useRef } from 'react'
import { motion } from 'framer-motion'
import { AlertCircle } from 'lucide-react'

/**
 * FloatingInput — Apple-style floating label input.
 *
 * The label floats up on focus with a spring animation.
 * Error state triggers a shake animation.
 *
 * Usage:
 *   <FloatingInput label="Email" type="email" value={email} onChange={setEmail} error={error} />
 */

export default function FloatingInput({
  label,
  value,
  onChange,
  type = 'text',
  error,
  disabled = false,
  className = '',
  ...props
}) {
  const [focused, setFocused] = useState(false)
  const inputRef = useRef(null)
  const hasValue = value !== '' && value != null

  const isActive = focused || hasValue

  return (
    <motion.div
      className={`relative ${className}`}
      animate={error ? { x: [-4, 4, -4, 4, 0] } : {}}
      transition={{ duration: 0.4 }}
    >
      <div className="relative">
        <input
          ref={inputRef}
          type={type}
          value={value}
          onChange={e => onChange(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          disabled={disabled}
          className={`
            w-full px-4 py-3.5 pt-5
            bg-white dark:bg-dark-card
            rounded-xl
            ring-1 transition-all duration-200
            text-sm text-slate-800 dark:text-dark-text-primary
            outline-none
            disabled:opacity-50 disabled:cursor-not-allowed
            ${error
              ? 'ring-red-300 focus:ring-2 focus:ring-red-500'
              : focused
                ? 'ring-brand-500 ring-2'
                : 'ring-slate-200 dark:ring-white/10 hover:ring-slate-300'
            }
          `}
          placeholder=" "
          {...props}
        />
        <label
          className={`
            absolute left-4 transition-all duration-200 pointer-events-none
            ${isActive
              ? 'top-2 text-[10px] font-semibold uppercase tracking-wider'
              : 'top-1/2 -translate-y-1/2 text-sm'
            }
            ${error
              ? 'text-red-500'
              : focused
                ? 'text-brand-600'
                : 'text-slate-400'
            }
          `}
        >
          {label}
        </label>
      </div>
      {error && (
        <motion.p
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-1 mt-1.5 text-xs text-red-600"
        >
          <AlertCircle className="w-3 h-3" />
          {error}
        </motion.p>
      )}
    </motion.div>
  )
}
