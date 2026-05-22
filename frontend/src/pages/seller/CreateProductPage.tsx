import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, X } from 'lucide-react'
import { useCreateProduct } from '../../hooks/useProducts'
import { useCategories } from '../../hooks/useCategories'
import { useToast } from '../../components/Toast'
import LoadingSpinner from '../../components/LoadingSpinner'

interface FormState {
  title: string
  description: string
  category_id: string
  tags: string[]
  price: string
  compare_at_price: string
  stock: string
  sku: string
}

interface ImagePreview {
  file: File
  url: string
}

const slugify = (t: string) =>
  t.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '').replace(/-+/g, '-').replace(/^-|-$/g, '')

const EMPTY: FormState = {
  title: '', description: '', category_id: '', tags: [],
  price: '', compare_at_price: '', stock: '', sku: '',
}

export default function CreateProductPage() {
  const navigate = useNavigate()
  const toast = useToast()
  const { mutateAsync: createProduct, isPending } = useCreateProduct()
  const { data: categories } = useCategories()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [form, setForm] = useState<FormState>(EMPTY)
  const [images, setImages] = useState<ImagePreview[]>([])
  const [tagInput, setTagInput] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const [status, setStatus] = useState<'draft' | 'active'>('draft')

  useEffect(() => {
    return () => { images.forEach((img) => URL.revokeObjectURL(img.url)) }
  }, [images])

  const addImages = (files: FileList | null) => {
    if (!files) return
    const remaining = 5 - images.length
    const valid = Array.from(files)
      .filter((f) => f.type.startsWith('image/') && f.size <= 5 * 1024 * 1024)
      .slice(0, remaining)
    if (!valid.length) return
    setImages((prev) => [...prev, ...valid.map((file) => ({ file, url: URL.createObjectURL(file) }))].slice(0, 5))
  }

  const removeImage = (idx: number) => {
    URL.revokeObjectURL(images[idx].url)
    setImages((prev) => prev.filter((_, i) => i !== idx))
  }

  const addTag = (input: string) => {
    const newTags = input.split(',').map((t) => t.trim()).filter((t) => t && !form.tags.includes(t))
    if (newTags.length) setForm((f) => ({ ...f, tags: [...f.tags, ...newTags] }))
    setTagInput('')
  }

  const removeTag = (tag: string) => setForm((f) => ({ ...f, tags: f.tags.filter((t) => t !== tag) }))

  const setField = (key: keyof Omit<FormState, 'tags'>) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      setForm((f) => ({ ...f, [key]: e.target.value }))

  const submit = async (publishStatus: 'draft' | 'active') => {
    if (publishStatus === 'active') {
      if (!form.stock || parseInt(form.stock) <= 0) { toast('Stock must be > 0 to publish', 'error'); return }
      if (!form.category_id) { toast('Please select a category to publish', 'error'); return }
    }
    try {
      await createProduct({
        payload: {
          title: form.title,
          description: form.description || undefined,
          price: parseFloat(form.price),
          compare_at_price: form.compare_at_price ? parseFloat(form.compare_at_price) : undefined,
          stock: parseInt(form.stock) || 0,
          category_id: form.category_id || undefined,
          tags: form.tags.length ? form.tags : undefined,
          sku: form.sku || undefined,
        },
        images: images.length ? images.map((i) => i.file) : undefined,
      })
      toast('Product created!', 'success')
      navigate('/seller/products')
    } catch {
      toast('Failed to create product', 'error')
    }
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Add Product</h1>

      <div className="space-y-6">
        {/* Section 1 — Basic Info */}
        <section className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
          <h2 className="font-semibold text-gray-900">Basic Info</h2>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Title <span className="text-red-500">*</span>
            </label>
            <input required type="text" value={form.title} onChange={setField('title')} minLength={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            {form.title && (
              <p className="text-xs text-gray-400 mt-1">Slug: {slugify(form.title)}</p>
            )}
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
              <option value="">Select category</option>
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
              placeholder="Type a tag and press Enter or comma"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
        </section>

        {/* Section 2 — Pricing & Inventory */}
        <section className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
          <h2 className="font-semibold text-gray-900">Pricing & Inventory</h2>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Price (₹) <span className="text-red-500">*</span>
              </label>
              <input required type="number" min="0.01" step="0.01" value={form.price} onChange={setField('price')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Compare At Price (₹)</label>
              <input type="number" min="0.01" step="0.01" value={form.compare_at_price} onChange={setField('compare_at_price')}
                placeholder="Original price (optional)"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Stock <span className="text-red-500">*</span>
              </label>
              <input required type="number" min="0" value={form.stock} onChange={setField('stock')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">SKU</label>
              <input type="text" value={form.sku} onChange={setField('sku')} placeholder="Optional"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            </div>
          </div>
        </section>

        {/* Section 3 — Images */}
        <section className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
          <h2 className="font-semibold text-gray-900">Images</h2>

          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => { e.preventDefault(); setDragOver(false); addImages(e.dataTransfer.files) }}
            className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer ${
              dragOver ? 'border-indigo-400 bg-indigo-50' : 'border-gray-300 hover:border-indigo-300'
            }`}
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload size={32} className="mx-auto mb-2 text-gray-400" />
            <p className="text-sm text-gray-600">
              Drop images here or <span className="text-indigo-600">browse</span>
            </p>
            <p className="text-xs text-gray-400 mt-1">Up to 5 images · JPG, PNG, WebP · max 5MB each</p>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={(e) => addImages(e.target.files)}
            />
          </div>

          {images.length > 0 && (
            <div className="grid grid-cols-5 gap-2">
              {images.map((img, idx) => (
                <div key={idx} className="relative aspect-square bg-gray-100 rounded-lg overflow-hidden group">
                  <img src={img.url} alt="" className="w-full h-full object-cover" />
                  <button
                    type="button"
                    onClick={() => removeImage(idx)}
                    className="absolute top-1 right-1 bg-black/60 text-white rounded-full p-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <X size={12} />
                  </button>
                </div>
              ))}
              {Array.from({ length: 5 - images.length }).map((_, idx) => (
                <div key={`empty-${idx}`} className="aspect-square bg-gray-50 border-2 border-dashed border-gray-200 rounded-lg" />
              ))}
            </div>
          )}
        </section>

        {/* Section 4 — Publish */}
        <section className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
          <h2 className="font-semibold text-gray-900">Publish</h2>

          <div className="flex gap-2">
            {(['draft', 'active'] as const).map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setStatus(s)}
                className={`flex-1 py-2 rounded-lg text-sm font-medium border transition-colors capitalize ${
                  status === s
                    ? 'bg-indigo-600 text-white border-indigo-600'
                    : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                }`}
              >
                {s === 'draft' ? 'Draft' : 'Active'}
              </button>
            ))}
          </div>

          <p className="text-xs text-gray-500">
            {status === 'draft' ? 'Draft products are not visible to buyers.' : 'Active products are visible to buyers. Requires stock > 0 and a category.'}
          </p>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={() => navigate('/seller/products')}
              className="flex-1 py-2.5 border border-gray-300 rounded-xl text-sm font-medium hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={isPending || !form.title || !form.price || !form.stock}
              onClick={() => submit(status)}
              className="flex-[2] py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
            >
              {isPending && <LoadingSpinner size="sm" />}
              {isPending ? 'Saving...' : status === 'draft' ? 'Save as Draft' : 'Publish Now'}
            </button>
          </div>
        </section>
      </div>
    </div>
  )
}
