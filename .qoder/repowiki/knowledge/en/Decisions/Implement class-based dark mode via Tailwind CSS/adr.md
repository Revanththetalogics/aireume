# Implement class-based dark mode via Tailwind CSS

_Source: coding plans from commit period 08fc91f → bdb09a8 — records intent at planning time; the implementation may lag or differ._

**Status:** accepted

## Context
The application lacks dark mode support. A system is needed to toggle themes while maintaining brand consistency and ensuring all 99+ components render correctly in both modes.

## Decision drivers
- User preference persistence
- System preference detection (prefers-color-scheme)
- Minimal runtime overhead
- Tailwind ecosystem compatibility

## Considered options
- **CSS variable-only theming** _(rejected)_ — pros: Pure CSS solution, no JS context needed for styling; cons: Harder to manage conditional logic in React components; less integrated with Tailwind's utility-first workflow
- **Tailwind 'class' strategy with ThemeContext** — pros: Leverages Tailwind's built-in dark: variant; easy to toggle via class on html/body; persists via localStorage; respects system preferences; cons: Requires auditing all components to add dark: variants; increases CSS output size slightly

## Decision
Enable Tailwind's darkMode: 'class' strategy, create a ThemeContext to manage state and persistence, and define semantic CSS variables for surfaces/text that map to light/dark palettes. All components will be updated with dark: variants.

## Consequences
Every component file (~99) requires updates to support dark variants. Provides a seamless toggle experience and automatic system detection. Requires careful management of color contrast and shadow opacity in dark mode.