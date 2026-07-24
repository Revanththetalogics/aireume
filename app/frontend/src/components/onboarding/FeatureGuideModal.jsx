import { ArrowRight, Sparkles } from 'lucide-react'
import ModalOverlay from '../motion/ModalOverlay'

export default function FeatureGuideModal({ open, guide, onDismiss }) {
  if (!guide) return null

  return (
    <ModalOverlay isOpen={open} onClose={onDismiss} ariaLabel={guide.title}>
      <div className="bg-white dark:bg-dark-card rounded-2xl shadow-brand-lg border border-brand-100 dark:border-white/10 p-6 max-w-md w-[min(100vw-2rem,28rem)]">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-brand-50 dark:bg-brand-950/40 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-brand-600 dark:text-brand-300" />
          </div>
          <h2 className="text-lg font-bold text-brand-900 dark:text-brand-100">{guide.title}</h2>
        </div>
        <p className="text-sm text-slate-600 dark:text-dark-text-secondary mb-4">{guide.body}</p>
        {guide.bullets?.length > 0 && (
          <ul className="text-sm text-slate-600 dark:text-dark-text-secondary space-y-2 mb-6 list-disc pl-5">
            {guide.bullets.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        )}
        <button
          type="button"
          onClick={onDismiss}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-brand-600 text-white rounded-xl text-sm font-semibold hover:bg-brand-700 transition-colors"
        >
          {guide.ctaLabel || 'Got it'}
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </ModalOverlay>
  )
}
