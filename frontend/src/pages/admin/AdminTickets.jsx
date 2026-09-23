import { useMemo, useState } from 'react'
import { Search, Ticket, User, Calendar, ChevronRight, Plus } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useTickets } from '../../contexts/useTickets'
import { STATUSES } from '../../components/tickets/constants'
import StatusBadge from '../../components/tickets/StatusBadge'
import PriorityBadge from '../../components/tickets/PriorityBadge'
import { toastService } from '../../services/toast'
import { useI18n } from '../../i18n/useI18n'

const ADMIN_STATUSES = ['open', 'in_progress', 'resolved', 'closed']

function AdminTickets() {
  const { t, formatDate } = useI18n()
  const { tickets, updateTicket, error } = useTickets()
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [savingId, setSavingId] = useState(null)

  const visibleTickets = useMemo(() => {
    const query = search.trim().toLowerCase()
    return tickets.filter((ticket) => {
      const matchesSearch = !query || [ticket.id, ticket.title, ticket.description, ticket.createdBy?.name, ticket.createdBy?.email]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(query))
      return matchesSearch && (statusFilter === 'all' || ticket.status === statusFilter)
    })
  }, [tickets, search, statusFilter])

  const changeStatus = async (ticket, status) => {
    if (ticket.status === status) return
    setSavingId(ticket.id)
    try {
      await updateTicket(ticket.id, { status })
      toastService.success(t('admin.tickets.statusToast', { id: ticket.id, status: STATUSES[status].label }))
    } catch (err) {
      toastService.error(err.message || t('td.errStatusDefault'))
    } finally {
      setSavingId(null)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-bold uppercase tracking-widest text-blue-600">{t('admin.tickets.supportCenter')}</p>
        <div className="flex items-start justify-between gap-4 mt-1">
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-slate-900">{t('admin.tickets.title')}</h2>
            <p className="text-slate-500 mt-1">{t('admin.tickets.subtitle')}</p>
          </div>
          <div className="flex items-center gap-3">
          <button onClick={() => navigate('/admin/tickets/new')} className="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl transition-colors">
            <Plus className="w-4 h-4" /> {t('tickets.newTicket')}
          </button>
        </div>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {ADMIN_STATUSES.map((status) => (
          <button key={status} onClick={() => setStatusFilter(status === statusFilter ? 'all' : status)} className={`bg-white rounded-2xl border p-4 text-left custom-shadow transition-colors ${statusFilter === status ? 'border-blue-400 ring-2 ring-blue-100' : 'border-slate-200 hover:border-slate-300'}`}>
            <p className="text-2xl font-bold text-slate-900">{tickets.filter((ticket) => ticket.status === status).length}</p>
            <p className="text-xs text-slate-500 mt-1">{STATUSES[status].label}</p>
          </button>
        ))}
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 custom-shadow overflow-hidden">
        <div className="p-4 flex flex-col sm:flex-row gap-3 border-b border-slate-100">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder={t('admin.tickets.search')} className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
          </div>
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} className="px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/20">
            <option value="all">{t('admin.tickets.allStatuses')}</option>
            {ADMIN_STATUSES.map((status) => <option key={status} value={status}>{STATUSES[status].label}</option>)}
          </select>
        </div>

        {error && <div className="px-5 py-3 text-sm text-red-700 bg-red-50 border-b border-red-100">{error}</div>}
        {visibleTickets.length === 0 ? (
          <div className="py-16 text-center">
            <Ticket className="w-10 h-10 mx-auto text-slate-300" />
            <p className="mt-3 text-sm font-semibold text-slate-700">{t('tickets.none')}</p>
            <p className="text-xs text-slate-400 mt-1">{t('admin.tickets.emptyHint')}</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {visibleTickets.map((ticket) => (
              <div
                key={ticket.id}
                role="button"
                tabIndex={0}
                onClick={() => navigate(`/admin/tickets/${ticket.id}`)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault()
                    navigate(`/admin/tickets/${ticket.id}`)
                  }
                }}
                className="p-5 flex flex-col lg:flex-row lg:items-center gap-4 hover:bg-slate-50/70 cursor-pointer"
              >
                <div className="flex items-start gap-3 flex-1 min-w-0">
                  <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center shrink-0"><Ticket className="w-5 h-5" /></div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2"><span className="text-xs font-bold text-slate-400">#{ticket.id}</span><PriorityBadge priority={ticket.priority} /></div>
                    <h3 className="font-bold text-slate-900 truncate mt-1">{ticket.title}</h3>
                    <p className="text-xs text-slate-500 truncate mt-0.5">{ticket.description}</p>
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 lg:w-56">
                  <span className="inline-flex items-center gap-1"><User className="w-3.5 h-3.5" />{ticket.createdBy?.name || ticket.createdBy?.email || t('admin.tickets.unknownRequester')}</span>
                  <span className="inline-flex items-center gap-1"><Calendar className="w-3.5 h-3.5" />{formatDate(ticket.createdAt)}</span>
                </div>
                <div className="flex items-center gap-3 lg:w-44 lg:justify-end">
                  <StatusBadge status={ticket.status} />
                  <select aria-label={t('admin.tickets.changeStatusAria', { id: ticket.id })} value={ADMIN_STATUSES.includes(ticket.status) ? ticket.status : 'open'} disabled={savingId === ticket.id} onClick={(event) => event.stopPropagation()} onChange={(event) => { event.stopPropagation(); changeStatus(ticket, event.target.value) }} className="min-w-28 px-2.5 py-2 bg-white border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 disabled:opacity-60">
                    {ADMIN_STATUSES.map((status) => <option key={status} value={status}>{STATUSES[status].label}</option>)}
                  </select>
                  <ChevronRight className="w-4 h-4 text-slate-300 shrink-0" />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default AdminTickets
