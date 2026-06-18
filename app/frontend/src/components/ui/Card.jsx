import { motion } from 'framer-motion'

/**
 * Card — Apple-style hover lift with spring physics.
 *
 * Usage:
 *   <Card hoverable className="p-6">
 *     Content here
 *   </Card>
 */

export default function Card({ children, hoverable = false, className = '', ...props }) {
  return (
    <motion.div
      className={`
        bg-white dark:bg-dark-card
        rounded-2xl
        ring-1 ring-brand-100 dark:ring-white/10
        shadow-brand-sm dark:shadow-dark-brand
        ${hoverable ? 'card-interactive' : ''}
        ${className}
      `}
      {...(hoverable && {
        whileHover: { y: -2, boxShadow: '0 8px 32px rgba(124,58,237,0.16)' },
        transition: { type: 'spring', stiffness: 300, damping: 20 },
      })}
      {...props}
    >
      {children}
    </motion.div>
  )
}
