# Workspace Readiness Onboarding — Design Spec

**Date:** 2026-07-24  
**Status:** Approved (user requested plan + implement)

## Goal

Unify tenant onboarding wizard and post-wizard checklist into a **Workspace Readiness** experience so admins can self-serve from signup to day-1 usable workspace, including plan-appropriate tenant settings.

## Scope (MVP)

1. Extended readiness checklist with configuration tasks (subscription review, requisition workflow, interview settings)
2. Server-persisted checklist dismissal (cross-device)
3. Plan- and role-aware item visibility (Starter vs Growth vs Business; admin-only config steps)
4. Wizard step 4 plan-aware navigation + sample data as recommended path
5. Auto-complete config items when settings are saved / subscription tab viewed
6. Settings → **Setup** tab mirroring dashboard widget for admins

Out of scope (future): contextual first-visit modals, analytics funnel, OAuth parity fixes, notification settings persistence.

## Architecture

- **Single item registry:** `app/frontend/src/lib/workspaceReadiness.js` — labels, hrefs, `feature`, `adminOnly`
- **Backend checklist JSON** on `users.getting_started_progress` — extended keys + `_dismissed` flag
- **API:** `GET /status` returns `checklist_dismissed`; `POST /checklist/dismiss`; existing `PATCH /checklist`
- **UI:** `GettingStarted.jsx` renamed conceptually to Workspace Readiness widget; `WorkspaceSetupPanel.jsx` for Settings tab

## Readiness Items

| Key | Label | Gate | Admin |
|-----|-------|------|-------|
| analyzedResume | Analyze a resume | all | no |
| shortlistedCandidate | Shortlist a candidate | all | no |
| createdJob | Create first requisition | requisitions | no |
| invitedTeamMember | Invite team member | all | yes |
| sharedWithHM | Share summary with HM | hm_workflow | no |
| reviewedSubscription | Review plan & usage | all | yes |
| configuredRequisitionWorkflow | Review requisition workflow | requisitions | yes |
| configuredInterviewSettings | Configure AI interviews | ai_interviews | yes |

## Wizard Step 4

- **Explore sample data** (recommended): seed + complete → `/` (checklist auto-progress from sample)
- **Upload first JD**: Growth+ → `/requisitions`; Starter → `/analyze`
- **Go to dashboard**: complete → `/`

## Data Flow

```
Wizard complete → Dashboard widget (filtered items)
Settings save / tab view → PATCH checklist key
Dismiss → POST checklist/dismiss → _dismissed in DB
Login → GET status merges checklist + dismissed
```

## Testing

- Backend: new checklist keys, dismiss endpoint, invalid key rejection
- Manual: Starter path, Growth admin path, dismiss persists after reload
