# Implement class-based Dark Mode with Tailwind CSS

_Source: coding plans from commit period d9f210d → cccda7d — records intent at planning time; the implementation may lag or differ._

## Context
The application lacked dark mode support. A system was needed to toggle themes while respecting user preferences and persisting choices, without incurring runtime performance costs or breaking existing light-mode styles.

## Decision drivers
- Zero runtime overhead for theme switching
- Persistence of user preference via localStorage
- System preference detection (prefers-color-scheme)

## Considered options
- **Tailwind 'class' strategy with CSS variables** — pros: Uses built-in dark: variants, no JavaScript style injection at runtime, easy to audit components, supports smooth CSS transitions between themes.; cons: Requires updating all 99 components to include dark: class variants.
- **Separate CSS themes / JS-injected styles** _(rejected)_ — pros: Complete isolation of theme styles.; cons: Higher complexity, potential flash-of-unstyled-content, harder to maintain alongside Tailwind utility classes.

## Decision
Enable darkMode: 'class' in tailwind.config.js, define semantic color tokens in index.css for both :root and .dark scopes, and manage state via a new ThemeContext that persists to localStorage.

## Consequences
Every component file requires a dark mode audit to add dark: variants. Chart libraries (Recharts) need specific color overrides for dark backgrounds. The UI will support smooth transitions between light and dark modes.