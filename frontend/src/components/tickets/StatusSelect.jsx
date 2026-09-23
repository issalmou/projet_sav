import { STATUS_ORDER, STATUSES } from './constants'
import { ChevronDown } from 'lucide-react'
import { useI18n } from '../../i18n/useI18n'

export default function StatusSelect({ value, onChange, disabled = false, allowedStatuses = STATUS_ORDER }) {
  const { t } = useI18n()
  return (
    <div className="relative">
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled}
        aria-label={t('tf.status')}
        className="w-full appearance-none rounded-xl border border-teal-200 bg-white pl-8 pr-9 py-2.5 text-sm font-semibold text-slate-800 shadow-sm outline-none transition focus:border-teal-600 focus:ring-2 focus:ring-teal-600/20 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500"
      >
        {allowedStatuses.map((status) => (
          <option key={status} value={status}>
            {t(`status.${status}`)}
          </option>
        ))}
      </select>
      <span className={`pointer-events-none absolute left-3 top-1/2 h-2 w-2 -translate-y-1/2 rounded-full ${STATUSES[value]?.dot || 'bg-slate-400'}`} />
      <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-teal-700" />
    </div>
  )
}
