import { resolveRole, ROLES } from '../../contexts/roles'
import { useI18n } from '../../i18n/useI18n'

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
  const { t } = useI18n()
  const key = resolveRole(role)
  const r = ROLES[key]
  if (!r) return <Badge className="bg-slate-50 text-slate-600 border-slate-200">{key || ''}</Badge>
  return (
    <Badge className={r.color}>
      <span className={`w-1.5 h-1.5 rounded-full ${r.dot}`} />
      {t(`role.${key}`)}
    </Badge>
  )
}

export function DocTypeBadge({ type }) {
  const { t } = useI18n()
  const map = {
    faq: { labelKey: 'admin.docTypes.faq', color: 'bg-blue-50 text-blue-600 border-blue-100' },
    manual: { labelKey: 'admin.docTypes.manual', color: 'bg-violet-50 text-violet-600 border-violet-100' },
    guide: { labelKey: 'admin.docTypes.guide', color: 'bg-amber-50 text-amber-600 border-amber-100' },
  }
  const m = map[type] || { labelKey: null, color: 'bg-slate-50 text-slate-600 border-slate-200' }
  return <Badge className={m.color}>{m.labelKey ? t(m.labelKey) : type}</Badge>
}

export function DocStatusBadge({ status }) {
  const { t } = useI18n()
  return status === 'published' ? (
    <Badge className="bg-teal-50 text-teal-600 border-teal-100">{t('admin.documents.publishedSingle')}</Badge>
  ) : (
    <Badge className="bg-amber-50 text-amber-600 border-amber-100">{t('admin.documents.draftSingle')}</Badge>
  )
}

export function StatusBadge({ status }) {
  const { t } = useI18n()
  return status === 'active' ? (
    <Badge className="bg-teal-50 text-teal-600 border-teal-100">{t('admin.users.statusActive')}</Badge>
  ) : (
    <Badge className="bg-slate-100 text-slate-500 border-slate-200">{t('admin.users.statusInactive')}</Badge>
  )
}

export function SeverityBadge({ severity }) {
  const { t } = useI18n()
  const map = {
    info: { labelKey: 'admin.logs.sevInfo', color: 'bg-blue-50 text-blue-600 border-blue-100' },
    warning: { labelKey: 'admin.logs.sevWarning', color: 'bg-amber-50 text-amber-600 border-amber-100' },
    critical: { labelKey: 'admin.logs.sevCritical', color: 'bg-red-50 text-red-600 border-red-100' },
  }
  const m = map[severity] || map.info
  return <Badge className={m.color}>{t(m.labelKey)}</Badge>
}

export function IntegrationBadge({ status }) {
  const { t } = useI18n()
  const map = {
    connected: {
      labelKey: 'admin.integrations.badgeConnected',
      color: 'bg-teal-50 text-teal-600 border-teal-100',
      dot: 'bg-teal-500',
    },
    error: {
      labelKey: 'admin.integrations.badgeError',
      color: 'bg-red-50 text-red-600 border-red-100',
      dot: 'bg-red-500',
    },
    disconnected: {
      labelKey: 'admin.integrations.badgeDisconnected',
      color: 'bg-slate-100 text-slate-500 border-slate-200',
      dot: 'bg-slate-400',
    },
  }
  const m = map[status] || map.disconnected
  return (
    <Badge className={m.color}>
      <span className={`w-1.5 h-1.5 rounded-full ${m.dot}`} />
      {t(m.labelKey)}
    </Badge>
  )
}
