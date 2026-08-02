# ICP Hiring Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or executing-plans for batch execution.

**Goal:** Align requisition workflow with real-world TA/HM/recruiter ICP — assignment, collaborative intake, feedback loops, unified HM packs.

**Architecture:** Extend `Requisition` model with assignment + routing fields; add `RequisitionOpenRequest` for HM-initiated openings; `ta_lead` role for assignment; `hm_feedback_service` for reject→sourcing loop; frontend modals and role-aware intake/HM review UI.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, React, existing requisition/HM workflow.

## Global Constraints

- Plan-gated: `hm_workflow`, `requisitions`, `ai_interviews`
- Copy in `uxLabels.js`
- Tests in `test_requisitions.py`

## Phases Implemented

### Phase A (P0) — Handshake fixes
- HM outcome modal with required reject reason
- Feedback suggestions + apply to search brief
- `ta_lead` role + recruiter assignment API
- HM open request queue + assign endpoint
- HM edit + approve with intake payload

### Phase B (P1) — Flow alignment
- Stepper step 3 at criteria v1+; renamed "Criteria locked"
- Consolidated fields in submission + handoff packs
- `screening_mode=requisition_required` enforced in analyze
- Routing policy + `suggested_action` on pipeline
- Assigned recruiter can manage requisition

### Phase C (P2) — Automation & scope
- Auto status: sourcing after intake ready; interviewing on HM advance
- HM email on submit + tenant event log
- Handoff uses submitted/shortlisted requisition candidates
- HM candidate list scoped to assigned reqs
- Sourcing brief UI on intake tab
- `hm_pipeline_permission` respected in frontend

### Phase D (P3) — Polish
- `opened_on_behalf_of_hm_id` metadata on create/assign
- `changes_requested` banner
- Submit recruiter note overlay
- SSO/invite accepts `ta_lead`
- Spec + plan docs

## Verification

```bash
pytest app/backend/tests/test_requisitions.py -v
```
