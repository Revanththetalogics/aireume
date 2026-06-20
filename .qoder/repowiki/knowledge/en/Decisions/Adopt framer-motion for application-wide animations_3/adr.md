# Adopt framer-motion for application-wide animations

_Source: coding plans from commit period 08fc91f → bdb09a8 — records intent at planning time; the implementation may lag or differ._

**Status:** accepted

## Context
The application currently relies on basic CSS animations and has an unused framer-motion dependency. To achieve an 'Apple-quality' UX with spring physics, layout transitions, and staggered lists, a dedicated motion library is required.

## Decision drivers
- Spring physics support for tactile feel
- Layout animation capabilities (layoutId)
- Component-level control over enter/exit states

## Considered options
- **Continue with CSS-only animations** _(rejected)_ — pros: No additional runtime overhead, simpler stack; cons: Cannot easily achieve complex spring physics, layout transitions, or coordinated staggered effects; limited interactivity
- **Activate framer-motion** — pros: Enables spring physics, AnimatePresence for route/modal transitions, and layoutId for shared element transitions; already installed; cons: Increases bundle size slightly; requires refactoring existing components to use motion wrappers

## Decision
Activate framer-motion by creating reusable motion primitives (PageTransition, MotionCard, StaggerContainer) and wrapping key interactive elements (modals, lists, navigation) with motion components using spring physics.

## Consequences
Significant improvement in perceived performance and polish. Requires updating ~15 files in the initial wave and establishing a pattern of using motion wrappers instead of raw CSS classes for interactive elements.