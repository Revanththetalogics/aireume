import NavBar from './NavBar'
import ToastProvider from './ToastProvider'

export default function AppShell({ children }) {
  return (
    <div className="h-screen flex flex-col overflow-hidden bg-surface">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-[100] focus:bg-white focus:px-4 focus:py-2 focus:rounded-lg focus:shadow-lg focus:text-brand-700 focus:ring-2 focus:ring-brand-500"
      >
        Skip to main content
      </a>
      <NavBar />
      <ToastProvider />
      <main id="main-content" tabIndex={-1} className="flex-1 min-h-0 overflow-y-auto">
        {children}
      </main>
    </div>
  )
}
