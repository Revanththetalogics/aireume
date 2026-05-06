import { Navigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

function isPlatformAdmin(user) {
  if (!user) return false
  return user.is_platform_admin === true || !!user.platform_role
}

export default function PlatformAdminRoute({ children }) {
  const { user, loading } = useAuth()

  if (loading) return null
  if (!isPlatformAdmin(user)) return <Navigate to="/" replace />
  return children
}
