import { Link, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'

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
        <motion.span
          key={crumb.path}
          initial={{ opacity: 0, x: -4 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: idx * 0.05 }}
          className="flex items-center gap-1.5"
        >
          {idx > 0 && (
            <motion.svg
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: idx * 0.05 + 0.025 }}
              viewBox="0 0 20 20" fill="currentColor" className="w-3.5 h-3.5 text-gray-300 shrink-0"
            >
              <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd"/>
            </motion.svg>
          )}
          {crumb.isLast ? (
            <motion.span
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: idx * 0.05 + 0.05 }}
              className="font-semibold text-gray-800 dark:text-dark-text-primary"
            >
              {crumb.label}
            </motion.span>
          ) : (
            <Link
              to={crumb.path}
              className="text-gray-500 hover:text-teal-600 transition-colors"
            >
              {crumb.label}
            </Link>
          )}
        </motion.span>
      ))}
    </nav>
  )
}
