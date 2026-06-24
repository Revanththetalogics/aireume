---
kind: design
name: Adopt framer-motion for application-wide animations
source: session
category: adr
---

# Adopt framer-motion for application-wide animations

_Source: coding plans from commit period d9f210d → 14c321e — records intent at planning time; the implementation may lag or differ._

**Status:** accepted

## Context
The application currently relies on basic CSS animations (fadeInUp, shimmer) and has framer-motion installed but unused. To achieve an 'Apple-quality' UX with tactile micro-interactions, spring physics, and smooth page transitions, a dedicated motion library is required.

## Decision drivers
- Need for spring physics in UI interactions
- Requirement for complex layout transitions (drag-reorder, shared elements)
- Desire to replace manual CSS animation patterns with declarative primitives

## Considered options
- **Continue with CSS-only animations** _(rejected)_ — pros: No additional runtime overhead, no new dependencies to manage; cons: Cannot easily implement spring physics, layout animations, or complex staggered sequences; requires verbose manual CSS management
- **Activate framer-motion** — pros: Provides spring physics, AnimatePresence for route transitions, and layoutId for shared element transitions; already installed in package.json; cons: Adds JavaScript bundle weight; requires refactoring existing components to use motion wrappers

## Decision
Activate framer-motion across the app by creating reusable motion primitives (PageTransition, MotionCard, StaggerContainer) and replacing existing CSS animations with spring-based framer-motion variants.

## Consequences
All major interactive elements (modals, lists, navigation) will use spring physics. New wrapper components in src/components/motion/ will be introduced. Existing components like VoiceScheduleModal and CandidatesPage must be refactored to use these primitives.