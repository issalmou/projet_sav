import { useState } from 'react'
import { Save, Building2, Shield, BellRing, Cpu } from 'lucide-react'
import { useAdmin } from '../../contexts/useAdmin'
import { PageHeader, Field, Toggle, inputClass } from '../../components/admin/ui'
import { useToast } from '../../services/toast'

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

export default function AdminSettings() {
  const { settings, updateSettings } = useAdmin()
  const { toastEl, showToast } = useToast()

  const [form, setForm] = useState({
    companyName: settings.companyName,
    supportEmail: settings.supportEmail,
    supportPhone: settings.supportPhone,
    language: settings.language,
    timezone: settings.timezone,
    defaultTicketPriority: settings.defaultTicketPriority,
    slaDays: settings.slaDays,
    autoResponder: settings.autoResponder,
    aiEnabled: settings.aiEnabled,
    maintenanceMode: settings.maintenanceMode,
    emailNotifications: { ...settings.emailNotifications },
    security: { ...settings.security },
  })

  const set = (field, value) => setForm((prev) => ({ ...prev, [field]: value }))
  const setNotification = (field, value) =>
    setForm((prev) => ({
      ...prev,
      emailNotifications: { ...prev.emailNotifications, [field]: value },
    }))
  const setSecurity = (field, value) =>
    setForm((prev) => ({
      ...prev,
      security: { ...prev.security, [field]: value },
    }))

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!form.companyName.trim()) {
      showToast("Le nom de la société est obligatoire.", 'error')
      return
    }
    updateSettings(form)
    showToast('Paramètres enregistrés avec succès')
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Paramètres"
        subtitle="Configuration générale de la plateforme 3LM Solutions."
        actions={
          <button
            onClick={handleSubmit}
            className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl shadow-lg shadow-blue-500/20 flex items-center gap-2 transition-all active:scale-[0.98]"
          >
            <Save className="w-5 h-5" />
            Enregistrer
          </button>
        }
      />

      <form onSubmit={handleSubmit} className="space-y-6">
        <Section icon={Building2} title="Informations générales">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <Field label="Nom de la société" required>
              <input
                type="text"
                value={form.companyName}
                onChange={(e) => set('companyName', e.target.value)}
                className={inputClass}
              />
            </Field>
            <Field label="Langue par défaut">
              <select
                value={form.language}
                onChange={(e) => set('language', e.target.value)}
                className={`${inputClass} cursor-pointer`}
              >
                <option value="fr">Français</option>
                <option value="en">Anglais</option>
              </select>
            </Field>
            <Field label="Email de support">
              <input
                type="email"
                value={form.supportEmail}
                onChange={(e) => set('supportEmail', e.target.value)}
                className={inputClass}
              />
            </Field>
            <Field label="Téléphone de support">
              <input
                type="tel"
                value={form.supportPhone}
                onChange={(e) => set('supportPhone', e.target.value)}
                className={inputClass}
              />
            </Field>
            <Field label="Fuseau horaire">
              <select
                value={form.timezone}
                onChange={(e) => set('timezone', e.target.value)}
                className={`${inputClass} cursor-pointer`}
              >
                <option value="Europe/Paris">Europe/Paris (UTC+1)</option>
                <option value="Europe/London">Europe/London (UTC+0)</option>
                <option value="America/New_York">America/New_York (UTC-5)</option>
                <option value="Asia/Dubai">Asia/Dubai (UTC+4)</option>
              </select>
            </Field>
            <Field label="Priorité par défaut des tickets">
              <select
                value={form.defaultTicketPriority}
                onChange={(e) => set('defaultTicketPriority', e.target.value)}
                className={`${inputClass} cursor-pointer`}
              >
                <option value="low">Basse</option>
                <option value="medium">Moyenne</option>
                <option value="high">Haute</option>
              </select>
            </Field>
            <Field label="SLA en jours">
              <input
                type="number"
                min="1"
                max="30"
                value={form.slaDays}
                onChange={(e) => set('slaDays', Number(e.target.value))}
                className={inputClass}
              />
            </Field>
          </div>
        </Section>

        <Section icon={Cpu} title="Système & automatisation">
          <ToggleRow
            label="Assistant IA conversationnel"
            description="Active l'agent IA pour répondre automatiquement aux tickets."
            checked={form.aiEnabled}
            onChange={(v) => set('aiEnabled', v)}
          />
          <div className="border-t border-slate-100" />
          <ToggleRow
            label="Répondeur automatique"
            description="Envoie un accusé de réception à la création d'un ticket."
            checked={form.autoResponder}
            onChange={(v) => set('autoResponder', v)}
          />
          <div className="border-t border-slate-100" />
          <ToggleRow
            label="Mode maintenance"
            description="Désactive temporairement le portail client pendant les interventions."
            checked={form.maintenanceMode}
            onChange={(v) => set('maintenanceMode', v)}
          />
        </Section>

        <Section icon={BellRing} title="Notifications email">
          <ToggleRow
            label="Ticket créé"
            description="Notifier lorsqu'un nouveau ticket est ouvert."
            checked={form.emailNotifications.ticketCreated}
            onChange={(v) => setNotification('ticketCreated', v)}
          />
          <div className="border-t border-slate-100" />
          <ToggleRow
            label="Ticket assigné"
            description="Notifier lorsqu'un ticket est assigné à un agent."
            checked={form.emailNotifications.ticketAssigned}
            onChange={(v) => setNotification('ticketAssigned', v)}
          />
          <div className="border-t border-slate-100" />
          <ToggleRow
            label="Ticket résolu"
            description="Notifier le client lorsqu'un ticket est résolu."
            checked={form.emailNotifications.ticketResolved}
            onChange={(v) => setNotification('ticketResolved', v)}
          />
          <div className="border-t border-slate-100" />
          <ToggleRow
            label="Rapport hebdomadaire"
            description="Résumé hebdomadaire des performances support."
            checked={form.emailNotifications.weeklyDigest}
            onChange={(v) => setNotification('weeklyDigest', v)}
          />
        </Section>

        <Section icon={Shield} title="Sécurité">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <Field label="Expiration de session (minutes)">
              <input
                type="number"
                min="5"
                max="240"
                value={form.security.sessionTimeout}
                onChange={(e) => setSecurity('sessionTimeout', Number(e.target.value))}
                className={inputClass}
              />
            </Field>
            <Field label="Politique de mot de passe">
              <select
                value={form.security.passwordPolicy}
                onChange={(e) => setSecurity('passwordPolicy', e.target.value)}
                className={`${inputClass} cursor-pointer`}
              >
                <option value="low">Simple (6 caractères)</option>
                <option value="medium">Moyenne (8 caractères)</option>
                <option value="strong">Forte (12 + complexité)</option>
              </select>
            </Field>
          </div>
          <div className="border-t border-slate-100" />
          <ToggleRow
            label="Authentification à deux facteurs"
            description="Exige une double authentification pour les comptes administrateurs."
            checked={form.security.twoFactorAuth}
            onChange={(v) => setSecurity('twoFactorAuth', v)}
          />
        </Section>

        <div className="flex items-center justify-end gap-3">
          <button
            type="submit"
            className="inline-flex items-center gap-2 px-6 py-2.5 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl transition-colors shadow-lg shadow-blue-500/20"
          >
            <Save className="w-4 h-4" />
            Enregistrer les paramètres
          </button>
        </div>
      </form>

      {toastEl}
    </div>
  )
}
