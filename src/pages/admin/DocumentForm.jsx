import { useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, FileText, Save, UploadCloud, X } from 'lucide-react'
import { useAdmin } from '../../contexts/useAdmin'
import { Field, inputClass } from '../../components/admin/ui'

const ACCEPTED_TYPES = ['application/pdf', 'image/png', 'image/jpeg', 'image/webp']
const ACCEPTED_EXT = '.pdf,.png,.jpg,.jpeg,.webp'
const MAX_FILE_SIZE = 2 * 1024 * 1024
const MAX_FILES = 3

function uid() {
  return `file-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} o`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} Ko`
  return `${(bytes / (1024 * 1024)).toFixed(2)} Mo`
}

const DOC_TYPES = [
  { value: 'faq', label: 'FAQ' },
  { value: 'manual', label: 'Manuel' },
  { value: 'guide', label: 'Guide' },
]

const CATEGORIES = ['Configuration', 'Dépannage', 'Manuels', 'Guides', 'Comptes & Facturation', 'Sécurité']

const LANGUAGES = [
  { value: 'fr', label: 'Français' },
  { value: 'en', label: 'Anglais' },
]

export default function DocumentForm() {
  const navigate = useNavigate()
  const { id } = useParams()
  const { documents, createDocument, updateDocument } = useAdmin()

  const editing = documents.find((d) => d.id === id)
  const isEdit = !!editing

  const [formData, setFormData] = useState({
    title: editing?.title || '',
    type: editing?.type || 'faq',
    category: editing?.category || '',
    language: editing?.language || 'fr',
    status: editing?.status || 'published',
    content: editing?.content || '',
    tags: editing?.tags?.join(', ') || '',
  })
  const [errors, setErrors] = useState({})
  const [attachments, setAttachments] = useState(editing?.attachments || [])
  const [uploadError, setUploadError] = useState('')
  const fileInputRef = useRef(null)

  const handleFiles = (fileList) => {
    setUploadError('')
    const files = Array.from(fileList || [])
    for (const file of files) {
      if (!ACCEPTED_TYPES.includes(file.type)) {
        setUploadError(`Type non pris en charge : ${file.name}. Formats acceptés : PDF, PNG, JPG, WEBP.`)
        continue
      }
      if (file.size > MAX_FILE_SIZE) {
        setUploadError(`Fichier trop volumineux : ${file.name} (2 Mo max).`)
        continue
      }
      if (attachments.length >= MAX_FILES) {
        setUploadError(`Nombre maximum de fichiers atteint (${MAX_FILES}).`)
        return
      }
      const reader = new FileReader()
      reader.onload = () => {
        setAttachments((prev) => [
          ...prev,
          {
            id: uid(),
            name: file.name,
            size: file.size,
            type: file.type,
            dataUrl: reader.result,
          },
        ])
      }
      reader.readAsDataURL(file)
    }
  }

  const removeAttachment = (id) => {
    setAttachments((prev) => prev.filter((a) => a.id !== id))
  }

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
    if (!formData.title.trim()) errs.title = 'Le titre est obligatoire.'
    if (!formData.category) errs.category = 'La catégorie est obligatoire.'
    if (!formData.content.trim()) errs.content = 'Le contenu est obligatoire.'
    setErrors(errs)
    if (Object.keys(errs).length > 0) return

    const payload = {
      title: formData.title.trim(),
      type: formData.type,
      category: formData.category,
      language: formData.language,
      status: formData.status,
      content: formData.content.trim(),
      attachments,
      tags: formData.tags
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean),
    }

    if (isEdit) {
      updateDocument(id, payload)
      navigate('/admin/documents', {
        state: { toast: { message: `Le document « ${payload.title} » a été mis à jour` } },
      })
    } else {
      createDocument(payload)
      navigate('/admin/documents', {
        state: { toast: { message: `Le document « ${payload.title} » a été créé` } },
      })
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <button
        onClick={() => navigate('/admin/documents')}
        className="inline-flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-blue-600 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Retour à la base documentaire
      </button>

      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
          {isEdit ? 'Modifier le document' : 'Nouveau document'}
        </h1>
        <p className="text-slate-500">
          {isEdit
            ? "Mettez à jour le contenu de la base documentaire."
            : 'Ajoutez une FAQ, un manuel ou un guide à la base documentaire.'}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-slate-200 custom-shadow overflow-hidden">
        <div className="p-6 space-y-5">
          <Field label="Titre" required error={errors.title}>
            <input
              type="text"
              value={formData.title}
              onChange={(e) => handleChange('title', e.target.value)}
              placeholder="Ex : Comment réinitialiser mon appareil ?"
              className={inputClass}
            />
          </Field>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <Field label="Type de document" required>
              <div className="grid grid-cols-3 gap-2">
                {DOC_TYPES.map((t) => (
                  <button
                    key={t.value}
                    type="button"
                    onClick={() => handleChange('type', t.value)}
                    className={`px-3 py-2.5 rounded-xl text-xs font-bold border transition-all ${
                      formData.type === t.value
                        ? 'bg-blue-50 text-blue-600 border-blue-200 ring-2 ring-offset-1 ring-blue-500'
                        : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </Field>

            <Field label="Catégorie" required error={errors.category}>
              <select
                value={formData.category}
                onChange={(e) => handleChange('category', e.target.value)}
                className={`${inputClass} cursor-pointer`}
              >
                <option value="">Sélectionner</option>
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Langue">
              <select
                value={formData.language}
                onChange={(e) => handleChange('language', e.target.value)}
                className={`${inputClass} cursor-pointer`}
              >
                {LANGUAGES.map((l) => (
                  <option key={l.value} value={l.value}>
                    {l.label}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Statut">
              <div className="grid grid-cols-2 gap-2">
                {[
                  { value: 'published', label: 'Publié' },
                  { value: 'draft', label: 'Brouillon' },
                ].map((s) => (
                  <button
                    key={s.value}
                    type="button"
                    onClick={() => handleChange('status', s.value)}
                    className={`px-3 py-2.5 rounded-xl text-xs font-bold border transition-all ${
                      formData.status === s.value
                        ? s.value === 'published'
                          ? 'bg-teal-50 text-teal-600 border-teal-200 ring-2 ring-offset-1 ring-teal-500'
                          : 'bg-amber-50 text-amber-600 border-amber-200 ring-2 ring-offset-1 ring-amber-500'
                        : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                    }`}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </Field>
          </div>

          <Field label="Contenu" required error={errors.content}>
            <textarea
              value={formData.content}
              onChange={(e) => handleChange('content', e.target.value)}
              placeholder="Rédigez le contenu du document..."
              rows={8}
              className={`${inputClass} resize-none leading-relaxed`}
            />
          </Field>

          <Field label="Tags" hint="Séparez les tags par des virgules">
            <input
              type="text"
              value={formData.tags}
              onChange={(e) => handleChange('tags', e.target.value)}
              placeholder="Ex : configuration, dépannage, wifi"
              className={inputClass}
            />
          </Field>

          <Field
            label="Fichiers joints"
            hint="PDF, PNG, JPG, WEBP — 2 Mo max par fichier, 3 fichiers max"
          >
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault()
                handleFiles(e.dataTransfer.files)
              }}
              onClick={() => fileInputRef.current?.click()}
              className="flex flex-col items-center justify-center gap-2 px-4 py-8 border-2 border-dashed border-slate-300 rounded-xl text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50/40 transition-colors"
            >
              <UploadCloud className="w-8 h-8 text-slate-400" />
              <p className="text-sm font-semibold text-slate-600">
                Glissez-déposez vos fichiers ici ou{' '}
                <span className="text-blue-600">parcourir</span>
              </p>
              <p className="text-xs text-slate-400">
                Formats acceptés : PDF, PNG, JPG, WEBP (2 Mo max par fichier)
              </p>
              <input
                ref={fileInputRef}
                type="file"
                accept={ACCEPTED_EXT}
                multiple
                className="hidden"
                onChange={(e) => {
                  handleFiles(e.target.files)
                  e.target.value = ''
                }}
              />
            </div>

            {uploadError && (
              <p className="mt-2 text-xs font-semibold text-red-600">{uploadError}</p>
            )}

            {attachments.length > 0 && (
              <ul className="mt-3 space-y-2">
                {attachments.map((att) => (
                  <li
                    key={att.id}
                    className="flex items-center gap-3 px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl"
                  >
                    <span className="w-9 h-9 shrink-0 rounded-lg bg-white border border-slate-200 flex items-center justify-center text-slate-400">
                      <FileText className="w-4 h-4" />
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-slate-700 truncate">{att.name}</p>
                      <p className="text-xs text-slate-400">
                        {formatFileSize(att.size)} ·{' '}
                        {att.type === 'application/pdf' ? 'PDF' : 'Image'}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => removeAttachment(att.id)}
                      title="Retirer le fichier"
                      className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Field>
        </div>

        <div className="p-5 border-t border-slate-100 bg-slate-50/50 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={() => navigate('/admin/documents')}
            className="px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
          >
            Annuler
          </button>
          <button
            type="submit"
            className="inline-flex items-center gap-2 px-5 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl transition-colors shadow-lg shadow-blue-500/20"
          >
            <Save className="w-4 h-4" />
            {isEdit ? 'Enregistrer les modifications' : 'Créer le document'}
          </button>
        </div>
      </form>
    </div>
  )
}
