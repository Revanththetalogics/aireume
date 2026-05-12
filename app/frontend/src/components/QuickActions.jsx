import { useState, useRef, useEffect } from 'react'
import {
  Check,
  X,
  Clock,
  MoreHorizontal,
  ChevronDown,
  Star,
  Share2,
  Download,
} from 'lucide-react'

/**
 * Quick action buttons for candidate status changes.
 *
 * Props:
 * - candidateId: string/number — ID for API calls
 * - currentStatus: string — current status
 * - onStatusChange: function(id, newStatus) — callback after status change
 * - compact: boolean (default false) — if true, show icon-only buttons
 * - className: string
 */
export default function QuickActions({
  candidateId,
  currentStatus,
  onStatusChange,
  compact = false,
  className = '',
}) {
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const dropdownRef = useRef(null)

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const actions = [
    {
      key: 'shortlisted',
      label: 'Shortlist',
      icon: Check,
      bg: 'bg-emerald-50',
      text: 'text-emerald-700',
      hover: 'hover:bg-emerald-100',
      activeBg: 'bg-emerald-600',
      activeText: 'text-white',
    },
    {
      key: 'rejected',
      label: 'Reject',
      icon: X,
      bg: 'bg-red-50',
      text: 'text-red-700',
      hover: 'hover:bg-red-100',
      activeBg: 'bg-red-600',
      activeText: 'text-white',
    },
    {
      key: 'in-review',
      label: 'Review Later',
      icon: Clock,
      bg: 'bg-slate-50',
      text: 'text-slate-600',
      hover: 'hover:bg-slate-100',
      activeBg: 'bg-slate-600',
      activeText: 'text-white',
    },
  ]

  const moreOptions = [
    { label: 'Compare', icon: Star },
    { label: 'Share', icon: Share2 },
    { label: 'Download', icon: Download },
  ]

  const handleAction = (status) => {
    if (onStatusChange) {
      onStatusChange(candidateId, status)
    }
  }

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {actions.map((action) => {
        const isActive = currentStatus === action.key
        const Icon = action.icon

        return (
          <button
            key={action.key}
            onClick={() => handleAction(action.key)}
            title={compact ? action.label : undefined}
            className={`
              inline-flex items-center justify-center gap-1.5
              rounded-lg font-medium transition-all duration-150
              active:scale-95
              ${compact ? 'w-8 h-8 p-0' : 'px-3 py-1.5 text-sm'}
              ${
                isActive
                  ? `${action.activeBg} ${action.activeText} shadow-sm`
                  : `${action.bg} ${action.text} ${action.hover}`
              }
            `}
          >
            <Icon className="w-4 h-4" />
            {!compact && <span>{action.label}</span>}
          </button>
        )
      })}

      <div className="relative" ref={dropdownRef}>
        <button
          onClick={() => setDropdownOpen((prev) => !prev)}
          title={compact ? 'More' : undefined}
          className={`
            inline-flex items-center justify-center gap-1
            rounded-lg font-medium transition-all duration-150
            active:scale-95
            ${compact ? 'w-8 h-8 p-0' : 'px-2.5 py-1.5 text-sm'}
            bg-white text-slate-600 border border-slate-200
            hover:bg-slate-50 hover:border-slate-300
          `}
        >
          <MoreHorizontal className="w-4 h-4" />
          {!compact && <ChevronDown className="w-3 h-3" />}
        </button>

        {dropdownOpen && (
          <div className="absolute right-0 mt-1.5 w-40 bg-white rounded-xl shadow-brand border border-slate-100 overflow-hidden z-20">
            {moreOptions.map((option) => {
              const OptionIcon = option.icon
              return (
                <button
                  key={option.label}
                  onClick={() => {
                    setDropdownOpen(false)
                    // Future: wire up specific handlers per option
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
                >
                  <OptionIcon className="w-4 h-4 text-slate-400" />
                  <span>{option.label}</span>
                </button>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
