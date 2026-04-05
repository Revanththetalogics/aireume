import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Sparkles, Users, LayoutTemplate, UserCircle, LogOut, ChevronDown, Upload, GitCompare, Users2, Video, MessageSquareText, Settings } from 'lucide-react'
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
  const navigate = useNavigate()
  const [userMenuOpen, setUserMenuOpen] = useState(false)

  const initials = user?.email ? user.email[0].toUpperCase() : '?'

  return (
    <header className="bg-white/80 backdrop-blur-xl border-b border-brand-100/60 sticky top-0 z-30 print:hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2.5 shrink-0 group">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-brand-600 to-brand-500 flex items-center justify-center shadow-brand-sm group-hover:shadow-brand transition-shadow">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <span className="text-lg font-bold text-brand-900 tracking-tight">ARIA</span>
          {tenant && (
            <span className="hidden sm:inline text-xs text-brand-600 border border-brand-200 bg-brand-50 rounded-full px-2.5 py-0.5 ml-1 font-medium">
              {tenant.name}
            </span>
          )}
        </Link>

        {/* Nav links */}
        <nav className="hidden md:flex items-center gap-0.5">
          {NAV_LINKS.map(({ to, label, icon: Icon }) => {
            const active = location.pathname === to
            return (
              <Link
                key={to}
                to={to}
                className={`relative flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${
                  active
                    ? 'text-brand-700 bg-brand-50'
                    : 'text-slate-500 hover:text-brand-700 hover:bg-brand-50/60'
                }`}
              >
                <Icon className={`w-4 h-4 ${active ? 'text-brand-600' : ''}`} />
                {label}
                {active && (
                  <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-4 h-0.5 bg-brand-600 rounded-full" />
                )}
              </Link>
            )
          })}
        </nav>

        {/* User menu */}
        <div className="relative">
          <button
            onClick={() => setUserMenuOpen((v) => !v)}
            className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm text-slate-600 hover:bg-brand-50 transition-colors"
          >
            <div className="w-7 h-7 rounded-full bg-gradient-to-br from-brand-600 to-brand-400 flex items-center justify-center text-white text-xs font-bold shrink-0">
              {initials}
            </div>
            <span className="hidden sm:inline max-w-[130px] truncate text-slate-700 font-medium">{user?.email}</span>
            <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${userMenuOpen ? 'rotate-180' : ''}`} />
          </button>

          {userMenuOpen && (
            <div className="absolute right-0 top-full mt-2 w-56 bg-white/95 backdrop-blur-xl border border-brand-100 rounded-2xl shadow-brand-lg py-1.5 z-40">
              <div className="px-4 py-3 border-b border-brand-50">
                <div className="flex items-center gap-2.5 mb-1">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-brand-600 to-brand-400 flex items-center justify-center text-white text-xs font-bold">
                    {initials}
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-slate-800 truncate">{user?.email}</p>
                    <p className="text-xs text-brand-600 font-medium capitalize">{user?.role}</p>
                  </div>
                </div>
              </div>

              {/* Settings Link */}
              <button
                onClick={() => { setUserMenuOpen(false); navigate('/settings') }}
                className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-700 hover:bg-brand-50 transition-colors"
              >
                <Settings className="w-4 h-4 text-slate-500" />
                Settings & Subscription
              </button>

              <div className="px-3 my-1.5 border-t border-brand-50" />

              <button
                onClick={() => { setUserMenuOpen(false); logout() }}
                className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors rounded-b-2xl"
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
