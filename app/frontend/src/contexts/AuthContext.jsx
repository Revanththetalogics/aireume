import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react'
import api from '../lib/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [tenant, setTenant] = useState(null)
  const [loading, setLoading] = useState(true)
  const authGenRef = useRef(0)

  // Check auth status on app load by calling /auth/me
  // Browser automatically sends httpOnly cookies with the request
  const loadUser = useCallback(async () => {
    const gen = ++authGenRef.current
    try {
      const res = await api.get('/auth/me')
      if (gen !== authGenRef.current) return   // stale — login/register won
      setUser(res.data.user)
      setTenant(res.data.tenant)
    } catch {
      if (gen !== authGenRef.current) return   // stale — login/register won
      // Cookie is invalid or expired - user is not authenticated
      setUser(null)
      setTenant(null)
    } finally {
      if (gen === authGenRef.current) {
        setLoading(false)
      }
    }
  }, [])

  useEffect(() => {
    loadUser()
  }, [loadUser])

  const login = async (email, password) => {
    authGenRef.current++   // invalidate any in-flight loadUser
    const res = await api.post('/auth/login', { email, password })
    // Tokens are set as httpOnly cookies by the server
    // We still receive tokens in response body for API clients
    setUser(res.data.user)
    setTenant(res.data.tenant)
    setLoading(false)
    return res.data
  }

  const register = async (companyName, email, password) => {
    authGenRef.current++   // invalidate any in-flight loadUser
    const res = await api.post('/auth/register', { company_name: companyName, email, password })
    // Tokens are set as httpOnly cookies by the server
    setUser(res.data.user)
    setTenant(res.data.tenant)
    setLoading(false)
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
