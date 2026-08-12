import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Save } from 'lucide-react'
import { useAdmin } from '../../contexts/useAdmin'
import { ROLE_ORDER, ROLES } from '../../contexts/roles'
import { Field, inputClass } from '../../components/admin/ui'

export default function UserForm() {
  const navigate = useNavigate()
  const { id } = useParams()
  const { users, createUser, updateUser } = useAdmin()

  const editing = users.find((u) => u.id === id)
  const isEdit = !!editing

  const [formData, setFormData] = useState({
    name: editing?.name || '',
    email: editing?.email || '',
    role: editing?.role || 'agent',
    status: editing?.status || 'active',
    department: editing?.department || '',
    phone: editing?.phone || '',
    password: '',
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
    const errs = {}
    if (!formData.name.trim()) errs.name = 'Le nom est obligatoire.'
    if (!formData.email.trim()) errs.email = "L'email est obligatoire."
    else if (!/\S+@\S+\.\S+/.test(formData.email)) errs.email = "L'email est invalide."
    if (!isEdit && formData.password.length < 6)
      errs.password = 'Le mot de passe doit contenir au moins 6 caractères.'
    setErrors(errs)
    if (Object.keys(errs).length > 0) return

    const payload = {
      name: formData.name.trim(),
      email: formData.email.trim(),
      role: formData.role,
      status: formData.status,
      department: formData.department.trim(),
      phone: formData.phone.trim(),
    }

    if (isEdit) {
      updateUser(id, payload)
      navigate('/admin/users', {
        state: { toast: { message: `Le compte de ${payload.name} a été mis à jour` } },
      })
    } else {
      createUser(payload)
      navigate('/admin/users', {
        state: { toast: { message: `Le compte de ${payload.name} a été créé` } },
      })
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <button
        onClick={() => navigate('/admin/users')}
        className="inline-flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-blue-600 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Retour aux utilisateurs
      </button>

      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
          {isEdit ? `Modifier ${editing.name}` : 'Ajouter un utilisateur'}
        </h1>
        <p className="text-slate-500">
          {isEdit
            ? "Mettez à jour les informations du compte et ses permissions."
            : 'Créez un nouveau compte et attribuez-lui un rôle.'}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-slate-200 custom-shadow overflow-hidden">
        <div className="p-6 space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <Field label="Nom complet" required error={errors.name}>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => handleChange('name', e.target.value)}
                placeholder="Ex : Jean Dupont"
                className={inputClass}
              />
            </Field>

            <Field label="Adresse email" required error={errors.email}>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => handleChange('email', e.target.value)}
                placeholder="jean@company.com"
                className={inputClass}
              />
            </Field>

            <Field label="Rôle" required>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {ROLE_ORDER.map((role) => (
                  <button
                    key={role}
                    type="button"
                    onClick={() => handleChange('role', role)}
                    className={`px-3 py-2.5 rounded-xl text-xs font-bold border transition-all ${
                      formData.role === role
                        ? ROLES[role].color + ' ring-2 ring-offset-1 ' + ROLES[role].dot.replace('bg-', 'ring-')
                        : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                    }`}
                  >
                    {ROLES[role].label}
                  </button>
                ))}
              </div>
            </Field>

            <Field label="Statut">
              <div className="grid grid-cols-2 gap-2">
                {['active', 'inactive'].map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => handleChange('status', s)}
                    className={`px-3 py-2.5 rounded-xl text-xs font-bold border transition-all ${
                      formData.status === s
                        ? s === 'active'
                          ? 'bg-teal-50 text-teal-600 border-teal-200 ring-2 ring-offset-1 ring-teal-500'
                          : 'bg-slate-100 text-slate-600 border-slate-200 ring-2 ring-offset-1 ring-slate-400'
                        : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                    }`}
                  >
                    {s === 'active' ? 'Actif' : 'Inactif'}
                  </button>
                ))}
              </div>
            </Field>

            <Field label="Service / Département">
              <input
                type="text"
                value={formData.department}
                onChange={(e) => handleChange('department', e.target.value)}
                placeholder="Ex : Support Niveau 1"
                className={inputClass}
              />
            </Field>

            <Field label="Téléphone">
              <input
                type="tel"
                value={formData.phone}
                onChange={(e) => handleChange('phone', e.target.value)}
                placeholder="+33 6 12 34 56 78"
                className={inputClass}
              />
            </Field>

            {!isEdit && (
              <Field label="Mot de passe" required error={errors.password}>
                <input
                  type="password"
                  value={formData.password}
                  onChange={(e) => handleChange('password', e.target.value)}
                  placeholder="Minimum 6 caractères"
                  className={inputClass}
                />
              </Field>
            )}
          </div>

          <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-xs text-slate-500 leading-relaxed">
            <strong className="text-slate-700">Permissions du rôle :</strong>{' '}
            {formData.role === 'admin' &&
              'Accès complet : gestion des utilisateurs, documents, intégrations, logs et paramètres.'}
            {formData.role === 'manager' &&
              'Accès supervision : gestion de l\u2019équipe support, base documentaire et logs d\u2019activité.'}
            {formData.role === 'agent' &&
              'Accès support : gestion de la base documentaire et consultation des logs d\u2019activité.'}
            {formData.role === 'client' &&
              'Accès client : tickets, chat AI et base de connaissances uniquement.'}
          </div>
        </div>

        <div className="p-5 border-t border-slate-100 bg-slate-50/50 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={() => navigate('/admin/users')}
            className="px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
          >
            Annuler
          </button>
          <button
            type="submit"
            className="inline-flex items-center gap-2 px-5 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl transition-colors shadow-lg shadow-blue-500/20"
          >
            <Save className="w-4 h-4" />
            {isEdit ? 'Enregistrer les modifications' : 'Créer le compte'}
          </button>
        </div>
      </form>
    </div>
  )
}
