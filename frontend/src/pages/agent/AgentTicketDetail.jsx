import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  User,
  Calendar,
  Clock,
  Paperclip,
  Circle,
  Check,
  AlertTriangle,
  ArrowUpCircle,
  Pencil
} from 'lucide-react'
import { useTickets } from '../../contexts/useTickets'
import { useAuth } from '../../contexts/useAuth'
import StatusBadge from '../../components/tickets/StatusBadge'
import PriorityBadge from '../../components/tickets/PriorityBadge'
import CategoryBadge from '../../components/tickets/CategoryBadge'
import { STATUSES, STATUS_ORDER } from '../../components/tickets/constants'
import StatusSelect from '../../components/tickets/StatusSelect'
import { canEditTicketStatus } from '../../components/tickets/permissions'
import { toastService } from '../../services/toast'

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: 'long',
    year: 'numeric'
  })
}

function StatusTimeline({ status }) {
  const step = STATUSES[status]?.step ?? 0
  return (
    <div className="flex items-center w-full">
      {STATUS_ORDER.map((s, idx) => {
        const meta = STATUSES[s]
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
                {meta.label}
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

function AgentTicketDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { getTicket, updateTicket } = useTickets()
  const { user } = useAuth()

  const [savingStatus, setSavingStatus] = useState(false)

  const ticket = getTicket(id)
  const assigneeName = !ticket?.assigneeId && !ticket?.assignee_id
    ? user?.name
    : String(ticket?.assigneeId || ticket?.assignee_id) === String(user?.id)
    ? user?.name
    : ticket?.assignee
  const canEditTicket = ['chatbot', 'responsable_sav'].includes(ticket?.source || ticket?.creation_source || ticket?.origin)
  const canEditStatus = canEditTicketStatus(ticket, user)

  if (!ticket) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
        <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mb-4">
          <AlertTriangle className="w-8 h-8 text-slate-300" />
        </div>
        <h2 className="text-lg font-bold text-slate-900 mb-1">Ticket introuvable</h2>
        <p className="text-sm text-slate-500 mb-6">Ce ticket n'existe pas ou a été supprimé.</p>
        <button
          onClick={() => navigate('/agent/tickets')}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl transition-colors"
        >
          Retour à la liste
        </button>
      </div>
    )
  }

  const handleStatusChange = async (newStatus) => {
    if (!canEditStatus || newStatus === ticket.status) return
    setSavingStatus(true)
    try {
      await updateTicket(ticket.id, { status: newStatus })
      toastService.success(`Le statut du ticket #${ticket.id} est maintenant « ${STATUSES[newStatus].label} ».`)
    } catch (error) {
      const messages = {
        403: 'Vous n’avez pas le droit de modifier le statut de ce ticket.',
        404: 'Ticket introuvable ou non visible.',
        422: 'Le statut sélectionné est invalide.',
      }
      toastService.error(messages[error.status] || error.message || 'Impossible de modifier le statut.')
    } finally {
      setSavingStatus(false)
    }
  }

  return (
    <div className="flex-1 overflow-y-auto p-8">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Back link */}
        <button
          onClick={() => navigate('/agent/tickets')}
          className="inline-flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-blue-600 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Retour à mes tickets
        </button>

        {/* Header card */}
        <div className="bg-white rounded-2xl border border-slate-200 custom-shadow overflow-hidden">
          <div className="p-6 border-b border-slate-100">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3 mb-3 flex-wrap">
                  <span className="text-xs font-bold text-slate-400">#{ticket.id}</span>
                  <StatusBadge status={ticket.status} />
                  <PriorityBadge priority={ticket.priority} />
                  <CategoryBadge category={ticket.category} />
                </div>
                <h1 className="text-xl font-bold text-slate-900 leading-tight">{ticket.title}</h1>
              </div>
              {canEditTicket && (
                <button
                  onClick={() => navigate(`/agent/tickets/${ticket.id}/edit`)}
                  className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl transition-colors shadow-lg shadow-blue-500/20"
                >
                  <Pencil className="w-4 h-4" />
                  Modifier
                </button>
              )}
            </div>

            <div className="mt-5">
              <StatusTimeline status={ticket.status} />
            </div>

            <div className="mt-5 pt-5 border-t border-slate-100 flex items-center justify-between gap-4 flex-wrap">
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <span className="font-semibold text-slate-600">Statut actuel :</span>
                <StatusBadge status={ticket.status} />
              </div>
              {canEditStatus && (
                <div className="w-full max-w-xs">
                  <StatusSelect
                    value={ticket.status}
                    onChange={handleStatusChange}
                    disabled={savingStatus}
                    allowedStatuses={['open', 'in_progress', 'resolved', 'closed']}
                  />
                </div>
              )}
            </div>
          </div>

          {/* Metadata */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-slate-100">
            <div className="bg-white p-5">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Assigné à</p>
              <div className="flex items-center gap-2">
                <User className="w-3.5 h-3.5 text-slate-400" />
                <span className="text-sm font-semibold text-slate-800 truncate">{assigneeName || 'Non assigné'}</span>
              </div>
            </div>
            <div className="bg-white p-5">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Créé par</p>
              <div className="flex items-center gap-2">
                <User className="w-3.5 h-3.5 text-slate-400" />
                <span className="text-sm font-semibold text-slate-800 truncate">
                  {ticket.source === 'responsable_sav'
                    ? 'Responsable SAV'
                    : ticket.source === 'chatbot'
                      ? 'Chatbot'
                      : ticket.createdBy?.name || 'AI Chatbot'}
                </span>
              </div>
            </div>
            <div className="bg-white p-5">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Créé le</p>
              <div className="flex items-center gap-2">
                <Calendar className="w-3.5 h-3.5 text-slate-400" />
                <span className="text-sm font-semibold text-slate-800">{formatDate(ticket.createdAt)}</span>
              </div>
            </div>
            <div className="bg-white p-5">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Dernière activité</p>
              <div className="flex items-center gap-2">
                <Clock className="w-3.5 h-3.5 text-slate-400" />
                <span className="text-sm font-semibold text-slate-800">{formatDate(ticket.updatedAt || ticket.createdAt)}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Escalation reason (if escalated) */}
        {ticket.status === 'escalated' && ticket.escalationReason && (
          <div className="bg-red-50 border border-red-200 rounded-2xl p-5">
            <div className="flex items-start gap-3">
              <ArrowUpCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
              <div>
                <h3 className="text-sm font-bold text-red-800 mb-1">Raison de l'escalade</h3>
                <p className="text-sm text-red-700">{ticket.escalationReason}</p>
              </div>
            </div>
          </div>
        )}

        {/* Description */}
        <div className="bg-white rounded-2xl border border-slate-200 custom-shadow p-6">
          <h2 className="text-sm font-bold text-slate-900 mb-3">Description</h2>
          <p className="text-sm text-slate-700 leading-relaxed">{ticket.description}</p>

          {ticket.attachments?.length > 0 && (
            <div className="mt-5 pt-5 border-t border-slate-100">
              <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-3">
                Pièces jointes ({ticket.attachments.length})
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

      </div>

    </div>
  )
}

export default AgentTicketDetail
