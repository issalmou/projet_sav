import { useState, useEffect, useCallback } from 'react'
import { AlertTriangle, CheckCircle2 } from 'lucide-react'

export function useToast() {
  const [toast, setToast] = useState(null)

  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => setToast(null), 3200)
    return () => clearTimeout(t)
  }, [toast])

  const showToast = useCallback((message, type = 'success') => {
    setToast({ message, type })
  }, [])

  const toastEl = toast && (
    <div
      className={`fixed bottom-6 right-6 z-[60] flex items-center gap-2 px-4 py-3 rounded-xl text-sm font-semibold text-white shadow-2xl ${
        toast.type === 'error' ? 'bg-red-600' : 'bg-slate-900'
      }`}
    >
      {toast.type === 'error' ? (
        <AlertTriangle className="w-4 h-4 shrink-0" />
      ) : (
        <CheckCircle2 className="w-4 h-4 shrink-0" />
      )}
      {toast.message}
    </div>
  )

  return { toastEl, showToast }
}
