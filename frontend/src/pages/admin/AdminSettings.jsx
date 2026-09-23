import { useState } from 'react'
import { Save, Building2, Shield, BellRing } from 'lucide-react'
import { useAdmin } from '../../contexts/useAdmin'
import { PageHeader, Field, Toggle, inputClass } from '../../components/admin/ui'
import { useToast } from '../../services/toast'
import { useI18n } from '../../i18n/useI18n'

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
  const { t } = useI18n()

  const [form, setForm] = useState({
    companyName: settings.companyName,
    supportEmail: settings.supportEmail,
    supportPhone: settings.supportPhone,
    language: settings.language,
    timezone: settings.timezone,
    defaultTicketPriority: settings.defaultTicketPriority,
    slaDays: settings.slaDays,
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
      showToast(t('admin.settings.companyRequired'), 'error')
      return
    }
    updateSettings(form)
    showToast(t('admin.settings.saved'))
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title={t('admin.nav.settings')}
        subtitle={t('admin.settings.subtitle')}
        actions={
          <button
            onClick={handleSubmit}
            className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl shadow-lg shadow-blue-500/20 flex items-center gap-2 transition-all active:scale-[0.98]"
          >
            <Save className="w-5 h-5" />
            {t('common.save')}
          </button>
        }
      />

      <form onSubmit={handleSubmit} className="space-y-6">
        <Section icon={Building2} title={t('admin.settings.general')}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <Field label={t('admin.settings.companyName')} required>
              <input
                type="text"
                value={form.companyName}
                onChange={(e) => set('companyName', e.target.value)}
                className={inputClass}
              />
            </Field>
            <Field label={t('admin.settings.defaultLang')}>
              <select
                value={form.language}
                onChange={(e) => set('language', e.target.value)}
                className={`${inputClass} cursor-pointer`}
              >
                <option value="fr">{t('admin.langs.fr')}</option>
                <option value="en">{t('admin.langs.en')}</option>
                <option value="ar">{t('admin.langs.ar')}</option>
              </select>
            </Field>
            <Field label={t('admin.settings.supportEmail')}>
              <input
                type="email"
                value={form.supportEmail}
                onChange={(e) => set('supportEmail', e.target.value)}
                className={inputClass}
              />
            </Field>
            <Field label={t('admin.settings.supportPhone')}>
              <input
                type="tel"
                value={form.supportPhone}
                onChange={(e) => set('supportPhone', e.target.value)}
                className={inputClass}
              />
            </Field>
            <Field label={t('admin.settings.timezone')}>
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
            <Field label={t('admin.settings.defaultPriority')}>
              <select
                value={form.defaultTicketPriority}
                onChange={(e) => set('defaultTicketPriority', e.target.value)}
                className={`${inputClass} cursor-pointer`}
              >
                <option value="low">{t('priority.low')}</option>
                <option value="medium">{t('priority.medium')}</option>
                <option value="high">{t('priority.high')}</option>
              </select>
            </Field>
            <Field label={t('admin.settings.slaDays')}>
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

        <Section icon={BellRing} title={t('admin.settings.emailNotifs')}>
          <ToggleRow
            label={t('admin.settings.notifTicketCreated')}
            description={t('admin.settings.notifTicketCreatedDesc')}
            checked={form.emailNotifications.ticketCreated}
            onChange={(v) => setNotification('ticketCreated', v)}
          />
          <div className="border-t border-slate-100" />
          <ToggleRow
            label={t('admin.settings.notifTicketAssigned')}
            description={t('admin.settings.notifTicketAssignedDesc')}
            checked={form.emailNotifications.ticketAssigned}
            onChange={(v) => setNotification('ticketAssigned', v)}
          />
          <div className="border-t border-slate-100" />
          <ToggleRow
            label={t('admin.settings.notifTicketResolved')}
            description={t('admin.settings.notifTicketResolvedDesc')}
            checked={form.emailNotifications.ticketResolved}
            onChange={(v) => setNotification('ticketResolved', v)}
          />
          <div className="border-t border-slate-100" />
          <ToggleRow
            label={t('admin.settings.notifWeekly')}
            description={t('admin.settings.notifWeeklyDesc')}
            checked={form.emailNotifications.weeklyDigest}
            onChange={(v) => setNotification('weeklyDigest', v)}
          />
        </Section>

        <Section icon={Shield} title={t('admin.settings.security')}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <Field label={t('admin.settings.sessionTimeout')}>
              <input
                type="number"
                min="5"
                max="240"
                value={form.security.sessionTimeout}
                onChange={(e) => setSecurity('sessionTimeout', Number(e.target.value))}
                className={inputClass}
              />
            </Field>
            <Field label={t('admin.settings.passwordPolicy')}>
              <select
                value={form.security.passwordPolicy}
                onChange={(e) => setSecurity('passwordPolicy', e.target.value)}
                className={`${inputClass} cursor-pointer`}
              >
                <option value="low">{t('admin.settings.pwSimple')}</option>
                <option value="medium">{t('admin.settings.pwMedium')}</option>
                <option value="strong">{t('admin.settings.pwStrong')}</option>
              </select>
            </Field>
          </div>
          <div className="border-t border-slate-100" />
          <ToggleRow
            label={t('admin.settings.twoFactor')}
            description={t('admin.settings.twoFactorDesc')}
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
            {t('admin.settings.saveAll')}
          </button>
        </div>
      </form>

      {toastEl}
    </div>
  )
}