import { describe, it, expect } from 'vitest'
import { getPermissions, normalizeTenantRole } from '../lib/rbac'

describe('rbac', () => {
  it('normalizes unknown roles to recruiter', () => {
    expect(normalizeTenantRole('hm')).toBe('recruiter')
  })

  it('grants write to admin and recruiter', () => {
    expect(getPermissions({ role: 'admin' }).canWrite).toBe(true)
    expect(getPermissions({ role: 'recruiter' }).canWrite).toBe(true)
  })

  it('denies write to viewer', () => {
    const perms = getPermissions({ role: 'viewer' })
    expect(perms.canWrite).toBe(false)
    expect(perms.isViewer).toBe(true)
    expect(perms.isAdmin).toBe(false)
  })
})
