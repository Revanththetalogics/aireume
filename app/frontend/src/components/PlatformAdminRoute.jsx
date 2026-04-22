import { Navigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function PlatformAdminRoute({ children }) {
  const { user, loading } = useAuth()

  if (loading) return null
  if (!user?.is_platform_admin) return <Navigate to="/" replace />
  return children
}
