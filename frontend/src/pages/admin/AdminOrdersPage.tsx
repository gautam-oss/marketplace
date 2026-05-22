import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronRight, XCircle } from 'lucide-react'
import { useAdminOrders, useAdminUpdateOrderStatus, useAdminCancelOrder } from '../../hooks/useAdmin'
import LoadingSpinner from '../../components/LoadingSpinner'
import Pagination from '../../components/Pagination'
import PriceDisplay from '../../components/PriceDisplay'
import { useToast } from '../../components/Toast'
import type { OrderStatus } from '../../types'

const STATUS_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'pending', label: 'Pending' },
  { value: 'paid', label: 'Paid' },
  { value: 'processing', label: 'Processing' },
  { value: 'shipped', label: 'Shipped' },
  { value: 'delivered', label: 'Delivered' },
  { value: 'cancelled', label: 'Cancelled' },
  { value: 'refunded', label: 'Refunded' },
]

const STATUS_BADGE: Record<OrderStatus, string> = {
  pending:    'bg-yellow-100 text-yellow-800',
  paid:       'bg-blue-100 text-blue-800',
  processing: 'bg-indigo-100 text-indigo-800',
  shipped:    'bg-purple-100 text-purple-800',
  delivered:  'bg-green-100 text-green-800',
  cancelled:  'bg-red-100 text-red-800',
  refunded:   'bg-gray-100 text-gray-800',
}

const NEXT_STATUS: Partial<Record<OrderStatus, string>> = {
  paid:       'processing',
  processing: 'shipped',
  shipped:    'delivered',
}

const NEXT_LABEL: Partial<Record<OrderStatus, string>> = {
  paid:       'Mark Processing',
  processing: 'Mark Shipped',
  shipped:    'Mark Delivered',
}

const CANCELABLE: OrderStatus[] = ['pending', 'paid', 'processing', 'shipped']

export default function AdminOrdersPage() {
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState<string | undefined>()
  const { data, isLoading } = useAdminOrders(page, 20, status)
  const { mutate: updateStatus, isPending: advancing } = useAdminUpdateOrderStatus()
  const { mutate: cancelOrder, isPending: cancelling } = useAdminCancelOrder()
  const navigate = useNavigate()
  const toast = useToast()

  const handleAdvance = (e: React.MouseEvent, order_id: string, next: string) => {
    e.stopPropagation()
    updateStatus(
      { order_id, status: next },
      {
        onSuccess: () => toast(`Order marked as ${next}`, 'success'),
        onError:   () => toast('Failed to update order status', 'error'),
      }
    )
  }

  const handleCancel = (e: React.MouseEvent, order_id: string) => {
    e.stopPropagation()
    if (!confirm('Cancel this order? This cannot be undone.')) return
    cancelOrder(order_id, {
      onSuccess: () => toast('Order cancelled', 'success'),
      onError:   () => toast('Failed to cancel order', 'error'),
    })
  }

  if (isLoading) return <LoadingSpinner className="py-20" size="lg" />

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Orders</h1>

      <div className="flex gap-2 flex-wrap mb-6">
        {STATUS_OPTIONS.map((s) => (
          <button
            key={s.value}
            onClick={() => { setStatus(s.value || undefined); setPage(1) }}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
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
              <th className="text-left px-4 py-3 text-gray-600 font-medium">Order</th>
              <th className="text-left px-4 py-3 text-gray-600 font-medium">Buyer</th>
              <th className="text-left px-4 py-3 text-gray-600 font-medium">Items</th>
              <th className="text-left px-4 py-3 text-gray-600 font-medium">Total</th>
              <th className="text-left px-4 py-3 text-gray-600 font-medium">Status</th>
              <th className="text-left px-4 py-3 text-gray-600 font-medium">Date</th>
              <th className="text-right px-4 py-3 text-gray-600 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data?.items.map((o) => {
              const next = NEXT_STATUS[o.status as OrderStatus]
              const nextLabel = NEXT_LABEL[o.status as OrderStatus]
              const canCancel = CANCELABLE.includes(o.status as OrderStatus)
              return (
                <tr
                  key={o.id}
                  onClick={() => navigate(`/orders/${o.id}`)}
                  className="hover:bg-gray-50 cursor-pointer transition-colors"
                >
                  <td className="px-4 py-3">
                    <span className="font-mono text-xs text-indigo-600 font-medium">
                      #{o.id.slice(0, 8).toUpperCase()}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-700">{o.buyer?.full_name ?? '—'}</td>
                  <td className="px-4 py-3 text-gray-600">
                    {o.items.length} item{o.items.length !== 1 ? 's' : ''}
                  </td>
                  <td className="px-4 py-3">
                    <PriceDisplay amount={o.total} size="sm" />
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${STATUS_BADGE[o.status as OrderStatus]}`}>
                      {o.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {new Date(o.created_at).toLocaleDateString('en-IN')}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1" onClick={(e) => e.stopPropagation()}>
                      {next && nextLabel && (
                        <button
                          onClick={(e) => handleAdvance(e, o.id, next)}
                          disabled={advancing}
                          className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-indigo-700 bg-indigo-50 hover:bg-indigo-100 rounded-lg transition-colors disabled:opacity-50"
                        >
                          <ChevronRight size={12} />
                          {nextLabel}
                        </button>
                      )}
                      {canCancel && (
                        <button
                          onClick={(e) => handleCancel(e, o.id)}
                          disabled={cancelling}
                          className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-red-700 bg-red-50 hover:bg-red-100 rounded-lg transition-colors disabled:opacity-50"
                        >
                          <XCircle size={12} />
                          Cancel
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {data?.items.length === 0 && (
          <p className="text-sm text-gray-400 text-center py-8">No orders found.</p>
        )}
      </div>

      {data && <Pagination page={page} pages={data.pages} total={data.total} onPageChange={setPage} />}
    </div>
  )
}
