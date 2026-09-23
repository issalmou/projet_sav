import { useNavigate } from 'react-router-dom'
import { Monitor, Server, Wifi, Printer, HardDrive, Headphones, Package } from 'lucide-react'
import WarrantyBadge, { WarrantyDot, getWarrantyInfo } from './WarrantyBadge'
import { useI18n } from '../../i18n/useI18n'

const ICON_MAP = {
  monitor: Monitor,
  server: Server,
  wifi: Wifi,
  printer: Printer,
  'hard-drive': HardDrive,
  headphones: Headphones,
  package: Package
}

const CATEGORY_COLORS = {
  Ecrans: 'bg-indigo-100 text-indigo-600',
  Serveurs: 'bg-blue-100 text-blue-600',
  Reseau: 'bg-purple-100 text-purple-600',
  Impression: 'bg-amber-100 text-amber-600',
  Stockage: 'bg-emerald-100 text-emerald-600',
  Audio: 'bg-rose-100 text-rose-600',
  Autre: 'bg-slate-100 text-slate-500'
}

export default function ProductCard({ product, categoryIcon, onClick, selected = false, highlighted = false, compact = false }) {
  const navigate = useNavigate()
  const { t } = useI18n()
  const Icon = ICON_MAP[categoryIcon || 'package'] || Package
  const iconColor = CATEGORY_COLORS[product.category] || 'bg-slate-100 text-slate-500'
  const warranty = getWarrantyInfo(product.warranty_purchase_date, product.warranty_months)

  const handleClick = () => {
    if (onClick) {
      onClick(product)
    } else if (product.id) {
      navigate(`/products/${product.id}`)
    }
  }

  if (compact) {
    return (
      <button
        type="button"
        onClick={handleClick}
        className={`w-full flex items-center gap-3 p-3 rounded-xl border transition-all text-left border-l-[3px] ${
          selected
            ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-500/20 border-l-blue-500'
            : highlighted
            ? 'border-slate-300 bg-slate-50 border-l-blue-400'
            : `border-slate-200 bg-white hover:bg-slate-50 hover:border-slate-300 ${warranty.borderColor}`
        }`}
      >
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 overflow-hidden ${iconColor}`}>
          {product.image_url ? (
            <img src={product.image_url} alt={product.name} className="w-full h-full object-cover" />
          ) : (
            <Icon className="w-5 h-5" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <WarrantyDot purchaseDate={product.warranty_purchase_date} warrantyMonths={product.warranty_months} size="xs" />
            <p className="text-sm font-semibold text-slate-900 truncate">{product.name}</p>
          </div>
          <p className="text-xs text-slate-500 truncate">{t('pc.ref', { ref: product.reference })}</p>
        </div>
      </button>
    )
  }

  return (
    <div
      onClick={handleClick}
      className={`bg-white rounded-2xl border transition-all cursor-pointer group border-l-4 ${
        selected
          ? 'border-blue-500 ring-2 ring-blue-500/20 border-l-blue-500'
          : `border-slate-200 hover:border-slate-300 custom-shadow card-hover ${warranty.borderColor}`
      }`}
    >
      <div className="relative h-40 rounded-t-2xl overflow-hidden bg-slate-50">
        {product.image_url ? (
          <img src={product.image_url} alt={product.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
        ) : (
          <div className={`w-full h-full flex items-center justify-center ${iconColor}`}>
            <Icon className="w-12 h-12 opacity-40" />
          </div>
        )}
        <div className="absolute top-3 right-3">
          <WarrantyBadge
            purchaseDate={product.warranty_purchase_date}
            warrantyMonths={product.warranty_months}
            compact
          />
        </div>
        {product.purchases && product.purchases.length > 0 && (
          <div className="absolute bottom-3 left-3">
            <span className="px-2 py-0.5 bg-black/50 text-white text-[10px] font-bold rounded-md backdrop-blur-sm">
              {t('pc.purchases', { count: product.purchases.length })}
            </span>
          </div>
        )}
      </div>
      <div className="p-5 space-y-2">
        <div className="flex items-center gap-1.5">
          <WarrantyDot purchaseDate={product.warranty_purchase_date} warrantyMonths={product.warranty_months} />
          <h4 className="text-sm font-bold text-slate-900 truncate group-hover:text-blue-600 transition-colors">
            {product.name}
          </h4>
        </div>
        <p className="text-xs text-slate-500">{t('pc.ref', { ref: product.reference })}</p>
        {product.brand && (
          <p className="text-xs text-slate-400">{product.brand}</p>
        )}
        <div className="flex items-center justify-between pt-2">
          <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded border border-slate-100 ${
            CATEGORY_COLORS[product.category] || 'bg-slate-100 text-slate-500'
          }`}>
            {t(`pcat.${product.category}`)}
          </span>
        </div>
      </div>
    </div>
  )
}
