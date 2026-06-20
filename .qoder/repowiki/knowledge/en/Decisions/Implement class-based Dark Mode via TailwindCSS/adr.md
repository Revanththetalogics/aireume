# Implement class-based Dark Mode via TailwindCSS

_Source: coding plans from commit period d9f210d → 14c321e — records intent at planning time; the implementation may lag or differ._

**Status:** accepted

## Context
The application currently lacks dark mode support. Users expect theme switching capabilities, and the existing design system (glassmorphism, branded shadows) needs to adapt to low-light environments without breaking visual hierarchy.

## Decision drivers
- User expectation for dark mode
- Leveraging existing TailwindCSS infrastructure
- Minimizing runtime performance overhead

## Considered options
- **CSS Variable-based theme switching** _(rejected)_ — pros: Standard web approach, easy to toggle via JS; cons: Requires manual mapping of every color token; loses Tailwind's utility-first convenience
- **TailwindCSS 'class' strategy** — pros: Native integration with existing utility classes (dark:bg-slate-900); no runtime JS overhead for styling; leverages prefers-color-scheme media query; cons: Requires auditing and updating all 99 JSX files to add dark: variants

## Decision
Enable darkMode: 'class' in tailwind.config.js and create a ThemeContext to manage user preference. All components will be updated to include dark: variant classes for backgrounds, text, and borders.

## Consequences
Every component file (~99) requires modification to support dark variants. A new ThemeContext.jsx will manage state and localStorage persistence. Chart libraries (Recharts) will need specific color overrides for dark mode.