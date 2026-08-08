import { NavLink, Outlet } from 'react-router-dom'
import {
  LayoutDashboard,
  Users,
  BookOpen,
  Plug,
  Activity,
  Settings,
  Shield,
} from 'lucide-react'
import { useAuth } from '../../contexts/useAuth'
import { can } from '../../contexts/roles'

const sections = [
  {
    label: 'Vue d\u2019ensemble',
    path: '/admin',
    end: true,
    icon: LayoutDashboard,
    permission: 'admin.view',
  },
  {
    label: 'Utilisateurs',
    path: '/admin/users',
    icon: Users,
    permission: 'users.manage',
  },
  {
    label: 'Base documentaire',
    path: '/admin/documents',
    icon: BookOpen,
    permission: 'documents.manage',
  },
  {
    label: 'Intégrations',
    path: '/admin/integrations',
    icon: Plug,
    permission: 'integrations.manage',
  },
  {
    label: 'Logs d\u2019activité',
    path: '/admin/logs',
    icon: Activity,
    permission: 'logs.view',
  },
  {
    label: 'Paramètres',
    path: '/admin/settings',
    icon: Settings,
    permission: 'settings.manage',
  },
]

function AdminLayout() {
  const { user } = useAuth()
  const visible = sections.filter((s) => can(user, s.permission))

  return (
    <div className="flex-1 overflow-y-auto p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 bg-slate-900 rounded-xl flex items-center justify-center">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Administration</h1>
            <p className="text-slate-500">
              Gérez la plateforme : utilisateurs, contenus, intégrations et paramètres.
            </p>
          </div>
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
                    ? 'bg-slate-900 text-white border-slate-900 shadow-lg shadow-slate-900/20'
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

export default AdminLayout
