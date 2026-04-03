import { Link, useLocation } from 'react-router-dom'
import { Sparkles, Users, LayoutTemplate, UserCircle, LogOut, ChevronDown, Upload, GitCompare, Users2, Video, MessageSquareText } from 'lucide-react'
import { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'

const NAV_LINKS = [
  { to: '/',            label: 'Analyze',    icon: Sparkles },
  { to: '/batch',       label: 'Batch',      icon: Upload },
  { to: '/candidates',  label: 'Candidates', icon: Users },
  { to: '/compare',     label: 'Compare',    icon: GitCompare },
  { to: '/templates',   label: 'Templates',  icon: LayoutTemplate },
  { to: '/video',       label: 'Video',      icon: Video },
  { to: '/transcript',  label: 'Transcript', icon: MessageSquareText },
  { to: '/team',        label: 'Team',       icon: Users2 },
]

export default function NavBar() {
  const { user, tenant, logout } = useAuth()
  const location = useLocation()
  const [userMenuOpen, setUserMenuOpen] = useState(false)

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30 print:hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 shrink-0">
          <Sparkles className="w-6 h-6 text-blue-600" />
          <span className="text-lg font-bold text-slate-800">ARIA</span>
          {tenant && (
            <span className="hidden sm:inline text-xs text-slate-400 border border-slate-200 rounded px-2 py-0.5 ml-1">
              {tenant.name}
            </span>
          )}
        </Link>

        {/* Nav links */}
        <nav className="hidden md:flex items-center gap-1">
          {NAV_LINKS.map(({ to, label, icon: Icon }) => {
            const active = location.pathname === to
            return (
              <Link
                key={to}
                to={to}
                className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  active
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-800'
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
              </Link>
            )
          })}
        </nav>

        {/* User menu */}
        <div className="relative">
          <button
            onClick={() => setUserMenuOpen((v) => !v)}
            className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-slate-700 hover:bg-slate-100 transition-colors"
          >
            <UserCircle className="w-5 h-5 text-slate-500" />
            <span className="hidden sm:inline max-w-[140px] truncate">{user?.email}</span>
            <ChevronDown className="w-4 h-4 text-slate-400" />
          </button>
          {userMenuOpen && (
            <div className="absolute right-0 top-full mt-1 w-48 bg-white border border-slate-200 rounded-xl shadow-lg py-1 z-40">
              <div className="px-4 py-2 border-b border-slate-100">
                <p className="text-xs text-slate-500">Signed in as</p>
                <p className="text-sm font-medium text-slate-800 truncate">{user?.email}</p>
                <p className="text-xs text-blue-600 capitalize">{user?.role}</p>
              </div>
              <button
                onClick={() => { setUserMenuOpen(false); logout() }}
                className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
              >
                <LogOut className="w-4 h-4" />
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
