import { API_URL } from '../api/auth'

// URL du serveur WebSocket. Surchargeable via VITE_WS_URL, sinon dérivée de
// l'URL de l'API (http -> ws) en pointant sur /ws/notifications.
export const WS_URL =
  import.meta.env.VITE_WS_URL || `${API_URL.replace(/^http/, 'ws')}/ws/notifications`

export const WS_STATUS = {
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  RECONNECTING: 'reconnecting',
  DISCONNECTED: 'disconnected',
}

const RECONNECT_BASE_DELAY = 1000
const RECONNECT_MAX_DELAY = 30000
const HEARTBEAT_INTERVAL = 30000

export class NotificationSocket {
  constructor({ url, token, onMessage, onStatusChange }) {
    this.url = url
    this.token = token
    this.onMessage = onMessage
    this.onStatusChange = onStatusChange

    this.socket = null
    this.status = WS_STATUS.DISCONNECTED
    this.shouldReconnect = false
    this.reconnectAttempt = 0
    this.reconnectTimer = null
    this.heartbeatTimer = null
  }

  connect(token = this.token) {
    this.token = token ?? this.token
    if (!this.token) {
      this.disconnect()
      return
    }
    this.shouldReconnect = true
    this._open()
  }

  disconnect() {
    this.shouldReconnect = false
    this._clearReconnectTimer()
    this._stopHeartbeat()
    if (this.socket) {
      this.socket.onclose = null
      this.socket.close()
      this.socket = null
    }
    this._setStatus(WS_STATUS.DISCONNECTED)
  }

  send(payload) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(payload))
    }
  }

  _open() {
    if (!this.shouldReconnect || !this.token) return

    this._clearReconnectTimer()
    this._setStatus(WS_STATUS.CONNECTING)

    try {
      this.socket = new WebSocket(`${this.url}?token=${encodeURIComponent(this.token)}`)
    } catch {
      this._scheduleReconnect()
      return
    }

    this.socket.onopen = () => {
      this.reconnectAttempt = 0
      this._setStatus(WS_STATUS.CONNECTED)
      this._startHeartbeat()
    }

    this.socket.onmessage = (event) => this._handleMessage(event)

    this.socket.onerror = () => {
      // L'erreur est traitée par onclose (le navigateur ferme la socket).
    }

    this.socket.onclose = () => {
      this._stopHeartbeat()
      if (this.shouldReconnect) {
        this._setStatus(WS_STATUS.RECONNECTING)
        this._scheduleReconnect()
      } else {
        this._setStatus(WS_STATUS.DISCONNECTED)
      }
    }
  }

  _handleMessage(event) {
    let payload
    try {
      payload = JSON.parse(event.data)
    } catch {
      return
    }

    // Heartbeat applicatif : répond au ping serveur.
    if (payload && payload.type === 'ping') {
      this.send({ type: 'pong' })
      return
    }

    // Acquittement de connexion : rien à afficher.
    if (payload && payload.type === 'connected') return

    if (typeof this.onMessage === 'function') {
      this.onMessage(payload)
    }
  }

  _startHeartbeat() {
    this._stopHeartbeat()
    this.heartbeatTimer = setInterval(() => {
      this.send({ type: 'ping' })
    }, HEARTBEAT_INTERVAL)
  }

  _stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  _scheduleReconnect() {
    this._clearReconnectTimer()
    const delay = Math.min(RECONNECT_BASE_DELAY * 2 ** this.reconnectAttempt, RECONNECT_MAX_DELAY)
    this.reconnectAttempt += 1
    this.reconnectTimer = setTimeout(() => this._open(), delay)
  }

  _clearReconnectTimer() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
  }

  _setStatus(status) {
    this.status = status
    if (typeof this.onStatusChange === 'function') {
      this.onStatusChange(status)
    }
  }
}
