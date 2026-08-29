import { createContext, useCallback, useEffect, useState } from 'react'
import { apiRequest } from '../api/client'
import { useAuth } from './useAuth'

const ProductsContext = createContext(null)

export const PRODUCT_CATEGORIES = [
  { value: 'Ecrans', label: 'Écrans', icon: 'monitor' },
  { value: 'Serveurs', label: 'Serveurs', icon: 'server' },
  { value: 'Reseau', label: 'Réseau', icon: 'wifi' },
  { value: 'Impression', label: 'Impression', icon: 'printer' },
  { value: 'Stockage', label: 'Stockage', icon: 'hard-drive' },
  { value: 'Audio', label: 'Audio', icon: 'headphones' },
  { value: 'Autre', label: 'Autre', icon: 'package' },
]

const adapt = (product) => ({ ...product, createdAt: product.created_at, updatedAt: product.updated_at, purchases: product.purchases || [] })

export function ProductsProvider({ children }) {
  const { user } = useAuth()
  const token = user?.access_token || user?.token
  const [products, setProducts] = useState([])
  const [error, setError] = useState(null)

  const reload = useCallback(async () => {
    try {
      setError(null)
      const data = await apiRequest('/products/', { token })
      setProducts((Array.isArray(data) ? data : data.items || []).map(adapt))
    } catch (err) {
      setError(err.message)
      setProducts([])
    }
  }, [token])

  useEffect(() => { reload() }, [reload])

  const createProduct = async (data) => { const result = await apiRequest('/products/', { token, method: 'POST', body: JSON.stringify(data) }); await reload(); return adapt(result) }
  const updateProduct = async (id, data) => { const result = await apiRequest(`/products/${id}`, { token, method: 'PATCH', body: JSON.stringify(data) }); await reload(); return adapt(result) }
  const deleteProduct = async (id) => { await apiRequest(`/products/${id}`, { token, method: 'DELETE' }); await reload() }
  const addPurchase = async (productId, purchaseData) => apiRequest(`/products/${productId}/purchases`, { token, method: 'POST', body: JSON.stringify(purchaseData) })
  const searchProducts = (query, category = null) => products.filter((p) => (!category || p.category === category) && (!query || [p.name, p.reference, p.brand, p.description, p.serial_number].some((value) => value?.toLowerCase().includes(query.toLowerCase()))))

  return <ProductsContext.Provider value={{ products, error, reload, getProduct: (id) => products.find((p) => p.id === id), getProductsByCategory: (category) => category ? products.filter((p) => p.category === category) : products, createProduct, updateProduct, deleteProduct, addPurchase, searchProducts, categories: PRODUCT_CATEGORIES }}>{children}</ProductsContext.Provider>
}

export default ProductsContext
