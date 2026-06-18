import { motion } from 'framer-motion'

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

export default function PageTransition({ children }) {
  return (
    <motion.div
      variants={variants}
      initial="initial"
      animate="animate"
      exit="exit"
      transition={{ duration: 0.35, ease: [0.25, 0.1, 0.25, 1] }}
    >
      {children}
    </motion.div>
  )
}
