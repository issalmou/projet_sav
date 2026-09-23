const STORAGE_KEY_PREFIX = 'sav_notification_prefs'

export const PREFERENCES_CHANGED_EVENT = 'sav-notification-prefs-changed'

export const DEFAULT_NOTIFICATION_PREFS = {
  notificationsEnabled: true,
  ticketUpdates: true,
  productAlerts: true,
}

export function prefsStorageKey(userId) {
  return `${STORAGE_KEY_PREFIX}_${userId}`
}

export function loadNotificationPrefs(userId) {
  if (!userId) return { ...DEFAULT_NOTIFICATION_PREFS }
  try {
    const raw = localStorage.getItem(prefsStorageKey(userId))
    return raw
      ? { ...DEFAULT_NOTIFICATION_PREFS, ...JSON.parse(raw) }
      : { ...DEFAULT_NOTIFICATION_PREFS }
  } catch {
    return { ...DEFAULT_NOTIFICATION_PREFS }
  }
}

export function saveNotificationPrefs(userId, prefs) {
  if (!userId) return false
  try {
    localStorage.setItem(prefsStorageKey(userId), JSON.stringify(prefs))
    window.dispatchEvent(new CustomEvent(PREFERENCES_CHANGED_EVENT, { detail: { userId, prefs } }))
    return true
  } catch {
    return false
  }
}