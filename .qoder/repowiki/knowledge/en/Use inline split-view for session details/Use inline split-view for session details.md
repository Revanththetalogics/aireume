---
kind: design
name: Use inline split-view for session details
source: session
category: adr
---

# Use inline split-view for session details

_Source: coding plans from commit period 7c78ec1 → 92ff434 — records intent at planning time; the implementation may lag or differ._

**Status:** accepted

## Context
The existing full-screen drawer (`fixed inset-0 z-50`) in `VoiceScreeningPage.jsx` forced recruiters to lose context of the session list when viewing details, hindering rapid triage and comparison of multiple candidates.

## Decision drivers
- recruiter workflow efficiency
- context preservation
- screen real estate utilization

## Considered options
- **Full-screen modal/drawer** _(rejected)_ — pros: Maximum space for transcript and assessment details; simple implementation; cons: Obscures the session list; requires closing the drawer to switch candidates; breaks flow for bulk review
- **Inline side-by-side split view** — pros: Recruiter stays in list context; allows quick switching between sessions; maintains spatial awareness of the queue; cons: Reduces horizontal space for the detail panel (constrained to `max-w-xl`); requires more complex layout management

## Decision
Convert the session detail UI from a full-screen drawer to an inline split view in `VoiceScreeningPage.jsx`, with the session list on the left (flex-1) and the detail panel on the right (max-w-xl, border-l).

## Consequences
Recruiters can view transcripts and actions without leaving the list view. The detail panel must be designed to fit within a narrower column, potentially requiring vertical scrolling for long transcripts.