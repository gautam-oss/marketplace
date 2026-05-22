import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Edit, Trash2 } from 'lucide-react'
import { useMyProducts, useDeleteProduct } from '../hooks/useProducts'
import LoadingSpinner from '../components/LoadingSpinner'
import Pagination from '../components/Pagination'
import PriceDisplay from '../components/PriceDisplay'
import EmptyState from '../components/EmptyState'
import { useToast } from '../components/Toast'

export default function SellerProductsPage() {
  const [page, setPage] = useState(1)
  const { data, isLoading } = useMyProducts(page)
  const { mutate: deleteProduct } = useDeleteProduct()
  const toast = useToast()

  const handleDelete = (slug: string, title: string) => {
    if (!confirm(`Delete "${title}"?`)) return
    deleteProduct(slug, {
      onSuccess: () => toast('Product deleted', 'success'),
      onError: () => toast('Failed to delete product', 'error'),
    })
  }

  if (isLoading) return <LoadingSpinner className="py-20" size="lg" />

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">My Products</h1>
        <Link
          to="/seller/products/new"
          className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
        >
          <Plus size={16} />
          Add product
        </Link>
      </div>

      {!data?.items.length ? (
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
                  <th className="text-left px-4 py-3 text-gray-600 font-medium">Product</th>
                  <th className="text-left px-4 py-3 text-gray-600 font-medium">Price</th>
                  <th className="text-left px-4 py-3 text-gray-600 font-medium">Stock</th>
                  <th className="text-left px-4 py-3 text-gray-600 font-medium">Status</th>
                  <th className="text-right px-4 py-3 text-gray-600 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.items.map((p) => (
                  <tr key={p.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-gray-100 rounded-lg overflow-hidden shrink-0">
                          {p.images?.[0] && <img src={p.images[0]} alt={p.title} className="w-full h-full object-cover" />}
                        </div>
                        <span className="font-medium text-gray-900 truncate max-w-xs">{p.title}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3"><PriceDisplay amount={p.price} size="sm" /></td>
                    <td className="px-4 py-3 text-gray-600">{p.stock}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${
                        p.status === 'active' ? 'bg-green-100 text-green-700' :
                        p.status === 'archived' ? 'bg-red-100 text-red-700' :
                        'bg-gray-100 text-gray-600'
                      }`}>
                        {p.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-2">
                        <Link to={`/seller/products/${p.slug}/edit`} className="p-1.5 text-gray-400 hover:text-indigo-600 transition-colors">
                          <Edit size={15} />
                        </Link>
                        <button onClick={() => handleDelete(p.slug, p.title)} className="p-1.5 text-gray-400 hover:text-red-600 transition-colors">
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={page} pages={data.pages} total={data.total} onPageChange={setPage} />
        </>
      )}
    </div>
  )
}
