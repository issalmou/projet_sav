import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  User,
  Calendar,
  Clock,
  Paperclip,
  Send,
  MessageSquare,
  CheckCircle2,
  RotateCcw,
  Circle,
  Check,
  Timer,
  AlertTriangle,
  ArrowUpCircle,
  X
} from 'lucide-react'
import { useTickets } from '../../contexts/useTickets'
import { useAuth } from '../../contexts/useAuth'
import StatusBadge from '../../components/tickets/StatusBadge'
import PriorityBadge from '../../components/tickets/PriorityBadge'
import CategoryBadge from '../../components/tickets/CategoryBadge'
import { STATUSES, STATUS_ORDER } from '../../components/tickets/constants'

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: 'long',
    year: 'numeric'
  })
}

function formatTime(iso) {
  return new Date(iso).toLocaleString('fr-FR', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit'
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

function AgentStatusActions({ status, onChange, onEscalate }) {
  const actions = {
    open: [
      { to: 'in_progress', label: 'Prendre en charge', icon: Timer, style: 'bg-amber-50 text-amber-700 border-amber-200 hover:bg-amber-100' },
      { to: 'escalated', label: 'Escalader', icon: ArrowUpCircle, style: 'bg-red-50 text-red-700 border-red-200 hover:bg-red-100' }
    ],
    in_progress: [
      { to: 'resolved', label: 'Marquer résolu', icon: CheckCircle2, style: 'bg-teal-50 text-teal-700 border-teal-200 hover:bg-teal-100' },
      { to: 'escalated', label: 'Escalader', icon: ArrowUpCircle, style: 'bg-red-50 text-red-700 border-red-200 hover:bg-red-100' },
      { to: 'closed', label: 'Fermer', icon: X, style: 'bg-slate-100 text-slate-600 border-slate-200 hover:bg-slate-200' }
    ],
    escalated: [
      { to: 'in_progress', label: 'Reprendre', icon: Timer, style: 'bg-amber-50 text-amber-700 border-amber-200 hover:bg-amber-100' },
      { to: 'resolved', label: 'Marquer résolu', icon: CheckCircle2, style: 'bg-teal-50 text-teal-700 border-teal-200 hover:bg-teal-100' }
    ],
    resolved: [
      { to: 'closed', label: 'Fermer', icon: X, style: 'bg-slate-100 text-slate-600 border-slate-200 hover:bg-slate-200' },
      { to: 'in_progress', label: ' rouvrir', icon: RotateCcw, style: 'bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100' }
    ],
    closed: [
      { to: 'in_progress', label: 'Rouvrir', icon: RotateCcw, style: 'bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100' }
    ]
  }

  return (
    <div className="flex items-center gap-2 flex-wrap">
      {(actions[status] || []).map((a) => {
        const Icon = a.icon
        return (
          <button
            key={a.to}
            onClick={() => a.to === 'escalated' ? onEscalate() : onChange(a.to)}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-colors ${a.style}`}
          >
            <Icon className="w-3.5 h-3.5" />
            {a.label}
          </button>
        )
      })}
    </div>
  )
}

function MessageBubble({ message, isClient }) {
  return (
    <div className={`flex items-start gap-3 ${isClient ? 'flex-row-reverse' : ''}`}>
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white shrink-0 ${
          isClient ? 'bg-slate-800' : 'bg-blue-600'
        }`}
      >
        {message.author?.charAt(0)?.toUpperCase() || '?'}
      </div>
      <div className={`max-w-[75%] ${isClient ? 'items-end' : ''}`}>
        <div
          className={`px-4 py-3 rounded-2xl ${
            isClient
              ? 'bg-blue-600 text-white rounded-tr-md'
              : 'bg-white border border-slate-200 text-slate-800 rounded-tl-md custom-shadow'
          }`}
        >
          <p className="text-xs font-semibold mb-1 opacity-80">{message.author}</p>
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
        </div>
        <p className={`text-[10px] text-slate-400 mt-1 font-medium ${isClient ? 'text-right' : ''}`}>
          {formatTime(message.createdAt)}
        </p>
      </div>
    </div>
  )
}

function AgentTicketDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { getTicket, updateTicket, addMessage } = useTickets()
  const { user } = useAuth()

  const [reply, setReply] = useState('')
  const [showEscalateModal, setShowEscalateModal] = useState(false)
  const [escalationReason, setEscalationReason] = useState('')

  const ticket = getTicket(id)

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

  const messages = [...(ticket.messages || [])].sort(
    (a, b) => new Date(a.createdAt) - new Date(b.createdAt)
  )

  const handleStatusChange = (newStatus) => {
    updateTicket(ticket.id, { status: newStatus })
  }

  const handleEscalate = () => {
    setShowEscalateModal(true)
  }

  const confirmEscalation = () => {
    updateTicket(ticket.id, { 
      status: 'escalated',
      escalationReason: escalationReason || 'Escaladé par agent support'
    })
    addMessage(ticket.id, {
      author: user?.name || 'Agent',
      role: 'agent',
      content: `Ticket escaladé au responsable SAV.\n\nRaison: ${escalationReason || 'Non spécifiée'}`
    })
    setShowEscalateModal(false)
    setEscalationReason('')
  }

  const handleSendReply = () => {
    const content = reply.trim()
    if (!content) return
    addMessage(ticket.id, { author: user?.name || 'Agent', role: 'agent', content })
    setReply('')
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
            </div>

            <div className="mt-5">
              <StatusTimeline status={ticket.status} />
            </div>

            <div className="mt-5 pt-5 border-t border-slate-100 flex items-center justify-between gap-4 flex-wrap">
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <span className="font-semibold text-slate-600">Statut actuel :</span>
                <StatusBadge status={ticket.status} />
              </div>
              <AgentStatusActions 
                status={ticket.status} 
                onChange={handleStatusChange}
                onEscalate={handleEscalate}
              />
            </div>
          </div>

          {/* Metadata */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-slate-100">
            <div className="bg-white p-5">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Assigné à</p>
              <div className="flex items-center gap-2">
                <User className="w-3.5 h-3.5 text-slate-400" />
                <span className="text-sm font-semibold text-slate-800 truncate">{ticket.assignee}</span>
              </div>
            </div>
            <div className="bg-white p-5">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Créé par</p>
              <div className="flex items-center gap-2">
                <User className="w-3.5 h-3.5 text-slate-400" />
                <span className="text-sm font-semibold text-slate-800 truncate">
                  {ticket.createdBy?.name || 'AI Chatbot'}
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

        {/* Messages */}
        <div className="bg-white rounded-2xl border border-slate-200 custom-shadow">
          <div className="p-6 border-b border-slate-100">
            <h2 className="text-sm font-bold text-slate-900">Conversation</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              {messages.length === 0
                ? "Aucun message pour le moment."
                : `Historique des échanges (${messages.length}).`}
            </p>
          </div>

          <div className="p-6 space-y-6 max-h-[480px] overflow-y-auto bg-slate-50/50">
            {messages.length === 0 && (
              <div className="text-center py-8">
                <MessageSquare className="w-10 h-10 text-slate-300 mx-auto mb-3" />
                <p className="text-xs text-slate-500">
                  Aucun échange pour le moment. Rédigez une réponse ci-dessous.
                </p>
              </div>
            )}
            {messages.map((m) => (
              <MessageBubble key={m.id} message={m} isClient={m.role === 'client'} />
            ))}
          </div>

          {/* Reply box */}
          <div className="p-5 border-t border-slate-100">
            <div className="flex items-end gap-3">
              <textarea
                value={reply}
                onChange={(e) => setReply(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    handleSendReply()
                  }
                }}
                rows={2}
                placeholder="Rédigez une réponse au client..."
                className="flex-1 px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all resize-none"
              />
              <button
                onClick={handleSendReply}
                disabled={!reply.trim()}
                className={`p-3 rounded-xl transition-all ${
                  reply.trim()
                    ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-lg shadow-blue-500/20 active:scale-95'
                    : 'bg-slate-200 text-slate-400 cursor-not-allowed'
                }`}
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Escalation Modal */}
      {showEscalateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6">
            <div className="w-12 h-12 bg-red-50 border border-red-200 rounded-xl flex items-center justify-center mb-4">
              <ArrowUpCircle className="w-6 h-6 text-red-500" />
            </div>
            <h3 className="text-base font-bold text-slate-900 mb-1">Escalader le ticket ?</h3>
            <p className="text-sm text-slate-500 mb-4">
              Ce ticket sera transmis au responsable SAV pour une prise en charge supérieure.
            </p>
            <div className="mb-4">
              <label className="text-xs font-semibold text-slate-600 mb-2 block">
                Raison de l'escalade *
              </label>
              <textarea
                value={escalationReason}
                onChange={(e) => setEscalationReason(e.target.value)}
                rows={3}
                placeholder="Expliquez pourquoi ce ticket doit être escaladé..."
                className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-red-500/20 focus:border-red-500 transition-all resize-none"
              />
            </div>
            <div className="flex items-center justify-end gap-3">
              <button
                onClick={() => {
                  setShowEscalateModal(false)
                  setEscalationReason('')
                }}
                className="px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
              >
                Annuler
              </button>
              <button
                onClick={confirmEscalation}
                disabled={!escalationReason.trim()}
                className="px-4 py-2 text-sm font-semibold text-white bg-red-600 hover:bg-red-700 rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Confirmer l'escalade
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default AgentTicketDetail
