import { createContext, useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { useAuth } from './useAuth'
import { NotificationSocket, WS_STATUS, WS_URL } from '../services/websocket'
import { toastService } from '../services/toast'
import { apiRequest } from '../api/client'
import { loadNotificationPrefs, PREFERENCES_CHANGED_EVENT } from '../services/notificationPreferences'
import { STATUSES } from '../components/tickets/constants'

const NotificationsContext = createContext(null)
const MAX_NOTIFICATIONS = 50
const DEBUG_NOTIFICATIONS = import.meta.env.DEV
const POLL_INTERVAL_MS = 30000
const SNAPSHOT_STORAGE_PREFIX = 'sav-notifications-snapshot'
// Le WebSocket est optionnel : le polling REST est le canal par défaut tant
// que le backend n'expose pas d'endpoint temps réel.
const WS_AVAILABLE = Boolean(WS_URL)

// Le snapshot est persisté entre les sessions : un ticket créé pendant que
// l'utilisateur est déconnecté déclenche tout de même sa notification au
// poll suivant.
function loadStoredSnapshot(userId) {
  try {
    const raw = localStorage.getItem(`${SNAPSHOT_STORAGE_PREFIX}-${userId}`)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    return {
      tickets: parsed.tickets || {},
      products: parsed.products || [],
    }
  } catch {
    return null
  }
}

function saveStoredSnapshot(userId, snapshot) {
  try {
    localStorage.setItem(
      `${SNAPSHOT_STORAGE_PREFIX}-${userId}`,
      JSON.stringify({ tickets: snapshot.tickets, products: snapshot.products })
    )
  } catch {
    // Stockage indisponible : le dédoublonnage reste assuré en session.
  }
}

// Coerce une valeur (string ou objet comme { title, name, description }) vers
// un texte affichable. Normalisée dès la réception pour ne jamais laisser un
// objet être rendu par React dans le composant d'affichage.
function asText(value, fallback = '') {
  if (typeof value === 'string') return value
  if (value == null) return fallback
  if (typeof value === 'object') {
    return value.description || value.name || value.title || value.message || fallback
  }
  return String(value)
}

function normalizeNotification(item) {
  const createdAt = item.created_at || item.createdAt || new Date().toISOString()
  const title = asText(item.title, 'Notification')
  const message = asText(item.message ?? item.body, '')
  const fallbackId = `${title}-${message}-${createdAt}`
  return {
    id: item.id || fallbackId,
    key: item.key || null,
    title,
    message,
    level: item.level || 'info',
    category: item.category || 'system',
    read: Boolean(item.read),
    created_at: createdAt,
  }
}

// Renvoie l'identifiant de l'assigné d'un ticket, ou null si aucun n'est défini.
function getAssigneeId(ticket) {
  return (
    ticket?.assigned_technician_id ??
    ticket?.assignee_id ??
    ticket?.assigneeId ??
    ticket?.technician_id ??
    ticket?.assigned_to ??
    ticket?.assigned_technician?.id ??
    null
  )
}

function statusLabel(status) {
  return STATUSES[status]?.label || status || 'inconnu'
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
  const seenNotificationIdsRef = useRef(new Set())
  const seenNotificationKeysRef = useRef(new Set())
  const snapshotRef = useRef(null)
  const pollingRef = useRef(false)
  const notificationPrefsRef = useRef(loadNotificationPrefs(user?.id))

  useEffect(() => {
    notificationPrefsRef.current = loadNotificationPrefs(user?.id)
    const sync = () => {
      notificationPrefsRef.current = loadNotificationPrefs(user?.id)
    }
    window.addEventListener(PREFERENCES_CHANGED_EVENT, sync)
    return () => window.removeEventListener(PREFERENCES_CHANGED_EVENT, sync)
  }, [user?.id])

  const addNotification = useCallback((raw) => {
    const notification = normalizeNotification(raw)
    if (seenNotificationIdsRef.current.has(notification.id)) return
    // La clé canonique garantit qu'un même événement n'est jamais répété.
    if (notification.key && seenNotificationKeysRef.current.has(notification.key)) return

    seenNotificationIdsRef.current.add(notification.id)
    if (notification.key) seenNotificationKeysRef.current.add(notification.key)
    setNotifications((prev) => [notification, ...prev].slice(0, MAX_NOTIFICATIONS))
    toastForNotification(notification)
    if (DEBUG_NOTIFICATIONS) {
      console.log('[notifications] notification ajoutée', notification.id, notification.key || '')
    }
  }, [])

  // Canal temps réel optionnel (WebSocket si VITE_WS_URL est configuré et que
  // le backend l'expose). Le dédoublonnage avec le polling repose sur les
  // clés canoniques partagées.
  const handleIncoming = useCallback((message) => {
    const raw = message?.notification || message?.data
    if (!raw) return

    addNotification(raw)
  }, [addNotification])

  useEffect(() => {
    if (!isAuthenticated) {
      socketRef.current?.disconnect()
      socketRef.current = null
      seenNotificationIdsRef.current.clear()
      seenNotificationKeysRef.current.clear()
      return
    }

    if (token && WS_AVAILABLE) {
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

    return undefined
  }, [isAuthenticated, token, handleIncoming])

  // Canal par défaut : polling REST sur les endpoints existants.
  // Tant que la socket n'est pas connectée, le polling livre les notifications.
  // Dès qu'elle est connectée, il est suspendu pour éviter les doublons, puis
  // reprend automatiquement en cas de perte de connexion (fallback).
  const usePolling = !(WS_AVAILABLE && connectionStatus === WS_STATUS.CONNECTED)

  useEffect(() => {
    if (!isAuthenticated || !token || !user?.id) return undefined
    if (!usePolling) return undefined

    const isClient = user?.role === 'client'
    let cancelled = false

    const detectChanges = async () => {
      if (cancelled || pollingRef.current) return
      pollingRef.current = true
      try {
        const [ticketsResult, productsResult] = await Promise.allSettled([
          apiRequest('/tickets/', { token }),
          isClient
            ? apiRequest(`/clients/${user.id}/products`, { token })
            : Promise.resolve(null),
        ])
        if (cancelled) return

        const tickets = ticketsResult.status === 'fulfilled'
          ? Array.isArray(ticketsResult.value) ? ticketsResult.value : ticketsResult.value?.items || []
          : []
        const products = isClient && productsResult.status === 'fulfilled'
          ? Array.isArray(productsResult.value) ? productsResult.value : productsResult.value?.items || []
          : []
        if (cancelled) return

        if (DEBUG_NOTIFICATIONS) {
          console.log('[notifications] poll', {
            role: user?.role,
            tickets: tickets.length,
            products: products.length,
          })
        }

        const prefs = notificationPrefsRef.current
        const notificationsEnabled = Boolean(prefs?.notificationsEnabled)
        const ticketAlerts = notificationsEnabled && Boolean(prefs?.ticketUpdates)
        const productAlerts = notificationsEnabled && Boolean(prefs?.productAlerts)
        const previous = snapshotRef.current

        const newTickets = {}
        tickets.forEach((ticket) => {
          const id = String(ticket.id)
          const status = String(ticket.status ?? '')
          const assignee = String(getAssigneeId(ticket) ?? '')
          const previousTicket = previous?.tickets?.[id]

          if (!previousTicket) {
            if (ticketAlerts) {
              const title = asText(ticket.title)
              addNotification({
                id: `ticket-new-${id}`,
                key: `ticket:${id}:new`,
                title: 'Nouveau ticket',
                message: title ? `Un nouveau ticket a été créé : « ${title} ».` : 'Un nouveau ticket a été créé.',
                category: 'ticket',
                level: 'info',
              })
            }
          } else {
            if (status && previousTicket.status && status !== previousTicket.status) {
              if (ticketAlerts) {
                addNotification({
                  id: `ticket-status-${id}-${status}`,
                  key: `ticket:${id}:status:${status}`,
                  title: 'Ticket mis à jour',
                  message: `Le statut du ticket est passé à « ${statusLabel(status)} ».`,
                  category: 'ticket',
                  level: 'info',
                })
              }
            }
            if (assignee && previousTicket.assignee !== assignee) {
              if (ticketAlerts) {
                const title = asText(ticket.title)
                addNotification({
                  id: `ticket-assignee-${id}-${assignee}`,
                  key: `ticket:${id}:assignee:${assignee}`,
                  title: 'Ticket réassigné',
                  message: title ? `Le ticket « ${title} » a été réassigné.` : 'Un ticket a été réassigné.',
                  category: 'ticket',
                  level: 'info',
                })
              }
            }
          }
          newTickets[id] = { status, assignee }
        })

        const newProducts = [...(previous?.products || [])]
        products.forEach((product) => {
          const id = String(product?.id)
          if (!id || previous?.products?.includes(id)) return
          if (productAlerts) {
            addNotification({
              id: `product-${id}`,
              key: `product:${id}`,
              title: 'Produit assigné',
              message: 'Un nouveau produit est disponible dans votre compte.',
              category: 'product',
              level: 'success',
            })
          }
          newProducts.push(id)
        })

        if (cancelled) return
        snapshotRef.current = { tickets: newTickets, products: newProducts }
        saveStoredSnapshot(user.id, snapshotRef.current)
      } catch (err) {
        if (DEBUG_NOTIFICATIONS) {
          console.error('[notifications] erreur durant le polling', err)
        }
      } finally {
        pollingRef.current = false
      }
    }

    snapshotRef.current = loadStoredSnapshot(user.id)
    detectChanges()
    const intervalId = window.setInterval(detectChanges, POLL_INTERVAL_MS)
    return () => {
      cancelled = true
      window.clearInterval(intervalId)
    }
  }, [isAuthenticated, token, user?.id, user?.role, usePolling, addNotification])

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