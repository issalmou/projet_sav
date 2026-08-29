import { Circle, Clock, CheckCircle2, XCircle } from 'lucide-react'
import { STATUSES } from './constants'

const STATUS_ICONS = {
  open: Circle,
  in_progress: Clock,
  resolved: CheckCircle2,
  closed: XCircle
}

export default function StatusBadge({ status, size = 'sm' }) {
  const s = STATUSES[status]
  const Icon = STATUS_ICONS[status]

  const sizes = {
    sm: 'px-2.5 py-1 text-[11px]',
    md: 'px-3 py-1.5 text-xs',
    lg: 'px-4 py-2 text-sm'
  }

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full font-semibold border ${s.color} ${sizes[size]}`}>
      <Icon className={`${size === 'sm' ? 'w-3 h-3' : 'w-4 h-4'}`} />
      {s.label}
    </span>
  )
}
