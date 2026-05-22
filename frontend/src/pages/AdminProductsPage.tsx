import { useState } from 'react'
import { useAdminProducts, useAdminUpdateProductStatus } from '../hooks/useAdmin'
import LoadingSpinner from '../components/LoadingSpinner'
import Pagination from '../components/Pagination'
import PriceDisplay from '../components/PriceDisplay'
import { useToast } from '../components/Toast'

const STATUSES = ['', 'draft', 'active', 'archived']

export default function AdminProductsPage() {
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState<string | undefined>()
  const { data, isLoading } = useAdminProducts(page, 20, status)
  const { mutate: updateStatus } = useAdminUpdateProductStatus()
  const toast = useToast()

  const handleStatusChange = (product_id: string, newStatus: string) => {
    updateStatus({ product_id, status: newStatus }, {
      onSuccess: () => toast('Product status updated', 'success'),
      onError: () => toast('Failed to update status', 'error'),
    })
  }

  if (isLoading) return <LoadingSpinner className="py-20" size="lg" />

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Products</h1>

      <div className="flex gap-2 mb-6">
        {STATUSES.map((s) => (
          <button key={s} onClick={() => { setStatus(s || undefined); setPage(1) }}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors capitalize ${
              (status ?? '') === s ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}>
            {s || 'All'}
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
              <th className="text-right px-4 py-3 text-gray-600 font-medium">Change status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data?.items.map((p) => (
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
                <td className="px-4 py-3 text-right">
                  <select value={p.status} onChange={(e) => handleStatusChange(p.id, e.target.value)}
                    className="text-xs border border-gray-300 rounded px-2 py-1 bg-white">
                    <option value="draft">Draft</option>
                    <option value="active">Active</option>
                    <option value="archived">Archived</option>
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data && <Pagination page={page} pages={data.pages} total={data.total} onPageChange={setPage} />}
    </div>
  )
}
