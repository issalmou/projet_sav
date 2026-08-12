import { createContext, useState, useEffect } from 'react'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const stored = localStorage.getItem('auth_user')
    return stored ? JSON.parse(stored) : null
  })

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
