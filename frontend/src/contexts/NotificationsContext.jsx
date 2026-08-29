import { createContext, useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { useAuth } from './useAuth'
import { NotificationSocket, WS_STATUS, WS_URL } from '../services/websocket'
import { toastService } from '../services/toast'

const NotificationsContext = createContext(null)
const MAX_NOTIFICATIONS = 50

function normalizeNotification(item) {
  return {
    id: item.id || `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    title: item.title || 'Notification',
    message: item.message || item.body || '',
    level: item.level || 'info',
    category: item.category || 'system',
    read: Boolean(item.read),
    created_at: item.created_at || item.createdAt || new Date().toISOString(),
  }
}

function toastForNotification(notification) {
  const method = { error: 'error', warning: 'warning', success: 'success' }[notification.level] || 'info'
  toastService[method]?.(notification.title)
}

export function NotificationsProvider({ children }) {
  const { user, isAuthenticated } = useAuth()
  const token = user?.access_token || user?.token || null

  const [notifications, setNotifications] = useState([])
  const [connectionStatus, setConnectionStatus] = useState(WS_STATUS.DISCONNECTED)
  const socketRef = useRef(null)

  const handleIncoming = useCallback((message) => {
    const raw = message?.notification || message?.data
    if (!raw) return

    const notification = normalizeNotification(raw)
    setNotifications((prev) => {
      if (prev.some((n) => n.id === notification.id)) return prev
      return [notification, ...prev].slice(0, MAX_NOTIFICATIONS)
    })
    toastForNotification(notification)
  }, [])

  useEffect(() => {
    if (!isAuthenticated) {
      socketRef.current?.disconnect()
      socketRef.current = null
      return
    }

    // Backend disponible (token JWT) : connexion WebSocket réelle.
    if (token) {
      const socket = new NotificationSocket({
        url: WS_URL,
        token,
        onMessage: handleIncoming,
        onStatusChange: setConnectionStatus,
      })
      socketRef.current = socket
      socket.connect()
      return () => {
        socket.disconnect()
        socketRef.current = null
      }
    }
  }, [isAuthenticated, token, handleIncoming])

  const markAsRead = useCallback((id) => {
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)))
  }, [])

  const markAllRead = useCallback(() => {
    setNotifications((prev) => (prev.every((n) => n.read) ? prev : prev.map((n) => ({ ...n, read: true }))))
  }, [])

  const clearNotifications = useCallback(() => {
    setNotifications([])
  }, [])

  const value = useMemo(
    () => ({
      notifications,
      unreadCount: notifications.filter((n) => !n.read).length,
      connectionStatus,
      markAsRead,
      markAllRead,
      clearNotifications,
    }),
    [notifications, connectionStatus, markAsRead, markAllRead, clearNotifications]
  )

  return (
    <NotificationsContext.Provider value={value}>{children}</NotificationsContext.Provider>
  )
}

export default NotificationsContext
