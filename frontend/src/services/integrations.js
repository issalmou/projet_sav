const STORAGE_KEY = 'crm_erp_integrations'
const UPDATE_EVENT = 'integrations-updated'

function uid() {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
}

export function readIntegrations() {
  try {
    const value = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
    return Array.isArray(value) ? value : []
  } catch {
    return []
  }
}

function persist(integrations) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(integrations))
  window.dispatchEvent(new Event(UPDATE_EVENT))
  return integrations
}

export function createIntegration(data) {
  const integration = {
    id: uid(),
    provider: data.provider || 'salesforce',
    name: data.name || '',
    type: data.type || 'crm',
    status: 'disconnected',
    enabled: false,
    apiUrl: '',
    apiKey: '',
    syncDirection: 'bidirectional',
    syncFrequency: 'realtime',
    lastSync: null,
    createdAt: new Date().toISOString(),
    ...data,
  }
  return persist([integration, ...readIntegrations()]).find((item) => item.id === integration.id)
}

export function updateIntegration(id, patch) {
  const integrations = readIntegrations()
  const index = integrations.findIndex((item) => item.id === id)
  if (index === -1) return null
  const updated = { ...integrations[index], ...patch }
  integrations[index] = updated
  persist(integrations)
  return updated
}

export function deleteIntegration(id) {
  const integrations = readIntegrations().filter((item) => item.id !== id)
  persist(integrations)
}

export function onIntegrationsChange(listener) {
  window.addEventListener(UPDATE_EVENT, listener)
  return () => window.removeEventListener(UPDATE_EVENT, listener)
}