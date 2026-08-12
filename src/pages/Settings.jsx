import { useState } from 'react'
import { Save, Shield, BellRing, KeyRound, User } from 'lucide-react'
import { useAuth } from '../contexts/useAuth'
import { PageHeader, Field, Toggle, inputClass } from '../components/admin/ui'
import { useToast } from '../services/toast'
import { RoleBadge } from '../components/admin/badges'

function Section({ icon: Icon, title, children }) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 custom-shadow overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-100 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center">
          <Icon className="w-4 h-4 text-slate-600" />
        </div>
        <h3 className="text-sm font-bold text-slate-900">{title}</h3>
      </div>
      <div className="p-6 space-y-5">{children}</div>
    </div>
  )
}

function ToggleRow({ label, description, checked, onChange }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div>
        <p className="text-sm font-semibold text-slate-800">{label}</p>
        {description && <p className="text-xs text-slate-500 mt-0.5">{description}</p>}
      </div>
      <Toggle checked={checked} onChange={onChange} />
    </div>
  )
}

function Settings() {
  const { user, updateProfile } = useAuth()
  const { toastEl, showToast } = useToast()

  const [profile, setProfile] = useState({
    name: user?.name || '',
    email: user?.email || '',
  })
  const [notifications, setNotifications] = useState({
    ticketUpdates: true,
    weeklyDigest: false,
    productAlerts: true,
  })
  const [passwords, setPasswords] = useState({
    current: '',
    new: '',
    confirm: '',
  })
  const [errors, setErrors] = useState({})

  const saveProfile = () => {
    const errs = {}
    if (!profile.name.trim()) errs.name = 'Le nom est obligatoire.'
    if (!profile.email.trim()) errs.email = "L'email est obligatoire."
    else if (!/\S+@\S+\.\S+/.test(profile.email)) errs.email = "L'email est invalide."
    setErrors(errs)
    if (Object.keys(errs).length > 0) return
    updateProfile({ name: profile.name.trim(), email: profile.email.trim() })
    showToast('Profil mis à jour')
  }

  const savePassword = () => {
    if (passwords.new.length < 6) {
      showToast('Le nouveau mot de passe doit contenir au moins 6 caractères.', 'error')
      return
    }
    if (passwords.new !== passwords.confirm) {
      showToast('Les mots de passe ne correspondent pas.', 'error')
      return
    }
    setPasswords({ current: '', new: '', confirm: '' })
    showToast('Mot de passe modifié')
  }

  return (
    <div className="flex-1 overflow-y-auto p-8">
      <div className="max-w-3xl mx-auto space-y-8">
        <PageHeader title="Paramètres" subtitle="Gérez votre profil et vos préférences personnelles." />

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

        <Section icon={User} title="Informations personnelles">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <Field label="Nom complet" required error={errors.name}>
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
            <Field label="Adresse email" required error={errors.email}>
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
          </div>
          <div className="flex justify-end">
            <button
              onClick={saveProfile}
              className="inline-flex items-center gap-2 px-5 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl transition-colors shadow-lg shadow-blue-500/20"
            >
              <Save className="w-4 h-4" />
              Enregistrer le profil
            </button>
          </div>
        </Section>

        <Section icon={KeyRound} title="Changer le mot de passe">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <Field label="Mot de passe actuel">
              <input
                type="password"
                value={passwords.current}
                onChange={(e) => setPasswords((prev) => ({ ...prev, current: e.target.value }))}
                className={inputClass}
              />
            </Field>
            <Field label="Nouveau mot de passe">
              <input
                type="password"
                value={passwords.new}
                onChange={(e) => setPasswords((prev) => ({ ...prev, new: e.target.value }))}
                className={inputClass}
              />
            </Field>
            <Field label="Confirmation">
              <input
                type="password"
                value={passwords.confirm}
                onChange={(e) => setPasswords((prev) => ({ ...prev, confirm: e.target.value }))}
                className={inputClass}
              />
            </Field>
          </div>
          <div className="flex justify-end">
            <button
              onClick={savePassword}
              className="inline-flex items-center gap-2 px-5 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl transition-colors shadow-lg shadow-blue-500/20"
            >
              <Save className="w-4 h-4" />
              Mettre à jour le mot de passe
            </button>
          </div>
        </Section>

        <Section icon={BellRing} title="Notifications">
          <ToggleRow
            label="Mises à jour de mes tickets"
            description="Être notifié à chaque changement sur un de mes tickets."
            checked={notifications.ticketUpdates}
            onChange={(v) => setNotifications((prev) => ({ ...prev, ticketUpdates: v }))}
          />
          <div className="border-t border-slate-100" />
          <ToggleRow
            label="Résumé hebdomadaire"
            description="Recevoir un résumé de mon activité support chaque semaine."
            checked={notifications.weeklyDigest}
            onChange={(v) => setNotifications((prev) => ({ ...prev, weeklyDigest: v }))}
          />
          <div className="border-t border-slate-100" />
          <ToggleRow
            label="Alertes produits"
            description="Être informé des mises à jour et alertes sur mes produits."
            checked={notifications.productAlerts}
            onChange={(v) => setNotifications((prev) => ({ ...prev, productAlerts: v }))}
          />
          <div className="flex justify-end">
            <button
              onClick={() => {
                showToast('Préférences de notification enregistrées')
              }}
              className="inline-flex items-center gap-2 px-5 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl transition-colors shadow-lg shadow-blue-500/20"
            >
              <Save className="w-4 h-4" />
              Enregistrer
            </button>
          </div>
        </Section>

        <div className="bg-slate-50 border border-slate-200 rounded-2xl p-5 flex items-start gap-3">
          <Shield className="w-5 h-5 text-slate-400 shrink-0 mt-0.5" />
          <p className="text-xs text-slate-500 leading-relaxed">
            Vos données personnelles sont protégées. Vous pouvez demander l'export ou la suppression de
            vos données à tout moment auprès de l'administrateur de la plateforme.
          </p>
        </div>

        {toastEl}
      </div>
    </div>
  )
}

export default Settings
