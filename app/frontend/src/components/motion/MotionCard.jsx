import { motion } from 'framer-motion'

/**
 * MotionCard — a card wrapper with enter animation (fade-up + subtle scale).
 *
 * Provides the "cards appearing one by one" feel that Apple uses throughout
 * iOS Settings, App Store, etc.
 *
 * Usage:
 *   <MotionCard delay={0.05}>
 *     <div className="bg-white rounded-3xl ...">Card content</div>
 *   </MotionCard>
 */

export default function MotionCard({ children, delay = 0, className = '', ...props }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{
        type: 'spring',
        stiffness: 260,
        damping: 24,
        delay,
      }}
      className={className}
      {...props}
    >
      {children}
    </motion.div>
  )
}
