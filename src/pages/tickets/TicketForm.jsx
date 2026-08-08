import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Save } from 'lucide-react'
import StatusSelect from '../../components/tickets/StatusSelect'
import { CATEGORIES, PRIORITIES } from '../../components/tickets/constants'

function PrioritySelect({ value, onChange }) {
  return (
    <div className="flex gap-2">
      {Object.entries(PRIORITIES).map(([key, p]) => (
        <button
          key={key}
          type="button"
          onClick={() => onChange(key)}
          className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-xl text-sm font-semibold border transition-all ${
            value === key
              ? p.color + ' ring-2 ring-offset-1 ' + p.dot.replace('bg-', 'ring-')
              : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
          }`}
        >
          <span className={`w-2 h-2 rounded-full ${p.dot}`} />
          {p.label}
        </button>
      ))}
    </div>
  )
}

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

export default function TicketForm({ mode, initialValues, onSubmit, submitLabel }) {
  const navigate = useNavigate()
  const [formData, setFormData] = useState({
    title: initialValues?.title || '',
    description: initialValues?.description || '',
    category: initialValues?.category || '',
    priority: initialValues?.priority || 'medium',
    status: initialValues?.status || 'open',
    assignee: initialValues?.assignee || ''
  })
  const [errors, setErrors] = useState({})

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
    if (!formData.title.trim()) validationErrors.title = 'Le titre est obligatoire.'
    if (!formData.description.trim()) validationErrors.description = 'La description est obligatoire.'
    if (!formData.category) validationErrors.category = 'La catégorie est obligatoire.'
    setErrors(validationErrors)
    if (Object.keys(validationErrors).length > 0) return
    onSubmit({
      title: formData.title.trim(),
      description: formData.description.trim(),
      category: formData.category,
      priority: formData.priority,
      status: formData.status,
      assignee: formData.assignee.trim()
    })
  }

  return (
    <div className="flex-1 overflow-y-auto p-8">
      <div className="max-w-3xl mx-auto space-y-6">
        <button
          onClick={() => navigate(mode === 'edit' ? `/tickets/${initialValues.id}` : '/tickets')}
          className="inline-flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-blue-600 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          {mode === 'edit' ? 'Retour au ticket' : 'Retour aux tickets'}
        </button>

        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            {mode === 'edit' ? `Modifier le ticket ${initialValues.id}` : 'Nouveau Ticket'}
          </h1>
          <p className="text-slate-500">
            {mode === 'edit'
              ? "Mettez à jour les informations du ticket."
              : 'Remplissez les informations ci-dessous pour ouvrir une demande de support.'}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-slate-200 custom-shadow overflow-hidden">
          <div className="p-6 space-y-5">
            <Field label="Titre" required error={errors.title}>
              <input
                type="text"
                value={formData.title}
                onChange={(e) => handleChange('title', e.target.value)}
                placeholder="Ex: Problème d'impression"
                className={inputClass}
              />
            </Field>

            <Field label="Description" required error={errors.description}>
              <textarea
                value={formData.description}
                onChange={(e) => handleChange('description', e.target.value)}
                placeholder="Décrivez votre problème en détail..."
                rows={5}
                className={`${inputClass} resize-none`}
              />
            </Field>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <Field label="Catégorie" required error={errors.category}>
                <select
                  value={formData.category}
                  onChange={(e) => handleChange('category', e.target.value)}
                  className={`${inputClass} cursor-pointer`}
                >
                  <option value="">Sélectionner</option>
                  {CATEGORIES.map((c) => (
                    <option key={c.value} value={c.value}>{c.label}</option>
                  ))}
                </select>
              </Field>

              <Field label="Assigné à">
                <input
                  type="text"
                  value={formData.assignee}
                  onChange={(e) => handleChange('assignee', e.target.value)}
                  placeholder="Non assigné"
                  className={inputClass}
                />
              </Field>
            </div>

            <Field label="Priorité">
              <PrioritySelect value={formData.priority} onChange={(v) => handleChange('priority', v)} />
            </Field>

            {mode === 'edit' && (
              <Field label="Statut">
                <StatusSelect value={formData.status} onChange={(v) => handleChange('status', v)} />
              </Field>
            )}
          </div>

          <div className="p-5 border-t border-slate-100 bg-slate-50/50 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={() => navigate(mode === 'edit' ? `/tickets/${initialValues.id}` : '/tickets')}
              className="px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
            >
              Annuler
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
