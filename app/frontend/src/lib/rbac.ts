/** Tenant role helpers — mirrors backend rbac.py */

export const TENANT_ROLE_ADMIN = 'admin' as const
export const TENANT_ROLE_TA_LEAD = 'ta_lead' as const
export const TENANT_ROLE_RECRUITER = 'recruiter' as const
export const TENANT_ROLE_VIEWER = 'viewer' as const
export const TENANT_ROLE_HIRING_MANAGER = 'hiring_manager' as const

export type TenantRole =
  | typeof TENANT_ROLE_ADMIN
  | typeof TENANT_ROLE_TA_LEAD
  | typeof TENANT_ROLE_RECRUITER
  | typeof TENANT_ROLE_VIEWER
  | typeof TENANT_ROLE_HIRING_MANAGER

const WRITE_ROLES = new Set<TenantRole>([TENANT_ROLE_ADMIN, TENANT_ROLE_TA_LEAD, TENANT_ROLE_RECRUITER])
const ASSIGNMENT_ROLES = new Set<TenantRole>([TENANT_ROLE_ADMIN, TENANT_ROLE_TA_LEAD])
const RECRUITER_NAV_ROLES = new Set<TenantRole>([
  TENANT_ROLE_ADMIN,
  TENANT_ROLE_TA_LEAD,
  TENANT_ROLE_RECRUITER,
  TENANT_ROLE_VIEWER,
])

export function normalizeTenantRole(role?: string | null): TenantRole {
  const r = (role || TENANT_ROLE_RECRUITER).toLowerCase()
  if (
    r === TENANT_ROLE_ADMIN
    || r === TENANT_ROLE_TA_LEAD
    || r === TENANT_ROLE_RECRUITER
    || r === TENANT_ROLE_VIEWER
    || r === TENANT_ROLE_HIRING_MANAGER
  ) {
    return r
  }
  return TENANT_ROLE_RECRUITER
}

export function getPermissions(user?: { role?: string } | null) {
  const role = normalizeTenantRole(user?.role)
  return {
    role,
    canWrite: WRITE_ROLES.has(role),
    canAssign: ASSIGNMENT_ROLES.has(role),
    isAdmin: role === TENANT_ROLE_ADMIN,
    isTaLead: role === TENANT_ROLE_TA_LEAD,
    isRecruiter: role === TENANT_ROLE_RECRUITER,
    isViewer: role === TENANT_ROLE_VIEWER,
    isHiringManager: role === TENANT_ROLE_HIRING_MANAGER,
    showRecruiterNav: RECRUITER_NAV_ROLES.has(role),
  }
}

export const VIEWER_READ_ONLY_MESSAGE =
  'Your account is read-only. Ask an admin to upgrade your role to recruiter.'
