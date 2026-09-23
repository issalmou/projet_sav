import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Save } from 'lucide-react'
import { useAuth } from '../../contexts/useAuth'
import { useAdmin } from '../../contexts/useAdmin'
import { useProducts } from '../../contexts/useProducts'
import { ROLES, canManageRole, manageableRoles, resolveRole } from '../../contexts/roles'
import { Field, inputClass } from '../../components/admin/ui'
import { useI18n } from '../../i18n/useI18n'

export default function UserForm({ basePath = '/admin' }) {
  const navigate = useNavigate()
  const { id } = useParams()
  const { t } = useI18n()
  const { user } = useAuth()
  const { users, roles, createUser, updateUser } = useAdmin()
  const { products } = useProducts()

  const editing = users.find((u) => u.id === id)
  const isEdit = !!editing

  const allowedRoles = manageableRoles(user)
  const defaultRole = allowedRoles.includes('agent') ? 'agent' : allowedRoles[0] || 'client'
  const selectableRoles = isEdit && !allowedRoles.includes(editing.role) ? [editing.role, ...allowedRoles] : allowedRoles

  const [formData, setFormData] = useState({
    name: editing?.name || '',
    email: editing?.email || '',
    role: editing?.role || defaultRole,
    roleId: editing?.roleId || null,
    status: editing?.status || 'active',
    phone: editing?.phone || '',
    password: '',
    productIds: editing?.product_ids || editing?.productIds || [],
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

  const selectRole = (role) => {
    if (!canManageRole(user, role)) return
    const backendRole = roles.find((item) => resolveRole(item.name) === role)
    const existingRole = users.find((user) => user.role === role && user.roleId)
    setFormData((prev) => ({
      ...prev,
      role,
      roleId: backendRole?.id || existingRole?.roleId || null,
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
const errs = {}
    if (!formData.name.trim()) errs.name = t('settings.nameRequired')
    if (!formData.email.trim()) errs.email = t('settings.emailRequired')
    else if (!/\S+@\S+\.\S+/.test(formData.email)) errs.email = t('settings.emailInvalid')
    if (formData.role === 'client' && formData.productIds.length === 0) {
      errs.productIds = t('admin.users.productRequired')
    }
    if (!isEdit) {
      if (formData.password.length < 8) {
        errs.password = t('settings.passwordMin')
      } else if (!/[A-Z]/.test(formData.password) || !/\d/.test(formData.password)) {
        errs.password = t('admin.users.passwordComplexity')
      }
    }
    setErrors(errs)
    if (Object.keys(errs).length > 0) return

    const payload = {
      name: formData.name.trim(),
      email: formData.email.trim(),
      role: formData.role,
      roleId:
        formData.roleId ||
        roles.find((item) => resolveRole(item.name) === formData.role)?.id ||
        users.find((user) => user.role === formData.role)?.roleId ||
        null,
status: formData.status,
      phone: formData.phone.trim(),
      password: formData.password,
      product_ids: formData.role === 'client' ? formData.productIds : [],
}

if (!payload.roleId) {
      setErrors({
        role: t('admin.users.roleNotFound', {
          role: ROLES[formData.role]?.label || formData.role,
        }),
      })
      return
    }

    try {
      if (isEdit) {
        await updateUser(id, payload)
        navigate(`${basePath}/users`, {
          state: { toast: { message: t('admin.users.updated', { name: payload.name }) } },
        })
      } else {
        await createUser(payload)
        navigate(`${basePath}/users`, {
          state: { toast: { message: t('admin.users.created', { name: payload.name }) } },
        })
      }
    } catch (error) {
      setErrors({ form: error.message || t('admin.users.createFailed') })
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <button
        onClick={() => navigate(`${basePath}/users`)}
        className="inline-flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-blue-600 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        {t('admin.users.backToList')}
      </button>

      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
          {isEdit ? t('admin.users.editTitle', { name: editing.name }) : t('admin.users.add')}
        </h1>
        <p className="text-slate-500">
          {isEdit
            ? t('admin.users.editSubtitle')
            : t('admin.users.createSubtitle')}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-slate-200 custom-shadow overflow-hidden">
        <div className="p-6 space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
<Field label={t('admin.users.user')} required error={errors.name}>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => handleChange('name', e.target.value)}
                placeholder="Ex : Jean Dupont"
                className={inputClass}
              />
            </Field>

            <Field label={t('settings.email')} required error={errors.email}>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => handleChange('email', e.target.value)}
                placeholder="jean@company.com"
                className={inputClass}
              />
            </Field>

            <Field label={t('admin.users.roleLabel')} required error={errors.role}>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {selectableRoles.map((role) => (
                  <button
                    key={role}
                    type="button"
                    onClick={() => selectRole(role)}
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

            <Field label={t('common.statu')}>
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
                    {s === 'active' ? t('admin.users.active') : t('admin.users.inactive')}
                  </button>
                ))}
              </div>
            </Field>

            <Field label={t('settings.phone')}>
              <input
                type="tel"
                value={formData.phone}
                onChange={(e) => handleChange('phone', e.target.value)}
                placeholder="+33 6 12 34 56 78"
                className={inputClass}
              />
            </Field>

            {formData.role === 'client' && (
              <Field label={t('admin.users.assignedProducts')} required error={errors.productIds}>
                <div className="max-h-44 overflow-y-auto space-y-2 rounded-xl border border-slate-200 bg-slate-50 p-3">
                  {products.length === 0 ? (
                    <p className="text-xs text-slate-500">{t('admin.users.noProducts')}</p>
                  ) : products.map((product) => (
                    <label key={product.id} className="flex items-center gap-2 text-sm text-slate-700 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData.productIds.includes(product.id)}
                        onChange={(e) => handleChange(
                          'productIds',
                          e.target.checked
                            ? [...formData.productIds, product.id]
                            : formData.productIds.filter((id) => id !== product.id),
                        )}
                        className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span>{product.name} ({product.reference})</span>
                    </label>
                  ))}
                </div>
              </Field>
            )}

            {!isEdit && (
              <Field label={t('admin.users.password')} required error={errors.password}>
                  <input
                    type="password"
                  value={formData.password}
                  onChange={(e) => handleChange('password', e.target.value)}
                  placeholder={t('admin.users.passwordHint')}
                  className={inputClass}
                />
              </Field>
            )}
          </div>

          <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-xs text-slate-500 leading-relaxed">
            {errors.form && <p className="mb-2 text-red-600 font-medium">{errors.form}</p>}
            <strong className="text-slate-700">{t('admin.users.rolePermsLabel')}</strong>{' '}
            {formData.role === 'admin' &&
              t('admin.users.roleAdminDesc')}
            {formData.role === 'manager' &&
              t('admin.users.roleManagerDesc')}
            {formData.role === 'agent' &&
              t('admin.users.roleAgentDesc')}
            {formData.role === 'client' &&
              t('admin.users.roleClientDesc')}
          </div>
        </div>

        <div className="p-5 border-t border-slate-100 bg-slate-50/50 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={() => navigate(`${basePath}/users`)}
            className="px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
          >
            {t('common.cancel')}
          </button>
          <button
            type="submit"
            className="inline-flex items-center gap-2 px-5 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl transition-colors shadow-lg shadow-blue-500/20"
          >
            <Save className="w-4 h-4" />
            {isEdit ? t('tf.submitEdit') : t('admin.users.createAccount')}
          </button>
        </div>
      </form>
    </div>
  )
}
