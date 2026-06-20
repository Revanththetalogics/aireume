# Implement class-based Dark Mode with Tailwind CSS

_Source: coding plans from commit period cccda7d → 08fc91f — records intent at planning time; the implementation may lag or differ._

**Status:** accepted

## Context
The application currently lacks dark mode support. To meet modern UX standards and reduce eye strain, a comprehensive dark theme is required that inverts surfaces, text, and borders while maintaining brand identity.

## Decision drivers
- User preference accommodation (prefers-color-scheme)
- Tailwind built-in support for maintainability
- No runtime overhead for theme switching

## Considered options
- **Tailwind 'class' strategy with CSS variables** — pros: Leverages Tailwind's dark: variant for compile-time efficiency, allows smooth CSS transitions, persists preference in localStorage via ThemeContext.; cons: Requires auditing and updating ~99 components to add dark: variants.
- **Separate dark theme stylesheet** _(rejected)_ — pros: Complete separation of concerns.; cons: Harder to maintain alongside Tailwind utility classes, no automatic component-level toggling.

## Decision
Enable darkMode: 'class' in tailwind.config.js and define a dark color palette in index.css using CSS variables. Implement a ThemeContext to manage state and persistence, and update all components to use dark: utility classes for backgrounds, text, and borders.

## Consequences
Every component in the application (~99 files) must be updated to support dark mode variants. A new ThemeContext is introduced. Chart libraries (Recharts) require specific color updates for dark compatibility. The UI will support seamless toggling between light and dark themes.