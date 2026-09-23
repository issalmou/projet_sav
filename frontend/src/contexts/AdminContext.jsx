import { createContext, useCallback, useEffect, useState } from 'react'
import { apiRequest } from '../api/client'
import { useAuth } from './useAuth'
import { can, resolveRole } from './roles'
import { clearActivityLogs, readActivityLogs, recordActivity } from '../services/activityLog'
import { readSettings, saveSettings } from '../services/settings'
import {
  createIntegration as persistCreateIntegration,
  deleteIntegration as persistDeleteIntegration,
  onIntegrationsChange,
  readIntegrations,
  updateIntegration as persistUpdateIntegration,
} from '../services/integrations'

const AdminContext = createContext(null)

function adaptUser(item) {
  const name = item.full_name || item.email
  const backendRole = typeof item.role === 'string' ? item.role : item.role?.name
  return {
    ...item,
    id: item.id,
    name,
    phone: item.phone_number || '',
    role: resolveRole(backendRole || item.role?.key || item.role_name) || 'client',
    roleId: item.role?.id || item.role_id || null,
    status: item.is_active === false || item.status === 'inactive' ? 'inactive' : 'active',
    createdAt: item.created_at,
    lastLogin: null,
  }
}

export function AdminProvider({ children }) {
  const { user } = useAuth()
  const token = user?.access_token || user?.token
  const canManageUsers = can(user, 'users.manage')
  const [users, setUsers] = useState([])
  const [roles, setRoles] = useState([])
  const [documents] = useState([])
  const [integrations, setIntegrations] = useState(readIntegrations)
  const [settings, setSettings] = useState(readSettings)
  const [logs, setLogs] = useState(readActivityLogs)

  useEffect(() => {
    const refreshLogs = () => setLogs(readActivityLogs())
    window.addEventListener('activity-log-updated', refreshLogs)
    return () => window.removeEventListener('activity-log-updated', refreshLogs)
  }, [])

  useEffect(() => {
    const refreshIntegrations = () => setIntegrations(readIntegrations())
    return onIntegrationsChange(refreshIntegrations)
  }, [])

  const logActivity = (entry) => recordActivity({
    actor: user?.name || user?.email || 'Utilisateur connecté',
    actorRole: user?.role || '',
    ...entry,
  })

  const reloadUsers = useCallback(async () => {
    const data = await apiRequest('/users/', { token })
    setUsers((Array.isArray(data) ? data : data.items || []).map(adaptUser))
  }, [token])
  useEffect(() => {
    if (token && canManageUsers) reloadUsers().catch(() => setUsers([]))
    else setUsers([])
  }, [token, canManageUsers, reloadUsers])

  const reloadRoles = useCallback(async () => {
    const data = await apiRequest('/roles/', { token })
    setRoles(Array.isArray(data) ? data : data.items || [])
  }, [token])
  useEffect(() => {
    if (token && canManageUsers) reloadRoles().catch(() => setRoles([]))
    else setRoles([])
  }, [token, canManageUsers, reloadRoles])

  const createUser = async (data) => {
    const result = await apiRequest('/users/', {
      token,
      method: 'POST',
      body: JSON.stringify({
        email: data.email,
        full_name: data.name,
        phone_number: data.phone,
        password: data.password,
        role_id: data.roleId,
        is_active: data.status !== 'inactive',
      }),
    })
    if (data.product_ids?.length && result.id) {
      await apiRequest(`/clients/${result.id}/products`, {
        token,
        method: 'POST',
        body: JSON.stringify({
          items: data.product_ids.map((productId) => ({ product_id: productId, qte: 1 })),
        }),
      })
    }
    await reloadUsers()
    logActivity({ action: 'user.created', category: 'users', target: String(result.id), details: `Utilisateur créé : ${data.email}` })
    return adaptUser(result)
  }
  const updateUser = async (id, data) => {
    const result = await apiRequest(`/users/${id}`, {
      token,
      method: 'PUT',
      body: JSON.stringify({
        full_name: data.name,
        phone_number: data.phone,
        role_id: data.roleId,
        is_active: data.status !== 'inactive',
      }),
    })
    if (data.product_ids && ['client'].includes(data.role)) {
      await apiRequest(`/clients/${id}/products`, {
        token,
        method: 'PUT',
        body: JSON.stringify({
          items: data.product_ids.map((productId) => ({ product_id: productId, qte: 1 })),
        }),
      })
    }
    await reloadUsers()
    logActivity({ action: 'user.updated', category: 'users', target: String(id), details: `Utilisateur modifié : ${data.name || id}` })
    return adaptUser(result)
  }
  const deleteUser = async (id) => {
    await apiRequest(`/users/${id}`, { token, method: 'DELETE' })
    await reloadUsers()
    logActivity({ action: 'user.deleted', category: 'users', target: String(id), details: `Utilisateur supprimé : ${id}`, severity: 'warning' })
  }

  const unsupported = () => { throw new Error('Cette fonctionnalité doit être implémentée par le backend.') }
  const clearLogs = () => clearActivityLogs()

  const updateSettings = (patch) => {
    const saved = saveSettings(patch)
    setSettings(saved)
    logActivity({ action: 'settings.updated', category: 'settings', details: 'Paramètres de la plateforme mis à jour.' })
    return saved
  }

  const addIntegration = (data) => {
    const integration = persistCreateIntegration(data)
    setIntegrations(readIntegrations())
    logActivity({ action: 'integration.created', category: 'integrations', target: integration.id, details: `Intégration ajoutée : ${integration.name}` })
    return integration
  }
  const updateIntegration = (id, patch) => {
    const updated = persistUpdateIntegration(id, patch)
    setIntegrations(readIntegrations())
    if (updated) {
      logActivity({ action: 'integration.updated', category: 'integrations', target: String(id), details: `Intégration modifiée : ${updated.name || id}` })
    }
    return updated
  }
  const toggleIntegration = (id) => {
    const current = readIntegrations().find((item) => item.id === id)
    const updated = persistUpdateIntegration(id, { enabled: !current?.enabled })
    setIntegrations(readIntegrations())
    if (updated) {
      logActivity({ action: 'integration.toggled', category: 'integrations', target: String(id), details: `Intégration ${updated.enabled ? 'activée' : 'désactivée'} : ${updated.name || id}` })
    }
    return updated
  }
  const deleteIntegration = (id) => {
    const current = readIntegrations().find((item) => item.id === id)
    persistDeleteIntegration(id)
    setIntegrations(readIntegrations())
    logActivity({ action: 'integration.deleted', category: 'integrations', target: String(id), details: `Intégration supprimée : ${current?.name || id}`, severity: 'warning' })
  }
  return <AdminContext.Provider value={{ users, roles, documents, integrations, settings, logs, createUser, updateUser, deleteUser, createDocument: unsupported, updateDocument: unsupported, deleteDocument: unsupported, addIntegration, updateIntegration, toggleIntegration, deleteIntegration, updateSettings, logActivity, clearLogs }}>{children}</AdminContext.Provider>
}

export default AdminContext
