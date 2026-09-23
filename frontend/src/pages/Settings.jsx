import { useEffect, useState } from 'react'
import { Save, Shield, BellRing, KeyRound, User, Phone, Globe, Loader2, Moon } from 'lucide-react'
import { useAuth } from '../contexts/useAuth'
import { apiRequest } from '../api/client'
import { loginRequest } from '../api/auth'
import { PageHeader, Field, Toggle, inputClass } from '../components/admin/ui'
import { useToast } from '../services/toast'
import { RoleBadge } from '../components/admin/badges'
import {
  loadNotificationPrefs,
  saveNotificationPrefs,
} from '../services/notificationPreferences'
import { useI18n } from '../i18n/useI18n'
import { LANGUAGES } from '../i18n/translations'

const DARK_MODE_STORAGE_KEY = 'sav_dark_mode'

function loadDarkMode() {
  try {
    return localStorage.getItem(DARK_MODE_STORAGE_KEY) === 'true'
  } catch {
    return false
  }
}

function validateNewPassword(value, t) {
  if (value.length < 8) return t('settings.passwordMin')
  if (!/[A-Z]/.test(value)) return t('settings.passwordUpper')
  if (!/\d/.test(value)) return t('settings.passwordDigit')
  return null
}

function Section({ icon: Icon, title, children }) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 custom-shadow overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-700 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-slate-100 dark:bg-slate-700 flex items-center justify-center">
          <Icon className="w-4 h-4 text-slate-600 dark:text-slate-300" />
        </div>
        <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">{title}</h3>
      </div>
      <div className="p-6 space-y-5">{children}</div>
    </div>
  )
}

function ToggleRow({ label, description, checked, onChange, disabled }) {
  return (
    <div className={`flex items-center justify-between gap-4 ${disabled ? 'opacity-50' : ''}`}>
      <div>
        <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">{label}</p>
        {description && <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{description}</p>}
      </div>
      <Toggle checked={checked} onChange={onChange} disabled={disabled} />
    </div>
  )
}

function SaveButton({ label, onClick, loading }) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className="inline-flex items-center gap-2 px-5 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed rounded-xl transition-colors shadow-lg shadow-blue-500/20"
    >
      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
      {label}
    </button>
  )
}

function Settings() {
  const { user, updateProfile } = useAuth()
  const { toastEl, showToast } = useToast()
  const { t, setLanguage } = useI18n()

  const token = user?.access_token || user?.token
  const [profile, setProfile] = useState({
    name: user?.full_name || user?.name || '',
    email: user?.email || '',
    phone: user?.phone_number || '',
    preferredLanguage: user?.preferred_language || 'fr',
  })
  const [notifications, setNotifications] = useState(() => loadNotificationPrefs(user?.id))
  const [passwords, setPasswords] = useState({
    current: '',
    new: '',
    confirm: '',
  })
  const [errors, setErrors] = useState({})
  const [savingProfile, setSavingProfile] = useState(false)
  const [savingPassword, setSavingPassword] = useState(false)
  const [darkMode, setDarkMode] = useState(loadDarkMode)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode)
    try {
      localStorage.setItem(DARK_MODE_STORAGE_KEY, JSON.stringify(darkMode))
    } catch {
      // stockage indisponible
    }
  }, [darkMode])

  const saveProfile = async () => {
    const errs = {}
    if (!profile.name.trim()) errs.name = t('settings.nameRequired')
    if (!profile.email.trim()) errs.email = t('settings.emailRequired')
    else if (!/\S+@\S+\.\S+/.test(profile.email)) errs.email = t('settings.emailInvalid')
    setErrors(errs)
    if (Object.keys(errs).length > 0) return

    setSavingProfile(true)
    try {
      const updated = await apiRequest('/auth/me', {
        token,
        method: 'PATCH',
        body: JSON.stringify({
          full_name: profile.name.trim(),
          email: profile.email.trim(),
          phone_number: profile.phone.trim() || null,
          preferred_language: profile.preferredLanguage,
        }),
      })
      const fullName = updated.full_name || profile.name.trim()
      updateProfile({
        name: fullName,
        full_name: fullName,
        phone_number: updated.phone_number ?? profile.phone.trim(),
        preferred_language: updated.preferred_language || profile.preferredLanguage,
        email: updated.email || profile.email.trim(),
      })
      showToast(t('settings.profileUpdated'))
    } catch (err) {
      const message = err.message || t('settings.profileError')
      if (/email/i.test(message)) {
        setErrors((prev) => ({ ...prev, email: t('settings.emailUsed') }))
      }
      showToast(message, 'error')
    } finally {
      setSavingProfile(false)
    }
  }

  const savePassword = async () => {
    if (!passwords.current) {
      showToast(t('settings.currentPasswordRequired'), 'error')
      return
    }
    const policyError = validateNewPassword(passwords.new, t)
    if (policyError) {
      showToast(policyError, 'error')
      return
    }
    if (passwords.new !== passwords.confirm) {
      showToast(t('settings.passwordMismatch'), 'error')
      return
    }

    setSavingPassword(true)
    try {
      await loginRequest({ email: user?.email, password: passwords.current })
    } catch {
      showToast(t('settings.passwordCurrentWrong'), 'error')
      setSavingPassword(false)
      return
    }

    try {
      await apiRequest('/auth/me', {
        token,
        method: 'PUT',
        body: JSON.stringify({ password: passwords.new }),
      })
      setPasswords({ current: '', new: '', confirm: '' })
      showToast(t('settings.passwordUpdated'))
    } catch (err) {
      showToast(err.message || t('settings.passwordError'), 'error')
    } finally {
      setSavingPassword(false)
    }
  }

  const saveNotifications = () => {
    const saved = saveNotificationPrefs(user?.id, notifications)
    if (saved) {
      showToast(t('settings.notifSaved'))
    } else {
      showToast(t('settings.notifSaveError'), 'error')
    }
  }

  return (
    <div className="flex-1 overflow-y-auto p-8">
      <div className="max-w-3xl mx-auto space-y-8">
        <PageHeader title={t('settings.title')} subtitle={t('settings.subtitle')} />

        {/* Profile card */}
        <div className="bg-gradient-to-r from-slate-900 to-blue-900 rounded-2xl p-6 text-white custom-shadow relative overflow-hidden">
          <div className="absolute -right-6 -bottom-6 opacity-10">
            <User className="w-40 h-40" />
          </div>
          <div className="relative z-10 flex items-center gap-4">
            <div className="w-16 h-16 rounded-full bg-white/10 border border-white/20 flex items-center justify-center text-xl font-bold">
              {user?.initials || 'U'}
            </div>
            <div>
              <p className="text-lg font-bold">{user?.name || 'Utilisateur'}</p>
              <p className="text-sm text-blue-200">{user?.email || ''}</p>
              <div className="mt-2">
                <RoleBadge role={user?.role} />
              </div>
            </div>
          </div>
        </div>

        <Section icon={User} title={t('settings.profile')}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <Field label={t('settings.fullName')} required error={errors.name}>
              <input
                type="text"
                value={profile.name}
                onChange={(e) => {
                  setProfile((prev) => ({ ...prev, name: e.target.value }))
                  if (errors.name) setErrors((prev) => ({ ...prev, name: undefined }))
                }}
                className={inputClass}
              />
            </Field>
            <Field label={t('settings.email')} required error={errors.email} hint={errors.email ? undefined : t('settings.emailHint')}>
              <input
                type="email"
                value={profile.email}
                onChange={(e) => {
                  setProfile((prev) => ({ ...prev, email: e.target.value }))
                  if (errors.email) setErrors((prev) => ({ ...prev, email: undefined }))
                }}
                className={inputClass}
              />
            </Field>
            <Field label={t('settings.phone')}>
              <div className="relative">
                <Phone className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="tel"
                  value={profile.phone}
                  onChange={(e) => setProfile((prev) => ({ ...prev, phone: e.target.value }))}
                  placeholder="+33 6 12 34 56 78"
                  className={`${inputClass} pl-10`}
                />
              </div>
            </Field>
            <Field label={t('settings.preferredLang')}>
              <div className="relative">
                <Globe className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <select
                  value={profile.preferredLanguage}
                  onChange={(e) => {
                    const value = e.target.value
                    setProfile((prev) => ({ ...prev, preferredLanguage: value }))
                    setLanguage(value)
                  }}
                  className={`${inputClass} pl-10 appearance-none`}
                >
                  {LANGUAGES.map((lang) => (
                    <option key={lang.value} value={lang.value}>{lang.label}</option>
                  ))}
                </select>
              </div>
            </Field>
          </div>
          <div className="flex justify-end">
            <SaveButton
              label={t('settings.saveProfile')}
              onClick={saveProfile}
              loading={savingProfile}
            />
          </div>
        </Section>

        <Section icon={KeyRound} title={t('settings.password')}>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <Field label={t('settings.currentPassword')}>
              <input
                type="password"
                value={passwords.current}
                onChange={(e) => setPasswords((prev) => ({ ...prev, current: e.target.value }))}
                className={inputClass}
              />
            </Field>
            <Field label={t('settings.newPassword')}>
              <input
                type="password"
                value={passwords.new}
                onChange={(e) => setPasswords((prev) => ({ ...prev, new: e.target.value }))}
                className={inputClass}
              />
            </Field>
            <Field label={t('settings.confirmPassword')}>
              <input
                type="password"
                value={passwords.confirm}
                onChange={(e) => setPasswords((prev) => ({ ...prev, confirm: e.target.value }))}
                className={inputClass}
              />
            </Field>
          </div>
          <p className="text-xs text-slate-400">
            {t('settings.passwordPolicy')}
          </p>
          <div className="flex justify-end">
            <SaveButton
              label={t('settings.savePassword')}
              onClick={savePassword}
              loading={savingPassword}
            />
          </div>
        </Section>

        <Section icon={BellRing} title={t('settings.notifications')}>
          <ToggleRow
            label={t('settings.notifEnabled')}
            description={t('settings.notifEnabledDesc')}
            checked={notifications.notificationsEnabled}
            onChange={(v) => setNotifications((prev) => ({ ...prev, notificationsEnabled: v }))}
          />
          <div className="border-t border-slate-100 dark:border-slate-700" />
          <ToggleRow
            label={t('settings.notifTickets')}
            description={t('settings.notifTicketsDesc')}
            checked={notifications.ticketUpdates}
            onChange={(v) => setNotifications((prev) => ({ ...prev, ticketUpdates: v }))}
          />
          <div className="border-t border-slate-100 dark:border-slate-700" />
          <ToggleRow
            label={t('settings.notifProducts')}
            description={t('settings.notifProductsDesc')}
            checked={notifications.productAlerts}
            onChange={(v) => setNotifications((prev) => ({ ...prev, productAlerts: v }))}
          />
          <div className="flex justify-end">
            <SaveButton
              label={t('settings.save')}
              onClick={saveNotifications}
            />
          </div>
        </Section>

        <Section icon={Moon} title={t('settings.appearance')}>
          <ToggleRow
            label={t('settings.darkMode')}
            description={t('settings.darkModeDesc')}
            checked={darkMode}
            onChange={setDarkMode}
          />
        </Section>

        <div className="bg-slate-50 border border-slate-200 rounded-2xl p-5 flex items-start gap-3">
          <Shield className="w-5 h-5 text-slate-400 shrink-0 mt-0.5" />
          <p className="text-xs text-slate-500 leading-relaxed">
            {t('settings.dataProtection')}
          </p>
        </div>

        {toastEl}
      </div>
    </div>
  )
}

export default Settings