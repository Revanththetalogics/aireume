# Adopt framer-motion for application-wide motion and interactions

_Source: coding plans from commit period 8626ec6 → dc66c1a — records intent at planning time; the implementation may lag or differ._

**Status:** accepted

## Context
The application had framer-motion installed but unused, relying on basic CSS animations. To achieve an 'Apple-quality' UX with tactile micro-interactions, spring physics, and smooth page transitions, a dedicated motion library was required to replace manual CSS patterns.

## Decision drivers
- Spring physics for natural feel
- Shared element transitions (layoutId)
- Complex orchestration (stagger, AnimatePresence)
- Existing dependency availability

## Considered options
- **framer-motion** — pros: Already installed, supports spring physics, layout animations, and complex exit/enter orchestration via AnimatePresence; cons: Adds runtime JS overhead compared to pure CSS
- **Pure CSS animations** _(rejected)_ — pros: Zero JS overhead, native browser support; cons: Lacks spring physics, difficult to orchestrate complex staggered lists or shared element transitions, limited dynamic control

## Decision
Activate framer-motion across the app by creating reusable primitives (PageTransition, MotionCard, StaggerContainer) and replacing existing CSS animations in modals, lists, and navigation with spring-based motion components.

## Consequences
Significant improvement in perceived UI quality and responsiveness. Requires wrapping route changes in AnimatePresence and refactoring existing modal/list components to use motion primitives. Introduces a dependency on framer-motion for all interactive elements.