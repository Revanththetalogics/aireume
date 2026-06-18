import { motion, AnimatePresence } from 'framer-motion'

/**
 * Sheet — Bottom-sheet on mobile, side-drawer on desktop.
 *
 * Spring physics for open/close with backdrop blur fade.
 *
 * Usage:
 *   <Sheet isOpen={showDetail} onClose={() => setShowDetail(false)}>
 *     <DetailContent />
 *   </Sheet>
 */

const backdropVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.2 } },
  exit: { opacity: 0, transition: { duration: 0.15 } },
}

export default function Sheet({ isOpen, onClose, children, maxWidth = 'max-w-2xl' }) {
  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50">
          {/* Backdrop */}
          <motion.div
            variants={backdropVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="absolute inset-0 bg-black/20 backdrop-blur-sm"
            onClick={onClose}
          />

          {/* Desktop: right drawer */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', stiffness: 300, damping: 32 }}
            className={`hidden md:block absolute right-0 top-0 bottom-0 w-full ${maxWidth} bg-white dark:bg-dark-card shadow-2xl overflow-y-auto ml-auto`}
          >
            {children}
          </motion.div>

          {/* Mobile: bottom sheet */}
          <motion.div
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', stiffness: 300, damping: 32 }}
            className="md:hidden absolute bottom-0 left-0 right-0 bg-white dark:bg-dark-card rounded-t-3xl shadow-2xl overflow-y-auto max-h-[85vh]"
          >
            {/* Drag handle */}
            <div className="sticky top-0 flex justify-center py-3 bg-white dark:bg-dark-card rounded-t-3xl border-b border-slate-100 dark:border-white/10">
              <div className="w-10 h-1 rounded-full bg-slate-300 dark:bg-slate-600" />
            </div>
            {children}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}
