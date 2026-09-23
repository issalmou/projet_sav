import { NavLink, useNavigate } from 'react-router-dom'
import { 
  Home,
  MessageCircle, 
  Ticket, 
  Package, 
  BarChart2, 
  Bell, 
  Settings,
  Cpu,
  LogOut
} from 'lucide-react'
import { useAuth } from '../../contexts/useAuth'
import { homeFor } from '../../contexts/roles'
import { useI18n } from '../../i18n/useI18n'

const menuItems = [
  { icon: MessageCircle, labelKey: 'nav.chat', path: '/chat' },
  { icon: Ticket, labelKey: 'nav.tickets', path: '/tickets' },
  { icon: Package, labelKey: 'nav.products', path: '/products' },
  { icon: BarChart2, labelKey: 'nav.analytics', path: '/analytics', roles: ['admin', 'agent'] },
  { icon: Bell, labelKey: 'nav.notifications', path: '/notifications' },
  { icon: Settings, labelKey: 'nav.settings', path: '/settings' },
]

function LeftSidebar() {
  const { user, logout } = useAuth()
  const { t } = useI18n()
  const navigate = useNavigate()

  const visibleItems = menuItems.filter(
    (item) => !item.roles || item.roles.includes(user?.role)
  )

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <aside className="w-64 bg-slate-900 text-white flex flex-col min-h-screen">
      {/* Logo */}
      <div className="p-6 border-b border-slate-800">
        <NavLink to={homeFor(user)} className="flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center">
            <Cpu className="w-6 h-6" />
          </div>
          <span className="text-xl font-bold tracking-tight">3LM Solutions</span>
        </NavLink>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 overflow-y-auto scrollbar-hide">
        <ul className="space-y-1 px-3">
          <li>
            <NavLink
              to="/dashboard"
              end
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-white/10 text-white border-l-3 border-blue-500'
                    : 'text-slate-400 hover:bg-white/5 hover:text-white'
                }`
              }
            >
              <Home className="w-5 h-5" />
              <span>{t('nav.home')}</span>
            </NavLink>
          </li>
          {visibleItems.map((item) => (
            <li key={item.path}>
              <NavLink
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-white/10 text-white border-l-3 border-blue-500'
                      : 'text-slate-400 hover:bg-white/5 hover:text-white'
                  }`
                }
              >
                <item.icon className="w-5 h-5" />
                <span>{t(item.labelKey)}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-slate-800">
        <button 
          onClick={handleLogout}
          className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium text-slate-400 hover:bg-white/5 hover:text-white transition-all w-full"
        >
          <LogOut className="w-5 h-5" />
          <span>{t('nav.logout')}</span>
        </button>
      </div>
    </aside>
  )
}

export default LeftSidebar