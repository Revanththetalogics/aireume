import { motion, useReducedMotion } from 'framer-motion'

/**
 * PageTransition — wraps each page element for route-level enter/exit animation.
 *
 * Usage:
 *   <Route path="/foo" element={<PageTransition><FooPage /></PageTransition>} />
 *
 * Combined with AnimatePresence in App.jsx this gives smooth cross-fade
 * with a subtle upward slide — the hallmark of Apple's page transitions.
 */

const variants = {
  initial: { opacity: 0, y: 14 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
}

const reducedVariants = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
}

export default function PageTransition({ children }) {
  const shouldReduceMotion = useReducedMotion()
  return (
    <motion.div
      variants={shouldReduceMotion ? reducedVariants : variants}
      initial="initial"
      animate="animate"
      exit="exit"
      transition={shouldReduceMotion ? { duration: 0.15 } : { duration: 0.35, ease: [0.25, 0.1, 0.25, 1] }}
    >
      {children}
    </motion.div>
  )
}
