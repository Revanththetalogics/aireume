import { Loader2, ClipboardList, AlertTriangle } from 'lucide-react'
import { Button, Sheet } from '../ui'
import { LIVE_SCREEN } from '../../lib/uxLabels'

/**
 * Gate before entering Live Screen Kit — kit loading or empty.
 */
export default function LiveScreenKitReadinessGate({
  open,
  onClose,
  state,
  onStartWithFallback,
  onRetry,
}) {
  const isLoading = state === 'loading'

  return (
    <Sheet isOpen={open} onClose={onClose}>
      <div className="p-6 flex flex-col items-center text-center gap-4">
        <h2 className="text-lg font-bold text-brand-900">
          {isLoading ? LIVE_SCREEN.readinessLoading : LIVE_SCREEN.readinessEmpty}
        </h2>

        {isLoading ? (
          <Loader2 className="w-10 h-10 text-brand-600 animate-spin" />
        ) : (
          <div className="w-12 h-12 rounded-2xl bg-amber-50 ring-1 ring-amber-200 flex items-center justify-center">
            <AlertTriangle className="w-6 h-6 text-amber-600" />
          </div>
        )}

        <p className="text-sm text-slate-600 max-w-sm leading-relaxed">
          {isLoading ? LIVE_SCREEN.readinessLoadingHint : LIVE_SCREEN.readinessEmptyHint}
        </p>

        <div className="flex flex-col sm:flex-row gap-2 w-full max-w-xs pt-2">
          {isLoading ? (
            <Button variant="secondary" className="w-full" onClick={onClose}>
              {LIVE_SCREEN.waitCta}
            </Button>
          ) : (
            <>
              {onStartWithFallback && (
                <Button variant="brand" className="w-full gap-2" onClick={onStartWithFallback}>
                  <ClipboardList className="w-4 h-4" />
                  {LIVE_SCREEN.useFallbackCta}
                </Button>
              )}
              <Button variant="secondary" className="w-full" onClick={onClose}>
                Close
              </Button>
            </>
          )}
          {onRetry && (
            <Button variant="ghost" size="sm" onClick={onRetry}>
              Refresh status
            </Button>
          )}
        </div>
      </div>
    </Sheet>
  )
}
