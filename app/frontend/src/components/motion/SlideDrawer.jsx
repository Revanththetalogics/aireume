import { motion, AnimatePresence } from 'framer-motion'

/**
 * SlideDrawer — right-slide panel with backdrop.
 *
 * Replaces the manual drawer pattern (fixed inset-0 + ml-auto + animate-slide-in-right)
 * with spring physics for the slide and fade for the backdrop.
 *
 * Usage:
 *   <SlideDrawer isOpen={showDetail} onClose={() => setShowDetail(false)} width="max-w-2xl">
 *     <DetailContent />
 *   </SlideDrawer>
 */

const backdropVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.2 } },
  exit: { opacity: 0, transition: { duration: 0.15 } },
}

const panelVariants = {
  hidden: { x: '100%' },
  visible: {
    x: 0,
    transition: { type: 'spring', stiffness: 300, damping: 32 },
  },
  exit: {
    x: '100%',
    transition: { type: 'spring', stiffness: 300, damping: 32 },
  },
}

export default function SlideDrawer({ isOpen, onClose, children, width = 'max-w-2xl' }) {
  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex">
          {/* Backdrop */}
          <motion.div
            variants={backdropVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="absolute inset-0 bg-black/20 backdrop-blur-sm"
            onClick={onClose}
          />
          {/* Panel */}
          <motion.div
            variants={panelVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className={`relative ml-auto w-full ${width} bg-white shadow-2xl overflow-y-auto`}
          >
            {children}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}
