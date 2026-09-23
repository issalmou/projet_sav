import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  Plus,
  Search,
  BookOpen,
  FileText,
  Eye,
  Pencil,
  Trash2,
  ChevronDown,
  Globe,
  Paperclip,
  RefreshCw,
} from 'lucide-react'
import { useAdmin } from '../../contexts/useAdmin'
import {
  PageHeader,
  EmptyState,
  ConfirmModal,
} from '../../components/admin/ui'
import { useToast } from '../../services/toast'
import { DocTypeBadge, DocStatusBadge } from '../../components/admin/badges'
import { useI18n } from '../../i18n/useI18n'

const PAGE_SIZE = 8

const DOC_TYPES = [
  { value: 'faq', labelKey: 'admin.docTypes.faq' },
  { value: 'manual', labelKey: 'admin.docTypes.manual' },
  { value: 'guide', labelKey: 'admin.docTypes.guide' },
]

const LANGUAGES = [
  { value: 'fr', labelKey: 'admin.langs.fr' },
  { value: 'en', labelKey: 'admin.langs.en' },
]

function StatCard({ icon: Icon, label, value, color }) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5 custom-shadow">
      <div className="flex items-start justify-between mb-3">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${color}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
      <p className="text-2xl font-bold text-slate-900">{value}</p>
      <p className="text-xs text-slate-500 mt-1">{label}</p>
    </div>
  )
}

function AdminDocuments({ basePath = '/admin' }) {
  const navigate = useNavigate()
  const location = useLocation()
  const { t, formatDate } = useI18n()
  const { documents, deleteDocument } = useAdmin()
  const { toastEl, showToast } = useToast()

  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [page, setPage] = useState(1)
  const [deleteTarget, setDeleteTarget] = useState(null)

  useEffect(() => {
    const state = location.state
    if (state?.toast) {
      showToast(state.toast.message, state.toast.type)
      window.history.replaceState({}, '')
    }
  }, [location.state, showToast])

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase()
    return documents
      .filter((d) => {
        const matchSearch =
          !query ||
          d.title.toLowerCase().includes(query) ||
          d.category.toLowerCase().includes(query) ||
          d.content.toLowerCase().includes(query)
        const matchType = typeFilter === 'all' || d.type === typeFilter
        const matchStatus = statusFilter === 'all' || d.status === statusFilter
        return matchSearch && matchType && matchStatus
      })
      .sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt))
  }, [documents, search, typeFilter, statusFilter])

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const currentPage = Math.min(page, pageCount)
  const visible = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)

  const resetFilters = () => {
    setSearch('')
    setTypeFilter('all')
    setStatusFilter('all')
    setPage(1)
  }

  const totalViews = documents.reduce((sum, d) => sum + (d.views || 0), 0)

  return (
    <div className="space-y-8">
<PageHeader
        title={t('admin.nav.documents')}
        subtitle={t('admin.documents.subtitle')}
        actions={
          <button
            onClick={() => navigate(`${basePath}/documents/new`)}
            className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl shadow-lg shadow-blue-500/20 flex items-center gap-2 transition-all active:scale-[0.98]"
          >
            <Plus className="w-5 h-5" />
            {t('admin.documents.newDocument')}
          </button>
        }
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard icon={BookOpen} label={t('admin.documents.total')} value={documents.length} color="bg-blue-50 text-blue-600" />
        <StatCard icon={FileText} label={t('admin.documents.published')} value={documents.filter((d) => d.status === 'published').length} color="bg-teal-50 text-teal-600" />
        <StatCard icon={FileText} label={t('admin.documents.drafts')} value={documents.filter((d) => d.status === 'draft').length} color="bg-amber-50 text-amber-600" />
        <StatCard icon={Eye} label={t('admin.documents.totalViews')} value={totalViews} color="bg-violet-50 text-violet-600" />
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 custom-shadow">
        <div className="p-4 flex items-center gap-3 border-b border-slate-100">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value)
                setPage(1)
              }}
              placeholder={t('admin.documents.search')}
              className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
            />
          </div>

          <div className="relative">
            <select
              value={typeFilter}
              onChange={(e) => {
                setTypeFilter(e.target.value)
                setPage(1)
              }}
              className="appearance-none pl-3 pr-9 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/20 cursor-pointer"
            >
              <option value="all">{t('admin.documents.allTypes')}</option>
              {DOC_TYPES.map((dt) => (
                <option key={dt.value} value={dt.value}>
                  {t(dt.labelKey)}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
          </div>

          <div className="relative">
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value)
                setPage(1)
              }}
              className="appearance-none pl-3 pr-9 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/20 cursor-pointer"
            >
              <option value="all">{t('admin.documents.allStatuses')}</option>
              <option value="published">{t('admin.documents.published')}</option>
              <option value="draft">{t('admin.documents.drafts')}</option>
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
          </div>

          <button
            onClick={resetFilters}
            title={t('admin.documents.resetFilters')}
            className="p-2.5 bg-slate-50 border border-slate-200 text-slate-500 hover:bg-slate-100 rounded-xl transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

<div className="px-5 py-3 flex items-center gap-4 text-[10px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-100">
          <span className="flex-1">{t('admin.documents.title')}</span>
          <span className="shrink-0 w-20">{t('admin.documents.type')}</span>
          <span className="hidden lg:inline shrink-0 w-28">{t('common.category')}</span>
          <span className="hidden md:inline shrink-0 w-16 text-center">{t('admin.documents.language')}</span>
          <span className="shrink-0 w-16 text-center">{t('admin.documents.views')}</span>
          <span className="hidden sm:inline shrink-0 w-24">{t('common.statu')}</span>
          <span className="shrink-0 w-20 text-center">{t('admin.documents.actions')}</span>
        </div>

        {filtered.length === 0 ? (
          <EmptyState
            icon={BookOpen}
            title={t('admin.documents.none')}
            message={
              documents.length === 0
                ? t('admin.documents.empty')
                : t('admin.documents.emptyFiltered')
            }
            action={
              documents.length === 0 && (
                <button
                  onClick={() => navigate(`${basePath}/documents/new`)}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-xl transition-colors"
                >
                  {t('admin.documents.create')}
                </button>
              )
            }
          />
        ) : (
          visible.map((d) => (
            <div
              key={d.id}
              className="group flex items-center gap-4 px-5 py-4 border-b border-slate-100 hover:bg-slate-50 transition-colors"
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm font-bold text-slate-900 truncate group-hover:text-blue-600 transition-colors">
                  {d.title}
                </p>
<p className="text-xs text-slate-400 mt-0.5 flex items-center gap-1">
                  {t('admin.documents.updatedOn', { date: formatDate(d.updatedAt) })}
                  {d.attachments?.length > 0 && (
                    <span className="inline-flex items-center gap-1 text-blue-500 font-semibold">
                      <Paperclip className="w-3 h-3" />
                      {d.attachments.length}
                    </span>
                  )}
                </p>
              </div>
              <div className="shrink-0 w-20">
                <DocTypeBadge type={d.type} />
              </div>
              <div className="hidden lg:inline shrink-0 w-28 text-xs text-slate-500">{t(`admin.docCategories.${d.category}`)}</div>
              <div className="hidden md:inline shrink-0 w-16 flex items-center justify-center gap-1 text-xs text-slate-500">
                <Globe className="w-3 h-3 text-slate-400" />
                {LANGUAGES.find((l) => l.value === d.language)?.labelKey
                  ? t(LANGUAGES.find((l) => l.value === d.language).labelKey)
                  : d.language}
              </div>
              <div className="shrink-0 w-16 text-center text-xs text-slate-500">
                {d.views || 0}
              </div>
              <div className="hidden sm:inline shrink-0 w-24">
                <DocStatusBadge status={d.status} />
              </div>
              <div className="shrink-0 w-20 flex items-center justify-end gap-1">
                <button
                  onClick={() => navigate(`${basePath}/documents/${d.id}/edit`)}
                  title={t('admin.documents.edit')}
                  className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                >
                  <Pencil className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setDeleteTarget(d)}
                  title={t('admin.documents.delete')}
                  className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {filtered.length > 0 && (
        <div className="flex items-center justify-between">
          <p className="text-xs text-slate-500">
            {t('admin.documents.showing', {
              from: (currentPage - 1) * PAGE_SIZE + 1,
              to: Math.min(currentPage * PAGE_SIZE, filtered.length),
              total: filtered.length,
            })}
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(currentPage - 1)}
              disabled={currentPage === 1}
              className="px-3 py-1.5 text-xs font-semibold text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {t('tickets.previous')}
            </button>
            {Array.from({ length: pageCount }, (_, i) => i + 1).map((p) => (
              <button
                key={p}
                onClick={() => setPage(p)}
                className={`w-8 h-8 text-xs font-semibold rounded-lg transition-colors ${
                  p === currentPage
                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20'
                    : 'text-slate-600 bg-white border border-slate-200 hover:bg-slate-50'
                }`}
              >
                {p}
              </button>
            ))}
            <button
              onClick={() => setPage(currentPage + 1)}
              disabled={currentPage === pageCount}
              className="px-3 py-1.5 text-xs font-semibold text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {t('tickets.next')}
            </button>
          </div>
        </div>
      )}

      <ConfirmModal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title={t('admin.documents.deleteTitle')}
        message={
          deleteTarget
            ? t('admin.documents.deleteMsg', { title: deleteTarget.title })
            : ''
        }
        onConfirm={() => {
          deleteDocument(deleteTarget.id)
          showToast(t('admin.documents.deleted'))
        }}
      />

      {toastEl}
    </div>
  )
}

export default AdminDocuments
