import { useState, useRef, useEffect } from 'react'
import { ChevronDown } from 'lucide-react'
import Button from './Button'

/**
 * Simple dropdown menu — design-system actions overflow.
 */
export default function DropdownMenu({
  label = 'More',
  icon: Icon = ChevronDown,
  items = [],
  variant = 'ghost',
  size = 'sm',
  align = 'right',
  className = '',
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    if (!open) return undefined
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  const visible = items.filter((item) => !item.hidden)

  if (visible.length === 0) return null

  return (
    <div className={`relative ${className}`} ref={ref}>
      <Button
        type="button"
        variant={variant}
        size={size}
        onClick={() => setOpen((v) => !v)}
        className="gap-1.5"
        aria-expanded={open}
        aria-haspopup="menu"
      >
        {label}
        <Icon className="w-4 h-4 opacity-60" />
      </Button>
      {open && (
        <div
          role="menu"
          className={`absolute top-full mt-1 min-w-[12rem] py-1 rounded-xl popover-surface z-50 ${
            align === 'right' ? 'right-0' : 'left-0'
          }`}
        >
          {visible.map((item) => (
            <button
              key={item.id || item.label}
              type="button"
              role="menuitem"
              disabled={item.disabled}
              onClick={() => {
                setOpen(false)
                item.onClick?.()
              }}
              className={`popover-item px-3 disabled:opacity-40 disabled:cursor-not-allowed ${
                item.danger ? 'text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30' : ''
              }`}
            >
              {item.icon && <item.icon className="popover-item-icon" />}
              <span>{item.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
