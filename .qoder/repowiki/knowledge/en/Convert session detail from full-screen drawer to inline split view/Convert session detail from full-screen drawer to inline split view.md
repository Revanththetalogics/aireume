---
kind: design
name: Convert session detail from full-screen drawer to inline split view
source: session
category: adr
---

# Convert session detail from full-screen drawer to inline split view

_Source: coding plans from commit period 160edcd → 0e8a407 — records intent at planning time; the implementation may lag or differ._

**Status:** accepted

## Context
The existing full-screen drawer (`fixed inset-0`) obscured the session list, forcing recruiters to close the detail view to return to the list context. This disrupted workflow when reviewing multiple candidates or comparing sessions.

## Decision drivers
- workflow continuity
- context preservation
- screen real estate efficiency

## Considered options
- **Inline split view (side-by-side)** — pros: Recruiter remains in list context while viewing details; easier to switch between candidates; maintains spatial awareness of the queue.; cons: Reduces width available for transcript/notes; requires responsive handling for smaller screens.
- **Full-screen overlay drawer (existing)** _(rejected)_ — pros: Maximum space for detailed content (transcripts, assessments).; cons: Breaks list context; requires extra click to navigate back; higher cognitive load for batch processing.

## Decision
Replace the full-screen drawer with a side-by-side layout: the session list occupies `flex-1` on the left, and the detail panel occupies `max-w-xl` on the right with a `border-l` separator. This allows recruiters to scan the list and inspect details simultaneously.

## Consequences
Improved multitasking and faster candidate triage. The detail panel must now handle overflow carefully within a fixed max-width, potentially requiring internal scrolling for long transcripts.