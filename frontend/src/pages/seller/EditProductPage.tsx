import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { X } from 'lucide-react'
import { useProduct, useUpdateProduct } from '../../hooks/useProducts'
import { useCategories } from '../../hooks/useCategories'
import { useToast } from '../../components/Toast'
import LoadingSpinner from '../../components/LoadingSpinner'
import ErrorMessage from '../../components/ErrorMessage'

interface FormState {
  title: string
  description: string
  category_id: string
  tags: string[]
  price: string
  compare_at_price: string
  stock: string
  sku: string
  status: 'draft' | 'active' | 'archived'
}

export default function EditProductPage() {
  const { slug } = useParams<{ slug: string }>()
  const navigate = useNavigate()
  const toast = useToast()
  const { data: product, isLoading, error } = useProduct(slug!)
  const { mutateAsync: updateProduct, isPending } = useUpdateProduct()
  const { data: categories } = useCategories()

  const [form, setForm] = useState<FormState>({
    title: '', description: '', category_id: '', tags: [],
    price: '', compare_at_price: '', stock: '', sku: '', status: 'draft',
  })
  const [tagInput, setTagInput] = useState('')

  useEffect(() => {
    if (product) {
      setForm({
        title: product.title,
        description: product.description ?? '',
        category_id: product.category_id ?? '',
        tags: product.tags ?? [],
        price: String(product.price),
        compare_at_price: product.compare_at_price ? String(product.compare_at_price) : '',
        stock: String(product.stock),
        sku: '',
        status: product.status,
      })
    }
  }, [product])

  if (isLoading) return <LoadingSpinner className="py-20" size="lg" />
  if (error || !product) return <ErrorMessage message="Product not found" />

  const setField = (key: keyof Omit<FormState, 'tags' | 'status'>) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      setForm((f) => ({ ...f, [key]: e.target.value }))

  const addTag = (input: string) => {
    const newTags = input.split(',').map((t) => t.trim()).filter((t) => t && !form.tags.includes(t))
    if (newTags.length) setForm((f) => ({ ...f, tags: [...f.tags, ...newTags] }))
    setTagInput('')
  }

  const removeTag = (tag: string) => setForm((f) => ({ ...f, tags: f.tags.filter((t) => t !== tag) }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await updateProduct({
        slug: slug!,
        payload: {
          title: form.title,
          description: form.description || undefined,
          price: parseFloat(form.price),
          stock: parseInt(form.stock),
          category_id: form.category_id || undefined,
          status: form.status,
        },
      })
      toast('Product updated', 'success')
      navigate('/seller/products')
    } catch {
      toast('Failed to update product', 'error')
    }
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Edit Product</h1>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Info */}
        <section className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
          <h2 className="font-semibold text-gray-900">Basic Info</h2>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Title <span className="text-red-500">*</span></label>
            <input required type="text" value={form.title} onChange={setField('title')} minLength={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea rows={4} value={form.description} onChange={setField('description')}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none" />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
            <select value={form.category_id} onChange={setField('category_id')}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white">
              <option value="">None</option>
              {categories?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Tags</label>
            <div className="flex flex-wrap gap-1.5 mb-2">
              {form.tags.map((tag) => (
                <span key={tag} className="flex items-center gap-1 px-2 py-0.5 bg-indigo-100 text-indigo-700 rounded-full text-xs">
                  {tag}
                  <button type="button" onClick={() => removeTag(tag)} className="hover:text-indigo-900">
                    <X size={10} />
                  </button>
                </span>
              ))}
            </div>
            <input
              type="text"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); addTag(tagInput) } }}
              onBlur={() => { if (tagInput.trim()) addTag(tagInput) }}
              placeholder="Type a tag and press Enter"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
        </section>

        {/* Pricing & Inventory */}
        <section className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
          <h2 className="font-semibold text-gray-900">Pricing & Inventory</h2>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Price (₹) <span className="text-red-500">*</span></label>
              <input required type="number" min="0.01" step="0.01" value={form.price} onChange={setField('price')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Compare At Price (₹)</label>
              <input type="number" min="0.01" step="0.01" value={form.compare_at_price} onChange={setField('compare_at_price')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Stock <span className="text-red-500">*</span></label>
              <input required type="number" min="0" value={form.stock} onChange={setField('stock')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
              <select value={form.status}
                onChange={(e) => setForm((f) => ({ ...f, status: e.target.value as FormState['status'] }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white">
                <option value="draft">Draft</option>
                <option value="active">Active</option>
                <option value="archived">Archived</option>
              </select>
            </div>
          </div>
        </section>

        {/* Existing Images (read-only) */}
        {product.images.length > 0 && (
          <section className="bg-white border border-gray-200 rounded-xl p-6">
            <h2 className="font-semibold text-gray-900 mb-3">Current Images</h2>
            <div className="grid grid-cols-5 gap-2">
              {product.images.map((url, idx) => (
                <div key={idx} className="aspect-square bg-gray-100 rounded-lg overflow-hidden">
                  <img src={url} alt="" className="w-full h-full object-cover" />
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-400 mt-2">Images cannot be changed after creation.</p>
          </section>
        )}

        <div className="flex gap-3">
          <button type="button" onClick={() => navigate('/seller/products')}
            className="flex-1 py-2.5 border border-gray-300 rounded-xl text-sm font-medium hover:bg-gray-50 transition-colors">
            Cancel
          </button>
          <button type="submit" disabled={isPending}
            className="flex-[2] py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-2">
            {isPending && <LoadingSpinner size="sm" />}
            {isPending ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </form>
    </div>
  )
}
