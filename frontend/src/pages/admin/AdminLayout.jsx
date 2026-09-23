import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  Users,
  BookOpen,
  Package,
  Plug,
  Activity,
  Settings,
  Shield,
  Ticket,
  LogOut,
} from 'lucide-react'
import { useAuth } from '../../contexts/useAuth'
import { can } from '../../contexts/roles'
import { useI18n } from '../../i18n/useI18n'

const sections = [
  {
    labelKey: 'admin.nav.overview',
    path: '/admin',
    end: true,
    icon: LayoutDashboard,
    permission: 'admin.view',
  },
  {
    labelKey: 'admin.nav.tickets',
    path: '/admin/tickets',
    icon: Ticket,
    permission: 'admin.view',
  },
  {
    labelKey: 'admin.nav.users',
    path: '/admin/users',
    icon: Users,
    permission: 'users.manage',
  },
  {
    labelKey: 'admin.nav.documents',
    path: '/admin/documents',
    icon: BookOpen,
    permission: 'documents.manage',
  },
  {
    labelKey: 'admin.nav.products',
    path: '/admin/products',
    icon: Package,
    permission: 'documents.manage',
  },
  {
    labelKey: 'admin.nav.integrations',
    path: '/admin/integrations',
    icon: Plug,
    permission: 'integrations.manage',
  },
  {
    labelKey: 'admin.nav.logs',
    path: '/admin/logs',
    icon: Activity,
    permission: 'logs.view',
  },
  {
    labelKey: 'admin.nav.settings',
    path: '/admin/settings',
    icon: Settings,
    permission: 'settings.manage',
  },
]

function AdminLayout() {
  const { user, logout } = useAuth()
  const { t } = useI18n()
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
            <div className="w-11 h-11 bg-slate-900 rounded-xl flex items-center justify-center">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">{t('admin.layout.title')}</h1>
              <p className="text-slate-500">{t('admin.layout.subtitle')}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-xl transition-colors"
          >
            <LogOut className="w-4 h-4" />
            {t('topbar.logout')}
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
                    ? 'bg-slate-900 text-white border-slate-900 shadow-lg shadow-slate-900/20'
                    : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                }`
              }
            >
              <s.icon className="w-4 h-4" />
              {t(s.labelKey)}
            </NavLink>
          ))}
        </nav>

        <Outlet />
      </div>
    </div>
  )
}

export default AdminLayout
