/**
 * Centralized user-facing labels — single vocabulary across the app.
 * API paths may still use legacy names (templates, voice, etc.).
 */

export const NAV = {
  home: 'Home',
  requisitions: 'Requisitions',
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
  hmDashboard: 'My Openings',
}

export const REQUISITIONS = {
  pageTitle: 'Requisitions',
  pageSubtitle: 'Calibrated openings — HM intake, criteria, and pipeline in one place',
  createCta: 'New Requisition',
  emptyHint: 'Create a requisition to run intake, calibrate must-haves, and source candidates.',
  hmPageTitle: 'My Openings',
  hmPageSubtitle: 'Approve intake, review submissions, and track pipeline for your roles',
  intakeTab: 'Intake',
  intakeSaved: 'Intake saved',
  intakeSaveHint: 'Add screen-focus topics or must-haves. Screen after save; HM approval locks criteria v1.',
  intakeSuggestCta: 'Suggest from job description',
  intakeSuggestDone: 'Fields filled from JD — review and save',
  intakeStepIntake: '1. HM intake',
  intakeStepScreen: '2. Screen',
  intakeStepRefine: '3. Refine bar',
  intakeUnsaved: 'Unsaved changes',
  hmReviewPackCta: 'HM review pack',
  hmReviewPackHint: 'Share shortlisted candidates with HM (after screening)',
  criteriaTab: 'Criteria',
  pipelineTab: 'Pipeline',
  overviewTab: 'Overview',
  calibrateCta: 'Calibrate criteria',
  approveIntakeCta: 'Approve intake',
  requestChangesCta: 'Request changes',
  submitToHmCta: 'Submit to HM',
  statusDraft: 'Draft',
  hmAssignHint: 'Assign a primary hiring manager for HM intake approval and pipeline ownership.',
  hmAssignCta: 'Save hiring manager',
  hmAssignSelfCta: 'Use me as HM (admin)',
  hmAssignOverview: 'Hiring manager',
  hmInviteCta: 'Invite HM',
  hmInviteTitle: 'Invite hiring manager',
  hmInviteHint: 'Creates a hiring manager account and assigns them to this requisition (admin only).',
  hmInviteSuccess: 'Hiring manager invited and assigned',
  hmRequestCta: 'Request HM',
  hmRequestTitle: 'Request hiring manager access',
  hmRequestHint: 'Submit the HM email for tenant admin approval. No account is created until approved.',
  hmRequestSuccess: 'HM access requested — waiting for admin approval',
  hmRequestPending: 'HM access requested',
  hmRequestApproveCta: 'Approve & assign',
  hmRequestRejectCta: 'Reject request',
  notCalibratedWarning: 'Save intake and assign a hiring manager before screening. Calibrate when HM feedback changes the bar.',
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
