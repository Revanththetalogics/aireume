import { useState, useRef, useEffect, useId } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, ChevronDown, Check, X } from 'lucide-react'

/**
 * SearchSelect — design-system combobox with a single search input + rich option rows.
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
      if (rootRef.current && !rootRef.current.contains(e.target)) {
        setOpen(false)
        setQuery('')
      }
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
    inputRef.current?.focus()
  }

  const displayValue = open ? query : (selected ? getOptionLabel(selected) : '')

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

      <div
        className={`w-full flex items-center gap-2 px-3.5 py-2.5 rounded-xl ring-1 text-left transition-all
          ${open ? 'ring-2 ring-brand-500 bg-white dark:bg-dark-card' : 'ring-slate-200 dark:ring-white/10 bg-white dark:bg-dark-card hover:ring-slate-300'}
          ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <Search className="w-4 h-4 text-slate-400 shrink-0" />
        <input
          ref={inputRef}
          type="text"
          disabled={disabled}
          value={displayValue}
          placeholder={placeholder}
          onChange={(e) => {
            setQuery(e.target.value)
            setOpen(true)
          }}
          onFocus={() => {
            setOpen(true)
            if (selected && !query) setQuery('')
          }}
          className="flex-1 min-w-0 text-sm bg-transparent outline-none text-slate-800 dark:text-dark-text-primary placeholder-slate-400 font-medium"
          aria-expanded={open}
          aria-haspopup="listbox"
          aria-controls={listId}
          role="combobox"
          autoComplete="off"
        />
        {selected && !disabled && (
          <button
            type="button"
            onClick={clear}
            className="p-0.5 rounded hover:bg-slate-100 dark:hover:bg-dark-card-elevated text-slate-400"
            aria-label="Clear selection"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
        <ChevronDown className={`w-4 h-4 text-slate-400 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
      </div>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.98 }}
            transition={{ type: 'spring', stiffness: 400, damping: 28 }}
            className="absolute z-50 mt-1 w-full popover-surface rounded-xl py-1 shadow-brand-lg max-h-64 flex flex-col"
          >
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
