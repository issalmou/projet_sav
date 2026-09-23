import { createContext, useCallback, useEffect, useMemo, useState } from 'react'
import { useAuth } from '../contexts/useAuth'
import { translations, DEFAULT_LANGUAGE, LANGUAGE_DIRS } from './translations'
import { readSettings, onSettingsChange } from '../services/settings'

export const LANGUAGE_STORAGE_KEY = 'sav_language'

function toLocale(lang) {
  if (lang === 'ar') return 'ar-MA'
  if (lang === 'en') return 'en-GB'
  return 'fr-FR'
}

function loadStoredLanguage() {
  try {
    const stored = localStorage.getItem(LANGUAGE_STORAGE_KEY)
    if (stored && ['fr', 'en', 'ar'].includes(stored)) return stored
  } catch {
    // stockage indisponible
  }
  return null
}

function loadPlatformLanguage() {
  try {
    const lang = readSettings().language
    return ['fr', 'en', 'ar'].includes(lang) ? lang : DEFAULT_LANGUAGE
  } catch {
    return DEFAULT_LANGUAGE
  }
}

function interpolate(template, vars) {
  if (!vars) return template
  return template.replace(/\{(\w+)\}/g, (_, key) =>
    vars[key] !== undefined && vars[key] !== null ? String(vars[key]) : `{${key}}`
  )
}

export const LanguageContext = createContext(null)

export function LanguageProvider({ children }) {
  const { user } = useAuth()
  const preferred = user?.preferred_language
  const [language, setLanguageState] = useState(
    () => loadStoredLanguage() || preferred || loadPlatformLanguage()
  )

  useEffect(() => {
    if (preferred && ['fr', 'en', 'ar'].includes(preferred)) {
      setLanguageState(preferred)
    }
  }, [preferred])

  useEffect(() => {
    return onSettingsChange(() => {
      if (loadStoredLanguage() || user?.preferred_language) return
      setLanguageState(loadPlatformLanguage())
    })
  }, [user?.preferred_language])

  useEffect(() => {
    try {
      localStorage.setItem(LANGUAGE_STORAGE_KEY, language)
    } catch {
      // stockage indisponible
    }
    document.documentElement.setAttribute('lang', language)
    document.documentElement.setAttribute('dir', LANGUAGE_DIRS[language] || 'ltr')
  }, [language])

  const setLanguage = useCallback((lang) => {
    if (['fr', 'en', 'ar'].includes(lang)) setLanguageState(lang)
  }, [])

  const t = useCallback(
    (key, vars) => {
      const dict = translations[language] || translations[DEFAULT_LANGUAGE]
      const value = dict[key]
      if (value === undefined) return translations[DEFAULT_LANGUAGE][key] ?? key
      return interpolate(value, vars)
    },
    [language]
  )

  const formatDate = useCallback(
    (iso, options = { day: '2-digit', month: '2-digit', year: 'numeric' }) => {
      if (!iso) return '—'
      try {
        return new Intl.DateTimeFormat(toLocale(language), options).format(new Date(iso))
      } catch {
        return '—'
      }
    },
    [language]
  )

  const timeAgo = useCallback(
    (iso) => {
      if (!iso) return ''
      const seconds = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
      if (seconds < 60) return t('time.justNow')
      const minutes = Math.floor(seconds / 60)
      if (minutes < 60) return t('time.minutesAgo', { n: minutes })
      const hours = Math.floor(minutes / 60)
      if (hours < 24) return t('time.hoursAgo', { n: hours })
      const days = Math.floor(hours / 24)
      if (days < 7) return t('time.daysAgo', { n: days })
      return formatDate(iso)
    },
    [t, formatDate]
  )

  const value = useMemo(
    () => ({ language, setLanguage, t, formatDate, timeAgo, dir: LANGUAGE_DIRS[language] || 'ltr' }),
    [language, setLanguage, t, formatDate, timeAgo]
  )

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}

export default LanguageContext