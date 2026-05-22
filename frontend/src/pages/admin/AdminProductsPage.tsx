import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ExternalLink, CheckCircle, Archive } from 'lucide-react'
import { useAdminProducts, useAdminUpdateProductStatus } from '../../hooks/useAdmin'
import LoadingSpinner from '../../components/LoadingSpinner'
import Pagination from '../../components/Pagination'
import PriceDisplay from '../../components/PriceDisplay'
import { useToast } from '../../components/Toast'

const STATUSES = [
  { value: '', label: 'All' },
  { value: 'draft', label: 'Draft' },
  { value: 'active', label: 'Active' },
  { value: 'archived', label: 'Archived' },
]

const STATUS_BADGE: Record<string, string> = {
  active: 'bg-green-100 text-green-700',
  draft: 'bg-gray-100 text-gray-600',
  archived: 'bg-red-100 text-red-700',
}

export default function AdminProductsPage() {
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState<string | undefined>()
  const { data, isLoading } = useAdminProducts(page, 20, status)
  const { mutate: updateStatus } = useAdminUpdateProductStatus()
  const toast = useToast()

  const handleStatus = (product_id: string, newStatus: string) => {
    updateStatus(
      { product_id, status: newStatus },
      {
        onSuccess: () => toast(`Product ${newStatus}`, 'success'),
        onError: () => toast('Failed to update status', 'error'),
      }
    )
  }

  if (isLoading) return <LoadingSpinner className="py-20" size="lg" />

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Products</h1>

      {/* Status filter pills */}
      <div className="flex gap-2 flex-wrap mb-6">
        {STATUSES.map((s) => (
          <button
            key={s.value}
            onClick={() => { setStatus(s.value || undefined); setPage(1) }}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              (status ?? '') === s.value
                ? 'bg-indigo-600 text-white'
                : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

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
            {data?.items.map((p) => (
              <tr key={p.id} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-gray-100 rounded-lg overflow-hidden shrink-0">
                      {p.images?.[0] && (
                        <img src={p.images[0]} alt={p.title} className="w-full h-full object-cover" />
                      )}
                    </div>
                    <span className="font-medium text-gray-900 truncate max-w-[220px]">{p.title}</span>
                  </div>
                </td>
                <td className="px-4 py-3"><PriceDisplay amount={p.price} size="sm" /></td>
                <td className="px-4 py-3 text-gray-600">{p.stock}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${STATUS_BADGE[p.status] ?? ''}`}>
                    {p.status}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1">
                    {p.status !== 'active' && (
                      <button
                        onClick={() => handleStatus(p.id, 'active')}
                        className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-green-700 bg-green-50 hover:bg-green-100 rounded-lg transition-colors"
                        title="Approve"
                      >
                        <CheckCircle size={12} />
                        Approve
                      </button>
                    )}
                    {p.status !== 'archived' && (
                      <button
                        onClick={() => handleStatus(p.id, 'archived')}
                        className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-red-700 bg-red-50 hover:bg-red-100 rounded-lg transition-colors"
                        title="Archive"
                      >
                        <Archive size={12} />
                        Archive
                      </button>
                    )}
                    <Link
                      to={`/products/${p.slug}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-1.5 text-gray-400 hover:text-gray-700 transition-colors"
                      title="View on site"
                    >
                      <ExternalLink size={14} />
                    </Link>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {data?.items.length === 0 && (
          <p className="text-sm text-gray-400 text-center py-8">No products found.</p>
        )}
      </div>

      {data && <Pagination page={page} pages={data.pages} total={data.total} onPageChange={setPage} />}
    </div>
  )
}
