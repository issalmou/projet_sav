/* eslint-disable react-refresh/only-export-components */
import { useCallback, useEffect, useState } from 'react'
import { AlertTriangle, CheckCircle2, Info, X } from 'lucide-react'

const DEFAULT_DURATION = 3200

let nextId = 0

const emitter = {
  push: null,
  queue: [],
}

function emit(item) {
  if (emitter.push) {
    emitter.push(item)
  } else {
    emitter.queue.push(item)
  }
}

export function toast(message, type = 'success', options = {}) {
  const item = {
    id: ++nextId,
    message,
    type,
    duration: options.duration ?? DEFAULT_DURATION,
  }
  emit(item)
  return item.id
}

export const toastService = {
  success: (message, options) => toast(message, 'success', options),
  error: (message, options) => toast(message, 'error', options),
  info: (message, options) => toast(message, 'info', options),
  warning: (message, options) => toast(message, 'warning', options),
}

const TYPE_CONFIG = {
  success: { icon: CheckCircle2, iconClass: 'text-emerald-500', bar: 'bg-emerald-500' },
  error: { icon: AlertTriangle, iconClass: 'text-red-500', bar: 'bg-red-500' },
  warning: { icon: AlertTriangle, iconClass: 'text-amber-500', bar: 'bg-amber-500' },
  info: { icon: Info, iconClass: 'text-blue-500', bar: 'bg-blue-500' },
}

function ToastCard({ item, onClose }) {
  const config = TYPE_CONFIG[item.type] || TYPE_CONFIG.info
  const Icon = config.icon

  useEffect(() => {
    const t = setTimeout(onClose, item.duration)
    return () => clearTimeout(t)
  }, [item.duration, onClose])

  return (
    <div className="pointer-events-auto relative w-full max-w-sm overflow-hidden rounded-xl bg-white border border-slate-200 shadow-2xl toast-in">
      <div className={`absolute left-0 top-0 h-full w-1 ${config.bar}`} />
      <div className="flex items-center gap-3 pl-4 pr-3 py-3">
        <Icon className={`w-5 h-5 shrink-0 ${config.iconClass}`} />
        <p className="flex-1 min-w-0 text-sm font-medium text-slate-800">{item.message}</p>
        <button
          type="button"
          onClick={onClose}
          className="p-1 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
          aria-label="Fermer la notification"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}

export function ToastProvider() {
  const [items, setItems] = useState([])

  useEffect(() => {
    emitter.push = (item) => setItems((prev) => [...prev, item])
    emitter.queue.forEach((item) => emitter.push(item))
    emitter.queue = []
    return () => {
      emitter.push = null
    }
  }, [])

  const dismiss = useCallback((id) => {
    setItems((prev) => prev.filter((item) => item.id !== id))
  }, [])

  return (
    <div className="fixed bottom-6 right-6 z-[70] flex flex-col items-end gap-2 pointer-events-none">
      {items.map((item) => (
        <ToastCard key={item.id} item={item} onClose={() => dismiss(item.id)} />
      ))}
    </div>
  )
}

export function useToast() {
  return { showToast: toast, toastEl: null }
}
