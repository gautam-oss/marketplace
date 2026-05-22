import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useProduct, useUpdateProduct } from '../hooks/useProducts'
import { useCategories } from '../hooks/useCategories'
import { useToast } from '../components/Toast'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'

export default function EditProductPage() {
  const { slug } = useParams<{ slug: string }>()
  const navigate = useNavigate()
  const toast = useToast()
  const { data: product, isLoading, error } = useProduct(slug!)
  const { mutate: updateProduct, isPending } = useUpdateProduct()
  const { data: categories } = useCategories()

  const [form, setForm] = useState({
    title: '',
    description: '',
    price: '',
    stock: '',
    category_id: '',
    status: 'draft' as 'draft' | 'active' | 'archived',
  })

  useEffect(() => {
    if (product) {
      setForm({
        title: product.title,
        description: product.description ?? '',
        price: String(product.price),
        stock: String(product.stock),
        category_id: product.category_id ?? '',
        status: product.status,
      })
    }
  }, [product])

  if (isLoading) return <LoadingSpinner className="py-20" size="lg" />
  if (error || !product) return <ErrorMessage message="Product not found" />

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    updateProduct(
      {
        slug: slug!,
        payload: {
          title: form.title,
          description: form.description || undefined,
          price: parseFloat(form.price),
          stock: parseInt(form.stock),
          category_id: form.category_id || undefined,
          status: form.status,
        },
      },
      {
        onSuccess: () => { toast('Product updated', 'success'); navigate('/seller/products') },
        onError: () => toast('Failed to update product', 'error'),
      }
    )
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Edit product</h1>
      <form onSubmit={handleSubmit} className="bg-white border border-gray-200 rounded-xl p-6 space-y-5">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Title <span className="text-red-500">*</span></label>
          <input type="text" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
          <textarea rows={4} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none" />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Price (₹) <span className="text-red-500">*</span></label>
            <input type="number" required min="0" step="0.01" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Stock <span className="text-red-500">*</span></label>
            <input type="number" required min="0" value={form.stock} onChange={(e) => setForm({ ...form, stock: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
            <select value={form.category_id} onChange={(e) => setForm({ ...form, category_id: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white">
              <option value="">None</option>
              {categories?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value as typeof form.status })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white">
              <option value="draft">Draft</option>
              <option value="active">Active</option>
              <option value="archived">Archived</option>
            </select>
          </div>
        </div>
        <div className="flex gap-3 pt-2">
          <button type="button" onClick={() => navigate('/seller/products')}
            className="flex-1 py-2 border border-gray-300 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors">
            Cancel
          </button>
          <button type="submit" disabled={isPending}
            className="flex-1 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-2">
            {isPending && <LoadingSpinner size="sm" />}
            {isPending ? 'Saving...' : 'Save changes'}
          </button>
        </div>
      </form>
    </div>
  )
}
