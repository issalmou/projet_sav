import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  AlertCircle,
  AlertTriangle,
  Bell,
  CheckCircle2,
  ChevronDown,
  Info,
  LogOut,
  Search,
  Settings,
  User,
} from 'lucide-react'
import { useAuth } from '../../contexts/useAuth'
import { useNotifications } from '../../contexts/useNotifications'
import { roleLabel } from '../../contexts/roles'

const LEVEL_CONFIG = {
  success: { icon: CheckCircle2, badge: 'bg-emerald-50 text-emerald-600' },
  info: { icon: Info, badge: 'bg-blue-50 text-blue-600' },
  warning: { icon: AlertTriangle, badge: 'bg-amber-50 text-amber-600' },
  error: { icon: AlertCircle, badge: 'bg-red-50 text-red-600' },
}

function timeAgo(iso) {
  if (!iso) return ''
  const seconds = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (seconds < 60) return 'à l\'instant'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `il y a ${minutes} min`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `il y a ${hours} h`
  const days = Math.floor(hours / 24)
  if (days < 7) return `il y a ${days} j`
  return new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

function NotificationDropdown({ onNavigate }) {
  const { notifications, unreadCount, markAsRead, markAllRead } = useNotifications()
  const recent = notifications.slice(0, 8)

  return (
    <div className="absolute right-0 mt-2 w-80 bg-white rounded-xl shadow-lg border border-slate-200 z-50 overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
        <p className="text-sm font-bold text-slate-900">
          Notifications
          {unreadCount > 0 && (
            <span className="ml-2 px-1.5 py-0.5 rounded-full bg-blue-600 text-white text-[10px] font-bold">
              {unreadCount}
            </span>
          )}
        </p>
        <button
          onClick={markAllRead}
          disabled={unreadCount === 0}
          className="text-xs font-semibold text-blue-600 hover:text-blue-700 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Tout marquer comme lu
        </button>
      </div>

      {recent.length === 0 ? (
        <div className="px-4 py-10 text-center">
          <p className="text-sm text-slate-500">Aucune notification</p>
        </div>
      ) : (
        <div className="max-h-80 overflow-y-auto divide-y divide-slate-50">
          {recent.map((notification) => {
            const config = LEVEL_CONFIG[notification.level] || LEVEL_CONFIG.info
            const Icon = config.icon
            return (
              <button
                key={notification.id}
                onClick={() => {
                  if (!notification.read) markAsRead(notification.id)
                  onNavigate()
                }}
                className={`w-full text-left flex items-start gap-3 px-4 py-3 hover:bg-slate-50 transition-colors ${
                  notification.read ? '' : 'bg-blue-50/40'
                }`}
              >
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${config.badge}`}>
                  <Icon className="w-4 h-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <p className={`text-xs truncate ${notification.read ? 'font-semibold text-slate-600' : 'font-bold text-slate-900'}`}>
                      {notification.title}
                    </p>
                    <span className="text-[10px] text-slate-400 shrink-0">{timeAgo(notification.created_at)}</span>
                  </div>
                  {notification.message && (
                    <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{notification.message}</p>
                  )}
                </div>
                {!notification.read && <span className="w-2 h-2 rounded-full bg-blue-500 shrink-0 mt-1" />}
              </button>
            )
          })}
        </div>
      )}

      <div className="px-4 py-2.5 border-t border-slate-100">
        <button
          onClick={onNavigate}
          className="w-full py-2 text-xs font-bold text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
        >
          Voir toutes les notifications
        </button>
      </div>
    </div>
  )
}

function TopNavBar() {
  const { user, logout } = useAuth()
  const { unreadCount, connectionStatus } = useNotifications()
  const navigate = useNavigate()
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [bellOpen, setBellOpen] = useState(false)
  const dropdownRef = useRef(null)
  const bellRef = useRef(null)

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setDropdownOpen(false)
      }
      if (bellRef.current && !bellRef.current.contains(e.target)) {
        setBellOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleLogout = () => {
    setDropdownOpen(false)
    logout()
    navigate('/login')
  }

  return (
    <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6">
      {/* Search Bar */}
      <div className="flex-1 max-w-xl">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
          <input
            type="text"
            placeholder="Rechercher..."
            className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
          />
        </div>
      </div>

      {/* Right Section */}
      <div className="flex items-center gap-4">
        {/* Notifications */}
        <div className="relative" ref={bellRef}>
          <button
            onClick={() => setBellOpen(!bellOpen)}
            className="relative p-2 text-slate-500 hover:bg-slate-100 rounded-lg transition-colors"
            aria-label="Notifications"
          >
            <Bell className="w-5 h-5" />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
            {unreadCount === 0 && connectionStatus === 'connected' && (
              <span className="absolute top-0 right-0 w-2 h-2 bg-emerald-500 rounded-full" />
            )}
          </button>
          {bellOpen && <NotificationDropdown onNavigate={() => { setBellOpen(false); navigate('/notifications') }} />}
        </div>

        {/* User Profile Dropdown */}
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center gap-3 pl-4 border-l border-slate-200 hover:bg-slate-50 rounded-lg py-1.5 pr-2 transition-colors"
          >
            <div className="w-9 h-9 bg-blue-600 rounded-full flex items-center justify-center text-white text-sm font-bold">
              {user?.initials || 'U'}
            </div>
            <div className="hidden md:block text-left">
              <p className="text-sm font-semibold text-slate-900">{user?.name || 'Utilisateur'}</p>
              <p className="text-xs text-slate-500">{roleLabel(user?.role) || 'Rôle'}</p>
            </div>
            <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${dropdownOpen ? 'rotate-180' : ''}`} />
          </button>

          {/* Dropdown Menu */}
          {dropdownOpen && (
            <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-lg border border-slate-200 py-1 z-50">
              <div className="px-4 py-3 border-b border-slate-100">
                <p className="text-sm font-semibold text-slate-900">{user?.name || 'Utilisateur'}</p>
                <p className="text-xs text-slate-500 mt-0.5">{user?.email || ''}</p>
              </div>
              <button
                onClick={() => { setDropdownOpen(false); navigate('/settings') }}
                className="flex items-center gap-3 w-full px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
              >
                <User className="w-4 h-4" />
                Mon profil
              </button>
              <button
                onClick={() => { setDropdownOpen(false); navigate('/settings') }}
                className="flex items-center gap-3 w-full px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
              >
                <Settings className="w-4 h-4" />
                Paramètres
              </button>
              <div className="border-t border-slate-100 mt-1 pt-1">
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-3 w-full px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                  Déconnexion
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}

export default TopNavBar
