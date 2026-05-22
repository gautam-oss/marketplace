import { useParams } from 'react-router-dom'
import { useOrder } from '../hooks/useOrders'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import PriceDisplay from '../components/PriceDisplay'

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  paid: 'bg-blue-100 text-blue-800',
  processing: 'bg-blue-100 text-blue-800',
  shipped: 'bg-purple-100 text-purple-800',
  delivered: 'bg-green-100 text-green-800',
  cancelled: 'bg-red-100 text-red-800',
  refunded: 'bg-gray-100 text-gray-800',
}

export default function OrderDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: order, isLoading, error } = useOrder(id!)

  if (isLoading) return <LoadingSpinner className="py-20" size="lg" />
  if (error || !order) return <ErrorMessage message="Order not found" />

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">
          Order #{order.id.slice(0, 8).toUpperCase()}
        </h1>
        <span className={`px-3 py-1 rounded-full text-sm font-medium capitalize ${STATUS_COLORS[order.status] ?? 'bg-gray-100 text-gray-800'}`}>
          {order.status}
        </span>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-6 mb-6">
        <h2 className="font-semibold text-gray-900 mb-4">Items</h2>
        <div className="space-y-4">
          {order.items.map((item) => (
            <div key={item.id} className="flex items-center gap-4">
              <div className="w-14 h-14 bg-gray-100 rounded-lg overflow-hidden shrink-0">
                {item.product_image && (
                  <img src={item.product_image} alt={item.product_title} className="w-full h-full object-cover" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900 truncate">{item.product_title}</p>
                <p className="text-sm text-gray-500">Qty: {item.quantity}</p>
              </div>
              <PriceDisplay amount={item.subtotal} />
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-6 mb-6">
        <h2 className="font-semibold text-gray-900 mb-4">Price breakdown</h2>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between text-gray-600">
            <span>Subtotal</span><PriceDisplay amount={order.subtotal} size="sm" />
          </div>
          <div className="flex justify-between text-gray-600">
            <span>GST (18%)</span><PriceDisplay amount={order.tax_amount} size="sm" />
          </div>
          <div className="flex justify-between text-gray-600">
            <span>Shipping</span><PriceDisplay amount={order.shipping_amount} size="sm" />
          </div>
          <div className="flex justify-between font-semibold text-gray-900 border-t pt-2 mt-2">
            <span>Total</span><PriceDisplay amount={order.total} />
          </div>
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-6">
        <h2 className="font-semibold text-gray-900 mb-3">Shipping address</h2>
        <address className="not-italic text-sm text-gray-600 space-y-1">
          <p>{order.shipping_address.line1}</p>
          {order.shipping_address.line2 && <p>{order.shipping_address.line2}</p>}
          <p>{order.shipping_address.city}, {order.shipping_address.state} {order.shipping_address.pincode}</p>
          <p>{order.shipping_address.country}</p>
        </address>
      </div>
    </div>
  )
}
