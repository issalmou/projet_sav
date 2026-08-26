import { useState, useMemo, useEffect, useRef, useCallback } from 'react'
import { Search, X, ChevronDown, ShieldCheck, ShieldAlert, ShieldX, ShieldQuestion } from 'lucide-react'
import { useProducts } from '../../contexts/useProducts'
import { Modal } from '../admin/ui'
import ProductCard from './ProductCard'
import CategoryFilter from './CategoryFilter'
import { getWarrantyInfo } from './WarrantyBadge'

const WARRANTY_FILTERS = [
  { value: null, label: 'Toutes', icon: null },
  { value: 'active', label: 'Sous garantie', icon: ShieldCheck, color: 'text-teal-600' },
  { value: 'expiring', label: 'Expire bientôt', icon: ShieldAlert, color: 'text-orange-600' },
  { value: 'expired', label: 'Expirée', icon: ShieldX, color: 'text-red-600' },
  { value: 'none', label: 'Sans garantie', icon: ShieldQuestion, color: 'text-slate-400' }
]

const inputClass =
  'w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all'

export default function ProductSelector({
  open,
  onClose,
  onSelect,
  selectedId = null,
  mode = 'modal',
  anchorRef = null,
  showWarrantyFilter = true,
  filterWarranty = null,
  placeholder = 'Rechercher par nom, référence ou marque...',
  multiple = false,
  selectedIds = []
}) {
  const { products, searchProducts, categories } = useProducts()
  const [query, setQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState(null)
  const [warrantyFilter, setWarrantyFilter] = useState(filterWarranty)
  const [highlightedIndex, setHighlightedIndex] = useState(-1)
  const listRef = useRef(null)
  const inputRef = useRef(null)

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

  useEffect(() => {
    if (open && mode === 'modal') {
      setTimeout(() => inputRef.current?.focus(), 100)
    }
    if (!open) {
      setQuery('')
      setSelectedCategory(null)
      setWarrantyFilter(filterWarranty)
      setHighlightedIndex(-1)
    }
  }, [open, mode, filterWarranty])

  const handleSelect = useCallback((product) => {
    if (multiple) {
      onSelect(product)
    } else {
      onSelect(product)
      onClose()
    }
  }, [multiple, onSelect, onClose])

  const handleKeyDown = useCallback((e) => {
    if (!results.length) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setHighlightedIndex((prev) => (prev < results.length - 1 ? prev + 1 : 0))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : results.length - 1))
    } else if (e.key === 'Enter' && highlightedIndex >= 0) {
      e.preventDefault()
      handleSelect(results[highlightedIndex])
    } else if (e.key === 'Escape') {
      onClose()
    }
  }, [results, highlightedIndex, handleSelect, onClose])

  useEffect(() => {
    setHighlightedIndex(-1)
  }, [query, selectedCategory, warrantyFilter])

  useEffect(() => {
    if (highlightedIndex >= 0 && listRef.current) {
      const items = listRef.current.querySelectorAll('[data-product-item]')
      items[highlightedIndex]?.scrollIntoView({ block: 'nearest' })
    }
  }, [highlightedIndex])

  const isIdSelected = (id) => multiple ? selectedIds.includes(id) : id === selectedId

  const selectorContent = (
    <div className="space-y-3">
      <div className="relative">
        <Search className="absolute left-3.5 top-2.5 w-4 h-4 text-slate-400" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className={`${inputClass} pl-10 ${query ? 'pr-10' : 'pr-4'}`}
          autoFocus
        />
        {query && (
          <button
            onClick={() => { setQuery(''); inputRef.current?.focus() }}
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

      {showWarrantyFilter && (
        <div className="flex items-center gap-1.5 flex-wrap">
          {WARRANTY_FILTERS.map((wf) => {
            const isActive = warrantyFilter === wf.value
            const Icon = wf.icon
            const count = wf.value ? warrantyCounts[wf.value] : warrantyCounts.total
            return (
              <button
                key={wf.value || 'all'}
                type="button"
                onClick={() => setWarrantyFilter(wf.value)}
                className={`inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[11px] font-semibold transition-all border ${
                  isActive
                    ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                    : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                }`}
              >
                {Icon && <Icon className={`w-3 h-3 ${isActive ? 'text-white' : wf.color}`} />}
                {!Icon && <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />}
                {wf.label}
                <span className={`text-[10px] ${isActive ? 'text-blue-200' : 'text-slate-400'}`}>{count}</span>
              </button>
            )
          })}
        </div>
      )}

      <div
        ref={listRef}
        className={`${mode === 'modal' ? 'max-h-[380px]' : 'max-h-[280px]'} overflow-y-auto space-y-1.5 pr-1 scrollbar-hide`}
      >
        {results.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 text-center">
            <div className="w-11 h-11 bg-slate-100 rounded-xl flex items-center justify-center mb-2.5">
              <Search className="w-5 h-5 text-slate-300" />
            </div>
            <p className="text-sm font-semibold text-slate-700">Aucun produit trouvé</p>
            <p className="text-xs text-slate-400 mt-1">Essayez avec d'autres mots-clés</p>
          </div>
        ) : (
          results.map((product, idx) => (
            <div key={product.id} data-product-item>
              <ProductCard
                product={product}
                categoryIcon={categories.find((c) => c.value === product.category)?.icon}
                onClick={() => handleSelect(product)}
                selected={isIdSelected(product.id)}
                highlighted={idx === highlightedIndex}
                compact
              />
            </div>
          ))
        )}
      </div>

      <div className="flex items-center justify-between text-[11px] text-slate-400 pt-2 border-t border-slate-100">
        <span>
          {results.length} produit{results.length > 1 ? 's' : ''}
        </span>
        {mode === 'modal' && (
          <span className="flex items-center gap-2">
            <kbd className="px-1.5 py-0.5 bg-slate-100 rounded text-[10px] font-mono">↑↓</kbd> naviguer
            <kbd className="px-1.5 py-0.5 bg-slate-100 rounded text-[10px] font-mono">Entrée</kbd> sélectionner
            <kbd className="px-1.5 py-0.5 bg-slate-100 rounded text-[10px] font-mono">Esc</kbd> fermer
          </span>
        )}
      </div>
    </div>
  )

  if (mode === 'dropdown') {
    if (!open) return null
    return (
      <div
        className="absolute left-0 right-0 top-full mt-2 z-50 bg-white rounded-2xl border border-slate-200 shadow-2xl p-4"
        onClick={(e) => e.stopPropagation()}
      >
        {selectorContent}
      </div>
    )
  }

  return (
    <Modal open={open} onClose={onClose} title="Sélectionner un produit" wide>
      {selectorContent}
    </Modal>
  )
}

export function ProductSelectorTrigger({ product, onClick, onRemove, placeholder = 'Sélectionner un produit' }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full"
    >
      {product ? (
        <div className="flex items-center gap-3 p-3 bg-slate-50 border border-slate-200 rounded-xl hover:bg-slate-100 hover:border-slate-300 transition-all group">
          <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center shrink-0">
            <ShieldCheck className="w-5 h-5 text-blue-600" />
          </div>
          <div className="flex-1 min-w-0 text-left">
            <p className="text-sm font-semibold text-slate-900 truncate">{product.name}</p>
            <p className="text-xs text-slate-500">Réf: {product.reference}</p>
          </div>
          {onRemove && (
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onRemove() }}
              className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors opacity-0 group-hover:opacity-100"
            >
              <X className="w-4 h-4" />
            </button>
          )}
          <ChevronDown className="w-4 h-4 text-slate-400 shrink-0" />
        </div>
      ) : (
        <div className="w-full flex items-center gap-2 px-4 py-3 bg-slate-50 border border-dashed border-slate-300 rounded-xl text-sm text-slate-500 hover:bg-slate-100 hover:border-slate-400 transition-all">
          <ShieldQuestion className="w-4 h-4" />
          {placeholder}
          <ChevronDown className="w-4 h-4 ml-auto text-slate-400" />
        </div>
      )}
    </button>
  )
}
