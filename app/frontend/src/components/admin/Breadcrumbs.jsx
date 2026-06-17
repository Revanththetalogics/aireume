import { Link, useLocation } from 'react-router-dom'

const PATH_LABELS = {
  admin:         'Admin',
  tenants:       'Tenants',
  plans:         'Plans',
  users:         'Users',
  features:      'Feature Flags',
  webhooks:      'Webhooks',
  'rate-limits': 'Rate Limits',
  sso:           'SSO',
  email:         'Email Settings',
  metrics:       'Metrics',
  audit:         'Audit Log',
  security:      'Security Events',
  billing:       'Revenue',
  invoices:      'Invoices',
  dunning:       'Dunning',
  erasure:       'Data Erasure',
  impersonation: 'Impersonation',
}

export default function Breadcrumbs() {
  const location = useLocation()

  // Build segments from pathname
  const segments = location.pathname
    .split('/')
    .filter(Boolean)

  // Build cumulative paths
  const crumbs = segments.map((seg, idx) => ({
    label: PATH_LABELS[seg] || decodeURIComponent(seg),
    path: '/' + segments.slice(0, idx + 1).join('/'),
    isLast: idx === segments.length - 1,
  }))

  if (crumbs.length === 0) return null

  return (
    <nav className="flex items-center gap-1.5 text-sm" aria-label="Breadcrumb">
      {crumbs.map((crumb, idx) => (
        <span key={crumb.path} className="flex items-center gap-1.5">
          {idx > 0 && (
            <svg viewBox="0 0 20 20" fill="currentColor" className="w-3.5 h-3.5 text-gray-300 shrink-0">
              <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd"/>
            </svg>
          )}
          {crumb.isLast ? (
            <span className="font-semibold text-gray-800">{crumb.label}</span>
          ) : (
            <Link
              to={crumb.path}
              className="text-gray-500 hover:text-teal-600 transition-colors"
            >
              {crumb.label}
            </Link>
          )}
        </span>
      ))}
    </nav>
  )
}
