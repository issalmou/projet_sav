const STORAGE_KEY = 'sav_platform_settings'
const UPDATE_EVENT = 'platform-settings-updated'

export const DEFAULT_PLATFORM_SETTINGS = {
  companyName: '3LM Solutions',
  supportEmail: '',
  supportPhone: '',
  language: 'fr',
  timezone: 'Europe/Paris',
  defaultTicketPriority: 'medium',
  slaDays: 7,
  emailNotifications: {
    ticketCreated: true,
    ticketAssigned: true,
    ticketResolved: true,
    weeklyDigest: false,
  },
  security: {
    sessionTimeout: 60,
    passwordPolicy: 'medium',
    twoFactorAuth: false,
  },
}

export function readSettings() {
  try {
    const value = JSON.parse(localStorage.getItem(STORAGE_KEY))
    if (!value || typeof value !== 'object') return { ...DEFAULT_PLATFORM_SETTINGS }
    return {
      ...DEFAULT_PLATFORM_SETTINGS,
      ...value,
      emailNotifications: { ...DEFAULT_PLATFORM_SETTINGS.emailNotifications, ...value.emailNotifications },
      security: { ...DEFAULT_PLATFORM_SETTINGS.security, ...value.security },
    }
  } catch {
    return { ...DEFAULT_PLATFORM_SETTINGS }
  }
}

export function saveSettings(patch) {
  const merged = {
    ...readSettings(),
    ...patch,
    emailNotifications: { ...readSettings().emailNotifications, ...(patch.emailNotifications || {}) },
    security: { ...readSettings().security, ...(patch.security || {}) },
  }
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(merged))
    window.dispatchEvent(new Event(UPDATE_EVENT))
  } catch {
    // stockage indisponible
  }
  return merged
}

export function onSettingsChange(listener) {
  window.addEventListener(UPDATE_EVENT, listener)
  return () => window.removeEventListener(UPDATE_EVENT, listener)
}