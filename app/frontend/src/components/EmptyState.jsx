import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

export default function EmptyState({
  icon: Icon,
  title,
  description,
  actionLabel,
  onAction,
  actionHref,
  className = '',
}) {
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setMounted(true), 10)
    return () => clearTimeout(t)
  }, [])

  return (
    <div
      className={`flex flex-col items-center justify-center text-center ${className} ${
        mounted ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3'
      } transition-all duration-500 ease-out`}
    >
      {Icon && (
        <div className="w-12 h-12 rounded-full bg-brand-100 flex items-center justify-center mb-4">
          <Icon className="w-6 h-6 text-brand-500" />
        </div>
      )}
      {title && (
        <h3 className="text-lg font-semibold text-slate-800 mb-1">{title}</h3>
      )}
      {description && (
        <p className="text-sm text-slate-500 max-w-sm text-center mb-5">{description}</p>
      )}
      {actionLabel && (onAction || actionHref) && (
        <>
          {actionHref ? (
            <Link
              to={actionHref}
              className="px-4 py-2 btn-brand text-white text-sm font-bold rounded-lg shadow-brand-sm"
            >
              {actionLabel}
            </Link>
          ) : (
            <button
              onClick={onAction}
              className="px-4 py-2 btn-brand text-white text-sm font-bold rounded-lg shadow-brand-sm"
            >
              {actionLabel}
            </button>
          )}
        </>
      )}
    </div>
  )
}
