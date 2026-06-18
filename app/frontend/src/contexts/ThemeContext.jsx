import { createContext, useContext, useState, useEffect } from 'react'

const ThemeContext = createContext()

/**
 * ThemeProvider — manages dark mode preference.
 *
 * - Persists preference in localStorage
 * - Respects prefers-color-scheme media query
 * - Applies 'dark' class to <html> element
 */

function getInitialTheme() {
  // Check localStorage first
  const stored = localStorage.getItem('theme')
  if (stored === 'dark' || stored === 'light') return stored

  // Fall back to system preference
  if (window.matchMedia?.('(prefers-color-scheme: dark)').matches) return 'dark'

  return 'light'
}

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(getInitialTheme)

  useEffect(() => {
    const root = document.documentElement
    if (theme === 'dark') {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }
    localStorage.setItem('theme', theme)
  }, [theme])

  // Listen for system preference changes
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = (e) => {
      // Only auto-switch if user hasn't explicitly set a preference
      if (!localStorage.getItem('theme')) {
        setTheme(e.matches ? 'dark' : 'light')
      }
    }
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark')
  }

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}
