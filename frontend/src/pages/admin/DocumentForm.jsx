import { useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, FileText, Save, UploadCloud, X } from 'lucide-react'
import { useAdmin } from '../../contexts/useAdmin'
import { Field, inputClass } from '../../components/admin/ui'
import { useI18n } from '../../i18n/useI18n'

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
  { value: 'faq', labelKey: 'admin.docTypes.faq' },
  { value: 'manual', labelKey: 'admin.docTypes.manual' },
  { value: 'guide', labelKey: 'admin.docTypes.guide' },
]

const CATEGORIES = ['Configuration', 'Dépannage', 'Manuels', 'Guides', 'Comptes & Facturation', 'Sécurité']

const LANGUAGES = [
  { value: 'fr', labelKey: 'admin.langs.fr' },
  { value: 'en', labelKey: 'admin.langs.en' },
]

export default function DocumentForm({ basePath = '/admin' }) {
  const navigate = useNavigate()
  const { id } = useParams()
  const { t } = useI18n()
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
        setUploadError(`${t('admin.documents.uploadTypeError', { name: file.name })}`)
        continue
      }
      if (file.size > MAX_FILE_SIZE) {
        setUploadError(`${t('admin.documents.uploadSizeError', { name: file.name })}`)
        continue
      }
      if (attachments.length >= MAX_FILES) {
        setUploadError(`${t('admin.documents.uploadMaxError', { max: MAX_FILES })}`)
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
    if (!formData.title.trim()) errs.title = t('admin.documents.titleRequired')
    if (!formData.category) errs.category = t('admin.documents.categoryRequired')
    if (!formData.content.trim()) errs.content = t('admin.documents.contentRequired')
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
        .map((tag) => tag.trim())
        .filter(Boolean),
    }

    if (isEdit) {
      updateDocument(id, payload)
      navigate(`${basePath}/documents`, {
        state: { toast: { message: t('admin.documents.updated', { title: payload.title }) } },
      })
    } else {
      createDocument(payload)
      navigate(`${basePath}/documents`, {
        state: { toast: { message: t('admin.documents.created', { title: payload.title }) } },
      })
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <button
        onClick={() => navigate(`${basePath}/documents`)}
        className="inline-flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-blue-600 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        {t('admin.documents.backToList')}
      </button>

      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
          {isEdit ? t('admin.documents.editTitle') : t('admin.documents.newDocument')}
        </h1>
        <p className="text-slate-500">
          {isEdit
            ? t('admin.documents.editSubtitle')
            : t('admin.documents.createSubtitle')}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-slate-200 custom-shadow overflow-hidden">
        <div className="p-6 space-y-5">
          <Field label={t('admin.documents.title')} required error={errors.title}>
            <input
              type="text"
              value={formData.title}
              onChange={(e) => handleChange('title', e.target.value)}
              placeholder={t('admin.documents.titlePlaceholder')}
              className={inputClass}
            />
          </Field>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <Field label={t('admin.documents.docType')} required>
              <div className="grid grid-cols-3 gap-2">
                {DOC_TYPES.map((dt) => (
                  <button
                    key={dt.value}
                    type="button"
                    onClick={() => handleChange('type', dt.value)}
                    className={`px-3 py-2.5 rounded-xl text-xs font-bold border transition-all ${
                      formData.type === dt.value
                        ? 'bg-blue-50 text-blue-600 border-blue-200 ring-2 ring-offset-1 ring-blue-500'
                        : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                    }`}
                  >
                    {t(dt.labelKey)}
                  </button>
                ))}
              </div>
            </Field>

            <Field label={t('tf.category')} required error={errors.category}>
              <select
                value={formData.category}
                onChange={(e) => handleChange('category', e.target.value)}
                className={`${inputClass} cursor-pointer`}
              >
                <option value="">{t('common.select')}</option>
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {t(`admin.docCategories.${c}`)}
                  </option>
                ))}
              </select>
            </Field>

            <Field label={t('admin.documents.language')}>
              <select
                value={formData.language}
                onChange={(e) => handleChange('language', e.target.value)}
                className={`${inputClass} cursor-pointer`}
              >
                {LANGUAGES.map((l) => (
                  <option key={l.value} value={l.value}>
                    {t(l.labelKey)}
                  </option>
                ))}
              </select>
            </Field>

            <Field label={t('common.statu')}>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { value: 'published', labelKey: 'admin.documents.publishedSingle' },
                  { value: 'draft', labelKey: 'admin.documents.draftSingle' },
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
                    {t(s.labelKey)}
                  </button>
                ))}
              </div>
            </Field>
          </div>

          <Field label={t('admin.documents.content')} required error={errors.content}>
            <textarea
              value={formData.content}
              onChange={(e) => handleChange('content', e.target.value)}
              placeholder={t('admin.documents.contentPlaceholder')}
              rows={8}
              className={`${inputClass} resize-none leading-relaxed`}
            />
          </Field>

          <Field label={t('admin.documents.tags')} hint={t('admin.documents.tagsHint')}>
            <input
              type="text"
              value={formData.tags}
              onChange={(e) => handleChange('tags', e.target.value)}
              placeholder={t('admin.documents.tagsPlaceholder')}
              className={inputClass}
            />
          </Field>

          <Field
            label={t('admin.documents.attachments')}
            hint={t('admin.documents.attachmentsHint')}
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
                {t('admin.documents.drop')}{' '}
                <span className="text-blue-600">{t('admin.documents.browse')}</span>
              </p>
              <p className="text-xs text-slate-400">
                {t('admin.documents.uploadHint')}
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
                      title={t('admin.documents.removeFile')}
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
            onClick={() => navigate(`${basePath}/documents`)}
            className="px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
          >
            {t('common.cancel')}
          </button>
          <button
            type="submit"
            className="inline-flex items-center gap-2 px-5 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl transition-colors shadow-lg shadow-blue-500/20"
          >
            <Save className="w-4 h-4" />
            {isEdit ? t('tf.submitEdit') : t('admin.documents.create')}
          </button>
        </div>
      </form>
    </div>
  )
}
