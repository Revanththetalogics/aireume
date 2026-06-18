import { motion, AnimatePresence } from 'framer-motion'
import { Search, X } from 'lucide-react'
import { useState, useEffect, useRef } from 'react'

/**
 * SearchOverlay — Full-screen search overlay with backdrop blur.
 *
 * Spring animation on open, instant filter results with stagger.
 *
 * Usage:
 *   <SearchOverlay
 *     isOpen={searchOpen}
 *     onClose={() => setSearchOpen(false)}
 *     items={candidates}
 *     renderItem={(item) => <CandidateRow key={item.id} {...item} />}
 *     placeholder="Search candidates..."
 *   />
 */

export default function SearchOverlay({ isOpen, onClose, items = [], renderItem, placeholder = 'Search...' }) {
  const [query, setQuery] = useState('')
  const inputRef = useRef(null)

  useEffect(() => {
    if (isOpen) {
      setQuery('')
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [isOpen])

  // Filter items based on query
  const filtered = query.trim()
    ? items.filter(item => {
        const searchStr = JSON.stringify(item).toLowerCase()
        return searchStr.includes(query.toLowerCase())
      })
    : items

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/30 backdrop-blur-md"
            onClick={onClose}
          />

          {/* Search panel */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -10 }}
            transition={{ type: 'spring', stiffness: 300, damping: 28 }}
            className="relative max-w-2xl mx-auto mt-20 mx-4 bg-white dark:bg-dark-card rounded-2xl shadow-2xl overflow-hidden"
          >
            {/* Search input */}
            <div className="flex items-center gap-3 px-5 py-4 border-b border-slate-100 dark:border-white/10">
              <Search className="w-5 h-5 text-slate-400 shrink-0" />
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder={placeholder}
                className="flex-1 text-base bg-transparent outline-none text-slate-800 dark:text-dark-text-primary placeholder-slate-400"
              />
              <button
                onClick={onClose}
                className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-dark-card-elevated text-slate-400"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Results */}
            <div className="max-h-96 overflow-y-auto">
              {filtered.length === 0 ? (
                <div className="px-5 py-8 text-center text-sm text-slate-400">
                  No results found
                </div>
              ) : (
                <motion.div
                  initial="hidden"
                  animate="show"
                  variants={{
                    hidden: {},
                    show: { transition: { staggerChildren: 0.03 } },
                  }}
                >
                  {filtered.slice(0, 20).map(item => (
                    <motion.div
                      key={item.id}
                      variants={{
                        hidden: { opacity: 0, y: 4 },
                        show: { opacity: 1, y: 0 },
                      }}
                      onClick={onClose}
                    >
                      {renderItem(item)}
                    </motion.div>
                  ))}
                </motion.div>
              )}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}
