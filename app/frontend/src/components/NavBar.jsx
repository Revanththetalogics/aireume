import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Sparkles, Users, LayoutTemplate, UserCircle, LogOut, ChevronDown, GitCompare, Users2, Video, MessageSquareText, Settings, LayoutDashboard, Shield, Menu, X, ChevronRight, BarChart3, Columns, Mail } from 'lucide-react'
import { useState, useRef, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'

const NAV_LINKS = [
  { label: 'Dashboard', path: '/', icon: LayoutDashboard },
  {
    label: 'Screening', icon: Sparkles,
    children: [
      { label: 'Analyze', path: '/analyze', icon: Sparkles },
      { label: 'Candidates', path: '/candidates', icon: Users },
      { label: 'Pipeline', path: '/pipeline', icon: Columns },
      { label: 'Compare', path: '/compare', icon: GitCompare },
      { label: 'Analytics', path: '/analytics', icon: BarChart3 },
    ]
  },
  { label: 'Jobs', path: '/jd-library', icon: LayoutTemplate },
  {
    label: 'Interviews', icon: Video,
    children: [
      { label: 'Video', path: '/video', icon: Video },
      { label: 'Transcript', path: '/transcript', icon: MessageSquareText },
    ]
  },
  { label: 'Team', path: '/team', icon: Users2 },
]

/* ── Helpers ──────────────────────────────────────────── */

function isActive(locationPath, item) {
  if (item.path) return locationPath === item.path
  if (item.children) {
    return item.children.some(
      child => locationPath === child.path || locationPath.startsWith(child.path + '/')
    )
  }
  return false
}

/* ── Desktop Dropdown ─────────────────────────────────── */

function NavDropdown({ item, location, onClose }) {
  const [open, setOpen] = useState(false)
  const containerRef = useRef(null)
  const timeoutRef = useRef(null)
  const active = isActive(location.pathname, item)

  // Close on outside click
  useEffect(() => {
    function handleClick(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    if (open) document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  // Close on route change
  useEffect(() => { setOpen(false) }, [location.pathname])

  function handleMouseEnter() {
    clearTimeout(timeoutRef.current)
    setOpen(true)
  }

  function handleMouseLeave() {
    timeoutRef.current = setTimeout(() => setOpen(false), 150)
  }

  return (
    <div ref={containerRef} className="relative" onMouseEnter={handleMouseEnter} onMouseLeave={handleMouseLeave}>
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className={`relative flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${
          active
            ? 'text-brand-700 bg-brand-50'
            : 'text-slate-500 hover:text-brand-700 hover:bg-brand-50/60'
        }`}
      >
        <item.icon className={`w-4 h-4 ${active ? 'text-brand-600' : ''}`} />
        {item.label}
        <ChevronDown className={`w-3 h-3 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
        {active && (
          <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-4 h-0.5 bg-brand-600 rounded-full" />
        )}
      </button>

      {open && (
        <div className="absolute left-0 top-full mt-1 w-48 bg-white border border-brand-100/80 shadow-lg rounded-xl py-1.5 z-50">
          {item.children.map(child => {
            const childActive = location.pathname === child.path
            return (
              <Link
                key={child.path}
                to={child.path}
                onClick={() => setOpen(false)}
                className={`flex items-center gap-2.5 px-3.5 py-2.5 text-sm font-medium transition-colors ${
                  childActive
                    ? 'text-brand-700 bg-brand-50'
                    : 'text-slate-600 hover:bg-gray-50 hover:text-brand-700'
                }`}
              >
                <child.icon className={`w-4 h-4 ${childActive ? 'text-brand-600' : 'text-slate-400'}`} />
                {child.label}
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}

/* ── Main Component ───────────────────────────────────── */

export default function NavBar() {
  const { user, tenant, logout } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [expandedGroup, setExpandedGroup] = useState(null)

  const initials = user?.email ? user.email[0].toUpperCase() : '?'

  // Close mobile menu on route change
  useEffect(() => { setMobileOpen(false); setExpandedGroup(null) }, [location.pathname])

  // Close user menu on outside click
  const userMenuRef = useRef(null)
  useEffect(() => {
    function handleClick(e) {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target)) {
        setUserMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  function toggleGroup(label) {
    setExpandedGroup(prev => (prev === label ? null : label))
  }

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

        {/* Desktop nav links */}
        <nav className="hidden md:flex items-center gap-0.5">
          {NAV_LINKS.map(item => {
            if (item.children) {
              return <NavDropdown key={item.label} item={item} location={location} />
            }

            const active = location.pathname === item.path
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`relative flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${
                  active
                    ? 'text-brand-700 bg-brand-50'
                    : 'text-slate-500 hover:text-brand-700 hover:bg-brand-50/60'
                }`}
              >
                <item.icon className={`w-4 h-4 ${active ? 'text-brand-600' : ''}`} />
                {item.label}
                {active && (
                  <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-4 h-0.5 bg-brand-600 rounded-full" />
                )}
              </Link>
            )
          })}
        </nav>

        {/* Right section: mobile hamburger + user menu */}
        <div className="flex items-center gap-2">
          {/* Mobile hamburger */}
          <button
            type="button"
            className="md:hidden p-2 rounded-xl text-slate-500 hover:bg-brand-50 hover:text-brand-700 transition-colors"
            onClick={() => setMobileOpen(v => !v)}
          >
            {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>

          {/* User menu */}
          <div ref={userMenuRef} className="relative">
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

                {/* Admin Link (conditional) */}
                {user?.is_platform_admin && (
                  <button
                    onClick={() => { setUserMenuOpen(false); navigate('/admin') }}
                    className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-700 hover:bg-brand-50 transition-colors"
                  >
                    <Shield className="w-4 h-4 text-slate-500" />
                    Admin Portal
                  </button>
                )}

                {/* Settings Link */}
                <button
                  onClick={() => { setUserMenuOpen(false); navigate('/settings') }}
                  className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-700 hover:bg-brand-50 transition-colors"
                >
                  <Settings className="w-4 h-4 text-slate-500" />
                  Settings & Subscription
                </button>

                {/* Email Settings Link */}
                <button
                  onClick={() => { setUserMenuOpen(false); navigate('/admin/email-settings') }}
                  className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-700 hover:bg-brand-50 transition-colors"
                >
                  <Mail className="w-4 h-4 text-slate-500" />
                  Email Settings
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
      </div>

      {/* ── Mobile menu overlay ────────────────────────── */}
      {mobileOpen && (
        <div className="md:hidden border-t border-brand-100/60 bg-white/95 backdrop-blur-xl">
          <nav className="max-w-7xl mx-auto px-4 py-3 space-y-1">
            {NAV_LINKS.map(item => {
              if (item.children) {
                const active = isActive(location.pathname, item)
                const expanded = expandedGroup === item.label
                return (
                  <div key={item.label}>
                    <button
                      type="button"
                      onClick={() => toggleGroup(item.label)}
                      className={`w-full flex items-center justify-between gap-1.5 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ${
                        active
                          ? 'text-brand-700 bg-brand-50'
                          : 'text-slate-500 hover:text-brand-700 hover:bg-brand-50/60'
                      }`}
                    >
                      <span className="flex items-center gap-1.5">
                        <item.icon className={`w-4 h-4 ${active ? 'text-brand-600' : ''}`} />
                        {item.label}
                      </span>
                      <ChevronRight className={`w-4 h-4 text-slate-400 transition-transform duration-200 ${expanded ? 'rotate-90' : ''}`} />
                    </button>
                    {expanded && (
                      <div className="ml-4 pl-3 border-l-2 border-brand-100 space-y-0.5 mt-0.5">
                        {item.children.map(child => {
                          const childActive = location.pathname === child.path
                          return (
                            <Link
                              key={child.path}
                              to={child.path}
                              className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                                childActive
                                  ? 'text-brand-700 bg-brand-50'
                                  : 'text-slate-500 hover:text-brand-700 hover:bg-brand-50/60'
                              }`}
                            >
                              <child.icon className={`w-4 h-4 ${childActive ? 'text-brand-600' : ''}`} />
                              {child.label}
                            </Link>
                          )
                        })}
                      </div>
                    )}
                  </div>
                )
              }

              const active = location.pathname === item.path
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-1.5 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ${
                    active
                      ? 'text-brand-700 bg-brand-50'
                      : 'text-slate-500 hover:text-brand-700 hover:bg-brand-50/60'
                  }`}
                >
                  <item.icon className={`w-4 h-4 ${active ? 'text-brand-600' : ''}`} />
                  {item.label}
                </Link>
              )
            })}
          </nav>
        </div>
      )}
    </header>
  )
}
