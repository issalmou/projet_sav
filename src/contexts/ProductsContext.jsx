import { createContext, useState, useEffect } from 'react'

const ProductsContext = createContext(null)
const STORAGE_KEY = 'sav_products'

export const PRODUCT_CATEGORIES = [
  { value: 'Ecrans', label: 'Écrans', icon: 'monitor' },
  { value: 'Serveurs', label: 'Serveurs', icon: 'server' },
  { value: 'Reseau', label: 'Réseau', icon: 'wifi' },
  { value: 'Impression', label: 'Impression', icon: 'printer' },
  { value: 'Stockage', label: 'Stockage', icon: 'hard-drive' },
  { value: 'Audio', label: 'Audio', icon: 'headphones' },
  { value: 'Autre', label: 'Autre', icon: 'package' }
]

const SEED_PRODUCTS = [
  {
    id: 'PRD-001',
    reference: 'NX-OLED-48293',
    name: '3LM Solution Pro 32" 4K OLED',
    category: 'Ecrans',
    description: 'Moniteur professionnel 32 pouces, résolution 4K OLED, connexion USB-C et HDMI 2.1. Excellent pour le design graphique et le montage vidéo.',
    warranty_months: 36,
    warranty_purchase_date: '2024-06-15',
    price: 1299.99,
    image_url: null,
    brand: '3LM Solutions',
    serial_number: 'SN-NXOLED-48293',
    model: '3LM-OLED-32',
    specs: { ecran: '32"', resolution: '4K OLED', connectivite: 'USB-C, HDMI 2.1', poids: '7.2 kg' },
    purchases: [
      { id: 'PUR-001', date: '2024-06-15', quantity: 2, unit_price: 1299.99, supplier: '3LM Solutions Direct', invoice: 'FAC-2024-0892', notes: 'Commande initiale bureau design' },
      { id: 'PUR-002', date: '2025-01-10', quantity: 1, unit_price: 1199.00, supplier: '3LM Solutions Direct', invoice: 'FAC-2025-0134', notes: 'Remplacement unité défectueuse' }
    ],
    createdAt: '2024-06-15T10:00:00Z',
    updatedAt: '2025-01-10T10:00:00Z'
  },
  {
    id: 'PRD-002',
    reference: 'SG-X1-9920',
    name: 'Smart Gateway Hub X-1',
    category: 'Reseau',
    description: 'Routeur intelligent double bande Wi-Fi 6E, gestion centralisée et sécurité avancée. Adapté aux environnements professionnels.',
    warranty_months: 24,
    warranty_purchase_date: '2024-01-10',
    price: 349.99,
    image_url: null,
    brand: '3LM Solutions',
    serial_number: 'SN-SGX1-9920',
    model: 'SG-HUB-X1',
    specs: { wifi: 'Wi-Fi 6E double bande', ports: '4x Gigabit', security: 'WPA3, VPN', autonomie: 'N/A' },
    purchases: [
      { id: 'PUR-003', date: '2024-01-10', quantity: 5, unit_price: 349.99, supplier: 'RéseauPro SAS', invoice: 'FAC-2024-0201', notes: 'Déploiement réseau étage 3' }
    ],
    createdAt: '2024-01-10T10:00:00Z',
    updatedAt: '2024-01-10T10:00:00Z'
  },
  {
    id: 'PRD-003',
    reference: 'SRV-DL380-G11',
    name: 'ProLiant DL380 Gen11',
    category: 'Serveurs',
    description: 'Serveur rack 2U, processeur Intel Xeon 4ème gen, 128 Go DDR5, stockage NVMe. Performance et fiabilité pour charges de travail critiques.',
    warranty_months: 60,
    warranty_purchase_date: '2025-03-20',
    price: 8750.00,
    image_url: null,
    brand: 'HP Enterprise',
    serial_number: 'SN-DL380G11-7742',
    model: 'DL380-G11-XEON',
    specs: { processeur: 'Intel Xeon 4ème gen', ram: '128 Go DDR5', stockage: '4x 960Go NVMe', os: 'Windows Server 2022' },
    purchases: [
      { id: 'PUR-004', date: '2025-03-20', quantity: 1, unit_price: 8750.00, supplier: 'HP Enterprise France', invoice: 'FAC-2025-0445', notes: 'Datacenter principal' }
    ],
    createdAt: '2025-03-20T10:00:00Z',
    updatedAt: '2025-03-20T10:00:00Z'
  },
  {
    id: 'PRD-004',
    reference: 'IMP-M404DN',
    name: 'LaserJet Pro M404dn',
    category: 'Impression',
    description: 'Imprimante laser monochrome, recto-verso automatique, 40 ppm, connectivité Ethernet. Compacte et rapide pour les bureaux.',
    warranty_months: 12,
    warranty_purchase_date: '2025-08-01',
    price: 429.00,
    image_url: null,
    brand: 'HP',
    serial_number: 'SN-HPM404-3318',
    model: 'M404DN',
    specs: { vitesse: '40 ppm', resolution: '1200x1200 dpi', duplex: 'Automatique', connectique: 'Ethernet, USB 2.0' },
    purchases: [
      { id: 'PUR-005', date: '2025-08-01', quantity: 3, unit_price: 429.00, supplier: 'Bureau Plus', invoice: 'FAC-2025-0712', notes: 'Bureaux accueil et salles de réunion' }
    ],
    createdAt: '2025-08-01T10:00:00Z',
    updatedAt: '2025-08-01T10:00:00Z'
  },
  {
    id: 'PRD-005',
    reference: 'STO-NAS-SYN423',
    name: 'Synology DiskStation DS423+',
    category: 'Stockage',
    description: 'NAS 4 baies, processeur Intel Celeron, 2 Go DDR4, idéal pour sauvegardes et partage de fichiers en réseau.',
    warranty_months: 36,
    warranty_purchase_date: '2023-11-05',
    price: 599.00,
    image_url: null,
    brand: 'Synology',
    serial_number: 'SN-SYN423-5501',
    model: 'DS423+',
    specs: { baies: '4x 3.5"/2.5"', processeur: 'Intel Celeron', ram: '2 Go DDR4', reseau: '2x 1GbE' },
    purchases: [
      { id: 'PUR-006', date: '2023-11-05', quantity: 1, unit_price: 599.00, supplier: 'Synology Store FR', invoice: 'FAC-2023-1189', notes: 'Sauvegarde serveur principal' },
      { id: 'PUR-007', date: '2024-06-20', quantity: 4, unit_price: 189.99, supplier: 'Synology Store FR', invoice: 'FAC-2024-0756', notes: 'Disques durs 4To WD Red pour NAS' }
    ],
    createdAt: '2023-11-05T10:00:00Z',
    updatedAt: '2024-06-20T10:00:00Z'
  },
  {
    id: 'PRD-006',
    reference: 'AUD-Jabra520',
    name: 'Jabra Speak 520',
    category: 'Audio',
    description: 'Haut-parleur Bluetooth portable pour conférences, micro omnidirectionnel, 15h d\'autonomie. Son cristallin pour réunions hybrides.',
    warranty_months: 24,
    warranty_purchase_date: '2025-01-18',
    price: 189.99,
    image_url: null,
    brand: 'Jabra',
    serial_number: 'SN-JAB520-8874',
    model: 'Speak 520',
    specs: { bluetooth: '5.0', autonomie: '15h', micro: 'Omnidirectionnel', portee: '30m' },
    purchases: [
      { id: 'PUR-008', date: '2025-01-18', quantity: 10, unit_price: 189.99, supplier: 'AudioPro Solutions', invoice: 'FAC-2025-0198', notes: 'Salles de réunion étages 1-3' }
    ],
    createdAt: '2025-01-18T10:00:00Z',
    updatedAt: '2025-01-18T10:00:00Z'
  },
  {
    id: 'PRD-007',
    reference: 'NX-OLED-55100',
    name: '3LM Solution Ultra 27" QHD',
    category: 'Ecrans',
    description: 'Moniteur QHD 27 pouces, panneau IPS 165Hz, temps de réponse 1ms, USB-C 90W PD. Polyvalent pour productivité et gaming.',
    warranty_months: 36,
    warranty_purchase_date: '2025-05-12',
    price: 649.99,
    image_url: null,
    brand: '3LM Solutions',
    serial_number: 'SN-NXQHD-55100',
    model: '3LM-ULTRA-27',
    specs: { ecran: '27"', resolution: 'QHD IPS 165Hz', reponse: '1ms', usb_c: '90W PD' },
    purchases: [
      { id: 'PUR-009', date: '2025-05-12', quantity: 4, unit_price: 649.99, supplier: '3LM Solutions Direct', invoice: 'FAC-2025-0567', notes: 'Postes développeurs' }
    ],
    createdAt: '2025-05-12T10:00:00Z',
    updatedAt: '2025-05-12T10:00:00Z'
  },
  {
    id: 'PRD-008',
    reference: 'SW-C9300-48T',
    name: 'Catalyst 9300 48-Port',
    category: 'Reseau',
    description: 'Commutateur enterprise 48 ports Gigabit, PoE+, modular, gestion Centralisée. Cœur de réseau pour infrastructures scale.',
    warranty_months: 120,
    warranty_purchase_date: '2024-09-01',
    price: 12450.00,
    image_url: null,
    brand: 'Cisco',
    serial_number: 'SN-C9300-1129',
    model: 'C9300-48T',
    specs: { ports: '48x 1GbE', poe: 'PoE+ (740W)', stack: 'StackWise-480', management: 'Cisco DNA Center' },
    purchases: [
      { id: 'PUR-010', date: '2024-09-01', quantity: 2, unit_price: 12450.00, supplier: 'Cisco Systems France', invoice: 'FAC-2024-0934', notes: 'Core network datacenter' }
    ],
    createdAt: '2024-09-01T10:00:00Z',
    updatedAt: '2024-09-01T10:00:00Z'
  }
]

const newId = (products) => {
  const max = products.reduce((m, p) => {
    const n = parseInt(String(p.id).replace('PRD-', ''), 10)
    return Number.isNaN(n) ? m : Math.max(m, n)
  }, 0)
  return 'PRD-' + String(max + 1).padStart(3, '0')
}

const newPurchaseId = (purchases) => {
  const max = purchases.reduce((m, p) => {
    const n = parseInt(String(p.id).replace('PUR-', ''), 10)
    return Number.isNaN(n) ? m : Math.max(m, n)
  }, 0)
  return 'PUR-' + String(max + 1).padStart(3, '0')
}

export function ProductsProvider({ children }) {
  const [products, setProducts] = useState(() => {
    try {
      const stored = JSON.parse(localStorage.getItem(STORAGE_KEY))
      if (Array.isArray(stored) && stored.length > 0) return stored
    } catch {}
    return SEED_PRODUCTS
  })

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(products))
  }, [products])

  const createProduct = (data) => {
    const now = new Date().toISOString()
    const product = {
      id: newId(products),
      reference: data.reference,
      name: data.name,
      category: data.category || 'Autre',
      description: data.description || '',
      warranty_months: data.warranty_months || null,
      warranty_purchase_date: data.warranty_purchase_date || null,
      price: data.price || 0,
      image_url: data.image_url || null,
      brand: data.brand || '',
      serial_number: data.serial_number || '',
      model: data.model || '',
      specs: data.specs || {},
      purchases: [],
      createdAt: now,
      updatedAt: now
    }
    setProducts((prev) => [product, ...prev])
    return product
  }

  const updateProduct = (id, data) =>
    setProducts((prev) =>
      prev.map((p) =>
        p.id === id ? { ...p, ...data, updatedAt: new Date().toISOString() } : p
      )
    )

  const deleteProduct = (id) =>
    setProducts((prev) => prev.filter((p) => p.id !== id))

  const getProduct = (id) => products.find((p) => p.id === id)

  const getProductsByCategory = (category) =>
    category ? products.filter((p) => p.category === category) : products

  const addPurchase = (productId, purchaseData) => {
    const now = new Date().toISOString()
    const purchase = {
      id: newPurchaseId(products.flatMap((p) => p.purchases || [])),
      date: purchaseData.date || new Date().toISOString().slice(0, 10),
      quantity: purchaseData.quantity || 1,
      unit_price: purchaseData.unit_price || 0,
      supplier: purchaseData.supplier || '',
      invoice: purchaseData.invoice || '',
      notes: purchaseData.notes || ''
    }
    setProducts((prev) =>
      prev.map((p) =>
        p.id === productId
          ? { ...p, purchases: [...(p.purchases || []), purchase], updatedAt: now }
          : p
      )
    )
    return purchase
  }

  const searchProducts = (query, category = null) => {
    let result = products
    if (category) {
      result = result.filter((p) => p.category === category)
    }
    if (query && query.trim()) {
      const q = query.toLowerCase().trim()
      result = result.filter(
        (p) =>
          p.name.toLowerCase().includes(q) ||
          p.reference.toLowerCase().includes(q) ||
          (p.brand && p.brand.toLowerCase().includes(q)) ||
          (p.description && p.description.toLowerCase().includes(q)) ||
          (p.serial_number && p.serial_number.toLowerCase().includes(q))
      )
    }
    return result
  }

  return (
    <ProductsContext.Provider
      value={{
        products,
        getProduct,
        getProductsByCategory,
        createProduct,
        updateProduct,
        deleteProduct,
        addPurchase,
        searchProducts,
        categories: PRODUCT_CATEGORIES
      }}
    >
      {children}
    </ProductsContext.Provider>
  )
}

export default ProductsContext
