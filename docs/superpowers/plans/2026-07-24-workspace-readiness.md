# Workspace Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or executing-plans.

**Goal:** Ship unified Workspace Readiness onboarding with server-dismiss, extended checklist, plan-aware wizard, and Settings Setup tab.

**Architecture:** Shared `workspaceReadiness.js` registry; backend extends checklist JSON; frontend syncs dismiss and auto-completes on settings actions.

**Tech Stack:** FastAPI, SQLAlchemy, React, existing OnboardingContext

## Global Constraints

- Do not break existing checklist keys or E2E onboarding test
- Plan gating via existing `isFeatureAvailable()` / `usePermissions().isAdmin`
- Minimal migration — use `_dismissed` in existing JSON column

---

### Task 1: Backend checklist extensions

**Files:** `app/backend/routes/onboarding.py`, `app/backend/tests/test_onboarding.py`

- Extend `DEFAULT_CHECKLIST` with 3 new keys
- `_load_checklist` / `_save_checklist` handle `_dismissed`
- `GET /status` returns `checklist_dismissed`
- `POST /checklist/dismiss`
- `seed-sample` marks `analyzedResume` + `shortlistedCandidate`
- Tests for dismiss + new keys

### Task 2: Frontend registry + context

**Files:** `workspaceReadiness.js`, `api.js`, `OnboardingContext.jsx`

- Item registry with filters `getVisibleReadinessItems({ isFeatureAvailable, isAdmin })`
- `dismissOnboardingChecklist()` API
- Context loads/syncs `checklist_dismissed` from status

### Task 3: Workspace Readiness UI

**Files:** `GettingStarted.jsx`, `WorkspaceSetupPanel.jsx`, `SettingsPage.jsx`, `DashboardNew.jsx`

- Widget uses registry; title "Workspace Readiness"
- Settings Setup tab for admins post-wizard

### Task 4: Wizard + auto-complete hooks

**Files:** `OnboardingWizard.jsx`, `RequisitionSettingsPanel.jsx`, `InterviewSettingsPanel.jsx`, `SettingsPage.jsx`

- Plan-aware step 4 navigation
- completeChecklistItem on settings save / subscription tab
