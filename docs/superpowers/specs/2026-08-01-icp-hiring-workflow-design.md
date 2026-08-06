# ICP Hiring Workflow — Design Spec

**Date:** 2026-08-01  
**Status:** Shipped (August 2026) — see Implementation Plan for phase checklist and known gaps  
**Scope:** Full prioritized improvement backlog (P0–P3) from ICP audit

> **Doc note (2026-08-02):** Core ICP spine is in production code (`ta_lead`, open requests, assignment, HM intake/outcomes, sourcing brief, handoff, `screening_mode`). Remaining gaps: routing-policy editor UI; screening gate not yet on every analyze entrypoint; external job-board APIs still out of scope. Canonical product description: `PRODUCT_SPECIFICATION.md` §3.

## Problem

The product implements a recruiter-centric screening spine but misses real-world TA org patterns: HM-initiated reqs, TA recruiter assignment, collaborative intake sign-off, closed-loop rejection feedback, and unified HM review packs.

## Personas & ICP

| Persona | Role key | Primary jobs |
|---------|----------|--------------|
| Hiring Manager | `hiring_manager` | Raise/delegate reqs, co-own intake, review consolidated packs, shortlist/reject with feedback |
| TA Lead / Manager | `ta_lead` | Assign recruiters, approve HM access, workload routing |
| Recruiter | `recruiter` | Intake session, source/screen, route call vs AI, submit to HM, apply feedback |
| Admin | `admin` | Tenant config, billing, all TA lead capabilities |

## Target End-to-End Flow

1. HM raises opening request **or** recruiter creates req on HM's behalf (`opened_on_behalf_of_hm_id`)
2. TA lead assigns `assigned_recruiter_id`
3. Recruiter + HM finalize intake; HM can edit + approve (locks criteria v1)
4. Intake complete → status `sourcing`; recruiter screens (requisition required when configured)
5. Routing policy suggests call vs AI interview vs HM submit based on scores
6. Unified submission/handoff pack includes resume + call + consolidated recommendation
7. HM shortlist/reject with required reason on reject; feedback proposes intake/search brief updates
8. HM advance → requisition status `interviewing`; recruiter continues out of app

## Architecture Decisions

### New role: `ta_lead`
- Can assign recruiters, view/manage all requisitions, approve HM requests
- Cannot access billing/SSO (admin-only)
- Included in write-capable assignment operations

### New entities / fields
- `requisitions.assigned_recruiter_id` — TA-assigned owner
- `requisitions.opened_on_behalf_of_hm_id` — audit when recruiter opens for HM
- `requisitions.routing_policy_json` — per-req score thresholds
- `requisition_open_requests` — HM-initiated opening queue

### Intake completion (unified)
- **Recruiter done:** minimum intake saved + HM assigned + can screen
- **HM done:** `intake_status == approved` (criteria v1 locked)
- **Stepper step 3:** renamed "Criteria locked"; complete when `current_criteria_version >= 1`
- Auto-transition: `intake_in_progress` → `sourcing` when intake screening-ready; → `interviewing` on first HM `advance`

### HM collaboration
- HM can Save intake and Approve with optional inline edits (single approve persists intake then calibrates)
- Reject intake → `changes_requested` with guided resubmit banner for recruiter

### Feedback loop
- Reject outcome requires `outcome_reason_code` + optional notes
- `hm_feedback_service` maps reason → search brief + intake suggestions
- Recruiter applies suggestions via API (confirms before write)

### HM review pack
- `build_submission_packet` and `build_handoff_package` include `call_fit_score`, `consolidated_recommendation`, `consolidated_reasoning`
- Handoff filters on `RequisitionCandidate.submission_status == submitted` OR shortlisted pipeline

### Screening policy
- Enforce `screening_mode=requisition_required` in analyze when no `requisition_id`

### Notifications
- On submit to HM: email primary HM + tenant event log

## Global Constraints

- Work on `main`; no feature branch unless requested
- Minimize unrelated refactors
- Backend tests in `test_requisitions.py`
- Plan-gated features remain gated (`hm_workflow`, `ai_interviews`)
- Copy centralized in `uxLabels.js`

## Out of Scope

- External sourcing integrations (LinkedIn, job boards)
- Full interview scheduling workflow post-shortlist
- In-app notification inbox (email + audit log only)

## Success Criteria

- All P0–P3 backlog items implemented or explicitly deferred with reason
- Existing requisition tests pass; new tests for assignment, feedback, screening gate
- HM can edit+approve intake; reject captures feedback that updates search brief
