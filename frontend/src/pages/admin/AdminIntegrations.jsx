import { useState } from 'react'
import {
  Plus,
  Plug,
  Settings2,
  Trash2,
  RefreshCw,
  Loader2,
  CheckCircle2,
  ExternalLink,
} from 'lucide-react'
import { useAdmin } from '../../contexts/useAdmin'
import {
  PageHeader,
  Field,
  Toggle,
  Modal,
  ConfirmModal,
  inputClass,
} from '../../components/admin/ui'
import { useToast } from '../../services/toast'
import { IntegrationBadge } from '../../components/admin/badges'
import { useI18n } from '../../i18n/useI18n'

const PROVIDERS = [
  { id: 'salesforce', label: 'Salesforce CRM', type: 'crm' },
  { id: 'hubspot', label: 'HubSpot CRM', type: 'crm' },
  { id: 'zoho', label: 'Zoho CRM', type: 'crm' },
  { id: 'sap', label: 'SAP Business One', type: 'erp' },
  { id: 'odoo', label: 'Odoo ERP', type: 'erp' },
  { id: 'dynamics', label: 'Microsoft Dynamics 365', type: 'erp' },
]

const SYNC_DIRECTIONS = [
  { value: 'bidirectional', labelKey: 'admin.integrations.dirBidirectional' },
  { value: 'oneway_in', labelKey: 'admin.integrations.dirIn' },
  { value: 'oneway_out', labelKey: 'admin.integrations.dirOut' },
]

const SYNC_FREQUENCIES = [
  { value: 'realtime', labelKey: 'admin.integrations.freqRealtime' },
  { value: 'hourly', labelKey: 'admin.integrations.freqHourly' },
  { value: 'daily', labelKey: 'admin.integrations.freqDaily' },
]

function AdminIntegrations() {
  const {
    integrations,
    addIntegration,
    updateIntegration,
    toggleIntegration,
    deleteIntegration,
  } = useAdmin()
  const { toastEl, showToast } = useToast()
  const { t, timeAgo } = useI18n()

  const [editTarget, setEditTarget] = useState(null)
  const [editForm, setEditForm] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [addOpen, setAddOpen] = useState(false)
  const [addForm, setAddForm] = useState({ provider: 'salesforce', name: '' })
  const [testingId, setTestingId] = useState(null)

  const openEdit = (integration) => {
    setEditTarget(integration)
    setEditForm({
      name: integration.name,
      apiUrl: integration.apiUrl,
      apiKey: integration.apiKey,
      syncDirection: integration.syncDirection,
      syncFrequency: integration.syncFrequency,
    })
  }

  const saveEdit = () => {
    if (!editForm?.name.trim()) {
      showToast(t('admin.integrations.nameRequired'), 'error')
      return
    }
    updateIntegration(editTarget.id, {
      name: editForm.name.trim(),
      apiUrl: editForm.apiUrl.trim(),
      apiKey: editForm.apiKey,
      syncDirection: editForm.syncDirection,
      syncFrequency: editForm.syncFrequency,
    })
    setEditTarget(null)
    setEditForm(null)
    showToast(t('admin.integrations.saved', { name: editForm.name }))
  }

  const handleAdd = () => {
    if (!addForm.name.trim()) {
      showToast(t('admin.integrations.nameRequired'), 'error')
      return
    }
    const provider = PROVIDERS.find((p) => p.id === addForm.provider)
    addIntegration({
      provider: addForm.provider,
      name: addForm.name.trim(),
      type: provider?.type || 'crm',
    })
    setAddOpen(false)
    setAddForm({ provider: 'salesforce', name: '' })
    showToast(t('admin.integrations.added'))
  }

  const testConnection = (integration) => {
    setTestingId(integration.id)
    setTimeout(() => {
      updateIntegration(integration.id, {
        status: 'connected',
        lastSync: new Date().toISOString(),
      })
      setTestingId(null)
      showToast(t('admin.integrations.connectedToast', { name: integration.name }))
    }, 1500)
  }

  const enabledCount = integrations.filter((i) => i.enabled && i.status === 'connected').length
  const crmCount = integrations.filter((i) => i.type === 'crm').length
  const erpCount = integrations.filter((i) => i.type === 'erp').length

  return (
    <div className="space-y-8">
      <PageHeader
        title={t('admin.integrations.title')}
        subtitle={t('admin.integrations.subtitle')}
        actions={
          <button
            onClick={() => setAddOpen(true)}
            className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl shadow-lg shadow-blue-500/20 flex items-center gap-2 transition-all active:scale-[0.98]"
          >
            <Plus className="w-5 h-5" />
            {t('admin.integrations.add')}
          </button>
        }
      />

      {/* Summary */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 custom-shadow grid grid-cols-1 sm:grid-cols-3 gap-6">
        <div className="flex items-center gap-4">
          <div className="w-11 h-11 rounded-xl bg-teal-50 text-teal-600 flex items-center justify-center">
            <Plug className="w-5 h-5" />
          </div>
          <div>
            <p className="text-2xl font-bold text-slate-900">{enabledCount}</p>
            <p className="text-xs text-slate-500">{t('admin.integrations.connected')}</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="w-11 h-11 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
            <Plug className="w-5 h-5" />
          </div>
          <div>
            <p className="text-2xl font-bold text-slate-900">{crmCount}</p>
            <p className="text-xs text-slate-500">{t('admin.integrations.crm')}</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="w-11 h-11 rounded-xl bg-violet-50 text-violet-600 flex items-center justify-center">
            <Plug className="w-5 h-5" />
          </div>
          <div>
            <p className="text-2xl font-bold text-slate-900">{erpCount}</p>
            <p className="text-xs text-slate-500">{t('admin.integrations.erp')}</p>
          </div>
        </div>
      </div>

      {/* Integration cards */}
      {integrations.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 custom-shadow">
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mb-4">
              <Plug className="w-8 h-8 text-slate-300" />
            </div>
            <h3 className="text-sm font-bold text-slate-900 mb-1">{t('admin.integrations.none')}</h3>
            <p className="text-xs text-slate-500 max-w-xs">
              {t('admin.integrations.empty')}
            </p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {integrations.map((int) => {
            const provider = PROVIDERS.find((p) => p.id === int.provider)
            const isTesting = testingId === int.id
            return (
              <div
                key={int.id}
                className="bg-white rounded-2xl border border-slate-200 p-6 custom-shadow space-y-5"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-11 h-11 rounded-xl bg-slate-100 flex items-center justify-center shrink-0">
                      <Plug className="w-5 h-5 text-slate-500" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-bold text-slate-900 truncate">{int.name}</p>
                      <p className="text-[11px] text-slate-400 uppercase tracking-wider">
                        {provider?.label || int.provider} · {int.type === 'crm' ? 'CRM' : 'ERP'}
                      </p>
                    </div>
                  </div>
                  <IntegrationBadge status={int.enabled ? int.status : 'disconnected'} />
                </div>

                <div className="space-y-2 text-xs text-slate-500">
                  <div className="flex items-center gap-2">
                    <ExternalLink className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <span className="truncate">{int.apiUrl || t('admin.integrations.noApiUrl')}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>{t('admin.integrations.syncLabel', { dir: SYNC_DIRECTIONS.find((d) => d.value === int.syncDirection)?.labelKey ? t(SYNC_DIRECTIONS.find((d) => d.value === int.syncDirection).labelKey) : '-' })}</span>
                    <span>{t('admin.integrations.freqLabel', { freq: SYNC_FREQUENCIES.find((f) => f.value === int.syncFrequency)?.labelKey ? t(SYNC_FREQUENCIES.find((f) => f.value === int.syncFrequency).labelKey) : '-' })}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>{t('admin.integrations.lastSyncLabel')}</span>
                    <span className="font-semibold text-slate-700">{int.lastSync ? timeAgo(int.lastSync) : t('admin.integrations.never')}</span>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-4 border-t border-slate-100">
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-semibold text-slate-600">
                      {int.enabled ? t('admin.integrations.enabled') : t('admin.integrations.disabled')}
                    </span>
                    <Toggle checked={int.enabled} onChange={() => toggleIntegration(int.id)} />
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => testConnection(int)}
                      disabled={isTesting}
                      className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isTesting ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          {t('admin.integrations.testing')}
                        </>
                      ) : (
                        <>
                          <RefreshCw className="w-3.5 h-3.5" />
                          {t('admin.integrations.test')}
                        </>
                      )}
                    </button>
                    <button
                      onClick={() => openEdit(int)}
                      title={t('admin.integrations.configure')}
                      className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                    >
                      <Settings2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setDeleteTarget(int)}
                      title={t('admin.integrations.delete')}
                      className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Configure modal */}
      <Modal
        open={!!editTarget}
        onClose={() => {
          setEditTarget(null)
          setEditForm(null)
        }}
        title={t('admin.integrations.configureTitle', { name: editTarget?.name || '' })}
        footer={
          <>
            <button
              onClick={() => {
                setEditTarget(null)
                setEditForm(null)
              }}
              className="px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
            >
              {t('common.cancel')}
            </button>
            <button
              onClick={saveEdit}
              className="inline-flex items-center gap-2 px-5 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl transition-colors shadow-lg shadow-blue-500/20"
            >
              <CheckCircle2 className="w-4 h-4" />
              {t('common.save')}
            </button>
          </>
        }
      >
        {editForm && (
          <div className="space-y-5">
            <Field label={t('admin.integrations.name')} required>
              <input
                type="text"
                value={editForm.name}
                onChange={(e) => setEditForm((prev) => ({ ...prev, name: e.target.value }))}
                className={inputClass}
              />
            </Field>
            <Field label={t('admin.integrations.apiUrl')}>
              <input
                type="text"
                value={editForm.apiUrl}
                onChange={(e) => setEditForm((prev) => ({ ...prev, apiUrl: e.target.value }))}
                placeholder={t('admin.integrations.apiUrlPlaceholder')}
                className={inputClass}
              />
            </Field>
            <Field label={t('admin.integrations.apiKey')} hint={t('admin.integrations.apiKeyHint')}>
              <input
                type="password"
                value={editForm.apiKey}
                onChange={(e) => setEditForm((prev) => ({ ...prev, apiKey: e.target.value }))}
                placeholder={t('admin.integrations.apiKeyPlaceholder')}
                className={inputClass}
              />
            </Field>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <Field label={t('admin.integrations.syncDirection')}>
                <select
                  value={editForm.syncDirection}
                  onChange={(e) => setEditForm((prev) => ({ ...prev, syncDirection: e.target.value }))}
                  className={`${inputClass} cursor-pointer`}
                >
                  {SYNC_DIRECTIONS.map((d) => (
                    <option key={d.value} value={d.value}>
                      {t(d.labelKey)}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label={t('admin.integrations.syncFrequency')}>
                <select
                  value={editForm.syncFrequency}
                  onChange={(e) => setEditForm((prev) => ({ ...prev, syncFrequency: e.target.value }))}
                  className={`${inputClass} cursor-pointer`}
                >
                  {SYNC_FREQUENCIES.map((f) => (
                    <option key={f.value} value={f.value}>
                      {t(f.labelKey)}
                    </option>
                  ))}
                </select>
              </Field>
            </div>
          </div>
        )}
      </Modal>

      {/* Add modal */}
      <Modal
        open={addOpen}
        onClose={() => {
          setAddOpen(false)
          setAddForm({ provider: 'salesforce', name: '' })
        }}
        title={t('admin.integrations.add')}
        footer={
          <>
            <button
              onClick={() => {
                setAddOpen(false)
                setAddForm({ provider: 'salesforce', name: '' })
              }}
              className="px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
            >
              {t('common.cancel')}
            </button>
            <button
              onClick={handleAdd}
              className="inline-flex items-center gap-2 px-5 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl transition-colors shadow-lg shadow-blue-500/20"
            >
              <Plus className="w-4 h-4" />
              {t('admin.integrations.addButton')}
            </button>
          </>
        }
      >
        <div className="space-y-5">
          <Field label={t('admin.integrations.provider')} required>
            <div className="grid grid-cols-2 gap-2">
              {PROVIDERS.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => setAddForm((prev) => ({ ...prev, provider: p.id }))}
                  className={`px-3 py-2.5 rounded-xl text-xs font-bold border text-left transition-all ${
                    addForm.provider === p.id
                      ? 'bg-blue-50 text-blue-600 border-blue-200 ring-2 ring-offset-1 ring-blue-500'
                      : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  {p.label}
                  <span className="block text-[10px] font-semibold text-slate-400 mt-0.5">
                    {p.type === 'crm' ? 'CRM' : 'ERP'}
                  </span>
                </button>
              ))}
            </div>
          </Field>
          <Field label={t('admin.integrations.name')} required>
            <input
              type="text"
              value={addForm.name}
              onChange={(e) => setAddForm((prev) => ({ ...prev, name: e.target.value }))}
              placeholder={t('admin.integrations.namePlaceholder')}
              className={inputClass}
            />
          </Field>
        </div>
      </Modal>

      <ConfirmModal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title={t('admin.integrations.deleteTitle')}
        message={
          deleteTarget
            ? t('admin.integrations.deleteMsg', { name: deleteTarget.name })
            : ''
        }
        onConfirm={() => {
          deleteIntegration(deleteTarget.id)
          showToast(t('admin.integrations.deleted'))
        }}
      />

      {toastEl}
    </div>
  )
}

export default AdminIntegrations