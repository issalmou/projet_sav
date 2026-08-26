import { useState, useRef, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Camera, Upload, Trash2, Edit3, Save, X,
  Monitor, Server, Wifi, Printer, HardDrive, Headphones, Package,
  Calendar, Tag, DollarSign, Hash, Building2, FileText,
  ShoppingCart, Plus, Clock, CheckCircle2, AlertTriangle
} from 'lucide-react'
import { useProducts } from '../../contexts/useProducts'
import WarrantyBadge, { getWarrantyInfo } from '../../components/products/WarrantyBadge'
import { Field } from '../../components/admin/ui'
import { ConfirmModal } from '../../components/admin/ui'
import { PRODUCT_CATEGORIES } from '../../contexts/ProductsContext'
import { toastService } from '../../services/toast'

const ICON_MAP = {
  monitor: Monitor, server: Server, wifi: Wifi, printer: Printer,
  'hard-drive': HardDrive, headphones: Headphones, package: Package
}

const CATEGORY_COLORS = {
  Ecrans: { bg: 'bg-indigo-100', text: 'text-indigo-600', ring: 'ring-indigo-100' },
  Serveurs: { bg: 'bg-blue-100', text: 'text-blue-600', ring: 'ring-blue-100' },
  Reseau: { bg: 'bg-purple-100', text: 'text-purple-600', ring: 'ring-purple-100' },
  Impression: { bg: 'bg-amber-100', text: 'text-amber-600', ring: 'ring-amber-100' },
  Stockage: { bg: 'bg-emerald-100', text: 'text-emerald-600', ring: 'ring-emerald-100' },
  Audio: { bg: 'bg-rose-100', text: 'text-rose-600', ring: 'ring-rose-100' },
  Autre: { bg: 'bg-slate-100', text: 'text-slate-500', ring: 'ring-slate-100' }
}

function formatPrice(price) {
  if (!price && price !== 0) return '—'
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(price)
}

function formatDate(dateStr) {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' })
}

function formatDateShort(dateStr) {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' })
}

function ImageUploader({ currentImage, onImageChange, productName, category }) {
  const fileInputRef = useRef(null)
  const colors = CATEGORY_COLORS[category] || CATEGORY_COLORS.Autre
  const catObj = PRODUCT_CATEGORIES.find((c) => c.value === category)
  const Icon = ICON_MAP[catObj?.icon] || Package

  const handleFileChange = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (file.size > 5 * 1024 * 1024) {
      toastService.error('L\'image ne doit pas dépasser 5 Mo.')
      return
    }
    const reader = new FileReader()
    reader.onload = (ev) => {
      onImageChange(ev.target.result)
    }
    reader.readAsDataURL(file)
  }

  const handleRemove = (e) => {
    e.stopPropagation()
    onImageChange(null)
  }

  return (
    <div
      onClick={() => fileInputRef.current?.click()}
      className="relative group cursor-pointer w-full aspect-square max-w-[320px] rounded-2xl overflow-hidden border-2 border-dashed border-slate-200 hover:border-blue-400 transition-all"
    >
      {currentImage ? (
        <>
          <img src={currentImage} alt={productName} className="w-full h-full object-cover" />
          <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-all flex items-center justify-center">
            <div className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-2">
              <span className="px-3 py-2 bg-white/90 rounded-xl text-xs font-semibold text-slate-700 backdrop-blur-sm">
                <Camera className="w-4 h-4 inline mr-1.5" />
                Changer l'image
              </span>
              <button
                onClick={handleRemove}
                className="p-2 bg-red-500/90 rounded-xl text-white backdrop-blur-sm hover:bg-red-600 transition-colors"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        </>
      ) : (
        <div className={`w-full h-full flex flex-col items-center justify-center ${colors.bg} ${colors.text} gap-3`}>
          <div className={`w-20 h-20 rounded-2xl bg-white/60 flex items-center justify-center`}>
            <Icon className="w-10 h-10 opacity-60" />
          </div>
          <div className="text-center">
            <p className="text-sm font-bold opacity-80">Ajouter une image</p>
            <p className="text-xs opacity-50 mt-0.5">JPEG, PNG • max 5 Mo</p>
          </div>
          <div className="opacity-0 group-hover:opacity-100 transition-opacity mt-1">
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white/80 rounded-lg text-xs font-semibold backdrop-blur-sm">
              <Upload className="w-3.5 h-3.5" />
              Parcourir
            </span>
          </div>
        </div>
      )}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileChange}
        className="hidden"
      />
    </div>
  )
}

function WarrantySection({ product }) {
  const info = getWarrantyInfo(product.warranty_purchase_date, product.warranty_months)
  const endDate = info.endDate
  const startDate = product.warranty_purchase_date ? new Date(product.warranty_purchase_date) : null
  const now = new Date()

  let progress = 0
  if (startDate && endDate && product.warranty_months) {
    const totalMs = endDate - startDate
    const elapsedMs = now - startDate
    progress = Math.min(100, Math.max(0, (elapsedMs / totalMs) * 100))
  }

  const progressColor =
    info.status === 'active' ? 'bg-teal-500' :
    info.status === 'expiring' ? 'bg-orange-500' :
    'bg-red-500'

  return (
    <div className="bg-white rounded-2xl border border-slate-200 custom-shadow overflow-hidden">
      <div className="p-5 border-b border-slate-100 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 bg-blue-50 rounded-xl flex items-center justify-center">
            <CheckCircle2 className="w-5 h-5 text-blue-600" />
          </div>
          <h3 className="text-sm font-bold text-slate-900">Garantie</h3>
        </div>
        <WarrantyBadge purchaseDate={product.warranty_purchase_date} warrantyMonths={product.warranty_months} />
      </div>
      <div className="p-5 space-y-4">
        <div className="space-y-2">
          <div className="flex justify-between text-xs">
            <span className="text-slate-500">Progression</span>
            <span className="font-semibold text-slate-700">{Math.round(progress)}%</span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
            <div className={`h-full rounded-full transition-all ${progressColor}`} style={{ width: `${progress}%` }} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-slate-50 rounded-xl p-3 space-y-1">
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Achat</p>
            <p className="text-sm font-semibold text-slate-800">{formatDate(product.warranty_purchase_date)}</p>
          </div>
          <div className="bg-slate-50 rounded-xl p-3 space-y-1">
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Expiration</p>
            <p className="text-sm font-semibold text-slate-800">{endDate ? formatDate(endDate.toISOString()) : '—'}</p>
          </div>
          <div className="bg-slate-50 rounded-xl p-3 space-y-1">
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Durée</p>
            <p className="text-sm font-semibold text-slate-800">{product.warranty_months ? `${product.warranty_months} mois` : '—'}</p>
          </div>
          <div className="bg-slate-50 rounded-xl p-3 space-y-1">
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Reste</p>
            <p className="text-sm font-semibold text-slate-800">
              {endDate ? (() => {
                const days = Math.ceil((endDate - now) / (1000 * 60 * 60 * 24))
                if (days < 0) return 'Expirée'
                if (days < 30) return `${days}j`
                const months = Math.floor(days / 30)
                return `${months} mois`
              })() : '—'}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

function SpecsSection({ specs }) {
  if (!specs || Object.keys(specs).length === 0) return null
  return (
    <div className="bg-white rounded-2xl border border-slate-200 custom-shadow overflow-hidden">
      <div className="p-5 border-b border-slate-100 flex items-center gap-2.5">
        <div className="w-9 h-9 bg-purple-50 rounded-xl flex items-center justify-center">
          <Hash className="w-5 h-5 text-purple-600" />
        </div>
        <h3 className="text-sm font-bold text-slate-900">Caractéristiques</h3>
      </div>
      <div className="p-5">
        <div className="space-y-2.5">
          {Object.entries(specs).map(([key, value]) => (
            <div key={key} className="flex items-center justify-between py-2 border-b border-slate-50 last:border-0">
              <span className="text-xs font-semibold text-slate-500 capitalize">{key.replace(/_/g, ' ')}</span>
              <span className="text-sm font-semibold text-slate-800">{value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function PurchaseHistory({ purchases, productId, onAddPurchase }) {
  const [showAddForm, setShowAddForm] = useState(false)
  const [newPurchase, setNewPurchase] = useState({
    date: new Date().toISOString().slice(0, 10),
    quantity: 1,
    unit_price: '',
    supplier: '',
    invoice: '',
    notes: ''
  })

  const inputClass = 'w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all'

  const totalSpent = useMemo(
    () => (purchases || []).reduce((sum, p) => sum + (p.quantity * p.unit_price), 0),
    [purchases]
  )

  const handleSubmit = () => {
    if (!newPurchase.supplier.trim()) {
      toastService.error('Le fournisseur est obligatoire.')
      return
    }
    onAddPurchase(productId, {
      ...newPurchase,
      quantity: Number(newPurchase.quantity) || 1,
      unit_price: Number(newPurchase.unit_price) || 0
    })
    setNewPurchase({ date: new Date().toISOString().slice(0, 10), quantity: 1, unit_price: '', supplier: '', invoice: '', notes: '' })
    setShowAddForm(false)
    toastService.success('Achat enregistré.')
  }

  const sorted = [...(purchases || [])].sort((a, b) => new Date(b.date) - new Date(a.date))

  return (
    <div className="bg-white rounded-2xl border border-slate-200 custom-shadow overflow-hidden">
      <div className="p-5 border-b border-slate-100 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 bg-emerald-50 rounded-xl flex items-center justify-center">
            <ShoppingCart className="w-5 h-5 text-emerald-600" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900">Historique des achats</h3>
            <p className="text-xs text-slate-400">{sorted.length} achat{sorted.length > 1 ? 's' : ''} • Total: {formatPrice(totalSpent)}</p>
          </div>
        </div>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          Ajouter
        </button>
      </div>

      {showAddForm && (
        <div className="p-5 bg-blue-50/50 border-b border-blue-100 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <Field label="Date" required>
              <input type="date" value={newPurchase.date} onChange={(e) => setNewPurchase((p) => ({ ...p, date: e.target.value }))} className={inputClass} />
            </Field>
            <Field label="Quantité">
              <input type="number" min="1" value={newPurchase.quantity} onChange={(e) => setNewPurchase((p) => ({ ...p, quantity: e.target.value }))} className={inputClass} />
            </Field>
            <Field label="Prix unitaire (€)">
              <input type="number" step="0.01" min="0" value={newPurchase.unit_price} onChange={(e) => setNewPurchase((p) => ({ ...p, unit_price: e.target.value }))} placeholder="0.00" className={inputClass} />
            </Field>
            <Field label="Fournisseur" required>
              <input type="text" value={newPurchase.supplier} onChange={(e) => setNewPurchase((p) => ({ ...p, supplier: e.target.value }))} placeholder="Nom du fournisseur" className={inputClass} />
            </Field>
            <Field label="N° Facture">
              <input type="text" value={newPurchase.invoice} onChange={(e) => setNewPurchase((p) => ({ ...p, invoice: e.target.value }))} placeholder="FAC-2025-XXXX" className={inputClass} />
            </Field>
            <Field label="Notes">
              <input type="text" value={newPurchase.notes} onChange={(e) => setNewPurchase((p) => ({ ...p, notes: e.target.value }))} placeholder="Notes optionnelles" className={inputClass} />
            </Field>
          </div>
          <div className="flex justify-end gap-2 pt-1">
            <button onClick={() => setShowAddForm(false)} className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg transition-colors">
              Annuler
            </button>
            <button onClick={handleSubmit} className="px-3 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors">
              Enregistrer
            </button>
          </div>
        </div>
      )}

      <div className="divide-y divide-slate-50">
        {sorted.length === 0 ? (
          <div className="p-8 text-center">
            <ShoppingCart className="w-8 h-8 text-slate-200 mx-auto mb-2" />
            <p className="text-sm text-slate-400">Aucun achat enregistré</p>
          </div>
        ) : (
          sorted.map((purchase, idx) => (
            <div key={purchase.id} className="p-4 hover:bg-slate-50/50 transition-colors">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center shrink-0 mt-0.5">
                  <ShoppingCart className="w-4 h-4 text-emerald-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-sm font-semibold text-slate-900">{purchase.supplier}</p>
                    <p className="text-sm font-bold text-slate-900">{formatPrice(purchase.quantity * purchase.unit_price)}</p>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-slate-500">
                    <span className="inline-flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {formatDateShort(purchase.date)}
                    </span>
                    <span>×{purchase.quantity}</span>
                    {purchase.unit_price > 0 && <span>@ {formatPrice(purchase.unit_price)}</span>}
                    {purchase.invoice && (
                      <span className="inline-flex items-center gap-1 text-blue-600 font-medium">
                        <FileText className="w-3 h-3" />
                        {purchase.invoice}
                      </span>
                    )}
                  </div>
                  {purchase.notes && (
                    <p className="text-xs text-slate-400 mt-1.5 italic">{purchase.notes}</p>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default function ProductDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { getProduct, updateProduct, addPurchase, deleteProduct } = useProducts()
  const product = getProduct(id)

  const [editing, setEditing] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [editData, setEditData] = useState({})

  if (!product) {
    return (
      <div className="flex-1 overflow-y-auto p-8">
        <div className="max-w-3xl mx-auto text-center py-20">
          <Package className="w-16 h-16 text-slate-200 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-slate-900 mb-2">Produit introuvable</h2>
          <p className="text-sm text-slate-500 mb-6">Ce produit n'existe pas ou a été supprimé.</p>
          <button onClick={() => navigate('/products')} className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl transition-colors">
            Retour aux produits
          </button>
        </div>
      </div>
    )
  }

  const catObj = PRODUCT_CATEGORIES.find((c) => c.value === product.category)
  const colors = CATEGORY_COLORS[product.category] || CATEGORY_COLORS.Autre
  const Icon = ICON_MAP[catObj?.icon] || Package

  const startEditing = () => {
    setEditData({
      name: product.name,
      reference: product.reference,
      brand: product.brand || '',
      category: product.category || 'Autre',
      description: product.description || '',
      price: product.price || 0,
      warranty_months: product.warranty_months || '',
      warranty_purchase_date: product.warranty_purchase_date || '',
      serial_number: product.serial_number || '',
      model: product.model || ''
    })
    setEditing(true)
  }

  const saveEdit = () => {
    updateProduct(product.id, {
      ...editData,
      price: Number(editData.price) || 0,
      warranty_months: editData.warranty_months ? Number(editData.warranty_months) : null
    })
    setEditing(false)
    toastService.success('Produit mis à jour.')
  }

  const handleImageChange = (newImageUrl) => {
    updateProduct(product.id, { image_url: newImageUrl })
  }

  const inputClass = 'w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all'
  const labelClass = 'text-[10px] font-bold text-slate-400 uppercase tracking-wider'

  return (
    <div className="flex-1 overflow-y-auto p-8">
      <div className="max-w-6xl mx-auto space-y-6">
        <button
          onClick={() => navigate('/products')}
          className="inline-flex items-center gap-2 text-sm font-semibold text-slate-500 hover:text-blue-600 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Retour aux produits
        </button>

        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className={`w-12 h-12 rounded-xl ${colors.bg} flex items-center justify-center`}>
              <Icon className={`w-6 h-6 ${colors.text}`} />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">{product.name}</h1>
              <p className="text-sm text-slate-500">Réf: {product.reference} • {product.brand}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {editing ? (
              <>
                <button onClick={() => setEditing(false)} className="px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition-colors">
                  Annuler
                </button>
                <button onClick={saveEdit} className="inline-flex items-center gap-2 px-5 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl shadow-lg shadow-blue-500/20 transition-all">
                  <Save className="w-4 h-4" />
                  Enregistrer
                </button>
              </>
            ) : (
              <>
                <button onClick={startEditing} className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-slate-600 bg-white border border-slate-200 hover:bg-slate-50 rounded-xl transition-colors">
                  <Edit3 className="w-4 h-4" />
                  Modifier
                </button>
                <button onClick={() => setShowDeleteModal(true)} className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-xl transition-colors">
                  <Trash2 className="w-4 h-4" />
                </button>
              </>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-white rounded-2xl border border-slate-200 custom-shadow p-6">
              <ImageUploader
                currentImage={editing ? editData.image_url : product.image_url}
                onImageChange={editing ? (url) => setEditData((d) => ({ ...d, image_url: url })) : handleImageChange}
                productName={product.name}
                category={product.category}
              />
            </div>

            <div className="bg-white rounded-2xl border border-slate-200 custom-shadow overflow-hidden">
              <div className="p-5 border-b border-slate-100 flex items-center gap-2.5">
                <div className="w-9 h-9 bg-blue-50 rounded-xl flex items-center justify-center">
                  <FileText className="w-5 h-5 text-blue-600" />
                </div>
                <h3 className="text-sm font-bold text-slate-900">Description</h3>
              </div>
              <div className="p-5">
                {editing ? (
                  <textarea
                    value={editData.description}
                    onChange={(e) => setEditData((d) => ({ ...d, description: e.target.value }))}
                    rows={4}
                    className={`${inputClass} resize-none`}
                    placeholder="Description du produit..."
                  />
                ) : (
                  <p className="text-sm text-slate-600 leading-relaxed">{product.description || 'Aucune description disponible.'}</p>
                )}
              </div>
            </div>

            <PurchaseHistory
              purchases={product.purchases}
              productId={product.id}
              onAddPurchase={addPurchase}
            />
          </div>

          <div className="space-y-6">
            <div className="bg-white rounded-2xl border border-slate-200 custom-shadow overflow-hidden">
              <div className="p-5 border-b border-slate-100 flex items-center gap-2.5">
                <div className="w-9 h-9 bg-slate-100 rounded-xl flex items-center justify-center">
                  <Tag className="w-5 h-5 text-slate-600" />
                </div>
                <h3 className="text-sm font-bold text-slate-900">Informations</h3>
              </div>
              <div className="p-5 space-y-3">
                {editing ? (
                  <>
                    <div className="space-y-1.5">
                      <label className={labelClass}>Nom</label>
                      <input type="text" value={editData.name} onChange={(e) => setEditData((d) => ({ ...d, name: e.target.value }))} className={inputClass} />
                    </div>
                    <div className="space-y-1.5">
                      <label className={labelClass}>Référence</label>
                      <input type="text" value={editData.reference} onChange={(e) => setEditData((d) => ({ ...d, reference: e.target.value }))} className={inputClass} />
                    </div>
                    <div className="space-y-1.5">
                      <label className={labelClass}>Marque</label>
                      <input type="text" value={editData.brand} onChange={(e) => setEditData((d) => ({ ...d, brand: e.target.value }))} className={inputClass} />
                    </div>
                    <div className="space-y-1.5">
                      <label className={labelClass}>Catégorie</label>
                      <select value={editData.category} onChange={(e) => setEditData((d) => ({ ...d, category: e.target.value }))} className={`${inputClass} cursor-pointer`}>
                        {PRODUCT_CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                      </select>
                    </div>
                    <div className="space-y-1.5">
                      <label className={labelClass}>Numéro de série</label>
                      <input type="text" value={editData.serial_number} onChange={(e) => setEditData((d) => ({ ...d, serial_number: e.target.value }))} className={inputClass} />
                    </div>
                    <div className="space-y-1.5">
                      <label className={labelClass}>Modèle</label>
                      <input type="text" value={editData.model} onChange={(e) => setEditData((d) => ({ ...d, model: e.target.value }))} className={inputClass} />
                    </div>
                    <div className="space-y-1.5">
                      <label className={labelClass}>Prix unitaire (€)</label>
                      <input type="number" step="0.01" min="0" value={editData.price} onChange={(e) => setEditData((d) => ({ ...d, price: e.target.value }))} className={inputClass} />
                    </div>
                    <div className="space-y-1.5">
                      <label className={labelClass}>Durée garantie (mois)</label>
                      <input type="number" min="0" value={editData.warranty_months} onChange={(e) => setEditData((d) => ({ ...d, warranty_months: e.target.value }))} className={inputClass} />
                    </div>
                    <div className="space-y-1.5">
                      <label className={labelClass}>Date d'achat</label>
                      <input type="date" value={editData.warranty_purchase_date} onChange={(e) => setEditData((d) => ({ ...d, warranty_purchase_date: e.target.value }))} className={inputClass} />
                    </div>
                  </>
                ) : (
                  <>
                    <InfoRow icon={<Tag className="w-4 h-4" />} label="Référence" value={product.reference} />
                    <InfoRow icon={<Building2 className="w-4 h-4" />} label="Marque" value={product.brand} />
                    <InfoRow icon={<Package className="w-4 h-4" />} label="Catégorie" value={catObj?.label || product.category} />
                    {product.serial_number && <InfoRow icon={<Hash className="w-4 h-4" />} label="S/N" value={product.serial_number} />}
                    {product.model && <InfoRow icon={<Monitor className="w-4 h-4" />} label="Modèle" value={product.model} />}
                    <InfoRow icon={<DollarSign className="w-4 h-4" />} label="Prix" value={formatPrice(product.price)} highlight />
                  </>
                )}
              </div>
            </div>

            <WarrantySection product={product} />

            <SpecsSection specs={product.specs} />

            <div className="bg-white rounded-2xl border border-slate-200 custom-shadow p-5 space-y-2">
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <Clock className="w-3.5 h-3.5" />
                <span>Créé le {formatDate(product.createdAt)}</span>
              </div>
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <Clock className="w-3.5 h-3.5" />
                <span>Modifié le {formatDate(product.updatedAt)}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <ConfirmModal
        open={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        onConfirm={() => { deleteProduct(product.id); navigate('/products') }}
        title="Supprimer le produit"
        message={`Êtes-vous sûr de vouloir supprimer "${product.name}" ? Cette action est irréversible.`}
        confirmLabel="Supprimer"
      />
    </div>
  )
}

function InfoRow({ icon, label, value, highlight = false }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-slate-50 last:border-0">
      <div className="flex items-center gap-2 text-slate-400">
        {icon}
        <span className="text-xs font-semibold">{label}</span>
      </div>
      <span className={`text-sm font-semibold ${highlight ? 'text-blue-600' : 'text-slate-800'}`}>{value || '—'}</span>
    </div>
  )
}
