import { useState, useRef, useEffect } from 'react'
import { useAnalysisProgress } from '../hooks/useAnalysisProgress'
import { Loader2, CheckCircle2, XCircle, ChevronDown } from 'lucide-react'

function StatusIcon({ status }) {
  if (status === 'completed') {
    return <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
  }
  if (status === 'error') {
    return <XCircle className="w-4 h-4 text-red-500 shrink-0" />
  }
  return <Loader2 className="w-4 h-4 text-brand-600 animate-spin shrink-0" />
}

export default function ProgressBadge() {
  const { isActive, completed, total, items } = useAnalysisProgress()
  const [popoverOpen, setPopoverOpen] = useState(false)
  const [showComplete, setShowComplete] = useState(false)
  const popoverRef = useRef(null)
  const wasActiveRef = useRef(false)

  // Track when analysis goes from active -> inactive to show brief complete state
  useEffect(() => {
    if (isActive) {
      wasActiveRef.current = true
      setShowComplete(false)
    } else if (wasActiveRef.current) {
      setShowComplete(true)
      const timer = setTimeout(() => setShowComplete(false), 3000)
      wasActiveRef.current = false
      return () => clearTimeout(timer)
    }
  }, [isActive])

  // Close popover on outside click
  useEffect(() => {
    function handleClick(e) {
      if (popoverRef.current && !popoverRef.current.contains(e.target)) {
        setPopoverOpen(false)
      }
    }
    if (popoverOpen) {
      document.addEventListener('mousedown', handleClick)
    }
    return () => document.removeEventListener('mousedown', handleClick)
  }, [popoverOpen])

  if (!isActive && !showComplete) return null

  const allDone = !isActive && showComplete

  return (
    <div ref={popoverRef} className="relative">
      <button
        onClick={() => setPopoverOpen((v) => !v)}
        className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-all duration-200 ${
          allDone
            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
            : 'bg-brand-50 text-brand-700 border border-brand-200 hover:bg-brand-100'
        }`}
        aria-label="Analysis progress"
      >
        {allDone ? (
          <>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
            <span>Complete</span>
          </>
        ) : (
          <>
            <Loader2 className="w-4 h-4 text-brand-600 animate-spin" />
            <span>
              Analyzing {completed}/{total}...
            </span>
          </>
        )}
        {!allDone && (
          <ChevronDown
            className={`w-3.5 h-3.5 text-brand-500 transition-transform duration-200 ${
              popoverOpen ? 'rotate-180' : ''
            }`}
          />
        )}
      </button>

      {/* Popover */}
      {popoverOpen && !allDone && (
        <div className="absolute right-0 top-full mt-2 w-72 bg-white border border-brand-100 rounded-xl shadow-brand-lg z-50 animate-fade-up overflow-hidden">
          <div className="px-4 py-3 border-b border-brand-50 flex items-center justify-between">
            <span className="text-sm font-semibold text-slate-800">Analysis Progress</span>
            <span className="text-xs font-medium text-brand-600 bg-brand-50 rounded-full px-2 py-0.5">
              {completed}/{total}
            </span>
          </div>

          <div className="max-h-64 overflow-y-auto py-1">
            {items.length === 0 ? (
              <div className="px-4 py-3 text-sm text-slate-400">No files yet...</div>
            ) : (
              items.map((item) => (
                <div
                  key={item.filename}
                  className="flex items-center gap-2.5 px-4 py-2 hover:bg-brand-50/60 transition-colors"
                >
                  <StatusIcon status={item.status} />
                  <span
                    className="text-sm text-slate-700 truncate flex-1 min-w-0"
                    title={item.filename}
                  >
                    {item.filename}
                  </span>
                </div>
              ))
            )}
          </div>

          {/* Progress bar */}
          {total > 0 && (
            <div className="px-4 pb-3">
              <div className="h-1.5 bg-brand-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-brand-500 to-brand-600 rounded-full transition-all duration-500"
                  style={{ width: `${total > 0 ? (completed / total) * 100 : 0}%` }}
                />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
