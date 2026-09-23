import { useState } from 'react'
import {
  Plus, 
  ChevronRight, 
  Monitor, 
  BookOpen, 
  Search,
  TicketCheck,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import StatCard from '../components/dashboard/StatCard'
import { useAuth } from '../contexts/useAuth'
import { useTickets } from '../contexts/useTickets'
import { useProducts } from '../contexts/useProducts'
import { useI18n } from '../i18n/useI18n'

function Dashboard() {
  const { user } = useAuth()
  const { t } = useI18n()
  const { getUserTickets } = useTickets()
  const { products } = useProducts()
  const navigate = useNavigate()
  const [ticketSearch, setTicketSearch] = useState('')
  const isClient = user?.role === 'client'
  const tickets = getUserTickets(user)
  const openTickets = tickets.filter((ticket) => ticket.status === 'open').length
  const inProgressTickets = tickets.filter((ticket) => ticket.status === 'in_progress').length
  const resolvedTickets = tickets.filter((ticket) => ['resolved', 'closed'].includes(ticket.status)).length
  const resolutionRate = tickets.length ? Math.round((resolvedTickets / tickets.length) * 100) : 0
  const recentTickets = [...tickets]
    .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
    .slice(0, 3)
  const featuredProducts = products.slice(0, 2)
  const matchingTickets = tickets
    .filter((ticket) => {
      const query = ticketSearch.trim().toLowerCase()
      return query && ticket.title?.toLowerCase().includes(query)
    })
    .slice(0, 5)

  return (
    <div className="flex-1 overflow-y-auto p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Welcome & Quick Stats */}
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">{t('dash.welcome', { name: user?.name?.split(' ')[0] || t('dash.user') })}</h1>
              <p className="text-slate-500">{t('dash.subtitle')}</p>
            </div>
            {!isClient && (
              <button 
                onClick={() => navigate('/tickets/new')}
                className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl shadow-lg shadow-blue-500/20 flex items-center gap-2 transition-all active:scale-[0.98]"
              >
                <Plus className="w-5 h-5" />
                {t('dash.newTicket')}
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
<StatCard 
              title={t('dash.openTickets')} 
              value={openTickets}
              trend={t('dash.updatedFromApi')}
              icon="ticket"
              color="blue"
            />
            <StatCard 
              title={t('dash.resolutionRate')} 
              value={`${resolutionRate}%`}
              icon="percent"
              color="blue"
            />
            <StatCard 
              title={t('dash.inProgress')} 
              value={inProgressTickets}
              subtitle={t('dash.totalTickets', { count: tickets.length })}
              icon="ticket"
              color="blue"
            />
            <StatCard 
              title={t('dash.avgResolution')} 
              value={resolvedTickets}
              subtitle={t('dash.resolvedSubtitle')}
              icon="timer"
              color="blue"
            />
          </div>
        </div>

        {/* Main Layout: Activities & Right Panel */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Recent Activity & Products */}
          <div className="lg:col-span-2 space-y-8">
            
            {/* Recent Activities */}
            <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden custom-shadow">
              <div className="p-6 border-b border-slate-100 flex items-center justify-between">
<h2 className="text-lg font-bold text-slate-900">{t('dash.recentActivities')}</h2>
                <button onClick={() => navigate('/tickets')} className="text-sm font-semibold text-blue-600 hover:text-blue-700">
                  {t('dash.viewHistory')}
                </button>
              </div>
              <div className="divide-y divide-slate-50">
                {recentTickets.length === 0 && (
                  <p className="p-8 text-center text-sm text-slate-400">{t('dash.noRecentTickets')}</p>
                )}
                {recentTickets.map((ticket) => (
                <div key={ticket.id} onClick={() => navigate(`/tickets/${ticket.id}`)} className="p-5 flex items-start gap-4 hover:bg-slate-50 transition-colors cursor-pointer group">
                  <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 shrink-0">
                    <TicketCheck className="w-5 h-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <h4 className="text-sm font-bold text-slate-900">{ticket.title}</h4>
                      <span className="text-xs text-slate-400">{t(`status.${ticket.status}`)}</span>
                    </div>
                    <p className="text-sm text-slate-600 truncate">{ticket.description}</p>
                  </div>
                  <ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-blue-500 transition-colors" />
                </div>
                ))}
              </div>
            </div>

            {/* Products Spotlight */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
<h2 className="text-lg font-bold text-slate-900">{t('dash.featuredProducts')}</h2>
                <button onClick={() => navigate('/products')} className="text-sm font-semibold text-blue-600 hover:text-blue-700">{t('dash.viewProducts')}</button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {featuredProducts.length === 0 && <p className="text-sm text-slate-400">{t('dash.noProducts')}</p>}
                {featuredProducts.map((product) => <div key={product.id} className="bg-white p-5 rounded-2xl border border-slate-200 custom-shadow card-hover flex gap-4">
                  <div className="w-16 h-16 rounded-xl bg-slate-100 flex items-center justify-center shrink-0">
                    <Monitor className="w-8 h-8 text-slate-400" />
                  </div>
                  <div className="flex-1 min-w-0 py-1">
                    <h4 className="text-sm font-bold text-slate-900 truncate">{product.name}</h4>
<p className="text-xs text-slate-500 mb-2">{t('dash.ref', { ref: product.reference })}</p>
                    <span className="px-2 py-0.5 bg-teal-50 text-teal-600 text-[10px] font-bold uppercase rounded border border-teal-100">
                      {product.warranty_months ? t('dash.warrantyMonths', { months: product.warranty_months }) : t('dash.noWarranty')}
                    </span>
                  </div>
                </div>)}
              </div>
            </div>
          </div>

          {/* Right Side Panels */}
          <div className="space-y-8">
            
            {/* Knowledge Base */}
            <div className="bg-white rounded-2xl border border-slate-200 p-6 custom-shadow space-y-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center text-blue-600">
                  <BookOpen className="w-5 h-5" />
                </div>
<h3 className="font-bold text-slate-900">{t('dash.helpDocs')}</h3>
              </div>
                <p className="text-sm text-slate-500 leading-relaxed">
                  {isClient
                    ? t('dash.clientHelp')
                    : t('dash.staffHelp')}
                </p>
                <div className="relative">
                  <input
                    type="text"
                    value={isClient ? ticketSearch : undefined}
                    onChange={isClient ? (event) => setTicketSearch(event.target.value) : undefined}
                    placeholder={isClient ? t('dash.searchTicket') : t('dash.searchGuide')}
                    className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                  />
                  <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
                </div>
                {isClient ? (
                  <div className="space-y-2 pt-2">
{ticketSearch.trim() && matchingTickets.length === 0 && (
                      <p className="text-xs text-slate-400 py-2">{t('dash.noTicketFound')}</p>
                    )}
                    {matchingTickets.map((ticket) => (
                      <button
                        key={ticket.id}
                        onClick={() => navigate(`/tickets/${ticket.id}`)}
                        className="w-full flex items-center justify-between gap-3 p-3 text-left bg-slate-50 hover:bg-blue-50 rounded-xl transition-colors group"
                      >
                        <span className="min-w-0">
                          <span className="block text-xs font-bold text-slate-800 truncate group-hover:text-blue-700">{ticket.title}</span>
                          <span className="block text-[10px] text-slate-400 mt-1">#{ticket.id}</span>
                        </span>
                        <span className="shrink-0 text-[10px] font-bold text-blue-600">{t(`status.${ticket.status}`)}</span>
                      </button>
                    ))}
                  </div>
                ) : (
                  <>
                    <ul className="space-y-3 pt-2">
                      <li className="flex items-center gap-2 text-xs font-semibold text-slate-700 group cursor-pointer">
                        <BookOpen className="w-4 h-4 text-blue-500" />
                        <span className="group-hover:text-blue-600 transition-colors">{t('dash.kbSetup')}</span>
                      </li>
                      <li className="flex items-center gap-2 text-xs font-semibold text-slate-700 group cursor-pointer">
                        <BookOpen className="w-4 h-4 text-blue-500" />
                        <span className="group-hover:text-blue-600 transition-colors">{t('dash.kbAi')}</span>
                      </li>
                    </ul>
<button className="w-full py-2.5 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl text-xs font-bold text-slate-600 transition-colors">
                      {t('dash.exploreKb')}
                    </button>
</>
                )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
