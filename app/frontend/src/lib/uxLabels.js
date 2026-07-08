/**
 * Centralized user-facing labels — single vocabulary across the app.
 * API paths may still use legacy names (templates, voice, etc.).
 */

export const NAV = {
  home: 'Home',
  roles: 'Roles',
  analyze: 'Analyze',
  candidates: 'Candidates',
  activity: 'Activity',
  interviews: 'Interviews',
  compare: 'Compare',
  pipeline: 'Pipeline',
  projects: 'Projects',
  analytics: 'Analytics',
  team: 'Team',
  settings: 'Settings',
  interviewReview: 'Interview Review',
}

export const ROLES = {
  pageTitle: 'Roles',
  pageSubtitle: 'Job descriptions, skills, and screening weights for each opening',
  createCta: 'New Role',
  emptyHint: 'Create a role to start screening resumes against it.',
}

export const INTERVIEW = {
  /** AI bot calls the candidate */
  aiScreenCall: 'AI Screen Call',
  aiScreenCallHint: 'ARIA calls the candidate — Quick, Standard, or Deep',
  newScreenCall: 'New AI Screen Call',
  newScreenCallSubtitle: 'Pick a candidate and role, then choose call depth',
  rescheduleCall: 'Reschedule call',
  /** Recruiter calls with kit */
  liveScreenKit: 'Live Screen Kit',
  liveScreenKitHint: 'You call the candidate using ARIA\'s interview questions and scorecard',
  hubTitle: 'Interviews',
  hubSubtitle: 'AI phone screens — scheduled, in progress, and completed',
  quick: 'Quick Screen',
  standard: 'Standard Interview',
  deep: 'Deep Assessment',
  viewBySession: 'By session',
  viewByCandidate: 'By candidate',
  needsAttention: 'Needs attention',
  upcoming: 'Upcoming',
  recent: 'Recent',
  settingsLink: 'Interview settings',
}

export const LIVE_SCREEN = {
  readinessLoading: 'Interview kit is still generating',
  readinessLoadingHint: 'Targeted questions are being prepared from the screening analysis. Start the live call once the kit is ready.',
  readinessEmpty: 'No interview questions available yet',
  readinessEmptyHint: 'The AI kit did not generate questions for this report. You can use standard probe questions based on skill gaps.',
  useFallbackCta: 'Start with standard questions',
  waitCta: 'Wait for kit',
  fallbackBadge: 'Standard questions',
  teleprompter: 'Guided',
  checklist: 'All questions',
  endCall: 'End call & debrief',
  debriefTitle: 'Post-call debrief',
  debriefHint: 'Capture your recommendation while the conversation is fresh.',
  roleMismatchTitle: 'Low pre-screen fit',
  roleMismatchHint: 'Resume and role may not align — confirm the candidate applied to the correct opening before proceeding.',
  prescreenNote: 'Pre-screen signal only — not your interview decision',
  resumePanel: 'Resume',
  briefing: 'Candidate briefing',
  listenFor: 'What to listen for',
  followUps: 'Follow-up questions',
  questionProgress: (current, total) => `Question ${current} of ${total}`,
  markedAsked: 'Mark as asked',
}

export const REPORT = {
  title: 'Screening Report',
  exportMenu: 'Export & share',
}

export const PIPELINE = {
  global: 'Pipeline',
  globalHint: 'All candidates by status',
  project: 'Project pipeline',
  role: 'Role pipeline',
}

/** Trust & compliance copy — cloud SaaS positioning */
export const TRUST = {
  authFooter: 'Multi-tenant security · Encrypted in transit · GDPR-ready controls',
  aiProcessingTitle: 'AI & data processing',
  aiProcessingBody:
    'Resume, job description, and interview content are processed by secure AI providers to generate screening scores, narratives, and interview plans. Data is stored in your tenant workspace and never used to train public models.',
  aiProcessingAck:
    'I understand that candidate and job data are processed by AI providers to deliver screening analysis.',
  aiSubprocessors: ['Ollama Cloud', 'Google Gemini (when configured)', 'LiveKit (voice screening)'],
}

/** Plan features that are deprecated or not offered — hidden in UI */
export const DEPRECATED_PLAN_FEATURES = [
  'On-premise deployment option',
]

export function sanitizePlanFeatures(features) {
  if (!Array.isArray(features)) return []
  return features.filter((f) => !DEPRECATED_PLAN_FEATURES.includes(f))
}
