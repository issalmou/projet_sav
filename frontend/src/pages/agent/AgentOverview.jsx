import { useNavigate } from 'react-router-dom'
import {
  Headphones,
  Ticket,
  Clock,
  CheckCircle2,
  AlertTriangle,
  ChevronRight,
  ArrowUpCircle,
  MessageSquare,
  Timer
} from 'lucide-react'
import { useAuth } from '../../contexts/useAuth'
import { useTickets } from '../../contexts/useTickets'
import StatusBadge from '../../components/tickets/StatusBadge'
import PriorityBadge from '../../components/tickets/PriorityBadge'

function StatCard({ icon: Icon, label, value, color, hint }) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5 custom-shadow">
      <div className="flex items-start justify-between mb-3">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${color}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
      <p className="text-2xl font-bold text-slate-900">{value}</p>
      <p className="text-xs text-slate-500 mt-1">{label}</p>
      {hint && <p className="text-[11px] text-slate-400 mt-1">{hint}</p>}
    </div>
  )
}

function formatRelative(iso) {
  if (!iso) return '—'
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return "à l'instant"
  if (mins < 60) return `Il y a ${mins} min`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `Il y a ${hours} h`
  const days = Math.floor(hours / 24)
  return `Il y a ${days} j`
}

function AgentOverview() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { tickets } = useTickets()

  const myTickets = tickets.filter((t) => t.assignee === user?.name || t.assignee === user?.email)
  const allTickets = tickets

  const myOpen = myTickets.filter((t) => t.status === 'open').length
  const myInProgress = myTickets.filter((t) => t.status === 'in_progress').length
  const myResolved = myTickets.filter((t) => t.status === 'resolved' || t.status === 'closed').length
  const myEscalated = myTickets.filter((t) => t.status === 'escalated').length

  const totalOpen = allTickets.filter((t) => t.status === 'open').length
  const totalInProgress = allTickets.filter((t) => t.status === 'in_progress').length

  const recentTickets = allTickets
    .filter((t) => t.status === 'open' || t.status === 'in_progress' || t.status === 'escalated')
    .sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt))
    .slice(0, 5)

  return (
    <div className="space-y-8">
      {/* Welcome banner */}
      <div className="bg-gradient-to-r from-blue-500 via-blue-600 to-indigo-600 rounded-2xl p-6 text-white custom-shadow relative overflow-hidden">
        <div className="absolute -right-8 -bottom-8 opacity-10">
          <Headphones className="w-48 h-48" />
        </div>
        <div className="relative z-10 space-y-3">
          <p className="text-xs font-bold uppercase tracking-widest text-blue-100">Espace Agent Support</p>
          <h2 className="text-xl font-bold">Bonjour, {user?.name?.split(' ')[0] || 'Agent'}</h2>
          <p className="text-sm text-blue-100 max-w-xl leading-relaxed">
            Gérez les tickets qui vous sont assignés. Vous pouvez modifier les statuts et escalader les problèmes complexes vers le responsable SAV.
          </p>
        </div>
      </div>

      {/* My Stats */}
      <div>
        <h3 className="text-sm font-bold text-slate-900 uppercase tracking-widest mb-4">Mes Tickets Assignés</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard
            icon={Ticket}
            label="Total assignés"
            value={myTickets.length}
            hint={`${myOpen + myInProgress} à traiter`}
            color="bg-blue-50 text-blue-600"
          />
          <StatCard
            icon={Clock}
            label="En cours"
            value={myInProgress}
            color="bg-amber-50 text-amber-600"
          />
          <StatCard
            icon={CheckCircle2}
            label="Résolus"
            value={myResolved}
            color="bg-emerald-50 text-emerald-600"
          />
          <StatCard
            icon={ArrowUpCircle}
            label="Escaladés"
            value={myEscalated}
            color="bg-red-50 text-red-600"
          />
        </div>
      </div>

      {/* Queue Stats */}
      <div>
        <h3 className="text-sm font-bold text-slate-900 uppercase tracking-widest mb-4">File d'attente</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          <StatCard
            icon={AlertTriangle}
            label="Tickets ouverts (non assignés)"
            value={totalOpen}
            hint="En attente d'assignation"
            color="bg-orange-50 text-orange-600"
          />
          <StatCard
            icon={Timer}
            label="Tickets en cours (tous agents)"
            value={totalInProgress}
            color="bg-blue-50 text-blue-600"
          />
        </div>
      </div>

      {/* Recent tickets requiring attention */}
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden custom-shadow">
        <div className="p-6 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Ticket className="w-4 h-4 text-slate-400" />
            <h2 className="text-lg font-bold text-slate-900">Tickets à traiter</h2>
          </div>
          <button
            onClick={() => navigate('/agent/tickets')}
            className="text-sm font-semibold text-blue-600 hover:text-blue-700"
          >
            Voir tous
          </button>
        </div>
        {recentTickets.length === 0 ? (
          <p className="p-8 text-center text-sm text-slate-400">Aucun ticket en attente.</p>
        ) : (
          <div className="divide-y divide-slate-50">
            {recentTickets.map((ticket) => (
              <div
                key={ticket.id}
                onClick={() => navigate(`/agent/tickets/${ticket.id}`)}
                className="p-5 flex items-start gap-4 hover:bg-slate-50 transition-colors cursor-pointer group"
              >
                <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${
                  ticket.status === 'escalated' ? 'bg-red-100 text-red-600' :
                  ticket.status === 'in_progress' ? 'bg-amber-100 text-amber-600' :
                  'bg-blue-100 text-blue-600'
                }`}>
                  {ticket.status === 'escalated' ? (
                    <ArrowUpCircle className="w-5 h-5" />
                  ) : ticket.status === 'in_progress' ? (
                    <Timer className="w-5 h-5" />
                  ) : (
                    <Ticket className="w-5 h-5" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-slate-400">#{ticket.id}</span>
                      <h4 className="text-sm font-bold text-slate-900 truncate group-hover:text-blue-600 transition-colors">
                        {ticket.title}
                      </h4>
                    </div>
                    <span className="text-xs text-slate-400 shrink-0 ml-3">
                      {formatRelative(ticket.updatedAt)}
                    </span>
                  </div>
                  <p className="text-sm text-slate-600 truncate">{ticket.description}</p>
                  <div className="flex items-center gap-2 mt-2">
                    <StatusBadge status={ticket.status} />
                    <PriorityBadge priority={ticket.priority} />
                    {ticket.messages?.length > 0 && (
                      <span className="flex items-center gap-1 text-xs text-slate-400">
                        <MessageSquare className="w-3 h-3" />
                        {ticket.messages.length}
                      </span>
                    )}
                  </div>
                </div>
                <ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-blue-500 transition-colors shrink-0 mt-2" />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default AgentOverview
