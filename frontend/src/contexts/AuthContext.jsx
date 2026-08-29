import { createContext, useState, useEffect } from 'react'
import { resolveRole } from './roles'

const AuthContext = createContext(null)

function loadStoredUser() {
  const stored = localStorage.getItem('auth_user')
  if (!stored) return null
  try {
    const user = JSON.parse(stored)
    if (user && typeof user.role === 'string') {
      user.role = resolveRole(user.role)
    }
    return user
  } catch {
    return null
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(loadStoredUser)

  useEffect(() => {
    if (user) {
      localStorage.setItem('auth_user', JSON.stringify(user))
    } else {
      localStorage.removeItem('auth_user')
    }
  }, [user])

  const login = (userData) => {
    const role = String(userData.role || '').toLowerCase()
    const email = userData.email || ''
    const name = userData.name || email.split('@')[0] || 'Utilisateur'
    const initials = name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2)

    setUser({
      ...userData,
      name,
      email,
      role,
      initials,
    })
    return true
  }

  const logout = () => {
    setUser(null)
  }

  const updateProfile = (updates) => {
    setUser((prev) => {
      if (!prev) return prev
      const name = updates.name?.trim() || prev.name
      const initials = name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
      return { ...prev, ...updates, name, initials }
    })
    return true
  }

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, login, logout, updateProfile }}>
      {children}
    </AuthContext.Provider>
  )
}

export default AuthContext
