# Adopt framer-motion for application-wide motion and interactions

_Source: coding plans from commit period cccda7d → 08fc91f — records intent at planning time; the implementation may lag or differ._

**Status:** accepted

## Context
The application currently relies on basic CSS animations (fadeInUp, shimmer) and has framer-motion installed but unused. To achieve an 'Apple-quality' UX with tactile micro-interactions, spring physics, and smooth page transitions, a dedicated motion library is required.

## Decision drivers
- High-fidelity spring physics for tactile feel
- Shared element transitions via layoutId
- Declarative animation composition (AnimatePresence, Stagger)

## Considered options
- **framer-motion** — pros: Already installed in package.json (no new dependency risk), provides spring physics, layout animations, and AnimatePresence for route transitions.; cons: Adds runtime JavaScript weight compared to pure CSS.
- **Pure CSS/Tailwind animations** _(rejected)_ — pros: Zero runtime overhead, simple implementation.; cons: Lacks complex spring physics, shared element transitions, and staggered list capabilities required for the target UX.

## Decision
Activate framer-motion across the app by creating reusable motion primitives (PageTransition, MotionCard, StaggerContainer) and replacing existing CSS animations with spring-based framer-motion variants for modals, lists, and interactive elements.

## Consequences
All major UI interactions (modals, page routes, list entries) will use framer-motion. New wrapper components in src/components/motion/ will be introduced. Existing CSS animations like animate-fade-up will be deprecated in favor of spring physics (stiffness: 300, damping: 30).