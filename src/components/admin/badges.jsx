import { ROLES } from '../../contexts/roles'

export function Badge({ className, children }) {
  return (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-0.5 text-[11px] font-bold rounded-full border ${className}`}
    >
      {children}
    </span>
  )
}

export function RoleBadge({ role }) {
  const r = ROLES[role]
  if (!r) return <Badge className="bg-slate-50 text-slate-600 border-slate-200">{role}</Badge>
  return (
    <Badge className={r.color}>
      <span className={`w-1.5 h-1.5 rounded-full ${r.dot}`} />
      {r.label}
    </Badge>
  )
}

export function DocTypeBadge({ type }) {
  const map = {
    faq: { label: 'FAQ', color: 'bg-blue-50 text-blue-600 border-blue-100' },
    manual: { label: 'Manuel', color: 'bg-violet-50 text-violet-600 border-violet-100' },
    guide: { label: 'Guide', color: 'bg-amber-50 text-amber-600 border-amber-100' },
  }
  const m = map[type] || { label: type, color: 'bg-slate-50 text-slate-600 border-slate-200' }
  return <Badge className={m.color}>{m.label}</Badge>
}

export function DocStatusBadge({ status }) {
  return status === 'published' ? (
    <Badge className="bg-teal-50 text-teal-600 border-teal-100">Publié</Badge>
  ) : (
    <Badge className="bg-amber-50 text-amber-600 border-amber-100">Brouillon</Badge>
  )
}

export function StatusBadge({ status }) {
  return status === 'active' ? (
    <Badge className="bg-teal-50 text-teal-600 border-teal-100">Actif</Badge>
  ) : (
    <Badge className="bg-slate-100 text-slate-500 border-slate-200">Inactif</Badge>
  )
}

export function SeverityBadge({ severity }) {
  const map = {
    info: { label: 'Info', color: 'bg-blue-50 text-blue-600 border-blue-100' },
    warning: { label: 'Avertissement', color: 'bg-amber-50 text-amber-600 border-amber-100' },
    critical: { label: 'Critique', color: 'bg-red-50 text-red-600 border-red-100' },
  }
  const m = map[severity] || map.info
  return <Badge className={m.color}>{m.label}</Badge>
}

export function IntegrationBadge({ status }) {
  const map = {
    connected: {
      label: 'Connecté',
      color: 'bg-teal-50 text-teal-600 border-teal-100',
      dot: 'bg-teal-500',
    },
    error: {
      label: 'Erreur',
      color: 'bg-red-50 text-red-600 border-red-100',
      dot: 'bg-red-500',
    },
    disconnected: {
      label: 'Déconnecté',
      color: 'bg-slate-100 text-slate-500 border-slate-200',
      dot: 'bg-slate-400',
    },
  }
  const m = map[status] || map.disconnected
  return (
    <Badge className={m.color}>
      <span className={`w-1.5 h-1.5 rounded-full ${m.dot}`} />
      {m.label}
    </Badge>
  )
}
