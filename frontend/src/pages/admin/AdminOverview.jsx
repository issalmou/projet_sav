import { useNavigate } from 'react-router-dom'
import {
  Users,
  BookOpen,
  Plug,
  Activity,
  Settings,
  ShieldAlert,
  ChevronRight,
  UserPlus,
  FilePlus2,
  Zap,
  Clock,
  TrendingUp,
} from 'lucide-react'
import { useAdmin } from '../../contexts/useAdmin'
import { useAuth } from '../../contexts/useAuth'
import { can } from '../../contexts/roles'
import { SeverityBadge, IntegrationBadge } from '../../components/admin/badges'

const SECTION_CARDS = [
  {
    label: 'Utilisateurs',
    description: 'Ajouter, modifier et gérer les accès',
    path: '/admin/users',
    icon: Users,
    color: 'bg-violet-50 text-violet-600',
    permission: 'users.manage',
  },
  {
    label: 'Base documentaire',
    description: 'FAQ, manuels et guides',
    path: '/admin/documents',
    icon: BookOpen,
    color: 'bg-blue-50 text-blue-600',
    permission: 'documents.manage',
  },
  {
    label: 'Intégrations CRM/ERP',
    description: 'Connecter et configurer les systèmes',
    path: '/admin/integrations',
    icon: Plug,
    color: 'bg-teal-50 text-teal-600',
    permission: 'integrations.manage',
  },
  {
    label: 'Logs d\u2019activité',
    description: 'Historique des actions système',
    path: '/admin/logs',
    icon: Activity,
    color: 'bg-amber-50 text-amber-600',
    permission: 'logs.view',
  },
  {
    label: 'Paramètres',
    description: 'Configuration générale de la plateforme',
    path: '/admin/settings',
    icon: Settings,
    color: 'bg-slate-100 text-slate-600',
    permission: 'settings.manage',
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

function AdminOverview() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { users, documents, integrations, logs } = useAdmin()

  const activeUsers = users.filter((u) => u.status === 'active').length
  const publishedDocs = documents.filter((d) => d.status === 'published').length
  const connected = integrations.filter((i) => i.status === 'connected' && i.enabled).length
  const criticalLogs = logs.filter((l) => l.severity === 'critical').length
  const recentLogs = logs.slice(0, 5)
  const visibleSections = SECTION_CARDS.filter((s) => can(user, s.permission))

  return (
    <div className="space-y-8">
      {/* Welcome banner */}
      <div className="bg-gradient-to-r from-slate-900 via-blue-900 to-blue-600 rounded-2xl p-6 text-white custom-shadow relative overflow-hidden">
        <div className="absolute -right-8 -bottom-8 opacity-10">
          <Zap className="w-48 h-48" />
        </div>
        <div className="relative z-10 space-y-3">
          <p className="text-xs font-bold uppercase tracking-widest text-blue-200">Panneau d'administration</p>
          <h2 className="text-xl font-bold">Bonjour, {user?.name?.split(' ')[0] || 'Administrateur'}</h2>
          <p className="text-sm text-blue-100 max-w-xl leading-relaxed">
            Centralisez la gestion de la plateforme : comptes utilisateurs, base documentaire,
            intégrations CRM/ERP et journaux d'activité.
          </p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          icon={Users}
          label="Utilisateurs actifs"
          value={activeUsers}
          hint={`${users.length} au total`}
          color="bg-violet-50 text-violet-600"
        />
        <StatCard
          icon={BookOpen}
          label="Documents publiés"
          value={publishedDocs}
          hint={`${documents.length} documents`}
          color="bg-blue-50 text-blue-600"
        />
        <StatCard
          icon={Plug}
          label="Intégrations connectées"
          value={connected}
          hint={`${integrations.length} configurées`}
          color="bg-teal-50 text-teal-600"
        />
        <StatCard
          icon={ShieldAlert}
          label="Événements critiques"
          value={criticalLogs}
          hint="7 derniers jours"
          color="bg-red-50 text-red-600"
        />
      </div>

      {/* Quick access */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-slate-900">Accès rapide</h2>
          <span className="text-xs font-semibold text-slate-400 flex items-center gap-1">
            <Clock className="w-3.5 h-3.5" />
            Actions de gestion
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
                <h4 className="text-sm font-bold text-slate-900 group-hover:text-blue-600 transition-colors">
                  {s.label}
                </h4>
                <p className="text-xs text-slate-500 mt-0.5">{s.description}</p>
              </div>
              <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-blue-500 transition-colors shrink-0 mt-1" />
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
              onClick={() => navigate('/admin/logs')}
              className="text-sm font-semibold text-blue-600 hover:text-blue-700"
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
                  <div className="w-2 h-2 rounded-full bg-blue-500 mt-2 shrink-0"></div>
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

        {/* Side panel: integration health + quick actions */}
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200 p-6 custom-shadow space-y-4">
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-widest">Santé des intégrations</h3>
            {integrations.length === 0 ? (
              <p className="text-sm text-slate-400">Aucune intégration configurée.</p>
            ) : (
              integrations.slice(0, 4).map((int) => (
                <div key={int.id} className="flex items-center justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-slate-800 truncate">{int.name}</p>
                    <p className="text-[11px] text-slate-400">
                      Dernière synchro : {formatRelative(int.lastSync)}
                    </p>
                  </div>
                  <IntegrationBadge status={int.enabled ? int.status : 'disconnected'} />
                </div>
              ))
            )}
          </div>

          <div className="bg-slate-900 rounded-2xl p-6 text-white custom-shadow space-y-3">
            <h3 className="text-sm font-bold uppercase tracking-widest">Actions rapides</h3>
            {can(user, 'users.manage') && (
              <button
                onClick={() => navigate('/admin/users/new')}
                className="flex items-center gap-2 w-full px-4 py-2.5 bg-white/10 hover:bg-white/20 rounded-xl text-sm font-semibold transition-colors"
              >
                <UserPlus className="w-4 h-4" />
                Ajouter un utilisateur
              </button>
            )}
            {can(user, 'documents.manage') && (
              <button
                onClick={() => navigate('/admin/documents/new')}
                className="flex items-center gap-2 w-full px-4 py-2.5 bg-white/10 hover:bg-white/20 rounded-xl text-sm font-semibold transition-colors"
              >
                <FilePlus2 className="w-4 h-4" />
                Créer un document
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default AdminOverview
