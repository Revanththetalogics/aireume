---
kind: design
name: Implement class-based Dark Mode with Tailwind CSS
source: session
category: adr
---

# Implement class-based Dark Mode with Tailwind CSS

_Source: coding plans from commit period 8626ec6 → dc66c1a — records intent at planning time; the implementation may lag or differ._

**Status:** accepted

## Context
The application lacked dark mode support. To meet modern UX expectations and reduce eye strain, a comprehensive dark theme was needed that could coexist with the existing light theme and persist user preferences.

## Decision drivers
- User preference persistence
- System preference detection
- Tailwind ecosystem integration
- No runtime JS theme switching overhead

## Considered options
- **Tailwind 'class' strategy with CSS variables** — pros: Leverages Tailwind's built-in dark: variant, allows smooth CSS transitions, respects localStorage and system preferences via ThemeContext; cons: Requires auditing and updating all 99 components to add dark: variants
- **Separate dark stylesheet** _(rejected)_ — pros: Clean separation of concerns; cons: Harder to maintain alongside utility classes, loses Tailwind's component-level scoping, harder to toggle dynamically without FOUC

## Decision
Enable darkMode: 'class' in tailwind.config.js, define semantic color tokens in index.css for both :root and .dark scopes, and create a ThemeContext to manage toggling and persistence. All components will be updated with dark: utility classes.

## Consequences
Full dark mode support across the application. Requires a one-time significant effort to audit and update all UI components. Future components must include dark mode variants by default.