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

const PROVIDERS = [
  { id: 'salesforce', label: 'Salesforce CRM', type: 'crm' },
  { id: 'hubspot', label: 'HubSpot CRM', type: 'crm' },
  { id: 'zoho', label: 'Zoho CRM', type: 'crm' },
  { id: 'sap', label: 'SAP Business One', type: 'erp' },
  { id: 'odoo', label: 'Odoo ERP', type: 'erp' },
  { id: 'dynamics', label: 'Microsoft Dynamics 365', type: 'erp' },
]

const SYNC_DIRECTIONS = [
  { value: 'bidirectional', label: 'Bidirectionnelle' },
  { value: 'oneway_in', label: 'Entrante (CRM → Plateforme)' },
  { value: 'oneway_out', label: 'Sortante (Plateforme → CRM)' },
]

const SYNC_FREQUENCIES = [
  { value: 'realtime', label: 'Temps réel' },
  { value: 'hourly', label: 'Chaque heure' },
  { value: 'daily', label: 'Quotidien' },
]

function formatRelative(iso) {
  if (!iso) return 'Jamais'
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `Il y a ${mins} min`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `Il y a ${hours} h`
  return new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

function AdminIntegrations() {
  const {
    integrations,
    addIntegration,
    updateIntegration,
    toggleIntegration,
    deleteIntegration,
  } = useAdmin()
  const { toastEl, showToast } = useToast()

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
      showToast('Le nom de l\u2019intégration est obligatoire.', 'error')
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
    showToast(`Configuration de ${editForm.name} enregistrée`)
  }

  const handleAdd = () => {
    if (!addForm.name.trim()) {
      showToast('Le nom de l\u2019intégration est obligatoire.', 'error')
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
    showToast('Intégration ajoutée. Configurez-la pour la connecter.')
  }

  const testConnection = (integration) => {
    setTestingId(integration.id)
    setTimeout(() => {
      updateIntegration(integration.id, {
        status: 'connected',
        lastSync: new Date().toISOString(),
      })
      setTestingId(null)
      showToast(`Connexion à ${integration.name} établie avec succès`)
    }, 1500)
  }

  const enabledCount = integrations.filter((i) => i.enabled && i.status === 'connected').length
  const crmCount = integrations.filter((i) => i.type === 'crm').length
  const erpCount = integrations.filter((i) => i.type === 'erp').length

  return (
    <div className="space-y-8">
      <PageHeader
        title="Intégrations CRM/ERP"
        subtitle="Connectez vos systèmes externes pour synchroniser vos données clients."
        actions={
          <button
            onClick={() => setAddOpen(true)}
            className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl shadow-lg shadow-blue-500/20 flex items-center gap-2 transition-all active:scale-[0.98]"
          >
            <Plus className="w-5 h-5" />
            Ajouter une intégration
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
            <p className="text-xs text-slate-500">Connectées / actives</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="w-11 h-11 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
            <Plug className="w-5 h-5" />
          </div>
          <div>
            <p className="text-2xl font-bold text-slate-900">{crmCount}</p>
            <p className="text-xs text-slate-500">Intégrations CRM</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="w-11 h-11 rounded-xl bg-violet-50 text-violet-600 flex items-center justify-center">
            <Plug className="w-5 h-5" />
          </div>
          <div>
            <p className="text-2xl font-bold text-slate-900">{erpCount}</p>
            <p className="text-xs text-slate-500">Intégrations ERP</p>
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
            <h3 className="text-sm font-bold text-slate-900 mb-1">Aucune intégration</h3>
            <p className="text-xs text-slate-500 max-w-xs">
              Ajoutez une intégration CRM ou ERP pour connecter vos systèmes.
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
                    <span className="truncate">{int.apiUrl || 'URL API non définie'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Synchronisation : {SYNC_DIRECTIONS.find((d) => d.value === int.syncDirection)?.label}</span>
                    <span>Fréquence : {SYNC_FREQUENCIES.find((f) => f.value === int.syncFrequency)?.label}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Dernière synchronisation :</span>
                    <span className="font-semibold text-slate-700">{formatRelative(int.lastSync)}</span>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-4 border-t border-slate-100">
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-semibold text-slate-600">
                      {int.enabled ? 'Activée' : 'Désactivée'}
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
                          Test...
                        </>
                      ) : (
                        <>
                          <RefreshCw className="w-3.5 h-3.5" />
                          Tester
                        </>
                      )}
                    </button>
                    <button
                      onClick={() => openEdit(int)}
                      title="Configurer"
                      className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                    >
                      <Settings2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setDeleteTarget(int)}
                      title="Supprimer"
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
        title={`Configurer ${editTarget?.name || ''}`}
        footer={
          <>
            <button
              onClick={() => {
                setEditTarget(null)
                setEditForm(null)
              }}
              className="px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
            >
              Annuler
            </button>
            <button
              onClick={saveEdit}
              className="inline-flex items-center gap-2 px-5 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl transition-colors shadow-lg shadow-blue-500/20"
            >
              <CheckCircle2 className="w-4 h-4" />
              Enregistrer
            </button>
          </>
        }
      >
        {editForm && (
          <div className="space-y-5">
            <Field label="Nom de l'intégration" required>
              <input
                type="text"
                value={editForm.name}
                onChange={(e) => setEditForm((prev) => ({ ...prev, name: e.target.value }))}
                className={inputClass}
              />
            </Field>
            <Field label="URL de l'API">
              <input
                type="text"
                value={editForm.apiUrl}
                onChange={(e) => setEditForm((prev) => ({ ...prev, apiUrl: e.target.value }))}
                placeholder="https://api.exemple.com/v1"
                className={inputClass}
              />
            </Field>
            <Field label="Clé API" hint="La clé existante reste masquée si le champ est laissé vide.">
              <input
                type="password"
                value={editForm.apiKey}
                onChange={(e) => setEditForm((prev) => ({ ...prev, apiKey: e.target.value }))}
                placeholder="Entrez une nouvelle clé API..."
                className={inputClass}
              />
            </Field>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <Field label="Direction de synchronisation">
                <select
                  value={editForm.syncDirection}
                  onChange={(e) => setEditForm((prev) => ({ ...prev, syncDirection: e.target.value }))}
                  className={`${inputClass} cursor-pointer`}
                >
                  {SYNC_DIRECTIONS.map((d) => (
                    <option key={d.value} value={d.value}>
                      {d.label}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Fréquence de synchronisation">
                <select
                  value={editForm.syncFrequency}
                  onChange={(e) => setEditForm((prev) => ({ ...prev, syncFrequency: e.target.value }))}
                  className={`${inputClass} cursor-pointer`}
                >
                  {SYNC_FREQUENCIES.map((f) => (
                    <option key={f.value} value={f.value}>
                      {f.label}
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
        title="Ajouter une intégration"
        footer={
          <>
            <button
              onClick={() => {
                setAddOpen(false)
                setAddForm({ provider: 'salesforce', name: '' })
              }}
              className="px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
            >
              Annuler
            </button>
            <button
              onClick={handleAdd}
              className="inline-flex items-center gap-2 px-5 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl transition-colors shadow-lg shadow-blue-500/20"
            >
              <Plus className="w-4 h-4" />
              Ajouter
            </button>
          </>
        }
      >
        <div className="space-y-5">
          <Field label="Fournisseur" required>
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
          <Field label="Nom de l'intégration" required>
            <input
              type="text"
              value={addForm.name}
              onChange={(e) => setAddForm((prev) => ({ ...prev, name: e.target.value }))}
              placeholder="Ex : Salesforce Production"
              className={inputClass}
            />
          </Field>
        </div>
      </Modal>

      <ConfirmModal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Supprimer l'intégration"
        message={
          deleteTarget
            ? `Voulez-vous vraiment supprimer « ${deleteTarget.name} » ? La synchronisation sera interrompue.`
            : ''
        }
        onConfirm={() => {
          deleteIntegration(deleteTarget.id)
          showToast('L\u2019intégration a été supprimée')
        }}
      />

      {toastEl}
    </div>
  )
}

export default AdminIntegrations
