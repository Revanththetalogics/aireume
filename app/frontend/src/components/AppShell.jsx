import NavBar from './NavBar'
import ToastProvider from './ToastProvider'

export default function AppShell({ children }) {
  return (
    <div className="h-screen flex flex-col overflow-hidden bg-surface">
      <NavBar />
      <ToastProvider />
      <div className="flex-1 min-h-0 overflow-y-auto">
        {children}
      </div>
    </div>
  )
}
