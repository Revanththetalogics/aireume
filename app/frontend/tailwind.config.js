/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#F5F3FF',
          100: '#EDE9FE',
          200: '#DDD6FE',
          300: '#C4B5FD',
          400: '#A78BFA',
          500: '#8B5CF6',
          600: '#7C3AED',
          700: '#6D28D9',
          800: '#5B21B6',
          900: '#1E1B4B',
        },
        surface: '#FAFBFF',
        'dark-surface': '#0A0A0F',
        'dark-card': '#1C1C1E',
        'dark-card-elevated': '#2C2C2E',
        'dark-border': 'rgba(255,255,255,0.1)',
        'dark-text-primary': '#F5F5F7',
        'dark-text-secondary': '#98989D',
        slate: {
          50:  '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        'display': ['3.5rem', { lineHeight: '1.1', letterSpacing: '-0.02em' }],
        'hero': ['4rem', { lineHeight: '1.05', letterSpacing: '-0.025em' }],
      },
      letterSpacing: {
        'tighter': '-0.03em',
        'tight': '-0.02em',
      },
      boxShadow: {
        'brand-sm': '0 1px 3px rgba(124,58,237,0.08)',
        'brand':    '0 4px 16px rgba(124,58,237,0.12)',
        'brand-lg': '0 8px 32px rgba(124,58,237,0.16)',
        'brand-xl': '0 16px 48px rgba(124,58,237,0.18)',
        'dark-brand': '0 4px 16px rgba(0,0,0,0.3)',
        'dark-brand-lg': '0 8px 32px rgba(0,0,0,0.4)',
      },
      backgroundImage: {
        'gradient-brand': 'linear-gradient(135deg, #7C3AED 0%, #6366F1 100%)',
      },
      animation: {
        'shimmer': 'shimmer 2s infinite',
        'fade-up': 'fadeInUp 0.4s ease-out',
        'spin-slow': 'spin 3s linear infinite',
        'smooth-shimmer': 'smoothShimmer 1.5s ease-in-out infinite',
      },
      keyframes: {
        shimmer: {
          '0%':   { backgroundPosition: '-200% center' },
          '100%': { backgroundPosition: '200% center' },
        },
        fadeInUp: {
          '0%':   { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        smoothShimmer: {
          '0%':   { opacity: '0.4' },
          '50%':  { opacity: '0.7' },
          '100%': { opacity: '0.4' },
        },
      },
    },
  },
  plugins: [],
}
