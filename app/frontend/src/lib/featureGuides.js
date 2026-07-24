/** First-visit contextual guides — one modal per feature area. */
export const FEATURE_GUIDES = {
  analyze: {
    id: 'analyze',
    title: 'Screen resumes in 3 steps',
    body: 'Paste or upload a job description, add resumes, and ARIA scores fit with explainable recommendations.',
    bullets: [
      'Step 1: Define role skills (or load from a requisition)',
      'Step 2: Upload one or many resumes',
      'Step 3: Review scores and shortlist top candidates',
    ],
    ctaLabel: 'Got it — start screening',
  },
  requisitions: {
    id: 'requisitions',
    title: 'Requisitions power your hiring workflow',
    body: 'Create a requisition for each open role. Calibrate must-haves, run intake, and track pipeline stages.',
    bullets: [
      'Create a JD in JD Library',
      'Calibrate skills with hiring managers',
      'Screen candidates into your pipeline',
    ],
    ctaLabel: 'Got it',
  },
  candidates: {
    id: 'candidates',
    title: 'Your candidate hub',
    body: 'All screened candidates live here. Filter by status, open fit reports, and move people through your pipeline.',
    bullets: [
      'Click a row to open the full screening report',
      'Update status to shortlist, reject, or hire',
      'Share HM debriefs from the report page',
    ],
    ctaLabel: 'Got it',
  },
  pipeline: {
    id: 'pipeline',
    title: 'Pipeline board',
    body: 'Drag candidates across stages or use bulk actions. Each column reflects your requisition workflow settings.',
    bullets: [
      'Pending → In Review → Shortlisted → Hired',
      'Click a card for the full report',
    ],
    ctaLabel: 'Got it',
  },
  ai_interviews: {
    id: 'ai_interviews',
    title: 'AI voice interviews',
    body: 'Send candidates an AI phone screen. Configure voice identity and opening script in Settings → Interviews first.',
    bullets: [
      'Quick screens for high volume',
      'Standard/deep kits for senior roles',
      'Results flow back to the candidate profile',
    ],
    ctaLabel: 'Got it',
    feature: 'ai_interviews',
  },
}
