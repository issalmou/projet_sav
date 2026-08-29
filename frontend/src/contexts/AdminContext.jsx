import { createContext, useCallback, useEffect, useState } from 'react'
import { apiRequest } from '../api/client'
import { useAuth } from './useAuth'

const AdminContext = createContext(null)

function adaptUser(item) {
  const name = item.full_name || item.email
  return { ...item, id: item.id, name, phone: item.phone_number || '', role: item.role?.name || 'client', status: item.is_active ? 'active' : 'inactive', createdAt: item.created_at, lastLogin: null }
}

export function AdminProvider({ children }) {
  const { user } = useAuth()
  const token = user?.access_token || user?.token
  const [users, setUsers] = useState([])
  const [documents] = useState([])
  const [integrations] = useState([])
  const [settings] = useState({})
  const [logs] = useState([])

  const reloadUsers = useCallback(async () => {
    const data = await apiRequest('/users/', { token })
    setUsers((Array.isArray(data) ? data : data.items || []).map(adaptUser))
  }, [token])
  useEffect(() => { if (token) reloadUsers().catch(() => setUsers([])) }, [token, reloadUsers])

  const createUser = async (data) => {
    const result = await apiRequest('/users/', { token, method: 'POST', body: JSON.stringify({ email: data.email, full_name: data.name, phone_number: data.phone, password: data.password || 'ChangeMe123!', is_active: data.status !== 'inactive' }) })
    await reloadUsers(); return adaptUser(result)
  }
  const updateUser = async (id, data) => {
    const result = await apiRequest(`/users/${id}`, { token, method: 'PUT', body: JSON.stringify({ full_name: data.name, phone_number: data.phone, is_active: data.status !== 'inactive' }) })
    await reloadUsers(); return adaptUser(result)
  }
  const deleteUser = async (id) => { await apiRequest(`/users/${id}`, { token, method: 'DELETE' }); await reloadUsers() }

  const unsupported = () => { throw new Error('Cette fonctionnalité doit être implémentée par le backend.') }
  const logActivity = () => {}
  return <AdminContext.Provider value={{ users, documents, integrations, settings, logs, createUser, updateUser, deleteUser, createDocument: unsupported, updateDocument: unsupported, deleteDocument: unsupported, addIntegration: unsupported, updateIntegration: unsupported, toggleIntegration: unsupported, deleteIntegration: unsupported, updateSettings: unsupported, logActivity, clearLogs: unsupported }}>{children}</AdminContext.Provider>
}

export default AdminContext
