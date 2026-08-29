import { 
  Plus, 
  ChevronRight, 
  Monitor, 
  Cpu, 
  BookOpen, 
  Search,
  CheckCircle2,
  TicketCheck,
  Zap,
  CreditCard
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import StatCard from '../components/dashboard/StatCard'
import { useAuth } from '../contexts/useAuth'

function Dashboard() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const isClient = user?.role === 'client'

  return (
    <div className="flex-1 overflow-y-auto p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Welcome & Quick Stats */}
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Bonjour, {user?.name?.split(' ')[0] || 'Utilisateur'}</h1>
              <p className="text-slate-500">Ravi de vous revoir. Voici un aperçu de vos services 3LM Solutions.</p>
            </div>
            {!isClient && (
              <button 
                onClick={() => navigate('/tickets/new')}
                className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl shadow-lg shadow-blue-500/20 flex items-center gap-2 transition-all active:scale-[0.98]"
              >
                <Plus className="w-5 h-5" />
                Nouveau Ticket
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <StatCard 
              title="Tickets Ouverts" 
              value="3" 
              trend="Dernière mise à jour: 2h ago"
              icon="ticket"
              color="blue"
            />
            <StatCard 
              title="Taux de résolution" 
              value="95%" 
              icon="percent"
              color="blue"
            />
            <StatCard 
              title="Ticket en cours" 
              value="128" 
              subtitle="+12 depuis hier"
              icon="ticket"
              color="blue"
            />
            <StatCard 
              title="Temps moyen de résolution" 
              value="3h 20min" 
              subtitle="Temps moyen nécessaire pour résoudre un ticket."
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
                <h2 className="text-lg font-bold text-slate-900">Activités Récentes</h2>
                <a href="#" className="text-sm font-semibold text-blue-600 hover:text-blue-700">
                  Voir tout l'historique
                </a>
              </div>
              <div className="divide-y divide-slate-50">
                <div className="p-5 flex items-start gap-4 hover:bg-slate-50 transition-colors cursor-pointer group">
                  <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 shrink-0">
                    <TicketCheck className="w-5 h-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <h4 className="text-sm font-bold text-slate-900">Ticket #NX-8241 Résolu</h4>
                      <span className="text-xs text-slate-400">Il y a 2h</span>
                    </div>
                    <p className="text-sm text-slate-600 truncate">Votre problème d'authentification a été corrigé par notre agent AI.</p>
                  </div>
                  <ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-blue-500 transition-colors" />
                </div>
                
                <div className="p-5 flex items-start gap-4 hover:bg-slate-50 transition-colors cursor-pointer group">
                  <div className="w-10 h-10 rounded-full bg-teal-100 flex items-center justify-center text-teal-600 shrink-0">
                    <Zap className="w-5 h-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <h4 className="text-sm font-bold text-slate-900">Mise à jour Système</h4>
                      <span className="text-xs text-slate-400">Hier</span>
                    </div>
                    <p className="text-sm text-slate-600 truncate">3LM Soltuion AI v2.5 est maintenant disponible avec de nouveaux agents conversationnels.</p>
                  </div>
                  <ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-blue-500 transition-colors" />
                </div>
                
                <div className="p-5 flex items-start gap-4 hover:bg-slate-50 transition-colors cursor-pointer group">
                  <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center text-orange-600 shrink-0">
                    <CreditCard className="w-5 h-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <h4 className="text-sm font-bold text-slate-900">Facture de Novembre disponible</h4>
                      <span className="text-xs text-slate-400">3 jours ago</span>
                    </div>
                    <p className="text-sm text-slate-600 truncate">Votre facture pour le cycle de facturation actuel est prête au téléchargement.</p>
                  </div>
                  <ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-blue-500 transition-colors" />
                </div>
              </div>
            </div>

            {/* Products Spotlight */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-bold text-slate-900">Mes Produits à la une</h2>
                <a href="#" className="text-sm font-semibold text-blue-600 hover:text-blue-700">Mes 8 produits</a>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-white p-5 rounded-2xl border border-slate-200 custom-shadow card-hover flex gap-4">
                  <div className="w-16 h-16 rounded-xl bg-slate-100 flex items-center justify-center shrink-0">
                    <Monitor className="w-8 h-8 text-slate-400" />
                  </div>
                  <div className="flex-1 min-w-0 py-1">
                    <h4 className="text-sm font-bold text-slate-900 truncate">3LM Soltuion Pro 32" 4K OLED</h4>
                    <p className="text-xs text-slate-500 mb-2">SN: NX-OLED-48293</p>
                    <span className="px-2 py-0.5 bg-teal-50 text-teal-600 text-[10px] font-bold uppercase rounded border border-teal-100">
                      Garantie Active
                    </span>
                  </div>
                </div>
                
                <div className="bg-white p-5 rounded-2xl border border-slate-200 custom-shadow card-hover flex gap-4">
                  <div className="w-16 h-16 rounded-xl bg-slate-100 flex items-center justify-center shrink-0">
                    <Cpu className="w-8 h-8 text-slate-400" />
                  </div>
                  <div className="flex-1 min-w-0 py-1">
                    <h4 className="text-sm font-bold text-slate-900 truncate">Smart Gateway Hub X-1</h4>
                    <p className="text-xs text-slate-500 mb-2">SN: SG-X1-9920</p>
                    <span className="px-2 py-0.5 bg-orange-50 text-orange-600 text-[10px] font-bold uppercase rounded border border-orange-100">
                      Expire bientôt
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Right Side Panels */}
          <div className="space-y-8">
            
            {/* Guide Section */}
            <div className="bg-blue-600 rounded-2xl p-6 text-white custom-shadow relative overflow-hidden">
              <div className="absolute -right-4 -bottom-4 opacity-10">
                <BookOpen className="w-32 h-32" />
              </div>
              <div className="relative z-10 space-y-4">
                <div className="flex items-center gap-2 mb-2">
                  <h3 className="text-sm font-bold uppercase tracking-widest">Guide du Portail</h3>
                </div>
                <p className="text-xs text-blue-100 leading-relaxed">
                  Bienvenue dans votre nouvel espace 3LM Soltuion AI. Ce tableau de bord centralise vos interactions : suivez vos tickets en temps réel, gérez votre parc de produits et accédez à vos factures via le menu latéral.
                </p>
                <button className="inline-flex items-center gap-2 bg-white text-blue-600 px-4 py-2 rounded-lg text-xs font-bold hover:bg-blue-50 transition-colors">
                  Télécharger le PDF explicatif
                </button>
              </div>
            </div>

            {/* Knowledge Base */}
            <div className="bg-white rounded-2xl border border-slate-200 p-6 custom-shadow space-y-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center text-blue-600">
                  <BookOpen className="w-5 h-5" />
                </div>
                <h3 className="font-bold text-slate-900">Aide & Documentation</h3>
              </div>
              <p className="text-sm text-slate-500 leading-relaxed">
                Trouvez des réponses instantanées dans notre centre d'aide alimenté par l'IA.
              </p>
              <div className="relative">
                <input 
                  type="text" 
                  placeholder="Rechercher un guide..." 
                  className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                />
                <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
              </div>
              <ul className="space-y-3 pt-2">
                <li className="flex items-center gap-2 text-xs font-semibold text-slate-700 group cursor-pointer">
                  <BookOpen className="w-4 h-4 text-blue-500" />
                  <span className="group-hover:text-blue-600 transition-colors">Configuration initiale du hub</span>
                </li>
                <li className="flex items-center gap-2 text-xs font-semibold text-slate-700 group cursor-pointer">
                  <BookOpen className="w-4 h-4 text-blue-500" />
                  <span className="group-hover:text-blue-600 transition-colors">Optimisation de l'IA conversationnelle</span>
                </li>
              </ul>
              <button className="w-full py-2.5 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl text-xs font-bold text-slate-600 transition-colors">
                Explorer la base de connaissances
              </button>
            </div>

            {/* Health Monitor */}
            <div className="bg-teal-50 rounded-2xl border border-teal-100 p-6 custom-shadow space-y-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-bold text-teal-900 uppercase tracking-widest">Mon Parc 3LM Soltuion</h3>
                <CheckCircle2 className="w-5 h-5 text-teal-600" />
              </div>
              <div className="space-y-4">
                <div className="space-y-1.5">
                  <div className="flex justify-between text-[10px] font-bold text-teal-800 uppercase">
                    <span>Santé du Parc</span>
                    <span>100%</span>
                  </div>
                  <div className="w-full bg-white h-1.5 rounded-full overflow-hidden">
                    <div className="bg-teal-500 h-full w-full"></div>
                  </div>
                </div>
                <p className="text-xs text-teal-700 leading-relaxed">
                  Tous vos équipements connectés fonctionnent de manière optimale. Aucune alerte critique détectée.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard