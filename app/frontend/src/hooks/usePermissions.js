import { useMemo } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { getPermissions } from '../lib/rbac'

/** Tenant RBAC permissions derived from the logged-in user. */
export function usePermissions() {
  const { user } = useAuth()
  return useMemo(() => getPermissions(user), [user?.role, user?.id])
}

export default usePermissions
