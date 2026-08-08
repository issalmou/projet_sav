import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  Plus,
  Search,
  Users as UsersIcon,
  UserCheck,
  UserX,
  Pencil,
  Trash2,
  ChevronDown,
  Mail,
  RefreshCw,
} from 'lucide-react'
import { useAdmin } from '../../contexts/useAdmin'
import { ROLE_ORDER, ROLES } from '../../contexts/roles'
import { PageHeader, EmptyState, ConfirmModal } from '../../components/admin/ui'
import { useToast } from '../../components/admin/useToast'
import { RoleBadge, StatusBadge } from '../../components/admin/badges'

const PAGE_SIZE = 8

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

function formatRelative(iso) {
  if (!iso) return 'Jamais'
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `Il y a ${mins} min`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `Il y a ${hours} h`
  return formatDate(iso)
}

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

function AdminUsers() {
  const navigate = useNavigate()
  const location = useLocation()
  const { users, updateUser, deleteUser } = useAdmin()
  const { toastEl, showToast } = useToast()

  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState('all')
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
    return users
      .filter((u) => {
        const matchSearch =
          !query ||
          u.name.toLowerCase().includes(query) ||
          u.email.toLowerCase().includes(query) ||
          u.department.toLowerCase().includes(query)
        const matchRole = roleFilter === 'all' || u.role === roleFilter
        const matchStatus = statusFilter === 'all' || u.status === statusFilter
        return matchSearch && matchRole && matchStatus
      })
      .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
  }, [users, search, roleFilter, statusFilter])

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const currentPage = Math.min(page, pageCount)
  const visible = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)

  const toggleStatus = (user) => {
    updateUser(user.id, { status: user.status === 'active' ? 'inactive' : 'active' })
    showToast(
      user.status === 'active'
        ? `Le compte ${user.name} a été désactivé`
        : `Le compte ${user.name} a été activé`
    )
  }

  const resetFilters = () => {
    setSearch('')
    setRoleFilter('all')
    setStatusFilter('all')
    setPage(1)
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Utilisateurs"
        subtitle="Gérez les comptes et les accès de la plateforme."
        actions={
          <button
            onClick={() => navigate('/admin/users/new')}
            className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl shadow-lg shadow-blue-500/20 flex items-center gap-2 transition-all active:scale-[0.98]"
          >
            <Plus className="w-5 h-5" />
            Ajouter un utilisateur
          </button>
        }
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard icon={UsersIcon} label="Total utilisateurs" value={users.length} color="bg-blue-50 text-blue-600" />
        <StatCard icon={UserCheck} label="Actifs" value={users.filter((u) => u.status === 'active').length} color="bg-teal-50 text-teal-600" />
        <StatCard icon={UserX} label="Inactifs" value={users.filter((u) => u.status === 'inactive').length} color="bg-slate-100 text-slate-500" />
        <StatCard
          icon={UsersIcon}
          label="Administrateurs"
          value={users.filter((u) => u.role === 'admin').length}
          color="bg-violet-50 text-violet-600"
        />
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
              placeholder="Rechercher par nom, email ou service..."
              className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
            />
          </div>

          <div className="relative">
            <select
              value={roleFilter}
              onChange={(e) => {
                setRoleFilter(e.target.value)
                setPage(1)
              }}
              className="appearance-none pl-3 pr-9 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/20 cursor-pointer"
            >
              <option value="all">Tous les rôles</option>
              {ROLE_ORDER.map((r) => (
                <option key={r} value={r}>
                  {ROLES[r].label}
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
              <option value="all">Tous les statuts</option>
              <option value="active">Actifs</option>
              <option value="inactive">Inactifs</option>
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
          </div>

          <button
            onClick={resetFilters}
            title="Réinitialiser les filtres"
            className="p-2.5 bg-slate-50 border border-slate-200 text-slate-500 hover:bg-slate-100 rounded-xl transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        <div className="px-5 py-3 flex items-center gap-4 text-[10px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-100">
          <span className="flex-1">Utilisateur</span>
          <span className="shrink-0 w-32">Rôle</span>
          <span className="shrink-0 w-24">Statut</span>
          <span className="hidden lg:inline shrink-0 w-24">Dernière connexion</span>
          <span className="hidden md:inline shrink-0 w-24">Créé le</span>
          <span className="shrink-0 w-20 text-center">Actions</span>
        </div>

        {filtered.length === 0 ? (
          <EmptyState
            icon={UsersIcon}
            title="Aucun utilisateur trouvé"
            message={
              users.length === 0
                ? "Aucun utilisateur pour le moment. Ajoutez-en un pour commencer."
                : "Aucun utilisateur ne correspond à vos critères."
            }
            action={
              users.length === 0 && (
                <button
                  onClick={() => navigate('/admin/users/new')}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-xl transition-colors"
                >
                  Ajouter un utilisateur
                </button>
              )
            }
          />
        ) : (
          visible.map((u) => (
            <div
              key={u.id}
              className="group flex items-center gap-4 px-5 py-4 border-b border-slate-100 hover:bg-slate-50 transition-colors"
            >
              <div className="flex-1 min-w-0 flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-bold shrink-0">
                  {u.name
                    .split(' ')
                    .map((n) => n[0])
                    .join('')
                    .slice(0, 2)
                    .toUpperCase()}
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-bold text-slate-900 truncate">{u.name}</p>
                  <p className="text-xs text-slate-500 flex items-center gap-1 truncate">
                    <Mail className="w-3 h-3 shrink-0" />
                    {u.email}
                  </p>
                </div>
              </div>
              <div className="shrink-0 w-32">
                <RoleBadge role={u.role} />
              </div>
              <div className="shrink-0 w-24">
                <StatusBadge status={u.status} />
              </div>
              <div className="hidden lg:inline shrink-0 w-24 text-xs text-slate-500">
                {formatRelative(u.lastLogin)}
              </div>
              <div className="hidden md:inline shrink-0 w-24 text-xs text-slate-500">
                {formatDate(u.createdAt)}
              </div>
              <div className="shrink-0 w-20 flex items-center justify-end gap-1">
                <button
                  onClick={() => navigate(`/admin/users/${u.id}/edit`)}
                  title="Modifier"
                  className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                >
                  <Pencil className="w-4 h-4" />
                </button>
                <button
                  onClick={() => toggleStatus(u)}
                  title={u.status === 'active' ? 'Désactiver' : 'Activer'}
                  className={`p-2 rounded-lg transition-colors ${
                    u.status === 'active'
                      ? 'text-slate-400 hover:text-amber-600 hover:bg-amber-50'
                      : 'text-slate-400 hover:text-teal-600 hover:bg-teal-50'
                  }`}
                >
                  {u.status === 'active' ? <UserX className="w-4 h-4" /> : <UserCheck className="w-4 h-4" />}
                </button>
                <button
                  onClick={() => setDeleteTarget(u)}
                  title="Supprimer"
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
            Affichage de{' '}
            <span className="font-semibold text-slate-700">{(currentPage - 1) * PAGE_SIZE + 1}</span> à{' '}
            <span className="font-semibold text-slate-700">
              {Math.min(currentPage * PAGE_SIZE, filtered.length)}
            </span>{' '}
            sur {filtered.length} utilisateur(s)
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(currentPage - 1)}
              disabled={currentPage === 1}
              className="px-3 py-1.5 text-xs font-semibold text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Précédent
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
              Suivant
            </button>
          </div>
        </div>
      )}

      <ConfirmModal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Supprimer l'utilisateur"
        message={
          deleteTarget
            ? `Voulez-vous vraiment supprimer le compte de ${deleteTarget.name} ? Cette action est irréversible.`
            : ''
        }
        onConfirm={() => {
          deleteUser(deleteTarget.id)
          showToast(`Le compte de ${deleteTarget.name} a été supprimé`)
        }}
      />

      {toastEl}
    </div>
  )
}

export default AdminUsers
