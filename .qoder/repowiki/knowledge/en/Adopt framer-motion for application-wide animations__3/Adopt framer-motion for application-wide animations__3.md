---
kind: design
name: Adopt framer-motion for application-wide animations
source: session
category: adr
---

# Adopt framer-motion for application-wide animations

_Source: coding plans from commit period d9f210d → cccda7d — records intent at planning time; the implementation may lag or differ._

## Context
The application had framer-motion installed but unused, relying on basic CSS animations. To achieve an 'Apple-quality' UX with tactile micro-interactions, spring physics, and smooth page transitions, a dedicated motion library was required.

## Decision drivers
- High-fidelity spring physics for tactile feel
- Shared element transitions (layoutId) for navigation continuity
- Declarative animation composition over imperative CSS

## Considered options
- **framer-motion** — pros: Already installed, provides AnimatePresence for route transitions, layoutId for shared elements, and spring physics out of the box.; cons: Adds runtime bundle size compared to pure CSS.
- **Pure CSS animations** _(rejected)_ — pros: Zero dependency overhead.; cons: Lacks complex spring physics, difficult to coordinate exit/enter transitions (AnimatePresence), and cannot easily handle shared element layout transitions.

## Decision
Activate framer-motion across the app by creating reusable primitives (PageTransition, MotionCard, StaggerContainer) and replacing existing CSS animations with spring-based motion components.

## Consequences
All interactive elements (buttons, cards, modals) will use spring physics. Route transitions will be handled via AnimatePresence in App.jsx. New component primitives in src/components/motion/ and src/components/ui/ must be maintained.