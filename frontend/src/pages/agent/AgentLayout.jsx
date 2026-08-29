import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  Headphones,
  BarChart3,
  Activity,
  BookOpen,
  LogOut,
} from 'lucide-react'
import { useAuth } from '../../contexts/useAuth'
import { can } from '../../contexts/roles'

const sections = [
  {
    label: "Vue d'ensemble",
    path: '/agent',
    end: true,
    icon: LayoutDashboard,
    permission: 'analytics.view',
  },
  {
    label: 'Mes Tickets',
    path: '/agent/tickets',
    icon: Headphones,
    permission: 'analytics.view',
  },
  {
    label: 'Base documentaire',
    path: '/agent/documents',
    icon: BookOpen,
    permission: 'documents.manage',
  },
  {
    label: 'Analytiques',
    path: '/agent/analytics',
    icon: BarChart3,
    permission: 'analytics.view',
  },
  {
    label: "Logs d'activité",
    path: '/agent/logs',
    icon: Activity,
    permission: 'logs.view',
  },
]

function AgentLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const visible = sections.filter((s) => can(user, s.permission))

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="flex-1 overflow-y-auto p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 bg-blue-500 rounded-xl flex items-center justify-center">
              <Headphones className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Agent Support</h1>
              <p className="text-slate-500">
                Gérez les tickets qui vous sont assignés et assistez les clients.
              </p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-xl transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Déconnexion
          </button>
        </div>

        <nav className="flex flex-wrap gap-2">
          {visible.map((s) => (
            <NavLink
              key={s.path}
              to={s.path}
              end={s.end}
              className={({ isActive }) =>
                `inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold border transition-all ${
                  isActive
                    ? 'bg-blue-500 text-white border-blue-500 shadow-lg shadow-blue-500/20'
                    : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                }`
              }
            >
              <s.icon className="w-4 h-4" />
              {s.label}
            </NavLink>
          ))}
        </nav>

        <Outlet />
      </div>
    </div>
  )
}

export default AgentLayout
