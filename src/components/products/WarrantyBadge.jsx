import { ShieldCheck, ShieldAlert, ShieldX, ShieldQuestion } from 'lucide-react'

function getWarrantyStatus(purchaseDate, warrantyMonths) {
  if (!purchaseDate || !warrantyMonths) return 'none'
  const purchase = new Date(purchaseDate)
  const expiry = new Date(purchase)
  expiry.setMonth(expiry.getMonth() + warrantyMonths)
  const now = new Date()
  const diffDays = Math.ceil((expiry - now) / (1000 * 60 * 60 * 24))
  if (diffDays < 0) return 'expired'
  if (diffDays <= 30) return 'expiring'
  return 'active'
}

function getWarrantyEndDate(purchaseDate, warrantyMonths) {
  if (!purchaseDate || !warrantyMonths) return null
  const d = new Date(purchaseDate)
  d.setMonth(d.getMonth() + warrantyMonths)
  return d
}

export function getWarrantyInfo(warranty_purchase_date, warranty_months) {
  const status = getWarrantyStatus(warranty_purchase_date, warranty_months)
  const endDate = getWarrantyEndDate(warranty_purchase_date, warranty_months)
  const configs = {
    active: {
      label: 'Garantie Active',
      color: 'bg-teal-50 text-teal-700 border-teal-100',
      dotColor: 'bg-teal-500',
      borderColor: 'border-l-teal-500',
      icon: ShieldCheck
    },
    expiring: {
      label: 'Expire bientôt',
      color: 'bg-orange-50 text-orange-700 border-orange-100',
      dotColor: 'bg-orange-500',
      borderColor: 'border-l-orange-400',
      icon: ShieldAlert
    },
    expired: {
      label: 'Garantie Expirée',
      color: 'bg-red-50 text-red-700 border-red-100',
      dotColor: 'bg-red-500',
      borderColor: 'border-l-red-400',
      icon: ShieldX
    },
    none: {
      label: 'Aucune Garantie',
      color: 'bg-slate-100 text-slate-500 border-slate-200',
      dotColor: 'bg-slate-300',
      borderColor: 'border-l-slate-300',
      icon: ShieldQuestion
    }
  }
  return { status, endDate, ...configs[status] }
}

export function WarrantyBadge({ purchaseDate, warrantyMonths, compact = false }) {
  const { label, color, icon: Icon } = getWarrantyInfo(purchaseDate, warrantyMonths)

  if (compact) {
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-bold uppercase rounded border ${color}`}>
        <Icon className="w-3 h-3" />
        {label}
      </span>
    )
  }

  return (
    <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-lg border ${color}`}>
      <Icon className="w-3.5 h-3.5" />
      {label}
    </div>
  )
}

export function WarrantyDot({ purchaseDate, warrantyMonths, size = 'sm' }) {
  const { dotColor } = getWarrantyInfo(purchaseDate, warrantyMonths)
  const sizeClass = size === 'xs' ? 'w-1.5 h-1.5' : size === 'sm' ? 'w-2 h-2' : 'w-2.5 h-2.5'
  return (
    <span className={`inline-block ${sizeClass} rounded-full ${dotColor} shrink-0`} />
  )
}

export function WarrantyCardBorder({ purchaseDate, warrantyMonths, children }) {
  const { borderColor } = getWarrantyInfo(purchaseDate, warrantyMonths)
  return (
    <div className={`border-l-4 ${borderColor}`}>
      {children}
    </div>
  )
}

export default WarrantyBadge
