import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Search,
  Filter,
  Ticket,
  CheckCircle2,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Calendar,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  RefreshCw,
  MessageSquare,
  ArrowUpCircle
} from 'lucide-react'
import { useTickets } from '../../contexts/useTickets'
import { useAuth } from '../../contexts/useAuth'
import StatusBadge from '../../components/tickets/StatusBadge'
import PriorityBadge from '../../components/tickets/PriorityBadge'
import CategoryBadge from '../../components/tickets/CategoryBadge'
import {
  STATUSES,
  STATUS_ORDER,
  PRIORITIES,
  CATEGORIES,
  SORT_OPTIONS
} from '../../components/tickets/constants'

const PAGE_SIZE = 8

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  })
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

function TicketRow({ ticket }) {
  const navigate = useNavigate()
  const messageCount = ticket.messages?.length ?? 0

  return (
    <div
      onClick={() => navigate(`/agent/tickets/${ticket.id}`)}
      className="group flex items-center gap-4 px-5 py-4 border-b border-slate-100 hover:bg-slate-50 cursor-pointer transition-colors"
    >
      <span className="text-xs font-bold text-slate-400 w-20 shrink-0">#{ticket.id}</span>

      <div className="flex-1 min-w-0">
        <h4 className="text-sm font-bold text-slate-900 truncate group-hover:text-blue-600 transition-colors">
          {ticket.title}
        </h4>
        <p className="text-xs text-slate-500 truncate mt-0.5">{ticket.description}</p>
      </div>

      <span className="hidden lg:inline shrink-0">
        <CategoryBadge category={ticket.category} />
      </span>

      <div className="shrink-0">
        <StatusBadge status={ticket.status} />
      </div>

      <div className="shrink-0">
        <PriorityBadge priority={ticket.priority} />
      </div>

      <div className="hidden sm:flex items-center gap-1.5 shrink-0">
        <Calendar className="w-3 h-3 text-slate-400" />
        <span className="text-xs text-slate-500">{formatDate(ticket.createdAt)}</span>
      </div>

      <div className="hidden md:flex items-center gap-1 shrink-0">
        <MessageSquare className="w-3.5 h-3.5 text-slate-400" />
        <span className="text-xs text-slate-500">{messageCount}</span>
      </div>

      <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-blue-500 transition-colors shrink-0" />
    </div>
  )
}

function SortButton({ label, active, direction, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-1 hover:text-blue-600 transition-colors ${
        active ? 'text-blue-600' : ''
      }`}
    >
      {label}
      {active &&
        (direction === 'asc' ? (
          <ArrowUp className="w-3 h-3" />
        ) : (
          <ArrowDown className="w-3 h-3" />
        ))}
      {!active && <ArrowUpDown className="w-3 h-3 opacity-0 group-hover:opacity-100" />}
    </button>
  )
}

function AgentTicketsList() {
  const { tickets } = useTickets()
  const { user } = useAuth()

  const myTickets = tickets.filter((t) => 
    t.assignee === user?.name || 
    t.assignee === user?.email ||
    t.status === 'open' ||
    t.status === 'escalated'
  )

  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [priorityFilter, setPriorityFilter] = useState('all')
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [sortBy, setSortBy] = useState('newest')
  const [sortAsc, setSortAsc] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const [page, setPage] = useState(1)

  const updateSearch = (value) => {
    setSearch(value)
    setPage(1)
  }

  const updateStatusFilter = (value) => {
    setStatusFilter(value)
    setPage(1)
  }

  const updatePriorityFilter = (value) => {
    setPriorityFilter(value)
    setPage(1)
  }

  const updateCategoryFilter = (value) => {
    setCategoryFilter(value)
    setPage(1)
  }

  const updateSort = (value) => {
    setSortBy(value)
    setSortAsc(false)
    setPage(1)
  }

  const filteredTickets = useMemo(() => {
    const query = search.trim().toLowerCase()
    const filtered = myTickets.filter((ticket) => {
      const matchSearch =
        !query ||
        ticket.title.toLowerCase().includes(query) ||
        ticket.id.toLowerCase().includes(query) ||
        ticket.description.toLowerCase().includes(query)
      const matchStatus = statusFilter === 'all' || ticket.status === statusFilter
      const matchPriority = priorityFilter === 'all' || ticket.priority === priorityFilter
      const matchCategory = categoryFilter === 'all' || ticket.category === categoryFilter
      return matchSearch && matchStatus && matchPriority && matchCategory
    })

    const sorters = {
      newest: (a, b) => new Date(b.createdAt) - new Date(a.createdAt),
      oldest: (a, b) => new Date(a.createdAt) - new Date(b.createdAt),
      priority: (a, b) => PRIORITIES[b.priority].rank - PRIORITIES[a.priority].rank,
      status: (a, b) => STATUSES[a.status].step - STATUSES[b.status].step,
      title: (a, b) => a.title.localeCompare(b.title, 'fr')
    }

    const sorter = sorters[sortBy]
    const sorted = [...filtered].sort(sorter)
    return sortAsc ? sorted.reverse() : sorted
  }, [myTickets, search, statusFilter, priorityFilter, categoryFilter, sortBy, sortAsc])

  const pageCount = Math.max(1, Math.ceil(filteredTickets.length / PAGE_SIZE))
  const currentPage = Math.min(page, pageCount)
  const visibleTickets = filteredTickets.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE
  )

  const statusCounts = useMemo(() => {
    const counts = { all: myTickets.length }
    STATUS_ORDER.forEach((s) => {
      counts[s] = myTickets.filter((t) => t.status === s).length
    })
    return counts
  }, [myTickets])

  const resetFilters = () => {
    setSearch('')
    setStatusFilter('all')
    setPriorityFilter('all')
    setCategoryFilter('all')
    setSortBy('newest')
    setSortAsc(false)
    setShowFilters(false)
  }

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard icon={Ticket} label="Total Tickets" value={myTickets.length} color="bg-blue-50 text-blue-600" />
        <StatCard
          icon={AlertTriangle}
          label="En cours"
          value={myTickets.filter((t) => t.status === 'in_progress').length}
          color="bg-amber-50 text-amber-600"
        />
        <StatCard
          icon={CheckCircle2}
          label="Résolus"
          value={myTickets.filter((t) => t.status === 'resolved').length}
          color="bg-teal-50 text-teal-600"
        />
        <StatCard
          icon={ArrowUpCircle}
          label="Escaladés"
          value={myTickets.filter((t) => t.status === 'escalated').length}
          color="bg-red-50 text-red-600"
        />
      </div>

      {/* Filters Bar */}
      <div className="bg-white rounded-2xl border border-slate-200 custom-shadow">
        <div className="p-4 flex items-center gap-3 border-b border-slate-100">
          {/* Search */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => updateSearch(e.target.value)}
              placeholder="Rechercher par ID, titre ou description..."
              className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
            />
          </div>

          {/* Sort */}
          <div className="relative">
            <select
              value={sortBy}
              onChange={(e) => updateSort(e.target.value)}
              className="appearance-none pl-3 pr-9 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/20 cursor-pointer"
            >
              {SORT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
          </div>

          <button
            onClick={() => setSortAsc(!sortAsc)}
            disabled={sortBy === 'title'}
            title="Inverser l'ordre"
            className={`p-2.5 rounded-xl border transition-colors ${
              sortAsc
                ? 'bg-blue-50 text-blue-600 border-blue-200'
                : 'bg-slate-50 text-slate-500 border-slate-200 hover:bg-slate-100'
            } ${sortBy === 'title' ? 'opacity-40 cursor-not-allowed' : ''}`}
          >
            <ArrowUpDown className="w-4 h-4" />
          </button>

          {/* Filter Toggle */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all ${
              showFilters || statusFilter !== 'all' || priorityFilter !== 'all' || categoryFilter !== 'all'
                ? 'bg-blue-50 text-blue-600 border border-blue-200'
                : 'bg-slate-50 text-slate-600 border border-slate-200 hover:bg-slate-100'
            }`}
          >
            <Filter className="w-4 h-4" />
            Filtres
            {(statusFilter !== 'all' || priorityFilter !== 'all' || categoryFilter !== 'all') && (
              <span className="w-5 h-5 rounded-full bg-blue-600 text-white text-[10px] flex items-center justify-center">
                {(statusFilter !== 'all' ? 1 : 0) + (priorityFilter !== 'all' ? 1 : 0) + (categoryFilter !== 'all' ? 1 : 0)}
              </span>
            )}
            <ChevronDown className={`w-4 h-4 transition-transform ${showFilters ? 'rotate-180' : ''}`} />
          </button>

          {/* Reset */}
          <button
            onClick={resetFilters}
            title="Réinitialiser"
            className="p-2.5 bg-slate-50 border border-slate-200 text-slate-500 hover:bg-slate-100 rounded-xl transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {/* Expanded Filters */}
        {showFilters && (
          <div className="p-4 flex flex-wrap items-center gap-x-8 gap-y-4 bg-slate-50 border-b border-slate-100">
            {/* Status pills */}
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-semibold text-slate-500">Statut :</span>
              <button
                onClick={() => updateStatusFilter('all')}
                className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors ${
                  statusFilter === 'all'
                    ? 'bg-slate-900 text-white border-slate-900'
                    : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-100'
                }`}
              >
                Tous ({statusCounts.all})
              </button>
              {STATUS_ORDER.map((status) => {
                const s = STATUSES[status]
                const active = statusFilter === status
                return (
                  <button
                    key={status}
                    onClick={() => updateStatusFilter(status)}
                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors ${
                      active ? s.color + ' ring-2 ring-offset-1 ' + s.dot.replace('bg-', 'ring-') : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-100'
                    }`}
                  >
                    <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
                    {s.label} ({statusCounts[status] || 0})
                  </button>
                )
              })}
            </div>

            {/* Priority */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-500">Priorité :</span>
              <select
                value={priorityFilter}
                onChange={(e) => updatePriorityFilter(e.target.value)}
                className="px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              >
                <option value="all">Toutes</option>
                <option value="high">Haute</option>
                <option value="medium">Moyenne</option>
                <option value="low">Basse</option>
              </select>
            </div>

            {/* Category */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-500">Catégorie :</span>
              <select
                value={categoryFilter}
                onChange={(e) => updateCategoryFilter(e.target.value)}
                className="px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              >
                <option value="all">Toutes</option>
                {CATEGORIES.map((c) => (
                  <option key={c.value} value={c.value}>{c.label}</option>
                ))}
              </select>
            </div>

            <button
              onClick={resetFilters}
              className="text-xs font-semibold text-blue-600 hover:text-blue-700"
            >
              Réinitialiser
            </button>
          </div>
        )}

        {/* Table Header */}
        <div className="px-5 py-3 flex items-center gap-4 text-[10px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-100 group">
          <span className="w-20 shrink-0">ID</span>
          <span className="flex-1">Titre</span>
          <span className="hidden lg:inline shrink-0">Catégorie</span>
          <span className="shrink-0 w-28 text-center">
            <SortButton label="Statut" active={sortBy === 'status'} direction={sortAsc ? 'asc' : 'desc'} onClick={() => {
              if (sortBy === 'status') { setSortAsc(!sortAsc); setPage(1) }
              else updateSort('status')
            }} />
          </span>
          <span className="shrink-0 w-24 text-center">
            <SortButton label="Priorité" active={sortBy === 'priority'} direction={sortAsc ? 'asc' : 'desc'} onClick={() => {
              if (sortBy === 'priority') { setSortAsc(!sortAsc); setPage(1) }
              else updateSort('priority')
            }} />
          </span>
          <span className="hidden sm:inline shrink-0 w-24">
            <SortButton label="Date" active={sortBy === 'newest' || sortBy === 'oldest'} direction={sortAsc ? 'asc' : 'desc'} onClick={() => {
              if (sortBy === 'newest' || sortBy === 'oldest') { setSortAsc(!sortAsc); setPage(1) }
              else updateSort('newest')
            }} />
          </span>
          <span className="hidden md:inline shrink-0 w-12 text-center">
            <MessageSquare className="w-3 h-3 inline" />
          </span>
          <span className="w-4 shrink-0" />
        </div>

        {/* Ticket List */}
        {filteredTickets.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mb-4">
              <Ticket className="w-8 h-8 text-slate-300" />
            </div>
            <h3 className="text-sm font-bold text-slate-900 mb-1">Aucun ticket trouvé</h3>
            <p className="text-xs text-slate-500 max-w-xs">
              {myTickets.length === 0
                ? "Aucun ticket ne vous est actuellement assigné."
                : "Aucun ticket ne correspond à vos critères de recherche ou de filtres."}
            </p>
          </div>
        ) : (
          visibleTickets.map((ticket) => <TicketRow key={ticket.id} ticket={ticket} />)
        )}
      </div>

      {/* Pagination */}
      {filteredTickets.length > 0 && (
        <div className="flex items-center justify-between">
          <p className="text-xs text-slate-500">
            Affichage de{' '}
            <span className="font-semibold text-slate-700">
              {(currentPage - 1) * PAGE_SIZE + 1}
            </span>{' '}
            à{' '}
            <span className="font-semibold text-slate-700">
              {Math.min(currentPage * PAGE_SIZE, filteredTickets.length)}
            </span>{' '}
            sur {filteredTickets.length} ticket(s)
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
    </div>
  )
}

export default AgentTicketsList
