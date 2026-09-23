import { useMemo, useState } from 'react'
import {
  Activity as ActivityIcon,
  Search,
  ChevronDown,
  Download,
  Trash2,
  RefreshCw,
  AlertTriangle,
} from 'lucide-react'
import { useAdmin } from '../../contexts/useAdmin'
import { useAuth } from '../../contexts/useAuth'
import { isAdmin } from '../../contexts/roles'
import {
  PageHeader,
  EmptyState,
  ConfirmModal,
} from '../../components/admin/ui'
import { useToast } from '../../services/toast'
import { SeverityBadge } from '../../components/admin/badges'
import { useI18n } from '../../i18n/useI18n'

const CATEGORIES = [
  { value: 'users', labelKey: 'admin.logs.catUsers' },
  { value: 'tickets', labelKey: 'admin.logs.catTickets' },
  { value: 'products', labelKey: 'admin.logs.catProducts' },
  { value: 'documents', labelKey: 'admin.logs.catDocuments' },
  { value: 'integrations', labelKey: 'admin.logs.catIntegrations' },
  { value: 'settings', labelKey: 'admin.logs.catSettings' },
  { value: 'logs', labelKey: 'admin.logs.catLogs' },
  { value: 'auth', labelKey: 'admin.logs.catAuth' },
]

const PAGE_SIZE = 10

function AdminLogs() {
  const { t, formatDate } = useI18n()
  const { logs, clearLogs } = useAdmin()
  const { user } = useAuth()
  const { toastEl, showToast } = useToast()

  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [severityFilter, setSeverityFilter] = useState('all')
  const [userFilter, setUserFilter] = useState('all')
  const [actionFilter, setActionFilter] = useState('all')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [page, setPage] = useState(1)
  const [confirmClear, setConfirmClear] = useState(false)

  const users = useMemo(() => {
    const set = new Set(logs.map((l) => l.actor).filter(Boolean))
    return [...set].sort((a, b) => a.localeCompare(b, 'fr'))
  }, [logs])

  const actions = useMemo(() => {
    const set = new Set(logs.map((l) => l.action).filter(Boolean))
    return [...set].sort((a, b) => a.localeCompare(b, 'fr'))
  }, [logs])

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase()
    return logs
      .filter((l) => {
        const matchSearch =
          !query ||
          l.details.toLowerCase().includes(query) ||
          l.actor.toLowerCase().includes(query) ||
          l.action.toLowerCase().includes(query) ||
          l.target.toLowerCase().includes(query)
        const matchCategory = categoryFilter === 'all' || l.category === categoryFilter
        const matchSeverity = severityFilter === 'all' || l.severity === severityFilter
        const matchUser = userFilter === 'all' || l.actor === userFilter
        const matchAction = actionFilter === 'all' || l.action === actionFilter
        const matchDate =
          (!dateFrom || new Date(l.createdAt) >= new Date(`${dateFrom}T00:00:00`)) &&
          (!dateTo || new Date(l.createdAt) <= new Date(`${dateTo}T23:59:59.999`))
        return matchSearch && matchCategory && matchSeverity && matchUser && matchAction && matchDate
      })
      .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
  }, [logs, search, categoryFilter, severityFilter, userFilter, actionFilter, dateFrom, dateTo])

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const currentPage = Math.min(page, pageCount)
  const visible = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)

  const resetFilters = () => {
    setSearch('')
    setCategoryFilter('all')
    setSeverityFilter('all')
    setUserFilter('all')
    setActionFilter('all')
    setDateFrom('')
    setDateTo('')
    setPage(1)
  }

  const exportCSV = () => {
    const headers = [
      t('admin.logs.csvDate'),
      t('admin.logs.csvAction'),
      t('admin.logs.csvCategory'),
      t('admin.logs.csvActor'),
      t('admin.logs.csvRole'),
      t('admin.logs.csvTarget'),
      t('admin.logs.csvDetails'),
      t('admin.logs.csvSeverity'),
      'IP',
    ]
    const rows = filtered.map((l) => [
      formatDate(l.createdAt, {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      }),
      l.action,
      l.category,
      `"${l.actor.replace(/"/g, '""')}"`,
      l.actorRole,
      l.target,
      `"${l.details.replace(/"/g, '""')}"`,
      l.severity,
      l.ip,
    ])
    const csv = [headers.join(';'), ...rows.map((r) => r.join(';'))].join('\r\n')
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'logs-activite.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  const criticalCount = logs.filter((l) => l.severity === 'critical').length

  return (
    <div className="space-y-8">
      <PageHeader
        title={t('admin.nav.logs')}
        subtitle={t('admin.logs.subtitle')}
        actions={
          <>
            <button
              onClick={exportCSV}
              disabled={filtered.length === 0}
              className="px-4 py-2.5 bg-slate-50 border border-slate-200 text-slate-600 hover:bg-slate-100 rounded-xl text-sm font-semibold flex items-center gap-2 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Download className="w-4 h-4" />
              {t('admin.logs.exportCsv')}
            </button>
            {isAdmin(user) && (
              <button
                onClick={() => setConfirmClear(true)}
                className="px-4 py-2.5 bg-red-50 border border-red-200 text-red-600 hover:bg-red-100 rounded-xl text-sm font-semibold flex items-center gap-2 transition-colors"
              >
                <Trash2 className="w-4 h-4" />
                {t('admin.logs.clear')}
              </button>
            )}
          </>
        }
      />

      {/* Alert banner if critical events */}
      {criticalCount > 0 && (
        <div className="flex items-center gap-3 px-5 py-4 bg-red-50 border border-red-200 rounded-2xl">
          <AlertTriangle className="w-5 h-5 text-red-600 shrink-0" />
          <p className="text-sm text-red-700">
            <strong className="font-bold">{t('admin.logs.criticalCount', { count: criticalCount })}</strong>{' '}
            {t('admin.logs.criticalText')}
          </p>
        </div>
      )}

      <div className="bg-white rounded-2xl border border-slate-200 custom-shadow">
        <div className="p-4 flex items-center gap-3 flex-wrap border-b border-slate-100">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value)
                setPage(1)
              }}
              placeholder={t('admin.logs.search')}
              className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
            />
          </div>

          <div className="relative">
            <select
              value={categoryFilter}
              onChange={(e) => {
                setCategoryFilter(e.target.value)
                setPage(1)
              }}
              className="appearance-none pl-3 pr-9 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/20 cursor-pointer"
            >
              <option value="all">{t('admin.logs.allCategories')}</option>
              {CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>
                  {t(c.labelKey)}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
          </div>

          <div className="relative">
            <select
              value={severityFilter}
              onChange={(e) => {
                setSeverityFilter(e.target.value)
                setPage(1)
              }}
              className="appearance-none pl-3 pr-9 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/20 cursor-pointer"
            >
              <option value="all">{t('admin.logs.allSeverities')}</option>
              <option value="critical">{t('admin.logs.sevCritical')}</option>
              <option value="warning">{t('admin.logs.sevWarning')}</option>
              <option value="info">{t('admin.logs.sevInfo')}</option>
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
          </div>

          <div className="relative">
            <select
              value={userFilter}
              onChange={(e) => {
                setUserFilter(e.target.value)
                setPage(1)
              }}
              className="appearance-none pl-3 pr-9 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/20 cursor-pointer"
            >
              <option value="all">{t('admin.logs.allUsers')}</option>
              {users.map((u) => (
                <option key={u} value={u}>
                  {u}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
          </div>

          <div className="relative">
            <select
              value={actionFilter}
              onChange={(e) => {
                setActionFilter(e.target.value)
                setPage(1)
              }}
              className="appearance-none pl-3 pr-9 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/20 cursor-pointer"
            >
              <option value="all">{t('admin.logs.allActions')}</option>
              {actions.map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
          </div>

          <input
            type="date"
            value={dateFrom}
            onChange={(e) => {
              setDateFrom(e.target.value)
              setPage(1)
            }}
            title={t('admin.logs.from')}
            className="px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/20 cursor-pointer"
          />

          <input
            type="date"
            value={dateTo}
            onChange={(e) => {
              setDateTo(e.target.value)
              setPage(1)
            }}
            title={t('admin.logs.to')}
            className="px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/20 cursor-pointer"
          />

          <button
            onClick={resetFilters}
            title={t('admin.logs.allCategories')}
            className="p-2.5 bg-slate-50 border border-slate-200 text-slate-500 hover:bg-slate-100 rounded-xl transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        <div className="px-5 py-3 flex items-center gap-4 text-[10px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-100">
          <span className="hidden sm:inline shrink-0 w-32">{t('admin.logs.date')}</span>
          <span className="flex-1">{t('admin.logs.event')}</span>
          <span className="hidden lg:inline shrink-0 w-28">{t('common.category')}</span>
          <span className="shrink-0 w-24">{t('admin.logs.severity')}</span>
          <span className="hidden md:inline shrink-0 w-24">{t('admin.logs.ip')}</span>
        </div>

        {filtered.length === 0 ? (
          <EmptyState
            icon={ActivityIcon}
            title={t('admin.logs.none')}
            message={
              logs.length === 0
                ? t('admin.logs.empty')
                : t('admin.logs.emptyFiltered')
            }
          />
        ) : (
          visible.map((log) => (
            <div
              key={log.id}
              className="px-5 py-4 border-b border-slate-100 hover:bg-slate-50 transition-colors flex items-start gap-4"
            >
              <div className="hidden sm:inline shrink-0 w-32 text-xs text-slate-500 pt-0.5">
                {formatDate(log.createdAt, {
                  day: '2-digit',
                  month: '2-digit',
                  year: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-slate-900">{log.details}</p>
                <div className="flex items-center gap-2 mt-1 flex-wrap">
                  <span className="text-xs text-slate-500">{log.actor}</span>
                  <span className="text-[10px] font-mono text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">
                    {log.action}
                  </span>
                  {log.target && (
                    <span className="text-[10px] font-mono text-slate-400">{t('admin.logs.target', { target: log.target })}</span>
                  )}
                </div>
              </div>
              <div className="hidden lg:inline shrink-0 w-28 text-xs text-slate-500 capitalize">
                {CATEGORIES.find((c) => c.value === log.category)?.labelKey
                  ? t(CATEGORIES.find((c) => c.value === log.category).labelKey)
                  : log.category}
              </div>
              <div className="shrink-0 w-24">
                <SeverityBadge severity={log.severity} />
              </div>
              <div className="hidden md:inline shrink-0 w-24 text-xs font-mono text-slate-400">
                {log.ip}
              </div>
            </div>
          ))
        )}
      </div>

      {filtered.length > 0 && (
        <div className="flex items-center justify-between">
          <p className="text-xs text-slate-500">
            {t('admin.logs.showing', {
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
        open={confirmClear}
        onClose={() => setConfirmClear(false)}
        title={t('admin.logs.clearTitle')}
        message={t('admin.logs.clearMsg')}
        onConfirm={() => {
          clearLogs()
          showToast(t('admin.logs.cleared'))
        }}
      />

      {toastEl}
    </div>
  )
}

export default AdminLogs
