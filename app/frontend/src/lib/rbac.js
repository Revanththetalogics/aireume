/** Tenant role helpers — mirrors backend rbac.py */

export const TENANT_ROLE_ADMIN = 'admin'
export const TENANT_ROLE_RECRUITER = 'recruiter'
export const TENANT_ROLE_VIEWER = 'viewer'

const WRITE_ROLES = new Set([TENANT_ROLE_ADMIN, TENANT_ROLE_RECRUITER])

export function normalizeTenantRole(role) {
  const r = (role || TENANT_ROLE_RECRUITER).toLowerCase()
  if (r === TENANT_ROLE_ADMIN || r === TENANT_ROLE_RECRUITER || r === TENANT_ROLE_VIEWER) {
    return r
  }
  return TENANT_ROLE_RECRUITER
}

export function getPermissions(user) {
  const role = normalizeTenantRole(user?.role)
  return {
    role,
    canWrite: WRITE_ROLES.has(role),
    isAdmin: role === TENANT_ROLE_ADMIN,
    isRecruiter: role === TENANT_ROLE_RECRUITER,
    isViewer: role === TENANT_ROLE_VIEWER,
  }
}

export const VIEWER_READ_ONLY_MESSAGE =
  'Your account is read-only. Ask an admin to upgrade your role to recruiter.'
