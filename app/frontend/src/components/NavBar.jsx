import { Link, useLocation, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, Briefcase, Users, BarChart3, Columns,
  Users2, Video, Settings, Shield, LogOut, Sparkles,
  MoreHorizontal,
} from 'lucide-react'
import { useState, useRef, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { STATUS_CONFIG } from '../lib/constants'
import ProgressBadge from './ProgressBadge'

/* ── Static config ───────────────────────────────────── */

const PRIMARY_NAV = [
  { label: 'Home', path: '/', icon: LayoutDashboard },
  { label: 'Jobs', path: '/jd-library', icon: Briefcase },
  { label: 'Candidates', path: '/candidates', icon: Users },
]

const USER_MENU_LINKS = [
  { label: 'Analytics', path: '/analytics', icon: BarChart3 },
  { label: 'Pipeline', path: '/pipeline', icon: Columns },
  { label: 'Team', path: '/team', icon: Users2 },
  { label: 'Team Skills', path: '/team-skills', icon: Users },
  { label: 'Interviews', path: '/video', icon: Video },
  { label: 'Settings', path: '/settings', icon: Settings },
]

/* ── Desktop user menu dropdown ──────────────────────── */

function UserMenu({ user, tenant, logout, onClose }) {
  const navigate = useNavigate()
  const isPlatformAdmin = user?.is_platform_admin || !!user?.platform_role
  const initials = user?.email ? user.email[0].toUpperCase() : '?'

  function handleNav(path) {
    onClose()
    navigate(path)
  }

  return (
    <div className="absolute right-0 top-full mt-2 w-64 bg-white/95 backdrop-blur-xl border border-brand-100 rounded-2xl shadow-brand-lg py-1.5 z-50 animate-fade-up">
      {/* User info */}
      <div className="px-4 py-3 border-b border-brand-50">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-brand-600 to-brand-400 flex items-center justify-center text-white text-sm font-bold shrink-0">
            {initials}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-slate-800 truncate">{user?.email}</p>
            <span className="inline-block mt-0.5 text-[11px] font-semibold uppercase tracking-wider text-brand-600 bg-brand-50 rounded-full px-2 py-0.5">
              {user?.role || 'user'}
            </span>
          </div>
        </div>
      </div>

      {/* Links */}
      <div className="py-1">
        {USER_MENU_LINKS.map(item => (
          <button
            key={item.path}
            onClick={() => handleNav(item.path)}
            className="w-full flex items-center gap-2.5 px-4 py-2 text-sm text-slate-600 hover:bg-brand-50 hover:text-brand-700 transition-colors"
          >
            <item.icon className="w-4 h-4 text-slate-400" />
            {item.label}
          </button>
        ))}
      </div>

      <div className="mx-3 my-1 border-t border-brand-50" />

      {/* Admin (conditional) */}
      {isPlatformAdmin && (
        <button
          onClick={() => handleNav('/admin')}
          className="w-full flex items-center gap-2.5 px-4 py-2 text-sm text-slate-600 hover:bg-brand-50 hover:text-brand-700 transition-colors"
        >
          <Shield className="w-4 h-4 text-slate-400" />
          Admin Portal
        </button>
      )}

      {/* Logout */}
      <button
        onClick={() => { onClose(); logout() }}
        className="w-full flex items-center gap-2.5 px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
      >
        <LogOut className="w-4 h-4" />
        Sign out
      </button>
    </div>
  )
}

/* ── Mobile bottom tab bar ───────────────────────────── */

function MobileTabBar({ location }) {
  const [moreOpen, setMoreOpen] = useState(false)
  const sheetRef = useRef(null)

  // Close sheet on route change
  useEffect(() => { setMoreOpen(false) }, [location.pathname])

  // Close sheet on outside tap
  useEffect(() => {
    function handleClick(e) {
      if (sheetRef.current && !sheetRef.current.contains(e.target)) {
        setMoreOpen(false)
      }
    }
    if (moreOpen) document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [moreOpen])

  const tabs = [
    { label: 'Home', path: '/', icon: LayoutDashboard },
    { label: 'Jobs', path: '/jd-library', icon: Briefcase },
    { label: 'Candidates', path: '/candidates', icon: Users },
  ]

  return (
    <>
      {/* Backdrop */}
      {moreOpen && (
        <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40 md:hidden" onClick={() => setMoreOpen(false)} />
      )}

      {/* More sheet */}
      {moreOpen && (
        <div
          ref={sheetRef}
          className="fixed bottom-16 left-0 right-0 bg-white/95 backdrop-blur-xl border-t border-brand-100 rounded-t-2xl shadow-brand-xl z-50 md:hidden animate-fade-up"
        >
          <MobileMoreSheet onNavigate={() => setMoreOpen(false)} />
        </div>
      )}

      {/* Tab bar */}
      <nav className="fixed bottom-0 left-0 right-0 bg-white/90 backdrop-blur-xl border-t border-brand-100/60 z-40 md:hidden">
        <div className="flex items-center justify-around h-16 px-2">
          {tabs.map(tab => {
            const active = location.pathname === tab.path
            return (
              <Link
                key={tab.path}
                to={tab.path}
                className={`flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-lg transition-colors ${
                  active ? 'text-brand-600' : 'text-slate-400'
                }`}
              >
                <tab.icon className="w-5 h-5" />
                <span className="text-[10px] font-medium">{tab.label}</span>
              </Link>
            )
          })}
          <button
            onClick={() => setMoreOpen(v => !v)}
            className={`flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-lg transition-colors ${
              moreOpen ? 'text-brand-600' : 'text-slate-400'
            }`}
          >
            <MoreHorizontal className="w-5 h-5" />
            <span className="text-[10px] font-medium">More</span>
          </button>
        </div>
      </nav>
    </>
  )
}

/* ── Mobile "More" sheet content ─────────────────────── */

function MobileMoreSheet({ onNavigate }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const isPlatformAdmin = user?.is_platform_admin || !!user?.platform_role
  const initials = user?.email ? user.email[0].toUpperCase() : '?'

  function handleNav(path) {
    onNavigate()
    navigate(path)
  }

  return (
    <div className="max-w-md mx-auto p-4 pb-6">
      {/* User info */}
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-brand-600 to-brand-400 flex items-center justify-center text-white text-sm font-bold">
          {initials}
        </div>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-slate-800 truncate">{user?.email}</p>
          <span className="inline-block text-[11px] font-semibold uppercase tracking-wider text-brand-600 bg-brand-50 rounded-full px-2 py-0.5">
            {user?.role || 'user'}
          </span>
        </div>
      </div>

      {/* Links grid */}
      <div className="grid grid-cols-3 gap-3">
        {USER_MENU_LINKS.map(item => (
          <button
            key={item.path}
            onClick={() => handleNav(item.path)}
            className="flex flex-col items-center gap-1.5 p-3 rounded-xl text-slate-600 hover:bg-brand-50 hover:text-brand-700 transition-colors"
          >
            <item.icon className="w-5 h-5" />
            <span className="text-xs font-medium">{item.label}</span>
          </button>
        ))}

        {isPlatformAdmin && (
          <button
            onClick={() => handleNav('/admin')}
            className="flex flex-col items-center gap-1.5 p-3 rounded-xl text-slate-600 hover:bg-brand-50 hover:text-brand-700 transition-colors"
          >
            <Shield className="w-5 h-5" />
            <span className="text-xs font-medium">Admin</span>
          </button>
        )}
      </div>

      <div className="mt-4 pt-3 border-t border-brand-50">
        <button
          onClick={() => { onNavigate(); logout() }}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 rounded-xl transition-colors"
        >
          <LogOut className="w-4 h-4" />
          Sign out
        </button>
      </div>
    </div>
  )
}

/* ── Main Component ──────────────────────────────────── */

export default function NavBar() {
  const { user, tenant, logout } = useAuth()
  const location = useLocation()
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const userMenuRef = useRef(null)
  const initials = user?.email ? user.email[0].toUpperCase() : '?'

  // Close user menu on outside click
  useEffect(() => {
    function handleClick(e) {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target)) {
        setUserMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  return (
    <>
      <header className="bg-white/80 backdrop-blur-xl border-b border-brand-100/60 sticky top-0 z-30 print:hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between gap-4">

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

          {/* Desktop primary nav */}
          <nav className="hidden md:flex items-center gap-1">
            {PRIMARY_NAV.map(item => {
              const active = location.pathname === item.path
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`relative flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                    active
                      ? 'text-brand-700'
                      : 'text-slate-500 hover:text-brand-700 hover:bg-brand-50/60'
                  }`}
                >
                  <item.icon className={`w-4 h-4 ${active ? 'text-brand-600' : ''}`} />
                  {item.label}
                  {/* Active underline */}
                  {active && (
                    <span className="absolute -bottom-[9px] left-1/2 -translate-x-1/2 w-5 h-0.5 bg-brand-600 rounded-full" />
                  )}
                </Link>
              )
            })}
          </nav>

          {/* Right: progress + avatar (desktop) */}
          <div className="hidden md:flex items-center gap-3">
            <ProgressBadge />
            <div ref={userMenuRef} className="relative">
              <button
                onClick={() => setUserMenuOpen(v => !v)}
                className="flex items-center gap-2 rounded-full p-1 hover:bg-brand-50 transition-colors"
                aria-label="User menu"
              >
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-brand-600 to-brand-400 flex items-center justify-center text-white text-xs font-bold">
                  {initials}
                </div>
              </button>

              {userMenuOpen && (
                <UserMenu user={user} tenant={tenant} logout={logout} onClose={() => setUserMenuOpen(false)} />
              )}
            </div>
          </div>

          {/* Mobile: logo already shown, just show progress + avatar on right */}
          <div className="md:hidden flex items-center gap-2">
            <ProgressBadge />
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-brand-600 to-brand-400 flex items-center justify-center text-white text-xs font-bold">
              {initials}
            </div>
          </div>
        </div>
      </header>

      {/* Mobile bottom tab bar */}
      <MobileTabBar location={location} />
    </>
  )
}
