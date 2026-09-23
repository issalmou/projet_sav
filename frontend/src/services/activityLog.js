const STORAGE_KEY = 'activity_logs'

export function readActivityLogs() {
  try {
    const value = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
    return Array.isArray(value) ? value : []
  } catch {
    return []
  }
}

export function recordActivity(entry) {
  const log = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    createdAt: new Date().toISOString(),
    actor: 'Utilisateur connecté',
    actorRole: '',
    target: '',
    ip: '—',
    severity: 'info',
    ...entry,
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify([log, ...readActivityLogs()]))
  window.dispatchEvent(new Event('activity-log-updated'))
  return log
}

export function clearActivityLogs() {
  localStorage.removeItem(STORAGE_KEY)
  window.dispatchEvent(new Event('activity-log-updated'))
}
