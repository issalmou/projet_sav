import { useContext } from 'react'
import { LanguageContext } from './LanguageContext'

export function useI18n() {
  const ctx = useContext(LanguageContext)
  if (!ctx) {
    throw new Error('useI18n must be used within a LanguageProvider')
  }
  return ctx
}