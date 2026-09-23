import { PRIORITIES } from './constants'
import { useI18n } from '../../i18n/useI18n'

export default function PriorityBadge({ priority, size = 'sm' }) {
  const { t } = useI18n()
  const p = PRIORITIES[priority] || PRIORITIES.medium

  const sizes = {
    sm: 'px-2.5 py-1 text-[11px]',
    md: 'px-3 py-1.5 text-xs',
    lg: 'px-4 py-2 text-sm'
  }

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full font-semibold border ${p.color} ${sizes[size] || sizes.sm}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${p.dot}`} />
      {t(`priority.${priority}`)}
    </span>
  )
}
