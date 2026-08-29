import { PRODUCT_CATEGORIES } from '../../contexts/ProductsContext'
import { Monitor, Server, Wifi, Printer, HardDrive, Headphones, Package } from 'lucide-react'

const ICON_MAP = {
  monitor: Monitor,
  server: Server,
  wifi: Wifi,
  printer: Printer,
  'hard-drive': HardDrive,
  headphones: Headphones,
  package: Package
}

const ACTIVE_COLORS = {
  Ecrans: 'bg-indigo-600 text-white',
  Serveurs: 'bg-blue-600 text-white',
  Reseau: 'bg-purple-600 text-white',
  Impression: 'bg-amber-600 text-white',
  Stockage: 'bg-emerald-600 text-white',
  Audio: 'bg-rose-600 text-white',
  Autre: 'bg-slate-600 text-white'
}

const INACTIVE_COLORS = {
  Ecrans: 'bg-indigo-50 text-indigo-700 hover:bg-indigo-100',
  Serveurs: 'bg-blue-50 text-blue-700 hover:bg-blue-100',
  Reseau: 'bg-purple-50 text-purple-700 hover:bg-purple-100',
  Impression: 'bg-amber-50 text-amber-700 hover:bg-amber-100',
  Stockage: 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100',
  Audio: 'bg-rose-50 text-rose-700 hover:bg-rose-100',
  Autre: 'bg-slate-50 text-slate-600 hover:bg-slate-100'
}

export default function CategoryFilter({ value, onChange, productCounts = {} }) {
  return (
    <div className="flex items-center gap-2 flex-wrap">
      <button
        type="button"
        onClick={() => onChange(null)}
        className={`px-3 py-2 rounded-xl text-xs font-semibold transition-all border ${
          value === null
            ? 'bg-blue-600 text-white border-blue-600 shadow-lg shadow-blue-500/20'
            : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
        }`}
      >
        Tous
        {productCounts.total > 0 && (
          <span className={`ml-1.5 text-[10px] ${value === null ? 'text-blue-200' : 'text-slate-400'}`}>
            {productCounts.total}
          </span>
        )}
      </button>
      {PRODUCT_CATEGORIES.map((cat) => {
        const Icon = ICON_MAP[cat.icon] || Package
        const isActive = value === cat.value
        const count = productCounts[cat.value] || 0
        if (count === 0 && value !== cat.value) return null
        return (
          <button
            key={cat.value}
            type="button"
            onClick={() => onChange(isActive ? null : cat.value)}
            className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold transition-all border ${
              isActive
                ? ACTIVE_COLORS[cat.value] + ' border-transparent shadow-lg'
                : INACTIVE_COLORS[cat.value] + ' border-transparent'
            }`}
          >
            <Icon className="w-3.5 h-3.5" />
            {cat.label}
            {count > 0 && (
              <span className={`text-[10px] ${isActive ? 'opacity-70' : 'opacity-50'}`}>
                {count}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}
