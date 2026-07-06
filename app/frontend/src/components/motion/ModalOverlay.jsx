import { useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

const FOCUSABLE = 'a[href],button:not([disabled]),textarea,input,select,[tabindex]:not([tabindex="-1"])'

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

export default function ModalOverlay({
  isOpen,
  onClose,
  children,
  zIndex = 'z-50',
  ariaLabel,
  labelledBy,
}) {
  const contentRef = useRef(null)
  const previouslyFocused = useRef(null)

  // Escape to close + basic focus trap (dependency-free)
  useEffect(() => {
    if (!isOpen) return
    previouslyFocused.current = document.activeElement

    const focusFirst = () => {
      const node = contentRef.current
      if (!node) return
      const focusable = node.querySelectorAll(FOCUSABLE)
      if (focusable.length) focusable[0].focus()
      else node.focus()
    }
    // Defer to allow the animated content to mount
    const t = setTimeout(focusFirst, 50)

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose?.()
        return
      }
      if (e.key === 'Tab' && contentRef.current) {
        const focusable = Array.from(contentRef.current.querySelectorAll(FOCUSABLE))
          .filter((el) => el.offsetParent !== null)
        if (focusable.length === 0) return
        const first = focusable[0]
        const last = focusable[focusable.length - 1]
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault()
          last.focus()
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault()
          first.focus()
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => {
      clearTimeout(t)
      document.removeEventListener('keydown', handleKeyDown)
      // Restore focus to the trigger element
      if (previouslyFocused.current && previouslyFocused.current.focus) {
        previouslyFocused.current.focus()
      }
    }
  }, [isOpen, onClose])

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
            ref={contentRef}
            role="dialog"
            aria-modal="true"
            aria-label={labelledBy ? undefined : ariaLabel}
            aria-labelledby={labelledBy}
            tabIndex={-1}
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
