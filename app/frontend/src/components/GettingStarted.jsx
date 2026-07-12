import { useEffect, useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  Briefcase, FileSearch, UserCheck, UserPlus, Share2,
  Check, Circle, X, ChevronRight, PartyPopper, Lock
} from 'lucide-react'
import { useOnboarding } from '../contexts/OnboardingContext'
import { useSubscription } from '../hooks/useSubscription'

const CHECKLIST_ITEMS = [
  { key: 'createdJob', label: 'Create your first requisition', href: '/requisitions', Icon: Briefcase, feature: 'requisitions' },
  { key: 'analyzedResume', label: 'Analyze a resume', href: '/analyze', Icon: FileSearch },
  { key: 'shortlistedCandidate', label: 'Shortlist a candidate', href: '/candidates', Icon: UserCheck },
  { key: 'invitedTeamMember', label: 'Invite a team member', href: '/team', Icon: UserPlus },
  { key: 'sharedWithHM', label: 'Share screening summary with HM', href: '/candidates', Icon: Share2, feature: 'hm_workflow' },
]

export default function GettingStarted() {
  const { checklist, checklistDismissed, dismissChecklist, isChecklistComplete } = useOnboarding()
  const { isFeatureAvailable } = useSubscription()

  const visibleItems = useMemo(
    () => CHECKLIST_ITEMS.filter((item) => !item.feature || isFeatureAvailable(item.feature)),
    [isFeatureAvailable],
  )
  const total = visibleItems.length

  const [celebrating, setCelebrating] = useState(false)

  const completedCount = visibleItems.filter((item) => checklist[item.key]).length
  const allComplete = total > 0 && completedCount === total

  useEffect(() => {
    if (allComplete) {
      setCelebrating(true)
      const timer = setTimeout(() => {
        dismissChecklist()
      }, 5000)
      return () => clearTimeout(timer)
    }
  }, [allComplete, dismissChecklist])

  if (checklistDismissed) return null

  if (celebrating) {
    return (
      <div className="bg-white rounded-xl shadow-lg border border-brand-200 p-6 w-full max-w-sm animate-pulse-once">
        <div className="text-center py-4">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-brand-100 mb-4">
            <PartyPopper className="w-7 h-7 text-brand-600" />
          </div>
          <h3 className="text-lg font-bold text-brand-900 mb-1">You're all set!</h3>
          <p className="text-sm text-slate-500">
            You've completed all the getting started steps. Welcome to ARIA!
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl shadow-lg border border-slate-200 p-6 w-full max-w-sm relative">
      <button
        onClick={dismissChecklist}
        className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 transition-colors"
        aria-label="Dismiss checklist"
      >
        <X className="w-4 h-4" />
      </button>

      <h3 className="text-base font-bold text-brand-900 pr-6">Getting Started with ARIA</h3>
      <p className="text-xs text-slate-500 mt-1 mb-4">
        Complete these steps to get the most out of your recruitment intelligence.
      </p>

      <div className="space-y-2 mb-5">
        {visibleItems.map(({ key, label, href, Icon }) => {
          const done = checklist[key]
          return (
            <Link
              key={key}
              to={href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors group ${
                done ? 'bg-green-50/60' : 'hover:bg-slate-50'
              }`}
            >
              {done ? (
                <span className="flex items-center justify-center w-5 h-5 rounded-full bg-green-500 text-white shrink-0">
                  <Check className="w-3 h-3" />
                </span>
              ) : (
                <Circle className="w-5 h-5 text-slate-300 shrink-0" />
              )}
              <span
                className={`flex-1 text-sm font-medium ${
                  done ? 'text-slate-400 line-through' : 'text-slate-700 group-hover:text-brand-600'
                }`}
              >
                {label}
              </span>
              {!done && (
                <ChevronRight className="w-3.5 h-3.5 text-slate-300 group-hover:text-brand-500 shrink-0 transition-colors" />
              )}
            </Link>
          )
        })}
      </div>

      {!isFeatureAvailable('requisitions') && (
        <p className="text-xs text-slate-500 mb-4 flex items-start gap-1.5">
          <Lock className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          On Starter, use <Link to="/analyze" className="text-brand-600 font-medium hover:underline">Analyze</Link> to screen resumes — no requisition needed.
        </p>
      )}

      <div>
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs font-semibold text-slate-500">Progress</span>
          <span className="text-xs font-bold text-brand-600">{completedCount}/{total} complete</span>
        </div>
        <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
          <div
            className="h-full rounded-full bg-brand-500 transition-all duration-500 ease-out"
            style={{ width: `${total ? (completedCount / total) * 100 : 0}%` }}
          />
        </div>
      </div>
    </div>
  )
}
