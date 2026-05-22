import { Link } from 'react-router-dom'
import { useOrders } from '../hooks/useOrders'
import { Package } from 'lucide-react'
import PriceDisplay from '../components/PriceDisplay'
import LoadingSpinner from '../components/LoadingSpinner'

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  paid: 'bg-blue-50 text-blue-700 border-blue-200',
  processing: 'bg-blue-50 text-blue-700 border-blue-200',
  shipped: 'bg-purple-50 text-purple-700 border-purple-200',
  delivered: 'bg-green-50 text-green-700 border-green-200',
  cancelled: 'bg-red-50 text-red-700 border-red-200',
  refunded: 'bg-gray-50 text-gray-700 border-gray-200',
}

export default function OrdersPage() {
  const { data, isLoading } = useOrders()

  if (isLoading) return <LoadingSpinner className="py-20" size="lg" />

  if (!data || data.items.length === 0) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-20 text-center">
        <Package size={64} className="mx-auto text-gray-300 mb-4" />
        <h2 className="text-xl font-semibold text-gray-700">No orders yet</h2>
        <p className="text-gray-500 mt-2">Your orders will appear here after checkout.</p>
        <Link to="/" className="mt-6 inline-block bg-indigo-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors">
          Browse products
        </Link>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">My Orders</h1>

      <div className="space-y-4">
        {data.items.map((order) => (
          <Link key={order.id} to={`/orders/${order.id}`} className="block bg-white border border-gray-200 rounded-xl p-5 hover:shadow-sm transition-shadow">
            <div className="flex items-start justify-between mb-3">
              <div>
                <p className="font-semibold text-gray-900">Order #{order.id.slice(0, 8).toUpperCase()}</p>
                <p className="text-sm text-gray-500 mt-0.5">
                  {new Date(order.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })}
                </p>
              </div>
              <span className={`text-xs font-medium px-2.5 py-1 rounded-full border capitalize ${STATUS_COLORS[order.status] ?? ''}`}>
                {order.status}
              </span>
            </div>

            <div className="text-sm text-gray-600 space-y-1 mb-3">
              {order.items.slice(0, 3).map((item) => (
                <div key={item.id} className="flex justify-between">
                  <span className="truncate flex-1 pr-2">{item.product?.title ?? 'Product'} × {item.quantity}</span>
                  <PriceDisplay amount={item.total_price} size="sm" />
                </div>
              ))}
              {order.items.length > 3 && (
                <p className="text-gray-400 text-xs">+{order.items.length - 3} more items</p>
              )}
            </div>

            <div className="border-t pt-3 flex justify-between text-sm">
              <span className="text-gray-500">Total</span>
              <PriceDisplay amount={order.total} size="md" />
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
