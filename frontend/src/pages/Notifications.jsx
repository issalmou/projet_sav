import { useMemo, useState } from 'react'
import {
  AlertCircle,
  AlertTriangle,
  CheckCheck,
  CheckCircle2,
  Info,
  Inbox,
  Trash2,
  Wifi,
  WifiOff,
} from 'lucide-react'
import { useNotifications } from '../contexts/useNotifications'
import { WS_STATUS } from '../services/websocket'

const LEVEL_CONFIG = {
  success: { icon: CheckCircle2, badge: 'bg-emerald-50 text-emerald-600', label: 'Succès' },
  info: { icon: Info, badge: 'bg-blue-50 text-blue-600', label: 'Information' },
  warning: { icon: AlertTriangle, badge: 'bg-amber-50 text-amber-600', label: 'Avertissement' },
  error: { icon: AlertCircle, badge: 'bg-red-50 text-red-600', label: 'Erreur' },
}

const STATUS_LABELS = {
  [WS_STATUS.CONNECTED]: { label: 'Connecté', dot: 'bg-emerald-500' },
  [WS_STATUS.CONNECTING]: { label: 'Connexion...', dot: 'bg-amber-500 animate-pulse' },
  [WS_STATUS.RECONNECTING]: { label: 'Reconnexion...', dot: 'bg-amber-500 animate-pulse' },
  [WS_STATUS.DISCONNECTED]: { label: 'Déconnecté', dot: 'bg-slate-400' },
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

function NotificationCard({ notification, onOpen }) {
  const config = LEVEL_CONFIG[notification.level] || LEVEL_CONFIG.info
  const Icon = config.icon

  return (
    <button
      onClick={() => onOpen(notification)}
      className={`w-full text-left flex items-start gap-4 px-5 py-4 border-b border-slate-100 hover:bg-slate-50 transition-colors ${
        notification.read ? '' : 'bg-blue-50/40'
      }`}
    >
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${config.badge}`}>
        <Icon className="w-5 h-5" />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-3">
          <h4 className={`text-sm truncate ${notification.read ? 'font-semibold text-slate-600' : 'font-bold text-slate-900'}`}>
            {notification.title}
          </h4>
          <span className="text-xs text-slate-400 shrink-0">{timeAgo(notification.created_at)}</span>
        </div>
        {notification.message && (
          <p className="text-sm text-slate-500 mt-0.5 line-clamp-2">{notification.message}</p>
        )}
        <div className="flex items-center gap-2 mt-2">
          <span className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-500 text-[10px] font-bold uppercase tracking-wide">
            {notification.category}
          </span>
          {!notification.read && (
            <span className="w-2 h-2 rounded-full bg-blue-500" aria-label="Non lue" />
          )}
        </div>
      </div>
    </button>
  )
}

function Notifications() {
  const { notifications, unreadCount, connectionStatus, markAsRead, markAllRead, clearNotifications } =
    useNotifications()
  const [filter, setFilter] = useState('all')

  const visibleNotifications = useMemo(
    () => (filter === 'unread' ? notifications.filter((n) => !n.read) : notifications),
    [notifications, filter]
  )

  const handleOpen = (notification) => {
    if (!notification.read) markAsRead(notification.id)
  }

  const status = STATUS_LABELS[connectionStatus] || STATUS_LABELS[WS_STATUS.DISCONNECTED]

  return (
    <div className="flex-1 overflow-y-auto p-8">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Notifications</h1>
            <p className="text-slate-500">Événements et alertes en temps réel sur votre activité.</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={markAllRead}
              disabled={unreadCount === 0}
              className="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-semibold text-slate-600 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <CheckCheck className="w-4 h-4" />
              Tout marquer comme lu
            </button>
            <button
              onClick={clearNotifications}
              disabled={notifications.length === 0}
              title="Effacer toutes les notifications"
              className="p-2.5 text-slate-500 bg-white border border-slate-200 rounded-xl hover:bg-red-50 hover:text-red-600 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Connection status */}
        <div className="flex items-center gap-2 text-xs font-semibold">
          {connectionStatus === WS_STATUS.CONNECTED ? (
            <Wifi className="w-4 h-4 text-emerald-500" />
          ) : (
            <WifiOff className="w-4 h-4 text-slate-400" />
          )}
          <span className="text-slate-600">Notifications temps réel</span>
          <span className={`w-2 h-2 rounded-full ${status.dot}`} />
          <span className="text-slate-400">{status.label}</span>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setFilter('all')}
            className={`px-4 py-2 rounded-xl text-sm font-semibold border transition-colors ${
              filter === 'all'
                ? 'bg-slate-900 text-white border-slate-900'
                : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-100'
            }`}
          >
            Toutes ({notifications.length})
          </button>
          <button
            onClick={() => setFilter('unread')}
            className={`px-4 py-2 rounded-xl text-sm font-semibold border transition-colors ${
              filter === 'unread'
                ? 'bg-slate-900 text-white border-slate-900'
                : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-100'
            }`}
          >
            Non lues ({unreadCount})
          </button>
        </div>

        {/* List */}
        <div className="bg-white rounded-2xl border border-slate-200 custom-shadow overflow-hidden">
          {visibleNotifications.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mb-4">
                <Inbox className="w-8 h-8 text-slate-300" />
              </div>
              <h3 className="text-sm font-bold text-slate-900 mb-1">
                {filter === 'unread' && notifications.length > 0 ? 'Aucune notification non lue' : 'Aucune notification'}
              </h3>
              <p className="text-xs text-slate-500 max-w-xs">
                {notifications.length === 0
                  ? 'Les nouvelles notifications apparaîtront ici en temps réel dès qu\'elles seront reçues.'
                  : 'Toutes vos notifications sont marquées comme lues.'}
              </p>
            </div>
          ) : (
            visibleNotifications.map((notification) => (
              <NotificationCard
                key={notification.id}
                notification={notification}
                onOpen={handleOpen}
              />
            ))
          )}
        </div>
      </div>
    </div>
  )
}

export default Notifications
