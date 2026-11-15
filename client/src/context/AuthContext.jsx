import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import AuthService from '../service/authService.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    let current = null
    try {
      const data = await AuthService.me()
      current = data.status === 200 && data.user ? data.user : null
    } catch {
      current = null
    }
    setUser(current)
    setLoading(false)
    return current
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  const logout = useCallback(() => setUser(null), [])

  const value = useMemo(
    () => ({ user, loading, isAuthenticated: !!user, refresh, setUser, logout }),
    [user, loading, refresh, logout]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
