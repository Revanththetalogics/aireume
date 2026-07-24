# Workspace Readiness Phase 2 — Design Addendum

**Date:** 2026-07-24

Extends `2026-07-24-workspace-readiness-design.md`.

## Delivered in Phase 2

1. **Contextual first-visit modals** — `FeatureGuideModal` + `useFeatureGuide` on Analyze, Requisitions, Candidates, Pipeline; persisted via `users.preferences_json.seen_modals`.

2. **Onboarding analytics funnel** — `onboarding_funnel_events` table, `POST /api/onboarding/events`, admin metrics `onboarding_funnel.events`, frontend `trackOnboardingEvent()`.

3. **OAuth vs email parity** — Removed auto Growth trial on OAuth signup; plan chosen in wizard for both paths. Email login redirects to `/onboarding` when tenant wizard incomplete.

4. **Notification settings persistence** — `users.preferences_json`, `GET/PATCH /api/users/me/preferences`, Settings → Notifications wired to API.

5. **Non-admin onboarding** — Role-filtered readiness checklist labels/items; `InvitedUserWelcome` modal for recruiter/viewer/HM; viewers land on `/candidates` from home.

## Migration

Run `alembic upgrade head` for revision `065_user_preferences_onboarding_events`.
