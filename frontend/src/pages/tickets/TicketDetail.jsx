import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  Pencil,
  Trash2,
  User,
  Calendar,
  Clock,
  Paperclip,
  Circle,
  Check,
  AlertTriangle
} from 'lucide-react'
import { useTickets } from '../../contexts/useTickets'
import { useAuth } from '../../contexts/useAuth'
import { useAdmin } from '../../contexts/useAdmin'
import StatusBadge from '../../components/tickets/StatusBadge'
import PriorityBadge from '../../components/tickets/PriorityBadge'
import CategoryBadge from '../../components/tickets/CategoryBadge'
import { STATUSES, STATUS_ORDER } from '../../components/tickets/constants'
import StatusSelect from '../../components/tickets/StatusSelect'
import { canEditTicketStatus } from '../../components/tickets/permissions'
import { toastService } from '../../services/toast'
import { useI18n } from '../../i18n/useI18n'

function StatusTimeline({ status }) {
  const { t } = useI18n()
  const step = STATUSES[status]?.step ?? 0
  return (
    <div className="flex items-center w-full">
      {STATUS_ORDER.map((s, idx) => {
        const done = idx <= step
        const current = idx === step
        const Icon = done ? Check : Circle
        return (
          <div key={s} className="flex items-center flex-1 last:flex-none">
            <div className="flex flex-col items-center">
              <div
                className={`w-9 h-9 rounded-full flex items-center justify-center border-2 transition-colors ${
                  done
                    ? 'bg-blue-600 border-blue-600 text-white'
                    : 'bg-white border-slate-300 text-slate-400'
                } ${current ? 'ring-4 ring-blue-100' : ''}`}
              >
                <Icon className="w-4 h-4" />
              </div>
              <span
                className={`mt-2 text-[10px] font-bold uppercase tracking-wider ${
                  done ? 'text-blue-700' : 'text-slate-400'
                }`}
              >
                {t(`status.${s}`)}
              </span>
            </div>
            {idx < STATUS_ORDER.length - 1 && (
              <div
                className={`flex-1 h-0.5 mx-2 mb-6 rounded-full ${done ? 'bg-blue-600' : 'bg-slate-200'}`}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}

function TicketDetail({ basePath = '/tickets' }) {
  const { id } = useParams()
  const navigate = useNavigate()
  const { getTicket, updateTicket, deleteTicket } = useTickets()
  const { user } = useAuth()
  const { users } = useAdmin()
  const { t, formatDate } = useI18n()

  const [confirmDelete, setConfirmDelete] = useState(false)
  const [savingStatus, setSavingStatus] = useState(false)

  const ticket = getTicket(id)
  const isClient = user?.role === 'client'
  const assignedUser = users.find((item) => String(item.id) === String(ticket?.assigneeId || ticket?.assignee_id))
  const assigneeName = assignedUser?.name || (
    String(ticket?.assigneeId || ticket?.assignee_id) === String(user?.id) ? user?.name : null
  ) || (typeof ticket?.assignee === 'string' && !ticket.assignee.match(/^[0-9a-f-]{20,}$/i) ? ticket.assignee : null)

  if (!ticket) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
        <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mb-4">
          <AlertTriangle className="w-8 h-8 text-slate-300" />
        </div>
        <h2 className="text-lg font-bold text-slate-900 mb-1">{t('td.notFound')}</h2>
        <p className="text-sm text-slate-500 mb-6">{t('td.notFoundMsg')}</p>
        <button
          onClick={() => navigate(basePath)}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl transition-colors"
        >
          {t('common.backToList')}
        </button>
      </div>
    )
  }

  const canEditStatus = canEditTicketStatus(ticket, user)

  const handleStatusChange = async (newStatus) => {
    if (!canEditStatus || newStatus === ticket.status) return
    setSavingStatus(true)
    try {
      await updateTicket(ticket.id, { status: newStatus })
toastService.success(t('td.statusUpdated', { id: ticket.id, status: t(`status.${newStatus}`) }))
    } catch (error) {
      const messages = {
        403: t('td.errStatus403'),
        404: t('td.errStatus404'),
        422: t('td.errStatus422'),
      }
      toastService.error(messages[error.status] || error.message || t('td.errStatusDefault'))
    } finally {
      setSavingStatus(false)
    }
  }

  const handleDelete = () => {
    deleteTicket(ticket.id)
    navigate(basePath)
  }

  return (
    <div className="flex-1 overflow-y-auto p-8">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Back link */}
        <button
          onClick={() => navigate(basePath)}
          className="inline-flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-blue-600 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          {t('td.backToTickets')}
        </button>

        {/* Header card */}
        <div className="bg-white rounded-2xl border border-slate-200 custom-shadow overflow-hidden">
          <div className="p-6 border-b border-slate-100">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3 mb-3 flex-wrap">
                  <span className="text-xs font-bold text-slate-400">#{ticket.id}</span>
                  <StatusBadge status={ticket.status} />
                   {!isClient && <>
                     <PriorityBadge priority={ticket.priority} />
                     <CategoryBadge category={ticket.category} />
                   </>}
                </div>
                <h1 className="text-xl font-bold text-slate-900 leading-tight">{ticket.title}</h1>
              </div>
              {!isClient && (
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => navigate(`${basePath}/${ticket.id}/edit`)}
                    className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl transition-colors shadow-lg shadow-blue-500/20"
                  >
                    <Pencil className="w-4 h-4" />
                    {t('common.modify')}
                  </button>
                  <button
                    onClick={() => setConfirmDelete(true)}
                    className="p-2.5 text-red-500 hover:bg-red-50 border border-red-200 bg-red-50 rounded-xl transition-colors"
                    title={t('common.delete')}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>

            <div className="mt-5">
              <StatusTimeline status={ticket.status} />
            </div>

            <div className="mt-5 pt-5 border-t border-slate-100 flex items-center justify-between gap-4 flex-wrap">
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <span className="font-semibold text-slate-600">{t('td.currentStatus')}</span>
                <StatusBadge status={ticket.status} />
              </div>
              {canEditStatus ? (
                <div className="w-full max-w-xs">
                  <StatusSelect
                    value={ticket.status}
                    onChange={handleStatusChange}
                    disabled={savingStatus}
                    allowedStatuses={['open', 'in_progress', 'resolved', 'closed']}
                  />
                </div>
              ) : null}
            </div>
          </div>

           {/* Metadata */}
           {!isClient && (
             <div className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-slate-100">
            <div className="bg-white p-5">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">{t('td.client')}</p>
              <div className="flex items-center gap-2">
                <User className="w-3.5 h-3.5 text-slate-400" />
                <span className="text-sm font-semibold text-slate-800 truncate">
                  {ticket.client?.full_name || ticket.client?.name || ticket.client?.email || ticket.client_id || '—'}
                </span>
              </div>
            </div>
            <div className="bg-white p-5">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">{t('td.assignee')}</p>
              <div className="flex items-center gap-2">
                <User className="w-3.5 h-3.5 text-slate-400" />
                  <span className="text-sm font-semibold text-slate-800 truncate">{assigneeName || t('common.unassigned')}</span>
              </div>
            </div>
            <div className="bg-white p-5">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">{t('td.createdOn')}</p>
              <div className="flex items-center gap-2">
                <Calendar className="w-3.5 h-3.5 text-slate-400" />
                <span className="text-sm font-semibold text-slate-800">{formatDate(ticket.createdAt)}</span>
              </div>
            </div>
            <div className="bg-white p-5">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">{t('td.lastActivity')}</p>
              <div className="flex items-center gap-2">
                <Clock className="w-3.5 h-3.5 text-slate-400" />
                <span className="text-sm font-semibold text-slate-800">{formatDate(ticket.updatedAt || ticket.createdAt)}</span>
              </div>
            </div>
          </div>
          )}
        </div>

          {/* Description */}
          {!isClient && (
            <div className="bg-white rounded-2xl border border-slate-200 custom-shadow p-6">
          <h2 className="text-sm font-bold text-slate-900 mb-3">{t('td.description')}</h2>
          <p className="text-sm text-slate-700 leading-relaxed">{ticket.description}</p>

          {ticket.attachments?.length > 0 && (
            <div className="mt-5 pt-5 border-t border-slate-100">
              <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-3">
                {t('td.attachments', { count: ticket.attachments.length })}
              </h3>
              <div className="flex flex-wrap gap-2">
                {ticket.attachments.map((att, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-2 px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                  >
                    <Paperclip className="w-4 h-4 text-slate-400" />
                    <span className="text-xs font-semibold text-slate-700">{att.name}</span>
                    <span className="text-[10px] text-slate-400">{att.size}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
             </div>
           )}

{/* Delete confirmation modal */}
      {confirmDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6">
            <div className="w-12 h-12 bg-red-50 border border-red-200 rounded-xl flex items-center justify-center mb-4">
              <Trash2 className="w-6 h-6 text-red-500" />
            </div>
            <h3 className="text-base font-bold text-slate-900 mb-1">{t('td.deleteTitle')}</h3>
            <p className="text-sm text-slate-500 mb-6">
              {t('td.deleteMsg', { id: ticket.id })}
            </p>
            <div className="flex items-center justify-end gap-3">
              <button
                onClick={() => setConfirmDelete(false)}
                className="px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
              >
                {t('common.cancel')}
              </button>
              <button
                onClick={handleDelete}
                className="px-4 py-2 text-sm font-semibold text-white bg-red-600 hover:bg-red-700 rounded-xl transition-colors"
              >
                {t('common.delete')}
              </button>
            </div>
             </div>
           </div>
       )}
       </div>
     </div>
  )
}

export default TicketDetail
