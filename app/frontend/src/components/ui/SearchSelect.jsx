import { useState, useRef, useEffect, useId } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, ChevronDown, Check, X } from 'lucide-react'

/**
 * SearchSelect — design-system combobox with search + rich option rows.
 *
 * Usage:
 *   <SearchSelect
 *     label="Candidate"
 *     placeholder="Search candidates…"
 *     options={candidates}
 *     value={selectedId}
 *     onChange={(id, option) => setSelected(option)}
 *     getOptionValue={(c) => c.id}
 *     getOptionLabel={(c) => c.name || c.email}
 *     renderOption={(c, { selected }) => (...)}
 *   />
 */
export default function SearchSelect({
  label,
  placeholder = 'Search…',
  options = [],
  value,
  onChange,
  getOptionValue = (o) => o?.id,
  getOptionLabel = (o) => String(o ?? ''),
  renderOption,
  disabled = false,
  required = false,
  emptyMessage = 'No matches',
  className = '',
}) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const rootRef = useRef(null)
  const inputRef = useRef(null)
  const listId = useId()

  const selected = options.find((o) => String(getOptionValue(o)) === String(value))

  const filtered = query.trim()
    ? options.filter((o) => {
        const labelText = getOptionLabel(o).toLowerCase()
        const extra = JSON.stringify(o).toLowerCase()
        const q = query.toLowerCase()
        return labelText.includes(q) || extra.includes(q)
      })
    : options

  useEffect(() => {
    function onDocClick(e) {
      if (rootRef.current && !rootRef.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onDocClick)
    return () => document.removeEventListener('mousedown', onDocClick)
  }, [])

  function pick(option) {
    onChange?.(getOptionValue(option), option)
    setQuery('')
    setOpen(false)
  }

  function clear(e) {
    e.stopPropagation()
    onChange?.('', null)
    setQuery('')
  }

  const defaultRender = (option, { selected: isSelected }) => (
    <div className="flex items-center justify-between gap-2 min-w-0">
      <span className={`text-sm truncate ${isSelected ? 'font-semibold text-brand-800' : 'text-slate-700 dark:text-dark-text-primary'}`}>
        {getOptionLabel(option)}
      </span>
      {isSelected && <Check className="w-4 h-4 text-brand-600 shrink-0" />}
    </div>
  )

  return (
    <div ref={rootRef} className={`relative ${className}`}>
      {label && (
        <label className="block text-sm font-semibold text-slate-700 dark:text-dark-text-secondary mb-1.5">
          {label}
          {required && <span className="text-red-500 ml-0.5">*</span>}
        </label>
      )}

      <button
        type="button"
        disabled={disabled}
        onClick={() => {
          setOpen((v) => !v)
          setTimeout(() => inputRef.current?.focus(), 50)
        }}
        className={`w-full flex items-center gap-2 px-3.5 py-2.5 rounded-xl ring-1 text-left transition-all outline-none
          ${open ? 'ring-2 ring-brand-500 bg-white dark:bg-dark-card' : 'ring-slate-200 dark:ring-white/10 bg-white dark:bg-dark-card hover:ring-slate-300'}
          disabled:opacity-50 disabled:cursor-not-allowed`}
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-controls={listId}
      >
        <Search className="w-4 h-4 text-slate-400 shrink-0" />
        <span className={`flex-1 text-sm truncate ${selected ? 'text-slate-800 dark:text-dark-text-primary font-medium' : 'text-slate-400'}`}>
          {selected ? getOptionLabel(selected) : placeholder}
        </span>
        {selected && !disabled && (
          <span
            role="button"
            tabIndex={0}
            onClick={clear}
            onKeyDown={(e) => e.key === 'Enter' && clear(e)}
            className="p-0.5 rounded hover:bg-slate-100 dark:hover:bg-dark-card-elevated text-slate-400"
            aria-label="Clear selection"
          >
            <X className="w-3.5 h-3.5" />
          </span>
        )}
        <ChevronDown className={`w-4 h-4 text-slate-400 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.98 }}
            transition={{ type: 'spring', stiffness: 400, damping: 28 }}
            className="absolute z-50 mt-1 w-full popover-surface rounded-xl py-1 shadow-brand-lg max-h-64 flex flex-col"
          >
            <div className="px-2 pt-2 pb-1 border-b border-brand-50 dark:border-white/10">
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={placeholder}
                className="w-full px-2.5 py-1.5 text-sm bg-slate-50 dark:bg-dark-card-elevated rounded-lg outline-none text-slate-800 dark:text-dark-text-primary placeholder-slate-400"
              />
            </div>
            <ul id={listId} role="listbox" className="overflow-y-auto py-1 flex-1">
              {filtered.length === 0 ? (
                <li className="px-4 py-3 text-sm text-slate-400 text-center">{emptyMessage}</li>
              ) : (
                filtered.slice(0, 30).map((option) => {
                  const optValue = getOptionValue(option)
                  const isSelected = String(optValue) === String(value)
                  return (
                    <li key={optValue} role="option" aria-selected={isSelected}>
                      <button
                        type="button"
                        onClick={() => pick(option)}
                        className={`w-full text-left px-3 py-2.5 transition-colors popover-item ${
                          isSelected ? 'bg-brand-50/80 dark:bg-dark-card-elevated' : ''
                        }`}
                      >
                        {(renderOption || defaultRender)(option, { selected: isSelected })}
                      </button>
                    </li>
                  )
                })
              )}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
