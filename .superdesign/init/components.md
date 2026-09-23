# Shared UI Components

## Stack
- React 19 + Vite 8
- Tailwind CSS 4 via `@tailwindcss/vite`
- Icons from `lucide-react`
- No external component library; reusable UI is custom React and Tailwind.

## `frontend/src/components/admin/ui.jsx`
Reusable admin/form primitives: input token, page header, field wrapper, switch, modal, confirmation modal, and empty state.

```jsx
import { X, AlertTriangle } from 'lucide-react'

export const inputClass =
  'w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all'

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">{title}</h1>
        {subtitle && <p className="text-slate-500 mt-1">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-3 shrink-0">{actions}</div>}
    </div>
  )
}

export function Field({ label, required, error, hint, children }) {
  return (
    <div className="space-y-1.5">
      <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
        {label} {required && <span className="text-red-400">*</span>}
      </label>
      {children}
      {hint && !error && <p className="text-xs text-slate-400">{hint}</p>}
      {error && <p className="text-xs text-red-500 font-medium">{error}</p>}
    </div>
  )
}

export function Toggle({ checked, onChange, disabled }) {
  return (
    <button type="button" role="switch" aria-checked={checked} disabled={disabled} onClick={() => onChange(!checked)} className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors ${checked ? 'bg-blue-600' : 'bg-slate-300'} ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}>
      <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${checked ? 'translate-x-6' : 'translate-x-1'}`} />
    </button>
  )
}

export function Modal({ open, onClose, title, children, footer, wide }) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm" onClick={onClose} />
      <div className={`relative w-full ${wide ? 'max-w-2xl' : 'max-w-lg'} bg-white rounded-2xl shadow-2xl overflow-hidden`}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <h3 className="text-base font-bold text-slate-900">{title}</h3>
          <button onClick={onClose} className="p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 rounded-lg transition-colors"><X className="w-4 h-4" /></button>
        </div>
        <div className="px-6 py-5 max-h-[70vh] overflow-y-auto">{children}</div>
        {footer && <div className="px-6 py-4 border-t border-slate-100 bg-slate-50/60 flex items-center justify-end gap-3">{footer}</div>}
      </div>
    </div>
  )
}

export function ConfirmModal({ open, onClose, onConfirm, title = 'Confirmer la suppression', message, confirmLabel = 'Supprimer', danger = true }) {
  return <Modal open={open} onClose={onClose} title={title} footer={<><button onClick={onClose} className="px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition-colors">Annuler</button><button onClick={() => { onConfirm(); onClose() }} className={`px-4 py-2 text-sm font-semibold text-white rounded-xl transition-colors ${danger ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700'}`}>{confirmLabel}</button></>}><div className="flex items-start gap-4"><div className="w-10 h-10 rounded-full bg-red-50 text-red-600 flex items-center justify-center shrink-0"><AlertTriangle className="w-5 h-5" /></div><p className="text-sm text-slate-600 leading-relaxed pt-1.5">{message}</p></div></Modal>
}

export function EmptyState({ icon: Icon, title, message, action }) {
  return <div className="flex flex-col items-center justify-center py-16 text-center"><div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mb-4"><Icon className="w-8 h-8 text-slate-300" /></div><h3 className="text-sm font-bold text-slate-900 mb-1">{title}</h3>{message && <p className="text-xs text-slate-500 max-w-xs">{message}</p>}{action && <div className="mt-4">{action}</div>}</div>
}
```

## `frontend/src/components/admin/badges.jsx`
Pill badges for roles, documents, status, severity, and integrations.

```jsx
import { ROLES } from '../../contexts/roles'
export function Badge({ className, children }) { return <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 text-[11px] font-bold rounded-full border ${className}`}>{children}</span> }
export function RoleBadge({ role }) { const r = ROLES[role]; if (!r) return <Badge className="bg-slate-50 text-slate-600 border-slate-200">{role}</Badge>; return <Badge className={r.color}><span className={`w-1.5 h-1.5 rounded-full ${r.dot}`} />{r.label}</Badge> }
export function DocTypeBadge({ type }) { const map = { faq: { label: 'FAQ', color: 'bg-blue-50 text-blue-600 border-blue-100' }, manual: { label: 'Manuel', color: 'bg-violet-50 text-violet-600 border-violet-100' }, guide: { label: 'Guide', color: 'bg-amber-50 text-amber-600 border-amber-100' } }; const m = map[type] || { label: type, color: 'bg-slate-50 text-slate-600 border-slate-200' }; return <Badge className={m.color}>{m.label}</Badge> }
export function DocStatusBadge({ status }) { return status === 'published' ? <Badge className="bg-teal-50 text-teal-600 border-teal-100">Publié</Badge> : <Badge className="bg-amber-50 text-amber-600 border-amber-100">Brouillon</Badge> }
export function StatusBadge({ status }) { return status === 'active' ? <Badge className="bg-teal-50 text-teal-600 border-teal-100">Actif</Badge> : <Badge className="bg-slate-100 text-slate-500 border-slate-200">Inactif</Badge> }
export function SeverityBadge({ severity }) { const map = { info: ['Info', 'bg-blue-50 text-blue-600 border-blue-100'], warning: ['Avertissement', 'bg-amber-50 text-amber-600 border-amber-100'], critical: ['Critique', 'bg-red-50 text-red-600 border-red-100'] }; const m = map[severity] || map.info; return <Badge className={m[1]}>{m[0]}</Badge> }
export function IntegrationBadge({ status }) { const map = { connected: ['Connecté', 'bg-teal-50 text-teal-600 border-teal-100', 'bg-teal-500'], error: ['Erreur', 'bg-red-50 text-red-600 border-red-100', 'bg-red-500'], disconnected: ['Déconnecté', 'bg-slate-100 text-slate-500 border-slate-200', 'bg-slate-400'] }; const m = map[status] || map.disconnected; return <Badge className={m[1]}><span className={`w-1.5 h-1.5 rounded-full ${m[2]}`} />{m[0]}</Badge> }
```

## Other reusable visual components
- `frontend/src/components/dashboard/StatCard.jsx`: metric card with icon, value, subtitle/trend, and blue/teal/indigo/orange color variants.
- `frontend/src/components/tickets/StatusBadge.jsx`, `PriorityBadge.jsx`, `CategoryBadge.jsx`, `StatusSelect.jsx`: ticket state pills and a two-column status selector using `STATUSES`, `PRIORITIES`, and category tokens.
- `frontend/src/components/products/ProductCard.jsx`: responsive product card and compact selectable card; supports images, category icon, warranty state, selected/highlighted states, and navigation.
- `frontend/src/components/products/CategoryFilter.jsx`: category pill filter with counts and category-specific color families.
- `frontend/src/components/products/WarrantyBadge.jsx`: active/expiring/expired/none warranty badge, dot, and border wrappers.
- `frontend/src/components/products/ProductSelector.jsx`: searchable modal/dropdown selector combining category, warranty, keyboard navigation, and `ProductCard`.
