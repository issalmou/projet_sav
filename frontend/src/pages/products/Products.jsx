import { useState, useMemo } from 'react'
import { Plus, Search, Package, X, ShieldCheck, ShieldAlert, ShieldX, ShieldQuestion } from 'lucide-react'
import { useProducts } from '../../contexts/useProducts'
import { useAuth } from '../../contexts/useAuth'
import ProductCard from '../../components/products/ProductCard'
import CategoryFilter from '../../components/products/CategoryFilter'
import { PageHeader } from '../../components/admin/ui'
import { getWarrantyInfo } from '../../components/products/WarrantyBadge'
import { useI18n } from '../../i18n/useI18n'

const WARRANTY_FILTERS = [
  { value: null, labelKey: 'ps.all', icon: null },
  { value: 'active', labelKey: 'ps.underWarranty', icon: ShieldCheck, color: 'text-teal-600', dot: 'bg-teal-500' },
  { value: 'expiring', labelKey: 'ps.expiringSoon', icon: ShieldAlert, color: 'text-orange-600', dot: 'bg-orange-500' },
  { value: 'expired', labelKey: 'ps.expired', icon: ShieldX, color: 'text-red-600', dot: 'bg-red-500' },
  { value: 'none', labelKey: 'ps.noWarranty', icon: ShieldQuestion, color: 'text-slate-400', dot: 'bg-slate-300' }
]

export default function Products() {
  const { products, searchProducts, categories } = useProducts()
  const { user } = useAuth()
  const { t } = useI18n()
  const [query, setQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState(null)
  const [warrantyFilter, setWarrantyFilter] = useState(null)

  const canManage = user?.role === 'admin' || user?.role === 'manager'

  const results = useMemo(() => {
    let filtered = searchProducts(query, selectedCategory)
    if (warrantyFilter) {
      filtered = filtered.filter((p) => {
        const info = getWarrantyInfo(p.warranty_purchase_date, p.warranty_months)
        return info.status === warrantyFilter
      })
    }
    return filtered
  }, [query, selectedCategory, warrantyFilter, products])

  const productCounts = useMemo(() => {
    const counts = { total: products.length }
    products.forEach((p) => {
      counts[p.category] = (counts[p.category] || 0) + 1
    })
    return counts
  }, [products])

  const warrantyCounts = useMemo(() => {
    const counts = { total: products.length, active: 0, expiring: 0, expired: 0, none: 0 }
    products.forEach((p) => {
      const info = getWarrantyInfo(p.warranty_purchase_date, p.warranty_months)
      counts[info.status] = (counts[info.status] || 0) + 1
    })
    return counts
  }, [products])

  return (
    <div className="flex-1 overflow-y-auto p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        <PageHeader
          title={t('ps.title')}
          subtitle={t('ps.registered', { count: products.length })}
          actions={
            canManage ? (
              <button className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl shadow-lg shadow-blue-500/20 transition-all active:scale-[0.98]">
                <Plus className="w-4 h-4" />
                {t('ps.addProduct')}
              </button>
            ) : null
          }
        />

        <div className="bg-white rounded-2xl border border-slate-200 custom-shadow p-4 space-y-4">
          <div className="relative">
            <Search className="absolute left-3.5 top-2.5 w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t('ps.placeholder')}
              className="w-full pl-10 pr-10 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
            />
            {query && (
              <button
                onClick={() => setQuery('')}
                className="absolute right-3 top-2.5 p-0.5 text-slate-400 hover:text-slate-600"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          <CategoryFilter
            value={selectedCategory}
            onChange={setSelectedCategory}
            productCounts={productCounts}
          />

          <div className="flex items-center gap-1.5 flex-wrap pt-2 border-t border-slate-100">
            {WARRANTY_FILTERS.map((wf) => {
              const isActive = warrantyFilter === wf.value
              const Icon = wf.icon
              const count = wf.value ? warrantyCounts[wf.value] : warrantyCounts.total
              return (
                <button
                  key={wf.value || 'all'}
                  type="button"
                  onClick={() => setWarrantyFilter(wf.value)}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-semibold transition-all border ${
                    isActive
                      ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                      : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  {Icon && <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-white' : wf.color}`} />}
                  {!Icon && <span className={`w-2 h-2 rounded-full ${isActive ? 'bg-white' : wf.dot}`} />}
                  {wf.labelKey && t(wf.labelKey)}
                  <span className={`text-[10px] ${isActive ? 'text-blue-200' : 'text-slate-400'}`}>{count}</span>
                </button>
              )
            })}
          </div>
        </div>

        {results.length === 0 ? (
          <div className="bg-white rounded-2xl border border-slate-200 custom-shadow">
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mb-4">
                <Package className="w-8 h-8 text-slate-300" />
              </div>
              <h3 className="text-sm font-bold text-slate-900 mb-1">{t('ps.none')}</h3>
              <p className="text-xs text-slate-500 max-w-xs">
                {query || selectedCategory || warrantyFilter
                  ? t('ps.emptySearch')
                  : t('ps.empty')}
              </p>
            </div>
          </div>
        ) : (
          <>
            <p className="text-xs text-slate-400 font-medium">
              {t('ps.resultCount', { count: results.length })}
              {selectedCategory && ` · ${t(`category.${selectedCategory}`)}`}
              {warrantyFilter && ` · ${WARRANTY_FILTERS.find((w) => w.value === warrantyFilter)?.labelKey ? t(WARRANTY_FILTERS.find((w) => w.value === warrantyFilter).labelKey) : ''}`}
              {query && ` · "${query}"`}
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {results.map((product) => (
                <ProductCard
                  key={product.id}
                  product={product}
                  categoryIcon={categories.find((c) => c.value === product.category)?.icon}
                />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
