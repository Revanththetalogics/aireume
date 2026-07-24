import {
  FileText,
  UserCheck,
  LayoutTemplate,
  Users,
  Share2,
  CreditCard,
  Settings,
  Mic,
} from 'lucide-react'

/** Default checklist shape — keep in sync with backend DEFAULT_CHECKLIST */
export const DEFAULT_READINESS_CHECKLIST = {
  createdJob: false,
  analyzedResume: false,
  shortlistedCandidate: false,
  invitedTeamMember: false,
  sharedWithHM: false,
  reviewedSubscription: false,
  configuredRequisitionWorkflow: false,
  configuredInterviewSettings: false,
}

/**
 * Workspace readiness tasks — product usage + tenant configuration.
 * @type {Array<{ key: string, label: string, description?: string, href: string, feature?: string|null, adminOnly?: boolean, Icon: import('lucide-react').LucideIcon }>}
 */
export const WORKSPACE_READINESS_ITEMS = [
  {
    key: 'analyzedResume',
    label: 'Analyze a resume',
    description: 'Run your first screening in Analyze',
    href: '/analyze',
    Icon: FileText,
  },
  {
    key: 'shortlistedCandidate',
    label: 'Shortlist a candidate',
    description: 'Mark a strong fit from Candidates',
    href: '/candidates',
    Icon: UserCheck,
  },
  {
    key: 'createdJob',
    label: 'Create your first requisition',
    description: 'Set up a role in JD Library',
    href: '/requisitions',
    feature: 'requisitions',
    Icon: LayoutTemplate,
  },
  {
    key: 'invitedTeamMember',
    label: 'Invite a team member',
    description: 'Add recruiters or hiring managers',
    href: '/team',
    adminOnly: true,
    Icon: Users,
  },
  {
    key: 'sharedWithHM',
    label: 'Share screening summary with HM',
    description: 'Generate a hiring manager debrief',
    href: '/candidates',
    feature: 'hm_workflow',
    Icon: Share2,
  },
  {
    key: 'reviewedSubscription',
    label: 'Review plan & usage limits',
    description: 'Confirm your tier and monthly analyses',
    href: '/settings?tab=subscription',
    adminOnly: true,
    Icon: CreditCard,
  },
  {
    key: 'configuredRequisitionWorkflow',
    label: 'Review requisition workflow',
    description: 'Intake gate and HM pipeline access',
    href: '/settings?tab=requisitions',
    feature: 'requisitions',
    adminOnly: true,
    Icon: Settings,
  },
  {
    key: 'configuredInterviewSettings',
    label: 'Configure AI interview settings',
    description: 'Voice identity and screening defaults',
    href: '/settings?tab=interviews',
    feature: 'ai_interviews',
    adminOnly: true,
    Icon: Mic,
  },
]

/** Keys hidden for non-admin roles (admin sees all plan-gated items). */
const HIDDEN_KEYS_BY_ROLE = {
  viewer: new Set([
    'invitedTeamMember',
    'reviewedSubscription',
    'configuredRequisitionWorkflow',
    'configuredInterviewSettings',
    'createdJob',
    'sharedWithHM',
  ]),
  hiring_manager: new Set([
    'invitedTeamMember',
    'reviewedSubscription',
    'configuredRequisitionWorkflow',
    'configuredInterviewSettings',
  ]),
  recruiter: new Set([
    'reviewedSubscription',
    'configuredRequisitionWorkflow',
    'configuredInterviewSettings',
  ]),
}

const ROLE_LABEL_OVERRIDES = {
  viewer: {
    analyzedResume: 'Browse screening reports',
    shortlistedCandidate: 'Review candidate statuses',
  },
  hiring_manager: {
    analyzedResume: 'Review screened candidates',
    createdJob: 'Review your requisitions',
  },
}

/**
 * Filter readiness items for the current user/plan/role.
 */
export function getVisibleReadinessItems({ isFeatureAvailable, isAdmin = false, role = 'recruiter' }) {
  const hidden = isAdmin ? new Set() : (HIDDEN_KEYS_BY_ROLE[role] || HIDDEN_KEYS_BY_ROLE.recruiter)
  const labels = ROLE_LABEL_OVERRIDES[role] || {}

  return WORKSPACE_READINESS_ITEMS.filter((item) => {
    if (!isAdmin && item.adminOnly) return false
    if (hidden.has(item.key)) return false
    if (item.feature && !isFeatureAvailable(item.feature)) return false
    return true
  }).map((item) => ({
    ...item,
    label: labels[item.key] || item.label,
  }))
}

export function isReadinessComplete(checklist, visibleItems) {
  return visibleItems.every((item) => checklist[item.key])
}

export function readinessProgress(checklist, visibleItems) {
  const total = visibleItems.length
  const completed = visibleItems.filter((item) => checklist[item.key]).length
  return { completed, total, percent: total ? Math.round((completed / total) * 100) : 0 }
}
