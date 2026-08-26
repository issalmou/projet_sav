import { useNavigate } from 'react-router-dom'
import {
  Users,
  BookOpen,
  BarChart3,
  Activity,
  Headphones,
  Ticket,
  Clock,
  ChevronRight,
  TrendingUp,
  UserCheck,
  AlertTriangle,
  CheckCircle2,
} from 'lucide-react'
import { useAdmin } from '../../contexts/useAdmin'
import { useAuth } from '../../contexts/useAuth'
import { useTickets } from '../../contexts/useTickets'
import { can } from '../../contexts/roles'
import { SeverityBadge } from '../../components/admin/badges'

const SECTION_CARDS = [
  {
    label: 'Tickets',
    description: 'Suivre et gérer les tickets SAV',
    path: '/responsable-sav/tickets',
    icon: Ticket,
    color: 'bg-blue-50 text-blue-600',
    permission: 'analytics.view',
  },
  {
    label: 'Utilisateurs',
    description: 'Gérer l\'équipe et les accès',
    path: '/responsable-sav/users',
    icon: Users,
    color: 'bg-violet-50 text-violet-600',
    permission: 'users.manage',
  },
  {
    label: 'Base documentaire',
    description: 'FAQ, manuels et guides',
    path: '/responsable-sav/documents',
    icon: BookOpen,
    color: 'bg-teal-50 text-teal-600',
    permission: 'documents.manage',
  },
  {
    label: 'Analytiques',
    description: 'Tableaux de bord et métriques',
    path: '/responsable-sav/analytics',
    icon: BarChart3,
    color: 'bg-amber-50 text-amber-600',
    permission: 'analytics.view',
  },
  {
    label: "Logs d'activité",
    description: 'Historique des actions système',
    path: '/responsable-sav/logs',
    icon: Activity,
    color: 'bg-red-50 text-red-600',
    permission: 'logs.view',
  },
]

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

function ResponsableSAVOverview() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { users } = useAdmin()
  const { logs } = useAdmin()
  const { tickets } = useTickets()

  const totalTickets = tickets.length
  const openTickets = tickets.filter((t) => t.status === 'open').length
  const inProgressTickets = tickets.filter((t) => t.status === 'in_progress').length
  const resolvedTickets = tickets.filter((t) => t.status === 'resolved' || t.status === 'closed').length
  const pendingTickets = openTickets + inProgressTickets
  const resolutionRate = totalTickets > 0 ? Math.round((resolvedTickets / totalTickets) * 100) : 0

  const activeUsers = users.filter((u) => u.status === 'active').length
  const agents = users.filter((u) => u.role === 'agent')
  const activeAgents = agents.filter((u) => u.status === 'active').length

  const recentLogs = logs.slice(0, 5)
  const visibleSections = SECTION_CARDS.filter((s) => can(user, s.permission))

  return (
    <div className="space-y-8">
      {/* Welcome banner */}
      <div className="bg-gradient-to-r from-amber-500 via-amber-600 to-orange-500 rounded-2xl p-6 text-white custom-shadow relative overflow-hidden">
        <div className="absolute -right-8 -bottom-8 opacity-10">
          <Headphones className="w-48 h-48" />
        </div>
        <div className="relative z-10 space-y-3">
          <p className="text-xs font-bold uppercase tracking-widest text-amber-100">Espace Responsable SAV</p>
          <h2 className="text-xl font-bold">Bonjour, {user?.name?.split(' ')[0] || 'Responsable'}</h2>
          <p className="text-sm text-amber-100 max-w-xl leading-relaxed">
            Supervisez les performances du service après-vente : suivez les tickets,
            analysez la satisfaction client et gérez votre équipe.
          </p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          icon={Ticket}
          label="Tickets totaux"
          value={totalTickets}
          hint={`${pendingTickets} en cours`}
          color="bg-blue-50 text-blue-600"
        />
        <StatCard
          icon={AlertTriangle}
          label="Tickets en attente"
          value={pendingTickets}
          hint={`${openTickets} ouverts, ${inProgressTickets} en cours`}
          color="bg-orange-50 text-orange-600"
        />
        <StatCard
          icon={CheckCircle2}
          label="Taux de résolution"
          value={`${resolutionRate}%`}
          hint={`${resolvedTickets} tickets résolus`}
          color="bg-emerald-50 text-emerald-600"
        />
        <StatCard
          icon={UserCheck}
          label="Agents actifs"
          value={activeAgents}
          hint={`${agents.length} au total`}
          color="bg-violet-50 text-violet-600"
        />
      </div>

      {/* Quick access */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-slate-900">Accès rapide</h2>
          <span className="text-xs font-semibold text-slate-400 flex items-center gap-1">
            <Clock className="w-3.5 h-3.5" />
            Navigation rapide
          </span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {visibleSections.map((s) => (
            <button
              key={s.path}
              onClick={() => navigate(s.path)}
              className="group bg-white p-5 rounded-2xl border border-slate-200 custom-shadow card-hover text-left flex items-start gap-4"
            >
              <div className={`w-11 h-11 rounded-xl flex items-center justify-center shrink-0 ${s.color}`}>
                <s.icon className="w-5 h-5" />
              </div>
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-bold text-slate-900 group-hover:text-amber-600 transition-colors">
                  {s.label}
                </h4>
                <p className="text-xs text-slate-500 mt-0.5">{s.description}</p>
              </div>
              <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-amber-500 transition-colors shrink-0 mt-1" />
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Recent activity */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 overflow-hidden custom-shadow">
          <div className="p-6 border-b border-slate-100 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-slate-400" />
              <h2 className="text-lg font-bold text-slate-900">Activité récente</h2>
            </div>
            <button
              onClick={() => navigate('/responsable-sav/logs')}
              className="text-sm font-semibold text-amber-600 hover:text-amber-700"
            >
              Voir tous les logs
            </button>
          </div>
          {recentLogs.length === 0 ? (
            <p className="p-8 text-center text-sm text-slate-400">Aucune activité récente.</p>
          ) : (
            <div className="divide-y divide-slate-50">
              {recentLogs.map((log) => (
                <div key={log.id} className="p-5 flex items-start gap-4 hover:bg-slate-50 transition-colors">
                  <div className="w-2 h-2 rounded-full bg-amber-500 mt-2 shrink-0"></div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-0.5">
                      <h4 className="text-sm font-bold text-slate-900 truncate">{log.details}</h4>
                      <span className="text-xs text-slate-400 shrink-0 ml-3">
                        {formatRelative(log.createdAt)}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 mt-1 flex-wrap">
                      <span className="text-xs text-slate-500">
                        {log.actor}
                        {log.actorRole !== 'system' && (
                          <span className="text-slate-400"> · {log.actorRole}</span>
                        )}
                      </span>
                      <SeverityBadge severity={log.severity} />
                      <span className="text-[10px] font-mono text-slate-300">{log.action}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Side panel: team + quick actions */}
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200 p-6 custom-shadow space-y-4">
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-widest">Équipe Support</h3>
            {agents.length === 0 ? (
              <p className="text-sm text-slate-400">Aucun agent enregistré.</p>
            ) : (
              agents.slice(0, 5).map((agent) => (
                <div key={agent.id} className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-xs font-bold text-blue-600 shrink-0">
                      {agent.name?.split(' ').map((n) => n[0]).join('').slice(0, 2).toUpperCase()}
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-slate-800 truncate">{agent.name}</p>
                      <p className="text-[11px] text-slate-400">{agent.department || 'Support'}</p>
                    </div>
                  </div>
                  <span className={`w-2 h-2 rounded-full shrink-0 ${agent.status === 'active' ? 'bg-emerald-500' : 'bg-slate-300'}`} />
                </div>
              ))
            )}
          </div>

          <div className="bg-slate-900 rounded-2xl p-6 text-white custom-shadow space-y-3">
            <h3 className="text-sm font-bold uppercase tracking-widest">Actions rapides</h3>
            <button
              onClick={() => navigate('/responsable-sav/analytics')}
              className="flex items-center gap-2 w-full px-4 py-2.5 bg-white/10 hover:bg-white/20 rounded-xl text-sm font-semibold transition-colors"
            >
              <BarChart3 className="w-4 h-4" />
              Voir les analytiques
            </button>
            <button
              onClick={() => navigate('/responsable-sav/tickets')}
              className="flex items-center gap-2 w-full px-4 py-2.5 bg-white/10 hover:bg-white/20 rounded-xl text-sm font-semibold transition-colors"
            >
              <Ticket className="w-4 h-4" />
              Gérer les tickets
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ResponsableSAVOverview
