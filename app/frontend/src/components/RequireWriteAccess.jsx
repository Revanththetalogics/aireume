import { Navigate } from 'react-router-dom'
import { Eye } from 'lucide-react'
import usePermissions from '../hooks/usePermissions'
import { VIEWER_READ_ONLY_MESSAGE } from '../lib/rbac'

/**
 * Redirect viewers away from write-only routes (e.g. /analyze).
 * Recruiters and admins pass through unchanged.
 */
export default function RequireWriteAccess({ children, redirectTo = '/' }) {
  const { canWrite } = usePermissions()

  if (!canWrite) {
    return (
      <Navigate
        to={redirectTo}
        replace
        state={{ viewerBlocked: true, message: VIEWER_READ_ONLY_MESSAGE }}
      />
    )
  }

  return children
}

export function ViewerReadOnlyBanner() {
  const { isViewer } = usePermissions()
  if (!isViewer) return null

  return (
    <div
      role="status"
      className="flex items-center gap-2 px-4 py-2.5 mb-4 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/50 text-amber-900 dark:text-amber-200 text-sm"
    >
      <Eye className="w-4 h-4 shrink-0" aria-hidden />
      <span>{VIEWER_READ_ONLY_MESSAGE}</span>
    </div>
  )
}
