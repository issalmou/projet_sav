import { useState, useRef } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeft, Save, Camera, Trash2, Upload,
  Monitor, Server, Wifi, Printer, HardDrive, Headphones, Package,
  Plus, X,
} from 'lucide-react'
import { useProducts } from '../../contexts/useProducts'
import { PRODUCT_CATEGORIES } from '../../contexts/ProductsContext'
import { Field, inputClass } from '../../components/admin/ui'
import { toastService } from '../../services/toast'
import { useI18n } from '../../i18n/useI18n'

const ICON_MAP = {
  monitor: Monitor, server: Server, wifi: Wifi, printer: Printer,
  'hard-drive': HardDrive, headphones: Headphones, package: Package,
}

const CATEGORY_COLORS = {
  Ecrans: { bg: 'bg-indigo-100', text: 'text-indigo-600' },
  Serveurs: { bg: 'bg-blue-100', text: 'text-blue-600' },
  Reseau: { bg: 'bg-purple-100', text: 'text-purple-600' },
  Impression: { bg: 'bg-amber-100', text: 'text-amber-600' },
  Stockage: { bg: 'bg-emerald-100', text: 'text-emerald-600' },
  Audio: { bg: 'bg-rose-100', text: 'text-rose-600' },
  Autre: { bg: 'bg-slate-100', text: 'text-slate-500' },
}

function ImageUploader({ image, onChange, category }) {
  const fileInputRef = useRef(null)
  const colors = CATEGORY_COLORS[category] || CATEGORY_COLORS.Autre
  const catObj = PRODUCT_CATEGORIES.find((c) => c.value === category)
  const Icon = ICON_MAP[catObj?.icon] || Package

  const handleFileChange = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (file.size > 5 * 1024 * 1024) {
      toastService.error("L'image ne doit pas dépasser 5 Mo.")
      return
    }
    if (!file.type.startsWith('image/')) {
      toastService.error("Le fichier doit être une image.")
      return
    }
    const reader = new FileReader()
    reader.onload = (ev) => onChange(ev.target.result)
    reader.readAsDataURL(file)
  }

  const handleRemove = (e) => {
    e.stopPropagation()
    onChange(null)
  }

  return (
    <div className="space-y-2">
      <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
        Photo du produit
      </label>
      <div
        onClick={() => fileInputRef.current?.click()}
        className="relative group cursor-pointer w-full aspect-[4/3] max-w-sm rounded-2xl overflow-hidden border-2 border-dashed border-slate-200 hover:border-blue-400 transition-all"
      >
        {image ? (
          <>
            <img src={image} alt="Preview" className="w-full h-full object-cover" />
            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-all flex items-center justify-center">
              <div className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-2">
                <span className="px-3 py-2 bg-white/90 rounded-xl text-xs font-semibold text-slate-700 backdrop-blur-sm">
                  <Camera className="w-4 h-4 inline mr-1.5" />
                  Changer
                </span>
                <button
                  onClick={handleRemove}
                  className="p-2 bg-red-500/90 rounded-xl text-white backdrop-blur-sm hover:bg-red-600 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className={`w-full h-full flex flex-col items-center justify-center ${colors.bg} ${colors.text} gap-3`}>
            <div className="w-16 h-16 rounded-2xl bg-white/60 flex items-center justify-center">
              <Icon className="w-8 h-8 opacity-60" />
            </div>
            <div className="text-center">
              <p className="text-sm font-bold opacity-80">Ajouter une image</p>
              <p className="text-xs opacity-50 mt-0.5">JPEG, PNG • max 5 Mo</p>
            </div>
            <div className="opacity-0 group-hover:opacity-100 transition-opacity mt-1">
              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white/80 rounded-lg text-xs font-semibold backdrop-blur-sm">
                <Upload className="w-3.5 h-3.5" />
                Parcourir
              </span>
            </div>
          </div>
        )}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleFileChange}
          className="hidden"
        />
      </div>
    </div>
  )
}

function SpecsEditor({ specs, onChange }) {
  const entries = Object.entries(specs || {})

  const addEntry = () => {
    onChange({ ...specs, '': '' })
  }

  const updateEntry = (oldKey, newKey, value) => {
    const next = {}
    for (const [k, v] of Object.entries(specs)) {
      if (k === oldKey) {
        next[newKey] = value
      } else {
        next[k] = v
      }
    }
    onChange(next)
  }

  const removeEntry = (key) => {
    const next = {}
    for (const [k, v] of Object.entries(specs)) {
      if (k !== key) next[k] = v
    }
    onChange(next)
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
          Caractéristiques
        </label>
        <button
          type="button"
          onClick={addEntry}
          className="inline-flex items-center gap-1 px-2 py-1 text-[10px] font-semibold text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors"
        >
          <Plus className="w-3 h-3" />
          Ajouter
        </button>
      </div>
      {entries.length === 0 ? (
        <p className="text-xs text-slate-400 italic">Aucune caractéristique. Cliquez sur "Ajouter" pour commencer.</p>
      ) : (
        <div className="space-y-2">
          {entries.map(([key, value], idx) => (
            <div key={idx} className="flex items-center gap-2">
              <input
                type="text"
                value={key}
                onChange={(e) => updateEntry(key, e.target.value, value)}
                placeholder="Clé"
                className="flex-1 px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
              />
              <input
                type="text"
                value={value}
                onChange={(e) => updateEntry(key, key, e.target.value)}
                placeholder="Valeur"
                className="flex-1 px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
              />
              <button
                type="button"
                onClick={() => removeEntry(key)}
                className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors shrink-0"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

void ImageUploader
void SpecsEditor

export default function ProductForm({ basePath = '/admin' }) {
  const navigate = useNavigate()
  const { id } = useParams()
  const { t } = useI18n()
  const { products, createProduct, updateProduct } = useProducts()

  const editing = products.find((p) => p.id === id)
  const isEdit = !!editing

  const [formData, setFormData] = useState({
    name: editing?.name || '',
    reference: editing?.reference || '',
    category: editing?.category || '',
    description: editing?.description || '',
    brand: editing?.brand || '',
    model: editing?.model || '',
    serial_number: editing?.serial_number || '',
    warranty_months: editing?.warranty_months || '',
    warranty_purchase_date: editing?.warranty_purchase_date || '',
    image_url: editing?.image_url || null,
    specs: editing?.specs || {},
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
    if (!formData.name.trim()) errs.name = t('admin.products.nameRequired')
    if (!formData.reference.trim()) errs.reference = t('admin.products.refRequired')
    if (formData.name.trim().length > 200) errs.name = t('admin.products.nameTooLong')
    if (formData.reference.trim().length > 100) errs.reference = t('admin.products.refTooLong')
    if (formData.description.trim().length > 400) errs.description = t('admin.products.descTooLong')
    if (formData.warranty_months !== '' && (!Number.isInteger(Number(formData.warranty_months)) || Number(formData.warranty_months) < 0)) {
      errs.warranty_months = t('admin.products.warrantyInvalid')
    }
    setErrors(errs)
    if (Object.keys(errs).length > 0) return

    const payload = {
      name: formData.name.trim(),
      reference: formData.reference.trim(),
      category: formData.category || null,
      description: formData.description.trim() || null,
      warranty_months: formData.warranty_months ? Number(formData.warranty_months) : null,
    }

    if (isEdit) {
      updateProduct(id, payload)
      navigate(`${basePath}/products`, {
        state: { toast: { message: t('admin.products.updated', { name: payload.name }) } },
      })
    } else {
      createProduct(payload)
      navigate(`${basePath}/products`, {
        state: { toast: { message: t('admin.products.created', { name: payload.name }) } },
      })
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <button
        onClick={() => navigate(`${basePath}/products`)}
        className="inline-flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-blue-600 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        {t('pd.backToProducts')}
      </button>

      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
          {isEdit ? t('admin.products.editTitle', { name: editing.name }) : t('products.add')}
        </h1>
        <p className="text-slate-500">
          {isEdit
            ? t('admin.products.editSubtitle')
            : t('admin.products.createSubtitle')}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-slate-200 custom-shadow overflow-hidden">
        <div className="p-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Field label={t('admin.products.name')} required error={errors.name}>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => handleChange('name', e.target.value)}
                maxLength={200}
                placeholder="Ex: 3LM Solution Pro 32&quot; 4K OLED"
                className={inputClass}
              />
            </Field>

            <Field label={t('pd.reference')} required error={errors.reference}>
              <input
                type="text"
                value={formData.reference}
                onChange={(e) => handleChange('reference', e.target.value)}
                maxLength={100}
                placeholder="Ex: NX-OLED-48293"
                className={inputClass}
              />
            </Field>

            <Field label={t('common.category')}>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {PRODUCT_CATEGORIES.map((c) => {
                  const colors = CATEGORY_COLORS[c.value] || CATEGORY_COLORS.Autre
                  const Icon = ICON_MAP[c.icon] || Package
                  return (
                    <button
                      key={c.value}
                      type="button"
                      onClick={() => handleChange('category', c.value)}
                      className={`inline-flex items-center gap-1.5 px-3 py-2.5 rounded-xl text-xs font-bold border transition-all ${
                        formData.category === c.value
                          ? `${colors.bg} ${colors.text} border-current ring-2 ring-offset-1 ring-current`
                          : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                      }`}
                    >
                      <Icon className="w-3.5 h-3.5" />
                      {c.label}
                    </button>
                  )
                })}
              </div>
            </Field>

            <Field label={t('pd.warrantyMonths')} error={errors.warranty_months}>
              <input
                type="number"
                min="0"
                value={formData.warranty_months}
                onChange={(e) => handleChange('warranty_months', e.target.value)}
                placeholder="Ex: 36"
                className={inputClass}
              />
            </Field>

            <div className="md:col-span-2">
              <Field label={t('pd.description')} error={errors.description}>
                <textarea
                  value={formData.description}
                  onChange={(e) => handleChange('description', e.target.value)}
                  maxLength={400}
                  rows={3}
                  placeholder={t('pd.descriptionPlaceholder')}
                  className={`${inputClass} resize-none`}
                />
              </Field>
            </div>

          </div>
        </div>

        <div className="p-5 border-t border-slate-100 bg-slate-50/50 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={() => navigate(`${basePath}/products`)}
            className="px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
          >
            {t('common.cancel')}
          </button>
          <button
            type="submit"
            className="inline-flex items-center gap-2 px-5 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl transition-colors shadow-lg shadow-blue-500/20"
          >
            <Save className="w-4 h-4" />
            {isEdit ? t('tf.submitEdit') : t('admin.products.create')}
          </button>
        </div>
      </form>
    </div>
  )
}
