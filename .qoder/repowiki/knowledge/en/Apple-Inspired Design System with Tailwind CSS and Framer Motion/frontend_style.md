## Overview
The frontend employs a modern, utility-first styling approach centered on **Tailwind CSS** for layout and theming, augmented by **Framer Motion** for sophisticated, Apple-inspired micro-interactions and page transitions. The design language prioritizes clean aesthetics, smooth animations, and a robust dark mode implementation.

## Core Styling Stack
- **CSS Framework**: Tailwind CSS v3 (utility-first)
- **Animation Library**: Framer Motion v12 (declarative animations)
- **Iconography**: Lucide React
- **Build Tool**: Vite
- **Font**: Inter (via Google Fonts)

## Theming & Dark Mode
The application uses a **class-based dark mode strategy** (`darkMode: 'class'` in Tailwind config).
- **Theme Context**: A `ThemeContext` manages user preference, persisting to `localStorage` and respecting system `prefers-color-scheme`.
- **Design Tokens**: Defined in `tailwind.config.js` and `index.css` using CSS variables for seamless theme switching.
  - **Brand Palette**: A custom `brand` scale (purple/violet hues, e.g., `#7C3AED`) is used for primary actions and accents.
  - **Surface Colors**: Custom tokens like `--surface-bg`, `--surface-card`, and `--dark-surface` ensure consistent background handling across themes.
  - **Typography**: The `Inter` font family is enforced globally with specific tracking and leading adjustments for display text.

## Component Architecture
- **UI Primitives**: Located in `src/components/ui/`, these include standardized `Button`, `Card`, `Badge`, and `Input` components that encapsulate Tailwind classes for consistency.
- **Motion Wrappers**: Located in `src/components/motion/`, components like `MotionCard` and `PageTransition` provide reusable animation patterns (e.g., fade-up entries, spring-based hover effects).
- **Micro-interactions**: Buttons and interactive elements use spring physics (`stiffness: 400, damping: 17`) for "press" and "hover" states, mimicking native iOS/macOS feel.

## Key Conventions
1. **Utility-First with Abstraction**: While Tailwind utilities are used extensively, complex or repeated patterns are abstracted into UI components or custom CSS classes in `index.css` (e.g., `.btn-brand`, `.card-interactive`).
2. **Animation Consistency**: Use `framer-motion` for all state-driven animations. Avoid raw CSS transitions for complex sequences. Use `MotionCard` for list items to achieve staggered entrance effects.
3. **Responsive Strategy**: Mobile-first responsive design using Tailwind's breakpoint prefixes (`sm:`, `md:`, `lg:`).
4. **Print Optimization**: Dedicated `@media print` styles in `index.css` ensure reports and candidate profiles render cleanly on paper, hiding interactive elements and optimizing spacing.

## Developer Guidelines
- **Adding New Colors**: Extend the `brand` or `slate` scales in `tailwind.config.js` rather than hardcoding hex values in components.
- **Dark Mode Testing**: Always verify new components in both light and dark modes using the `ThemeContext` toggle.
- **Performance**: Use `motion.div` sparingly for static elements; prefer CSS transitions for simple hover states if Framer Motion isn't already managing the component's lifecycle.