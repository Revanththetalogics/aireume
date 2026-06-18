import { motion, AnimatePresence } from 'framer-motion'

/**
 * ModalOverlay — backdrop blur fade-in + content spring scale.
 *
 * Replaces the manual `bg-black/30 backdrop-blur-sm` + `animate-fade-up`
 * pattern used throughout the app with proper spring physics.
 *
 * Usage:
 *   <ModalOverlay isOpen={showModal} onClose={() => setShowModal(false)}>
 *     <div className="bg-white rounded-3xl p-8">Modal content</div>
 *   </ModalOverlay>
 */

const backdropVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.2 } },
  exit: { opacity: 0, transition: { duration: 0.15 } },
}

const contentVariants = {
  hidden: { opacity: 0, scale: 0.92, y: 16 },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { type: 'spring', stiffness: 300, damping: 28 },
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    y: 8,
    transition: { duration: 0.15 },
  },
}

export default function ModalOverlay({ isOpen, onClose, children, zIndex = 'z-50' }) {
  return (
    <AnimatePresence>
      {isOpen && (
        <div className={`fixed inset-0 flex items-center justify-center p-4 ${zIndex}`}>
          {/* Backdrop */}
          <motion.div
            variants={backdropVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="absolute inset-0 bg-black/30 backdrop-blur-sm"
            onClick={onClose}
          />
          {/* Content */}
          <motion.div
            variants={contentVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="relative"
          >
            {children}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}
