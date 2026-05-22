import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAdminOrders } from '../hooks/useAdmin'
import LoadingSpinner from '../components/LoadingSpinner'
import Pagination from '../components/Pagination'
import PriceDisplay from '../components/PriceDisplay'

const STATUS_OPTIONS = ['', 'pending', 'paid', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded']

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  paid: 'bg-blue-100 text-blue-800',
  processing: 'bg-blue-100 text-blue-800',
  shipped: 'bg-purple-100 text-purple-800',
  delivered: 'bg-green-100 text-green-800',
  cancelled: 'bg-red-100 text-red-800',
  refunded: 'bg-gray-100 text-gray-800',
}

export default function AdminOrdersPage() {
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState<string | undefined>()
  const { data, isLoading } = useAdminOrders(page, 20, status)

  if (isLoading) return <LoadingSpinner className="py-20" size="lg" />

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Orders</h1>

      <div className="flex gap-2 flex-wrap mb-6">
        {STATUS_OPTIONS.map((s) => (
          <button key={s} onClick={() => { setStatus(s || undefined); setPage(1) }}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors capitalize ${
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
              <th className="text-left px-4 py-3 text-gray-600 font-medium">Order ID</th>
              <th className="text-left px-4 py-3 text-gray-600 font-medium">Buyer</th>
              <th className="text-left px-4 py-3 text-gray-600 font-medium">Total</th>
              <th className="text-left px-4 py-3 text-gray-600 font-medium">Status</th>
              <th className="text-left px-4 py-3 text-gray-600 font-medium">Date</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data?.items.map((o) => (
              <tr key={o.id} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  <Link to={`/orders/${o.id}`} className="font-mono text-indigo-600 hover:underline text-xs">
                    #{o.id.slice(0, 8).toUpperCase()}
                  </Link>
                </td>
                <td className="px-4 py-3 text-gray-600">{o.buyer?.full_name ?? '—'}</td>
                <td className="px-4 py-3"><PriceDisplay amount={o.total} size="sm" /></td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${STATUS_COLORS[o.status] ?? ''}`}>
                    {o.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-500">{new Date(o.created_at).toLocaleDateString('en-IN')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data && <Pagination page={page} pages={data.pages} total={data.total} onPageChange={setPage} />}
    </div>
  )
}
