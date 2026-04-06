import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import api from '../lib/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [tenant, setTenant] = useState(null)
  const [loading, setLoading] = useState(true)

  // Check auth status on app load by calling /auth/me
  // Browser automatically sends httpOnly cookies with the request
  const loadUser = useCallback(async () => {
    try {
      const res = await api.get('/auth/me')
      setUser(res.data.user)
      setTenant(res.data.tenant)
    } catch {
      // Cookie is invalid or expired - user is not authenticated
      setUser(null)
      setTenant(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadUser()
  }, [loadUser])

  const login = async (email, password) => {
    const res = await api.post('/auth/login', { email, password })
    // Tokens are set as httpOnly cookies by the server
    // We still receive tokens in response body for API clients
    setUser(res.data.user)
    setTenant(res.data.tenant)
    return res.data
  }

  const register = async (companyName, email, password) => {
    const res = await api.post('/auth/register', { company_name: companyName, email, password })
    // Tokens are set as httpOnly cookies by the server
    setUser(res.data.user)
    setTenant(res.data.tenant)
    return res.data
  }

  const logout = async () => {
    try {
      // Call logout endpoint to clear httpOnly cookies
      await api.post('/auth/logout')
    } catch {
      // Ignore errors - proceed to clear local state
    }
    setUser(null)
    setTenant(null)
  }

  return (
    <AuthContext.Provider value={{ user, tenant, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
