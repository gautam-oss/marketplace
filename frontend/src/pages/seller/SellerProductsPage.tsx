import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Edit, Archive, ExternalLink } from 'lucide-react'
import { useMyProducts, useUpdateProduct } from '../../hooks/useProducts'
import LoadingSpinner from '../../components/LoadingSpinner'
import Pagination from '../../components/Pagination'
import PriceDisplay from '../../components/PriceDisplay'
import EmptyState from '../../components/EmptyState'
import { useToast } from '../../components/Toast'

const STATUS_BADGE: Record<string, string> = {
  active: 'bg-green-100 text-green-700',
  draft: 'bg-gray-100 text-gray-600',
  archived: 'bg-red-100 text-red-700',
}

export default function SellerProductsPage() {
  const [page, setPage] = useState(1)
  const [q, setQ] = useState('')
  const [selected, setSelected] = useState<Set<string>>(new Set())

  const { data, isLoading } = useMyProducts(page, 20)
  const { mutateAsync: updateProductAsync } = useUpdateProduct()
  const toast = useToast()

  const filtered = (data?.items ?? []).filter(
    (p) => !q || p.title.toLowerCase().includes(q.toLowerCase())
  )

  const toggleSelect = (slug: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(slug) ? next.delete(slug) : next.add(slug)
      return next
    })
  }

  const toggleSelectAll = () => {
    if (selected.size === filtered.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(filtered.map((p) => p.slug)))
    }
  }

  const handleBulkAction = async (status: 'active' | 'archived') => {
    const slugs = Array.from(selected)
    try {
      await Promise.all(slugs.map((slug) => updateProductAsync({ slug, payload: { status } })))
      setSelected(new Set())
      toast(`${slugs.length} product${slugs.length !== 1 ? 's' : ''} ${status === 'archived' ? 'archived' : 'activated'}`, 'success')
    } catch {
      toast('Some updates failed', 'error')
    }
  }

  const handleToggleStatus = async (slug: string, currentStatus: string) => {
    const newStatus = currentStatus === 'active' ? 'archived' : 'active'
    try {
      await updateProductAsync({ slug, payload: { status: newStatus as 'active' | 'archived' } })
      toast(`Product ${newStatus === 'active' ? 'activated' : 'archived'}`, 'success')
    } catch {
      toast('Failed to update product', 'error')
    }
  }

  if (isLoading) return <LoadingSpinner className="py-20" size="lg" />

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">My Products</h1>
        <Link
          to="/seller/products/new"
          className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
        >
          <Plus size={16} />
          New Product
        </Link>
      </div>

      {/* Search + bulk actions */}
      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        <input
          type="search"
          placeholder="Search products..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        {selected.size > 0 && (
          <div className="flex gap-2">
            <button
              onClick={() => handleBulkAction('active')}
              className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition-colors"
            >
              Activate ({selected.size})
            </button>
            <button
              onClick={() => handleBulkAction('archived')}
              className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 transition-colors"
            >
              Archive ({selected.size})
            </button>
          </div>
        )}
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          title="No products yet"
          description="Start selling by adding your first product."
          action={
            <Link to="/seller/products/new" className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors">
              Add product
            </Link>
          }
        />
      ) : (
        <>
          <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 w-8">
                    <input
                      type="checkbox"
                      checked={selected.size === filtered.length && filtered.length > 0}
                      onChange={toggleSelectAll}
                      className="accent-indigo-600"
                    />
                  </th>
                  <th className="text-left px-4 py-3 text-gray-600 font-medium">Product</th>
                  <th className="text-left px-4 py-3 text-gray-600 font-medium">Price</th>
                  <th className="text-left px-4 py-3 text-gray-600 font-medium">Stock</th>
                  <th className="text-left px-4 py-3 text-gray-600 font-medium">Status</th>
                  <th className="text-left px-4 py-3 text-gray-600 font-medium">Reviews</th>
                  <th className="text-right px-4 py-3 text-gray-600 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filtered.map((p) => (
                  <tr key={p.id} className={`hover:bg-gray-50 ${selected.has(p.slug) ? 'bg-indigo-50/50' : ''}`}>
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={selected.has(p.slug)}
                        onChange={() => toggleSelect(p.slug)}
                        className="accent-indigo-600"
                      />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-gray-100 rounded-lg overflow-hidden shrink-0">
                          {p.images?.[0] && (
                            <img src={p.images[0]} alt={p.title} className="w-full h-full object-cover" />
                          )}
                        </div>
                        <span className="font-medium text-gray-900 truncate max-w-[200px]">{p.title}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3"><PriceDisplay amount={p.price} size="sm" /></td>
                    <td className="px-4 py-3 text-gray-600">{p.stock}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${STATUS_BADGE[p.status] ?? ''}`}>
                        {p.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-500">{p.review_count}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        <Link
                          to={`/seller/products/${p.slug}/edit`}
                          className="p-1.5 text-gray-400 hover:text-indigo-600 transition-colors"
                          title="Edit"
                        >
                          <Edit size={15} />
                        </Link>
                        <button
                          onClick={() => handleToggleStatus(p.slug, p.status)}
                          className="p-1.5 text-gray-400 hover:text-amber-600 transition-colors"
                          title={p.status === 'active' ? 'Archive' : 'Restore'}
                        >
                          <Archive size={15} />
                        </button>
                        <Link
                          to={`/products/${p.slug}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="p-1.5 text-gray-400 hover:text-gray-700 transition-colors"
                          title="View on site"
                        >
                          <ExternalLink size={15} />
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {data && (
            <Pagination page={page} pages={data.pages} total={data.total} onPageChange={setPage} />
          )}
        </>
      )}
    </div>
  )
}
