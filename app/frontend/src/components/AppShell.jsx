import NavBar from './NavBar'

export default function AppShell({ children }) {
  return (
    <div className="h-screen flex flex-col overflow-hidden bg-surface">
      <NavBar />
      <div className="flex-1 min-h-0 overflow-y-auto">
        {children}
      </div>
    </div>
  )
}
