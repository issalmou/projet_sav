import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  Plus,
  Search,
  Package,
  Monitor, Server, Wifi, Printer, HardDrive, Headphones,
  Pencil,
  Trash2,
  ChevronDown,
  RefreshCw,
  ShieldCheck, ShieldAlert, ShieldX, ShieldQuestion,
  Image,
} from 'lucide-react'
import { useProducts } from '../../contexts/useProducts'
import { PRODUCT_CATEGORIES } from '../../contexts/ProductsContext'
import { PageHeader, EmptyState, ConfirmModal } from '../../components/admin/ui'
import { useToast } from '../../services/toast'
import { getWarrantyInfo } from '../../components/products/WarrantyBadge'

const PAGE_SIZE = 8

const CATEGORY_ICONS = {
  monitor: Monitor, server: Server, wifi: Wifi, printer: Printer,
  'hard-drive': HardDrive, headphones: Headphones, package: Package,
}

const CATEGORY_COLORS = {
  Ecrans: { bg: 'bg-indigo-100', text: 'text-indigo-600' },
  Serveurs: { bg: 'bg-blue-100', text: 'text-blue-600' },
  Reseau: { bg: 'bg-purple-100', text: 'text-purple-600' },
  Impression: { bg: 'bg-amber-100', text: 'text-amber-600' },
  Stockage: { bg: 'bg-emerald-100', text: 'text-emerald-600' },
  Audio: { bg: 'bg-rose-100', text: 'text-rose-600' },
  Autre: { bg: 'bg-slate-100', text: 'text-slate-500' },
}

const WARRANTY_ICONS = {
  active: ShieldCheck,
  expiring: ShieldAlert,
  expired: ShieldX,
  none: ShieldQuestion,
}

const WARRANTY_COLORS = {
  active: 'text-teal-600 bg-teal-50',
  expiring: 'text-orange-600 bg-orange-50',
  expired: 'text-red-600 bg-red-50',
  none: 'text-slate-400 bg-slate-50',
}

function formatPrice(price) {
  if (!price && price !== 0) return '—'
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(price)
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

function StatCard({ icon: Icon, label, value, color }) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5 custom-shadow">
      <div className="flex items-start justify-between mb-3">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${color}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
      <p className="text-2xl font-bold text-slate-900">{value}</p>
      <p className="text-xs text-slate-500 mt-1">{label}</p>
    </div>
  )
}

export default function AdminProducts() {
  const navigate = useNavigate()
  const location = useLocation()
  const { products, deleteProduct } = useProducts()
  const { toastEl, showToast } = useToast()

  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [warrantyFilter, setWarrantyFilter] = useState('all')
  const [page, setPage] = useState(1)
  const [deleteTarget, setDeleteTarget] = useState(null)

  useEffect(() => {
    const state = location.state
    if (state?.toast) {
      showToast(state.toast.message, state.toast.type)
      window.history.replaceState({}, '')
    }
  }, [location.state, showToast])

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase()
    return products
      .filter((p) => {
        const matchSearch =
          !query ||
          p.name.toLowerCase().includes(query) ||
          p.reference.toLowerCase().includes(query) ||
          (p.brand && p.brand.toLowerCase().includes(query)) ||
          (p.serial_number && p.serial_number.toLowerCase().includes(query))
        const matchCategory = categoryFilter === 'all' || p.category === categoryFilter
        const warranty = getWarrantyInfo(p.warranty_purchase_date, p.warranty_months)
        const matchWarranty = warrantyFilter === 'all' || warranty.status === warrantyFilter
        return matchSearch && matchCategory && matchWarranty
      })
      .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
  }, [products, search, categoryFilter, warrantyFilter])

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const currentPage = Math.min(page, pageCount)
  const visible = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)

  const resetFilters = () => {
    setSearch('')
    setCategoryFilter('all')
    setWarrantyFilter('all')
    setPage(1)
  }

  const productCounts = useMemo(() => {
    const counts = { total: products.length, active: 0, expiring: 0, expired: 0, none: 0 }
    products.forEach((p) => {
      const w = getWarrantyInfo(p.warranty_purchase_date, p.warranty_months)
      counts[w.status] = (counts[w.status] || 0) + 1
    })
    return counts
  }, [products])

  return (
    <div className="space-y-8">
      <PageHeader
        title="Produits"
        subtitle="Gérez le catalogue de produits du parc SAV."
        actions={
          <button
            onClick={() => navigate('/admin/products/new')}
            className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl shadow-lg shadow-blue-500/20 flex items-center gap-2 transition-all active:scale-[0.98]"
          >
            <Plus className="w-5 h-5" />
            Ajouter un produit
          </button>
        }
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard icon={Package} label="Total produits" value={products.length} color="bg-blue-50 text-blue-600" />
        <StatCard icon={ShieldCheck} label="Sous garantie" value={productCounts.active} color="bg-teal-50 text-teal-600" />
        <StatCard icon={ShieldAlert} label="Garantie bientôt" value={productCounts.expiring} color="bg-orange-50 text-orange-600" />
        <StatCard icon={ShieldX} label="Garantie expirée" value={productCounts.expired} color="bg-red-50 text-red-600" />
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 custom-shadow">
        <div className="p-4 flex items-center gap-3 border-b border-slate-100">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value)
                setPage(1)
              }}
              placeholder="Rechercher par nom, référence, marque ou S/N..."
              className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
            />
          </div>

          <div className="relative">
            <select
              value={categoryFilter}
              onChange={(e) => {
                setCategoryFilter(e.target.value)
                setPage(1)
              }}
              className="appearance-none pl-3 pr-9 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/20 cursor-pointer"
            >
              <option value="all">Toutes catégories</option>
              {PRODUCT_CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
          </div>

          <div className="relative">
            <select
              value={warrantyFilter}
              onChange={(e) => {
                setWarrantyFilter(e.target.value)
                setPage(1)
              }}
              className="appearance-none pl-3 pr-9 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/20 cursor-pointer"
            >
              <option value="all">Toutes garanties</option>
              <option value="active">Sous garantie</option>
              <option value="expiring">Expire bientôt</option>
              <option value="expired">Expirée</option>
              <option value="none">Sans garantie</option>
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
          </div>

          <button
            onClick={resetFilters}
            title="Réinitialiser les filtres"
            className="p-2.5 bg-slate-50 border border-slate-200 text-slate-500 hover:bg-slate-100 rounded-xl transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        <div className="px-5 py-3 flex items-center gap-4 text-[10px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-100">
          <span className="flex-1 min-w-0">Produit</span>
          <span className="shrink-0 w-28">Catégorie</span>
          <span className="shrink-0 w-24">Prix</span>
          <span className="shrink-0 w-28">Garantie</span>
          <span className="hidden lg:inline shrink-0 w-24">Créé le</span>
          <span className="shrink-0 w-20 text-center">Actions</span>
        </div>

        {filtered.length === 0 ? (
          <EmptyState
            icon={Package}
            title="Aucun produit trouvé"
            message={
              products.length === 0
                ? "Aucun produit pour le moment. Ajoutez-en un pour commencer."
                : "Aucun produit ne correspond à vos critères."
            }
            action={
              products.length === 0 && (
                <button
                  onClick={() => navigate('/admin/products/new')}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-xl transition-colors"
                >
                  Ajouter un produit
                </button>
              )
            }
          />
        ) : (
          visible.map((p) => {
            const catObj = PRODUCT_CATEGORIES.find((c) => c.value === p.category)
            const CatIcon = CATEGORY_ICONS[catObj?.icon] || Package
            const catColors = CATEGORY_COLORS[p.category] || CATEGORY_COLORS.Autre
            const warranty = getWarrantyInfo(p.warranty_purchase_date, p.warranty_months)
            const WarrantyIcon = WARRANTY_ICONS[warranty.status] || ShieldQuestion
            const warrantyColor = WARRANTY_COLORS[warranty.status] || WARRANTY_COLORS.none

            return (
              <div
                key={p.id}
                className="group flex items-center gap-4 px-5 py-4 border-b border-slate-100 hover:bg-slate-50 transition-colors"
              >
                <div className="flex-1 min-w-0 flex items-center gap-3">
                  {p.image_url ? (
                    <img
                      src={p.image_url}
                      alt={p.name}
                      className="w-9 h-9 rounded-lg object-cover shrink-0"
                    />
                  ) : (
                    <div className={`w-9 h-9 rounded-lg ${catColors.bg} flex items-center justify-center shrink-0`}>
                      <CatIcon className={`w-4 h-4 ${catColors.text}`} />
                    </div>
                  )}
                  <div className="min-w-0">
                    <p className="text-sm font-bold text-slate-900 truncate">{p.name}</p>
                    <p className="text-xs text-slate-500 truncate">
                      Réf: {p.reference} {p.brand && `• ${p.brand}`}
                    </p>
                  </div>
                </div>

                <div className="shrink-0 w-28">
                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold ${catColors.bg} ${catColors.text}`}>
                    <CatIcon className="w-3 h-3" />
                    {catObj?.label || p.category}
                  </span>
                </div>

                <div className="shrink-0 w-24 text-sm font-bold text-slate-900">
                  {formatPrice(p.price)}
                </div>

                <div className="shrink-0 w-28">
                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold ${warrantyColor}`}>
                    <WarrantyIcon className="w-3 h-3" />
                    {warranty.label}
                  </span>
                </div>

                <div className="hidden lg:inline shrink-0 w-24 text-xs text-slate-500">
                  {formatDate(p.createdAt)}
                </div>

                <div className="shrink-0 w-20 flex items-center justify-end gap-1">
                  <button
                    onClick={() => navigate(`/admin/products/${p.id}/edit`)}
                    title="Modifier"
                    className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                  >
                    <Pencil className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setDeleteTarget(p)}
                    title="Supprimer"
                    className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )
          })
        )}
      </div>

      {filtered.length > 0 && (
        <div className="flex items-center justify-between">
          <p className="text-xs text-slate-500">
            Affichage de{' '}
            <span className="font-semibold text-slate-700">{(currentPage - 1) * PAGE_SIZE + 1}</span> à{' '}
            <span className="font-semibold text-slate-700">
              {Math.min(currentPage * PAGE_SIZE, filtered.length)}
            </span>{' '}
            sur {filtered.length} produit(s)
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(currentPage - 1)}
              disabled={currentPage === 1}
              className="px-3 py-1.5 text-xs font-semibold text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Précédent
            </button>
            {Array.from({ length: pageCount }, (_, i) => i + 1).map((p) => (
              <button
                key={p}
                onClick={() => setPage(p)}
                className={`w-8 h-8 text-xs font-semibold rounded-lg transition-colors ${
                  p === currentPage
                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20'
                    : 'text-slate-600 bg-white border border-slate-200 hover:bg-slate-50'
                }`}
              >
                {p}
              </button>
            ))}
            <button
              onClick={() => setPage(currentPage + 1)}
              disabled={currentPage === pageCount}
              className="px-3 py-1.5 text-xs font-semibold text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Suivant
            </button>
          </div>
        </div>
      )}

      <ConfirmModal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Supprimer le produit"
        message={
          deleteTarget
            ? `Voulez-vous vraiment supprimer "${deleteTarget.name}" ? Cette action est irréversible.`
            : ''
        }
        onConfirm={() => {
          deleteProduct(deleteTarget.id)
          showToast(`Le produit "${deleteTarget.name}" a été supprimé`)
        }}
      />

      {toastEl}
    </div>
  )
}
