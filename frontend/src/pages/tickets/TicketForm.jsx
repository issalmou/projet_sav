import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Save } from 'lucide-react'
import StatusSelect from '../../components/tickets/StatusSelect'
import { CATEGORIES } from '../../components/tickets/constants'
import { useAuth } from '../../contexts/useAuth'
import { useAdmin } from '../../contexts/useAdmin'
import { useTickets } from '../../contexts/useTickets'
import { canEditTicketAssignment, canEditTicketStatus, isStaffOrSuperuser } from '../../components/tickets/permissions'
import { useI18n } from '../../i18n/useI18n'

function Field({ label, required, error, children }) {
  return (
    <div className="space-y-1.5">
      <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
        {label} {required && <span className="text-red-400">*</span>}
      </label>
      {children}
      {error && <p className="text-xs text-red-500 font-medium">{error}</p>}
    </div>
  )
}

const inputClass =
  'w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all'

function normalizeCategory(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
}

export default function TicketForm({ mode, initialValues, onSubmit, submitLabel, basePath = '/tickets' }) {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { users } = useAdmin()
  const { tickets } = useTickets()
  const { t } = useI18n()
const isStaff = ['admin', 'manager', 'agent'].includes(user?.role) || isStaffOrSuperuser(user)
  const canAssignTicket = canEditTicketAssignment(user)
  const canEditStatus = mode === 'edit' && canEditTicketStatus(initialValues, user)
  const isStaffTicketCreate = ['admin', 'manager'].includes(user?.role) && mode === 'create'
  const clients = users.filter((item) => item.role === 'client')
  const [formData, setFormData] = useState({
    title: initialValues?.title || '',
    description: initialValues?.description || '',
    category: initialValues?.category || '',
    status: initialValues?.status || 'open',
    assignee: initialValues?.assignee || '',
     assigned_technician_id: initialValues?.assigned_technician_id || initialValues?.assignee_id || initialValues?.assigneeId || '',
    client_id: initialValues?.client_id || (!isStaff ? user?.id : ''),
  })
  const [errors, setErrors] = useState({})
  const technicians = users
    .filter((item) => item.role === 'agent' && item.status === 'active')
    .map((technician) => {
      const specialties = [
        technician.specialty,
        technician.speciality,
        technician.department,
        technician.expertise,
        ...(Array.isArray(technician.categories) ? technician.categories : []),
        ...(Array.isArray(technician.supported_categories) ? technician.supported_categories : []),
      ].map(normalizeCategory).filter(Boolean)
      const category = normalizeCategory(formData.category)
      const hasCategoryHistory = tickets.some((ticket) => (
        String(ticket.assigneeId || ticket.assignee_id) === String(technician.id) &&
        normalizeCategory(ticket.category) === category
      ))
      const categoryMatch = Boolean(category && (
        specialties.some((specialty) => specialty.includes(category) || category.includes(specialty)) ||
        hasCategoryHistory
      ))
      return {
        ...technician,
        categoryMatch,
        openTickets: tickets.filter((ticket) => (
          String(ticket.assigneeId || ticket.assignee_id) === String(technician.id) &&
          !['resolved', 'closed'].includes(ticket.status)
        )).length,
      }
    })
    .sort((a, b) => Number(b.categoryMatch) - Number(a.categoryMatch) || a.openTickets - b.openTickets || a.name.localeCompare(b.name))

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
    if (errors[field]) {
      setErrors((prev) => {
        const next = { ...prev }
        delete next[field]
        return next
      })
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
const validationErrors = {}
    if (!formData.title.trim()) validationErrors.title = t('tf.titleRequired')
    if (!formData.description.trim()) validationErrors.description = t('tf.descRequired')
    if (isStaff && !formData.client_id) validationErrors.client_id = t('tf.clientRequired')
     if (isStaffTicketCreate && !formData.assigned_technician_id) validationErrors.assigned_technician_id = t('tf.technicianRequired')
    if (formData.title.trim().length > 200) validationErrors.title = t('tf.titleTooLong')
    setErrors(validationErrors)
    if (Object.keys(validationErrors).length > 0) return
    onSubmit({
      title: formData.title.trim(),
      description: formData.description.trim(),
      category: formData.category || null,
      client_id: formData.client_id || user?.id,
      status: formData.status,
      assignee: formData.assignee.trim(),
       assigned_technician_id: formData.assigned_technician_id || null,
       source: mode === 'create' && isStaffTicketCreate ? 'responsable_sav' : initialValues?.source,
    })
  }

  return (
    <div className="flex-1 overflow-y-auto p-8">
      <div className="max-w-3xl mx-auto space-y-6">
        <button
          onClick={() => navigate(mode === 'edit' ? `${basePath}/${initialValues.id}` : basePath)}
          className="inline-flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-blue-600 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          {mode === 'edit' ? t('tf.backToTicket') : t('tf.backToTickets')}
        </button>

        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            {mode === 'edit' ? t('tf.editTitle', { id: initialValues.id }) : t('tf.newTitle')}
          </h1>
          <p className="text-slate-500">
            {mode === 'edit'
              ? t('tf.editSubtitle')
              : t('tf.newSubtitle')}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-slate-200 custom-shadow overflow-hidden">
          <div className="p-6 space-y-5">
<Field label={t('tf.title')} required error={errors.title}>
              <input
                type="text"
                value={formData.title}
                onChange={(e) => handleChange('title', e.target.value)}
                maxLength={200}
                placeholder={t('tf.titlePlaceholder')}
                className={inputClass}
              />
            </Field>

            <Field label={t('tf.description')} required error={errors.description}>
              <textarea
                value={formData.description}
                onChange={(e) => handleChange('description', e.target.value)}
                placeholder={t('tf.descPlaceholder')}
                rows={5}
                className={`${inputClass} resize-none`}
              />
            </Field>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {isStaff && (
<Field label={t('tf.client')} required error={errors.client_id}>
                  <select
                    value={formData.client_id}
                    onChange={(e) => handleChange('client_id', e.target.value)}
                    className={`${inputClass} cursor-pointer`}
                  >
                    <option value="">{t('tf.selectClient')}</option>
                    {clients.map((client) => (
                      <option key={client.id} value={client.id}>{client.name} ({client.email})</option>
                    ))}
                  </select>
                </Field>
              )}

<Field label={t('tf.category')} error={errors.category}>
                <select
                  value={formData.category}
                  onChange={(e) => handleChange('category', e.target.value)}
                  className={`${inputClass} cursor-pointer`}
                >
                  <option value="">{t('tf.select')}</option>
                  {CATEGORIES.map((c) => (
                    <option key={c.value} value={c.value}>{t(`category.${c.value}`)}</option>
                  ))}
                </select>
              </Field>

{canAssignTicket && <Field label={isStaffTicketCreate ? t('tf.assignedTechnician') : t('tf.assignedTo')} error={errors.assigned_technician_id}>
                 {isStaffTicketCreate ? (
                   <select
                      value={formData.assigned_technician_id}
                     onChange={(e) => {
                       const selected = technicians.find((technician) => String(technician.id) === e.target.value)
                        handleChange('assigned_technician_id', e.target.value)
                       handleChange('assignee', selected?.name || '')
                     }}
                     className={`${inputClass} cursor-pointer`}
                   >
                     <option value="">{t('tf.selectTechnician')}</option>
                     {technicians.map((technician) => (
                       <option key={technician.id} value={technician.id}>
                         {technician.name} - {t('tf.openTickets', { count: technician.openTickets })}
                       </option>
                     ))}
                   </select>
                 ) : (
                   <input
                     type="text"
                     value={formData.assignee}
                     onChange={(e) => handleChange('assignee', e.target.value)}
                     placeholder={t('tf.unassignedPlaceholder')}
                     className={inputClass}
                   />
                 )}
                </Field>}
            </div>

             {canEditStatus && (
              <Field label={t('tf.status')}>
                <StatusSelect value={formData.status} onChange={(v) => handleChange('status', v)} />
              </Field>
            )}
          </div>

          <div className="p-5 border-t border-slate-100 bg-slate-50/50 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={() => navigate(mode === 'edit' ? `${basePath}/${initialValues.id}` : basePath)}
              className="px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
            >
              {t('tf.cancel')}
            </button>
            <button
              type="submit"
              className="inline-flex items-center gap-2 px-5 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl transition-colors shadow-lg shadow-blue-500/20"
            >
              <Save className="w-4 h-4" />
              {submitLabel}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
