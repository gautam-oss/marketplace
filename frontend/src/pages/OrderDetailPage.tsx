import { useParams } from 'react-router-dom'
import { Check, X } from 'lucide-react'
import { useOrder } from '../hooks/useOrders'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import PriceDisplay from '../components/PriceDisplay'
import type { OrderResponse } from '../types'

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  paid: 'bg-blue-100 text-blue-800',
  processing: 'bg-blue-100 text-blue-800',
  shipped: 'bg-purple-100 text-purple-800',
  delivered: 'bg-green-100 text-green-800',
  cancelled: 'bg-red-100 text-red-800',
  refunded: 'bg-gray-100 text-gray-800',
}

type StepState = 'done' | 'active' | 'pending'

interface TimelineStep {
  label: string
  ts: string | null
  description?: string
}

function getStepState(idx: number, order: OrderResponse): StepState {
  const isTerminal = order.status === 'cancelled' || order.status === 'refunded'

  if (isTerminal) {
    // For terminal orders, derive completion from timestamps only
    if (idx === 0) return 'done'                                        // created_at always exists
    if (idx === 1) return order.paid_at ? 'done' : 'pending'            // was payment ever made?
    if (idx === 2) return order.shipped_at ? 'done' : 'pending'         // processing done iff shipped
    if (idx === 3) return order.shipped_at ? 'done' : 'pending'         // shipped?
    if (idx === 4) return order.delivered_at ? 'done' : 'pending'       // delivered?
    return 'pending'
  }

  // Normal flow: explicit per-step logic
  // Step 0 — Order Placed: always done (the order exists, we're looking at it)
  if (idx === 0) return 'done'

  // Step 1 — Payment Confirmed: done when paid_at exists; active while awaiting (status=pending)
  if (idx === 1) {
    if (order.paid_at) return 'done'
    if (order.status === 'pending') return 'active'
    return 'pending'
  }

  // Step 2 — Processing: done when shipped; active when paid or processing
  if (idx === 2) {
    if (order.shipped_at) return 'done'
    if (order.status === 'paid' || order.status === 'processing') return 'active'
    return 'pending'
  }

  // Step 3 — Shipped: done when delivered; active when shipped
  if (idx === 3) {
    if (order.delivered_at) return 'done'
    if (order.status === 'shipped') return 'active'
    return 'pending'
  }

  // Step 4 — Delivered: done when delivered
  if (idx === 4) return order.status === 'delivered' ? 'done' : 'pending'

  return 'pending'
}

function fmt(ts: string) {
  return new Date(ts).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
}

function StatusTimeline({ order }: { order: OrderResponse }) {
  const isTerminal = order.status === 'cancelled' || order.status === 'refunded'

  const steps: TimelineStep[] = [
    { label: 'Order Placed', ts: order.created_at },
    { label: 'Payment Confirmed', ts: order.paid_at },
    { label: 'Processing', ts: null, description: 'Seller is preparing your order' },
    { label: 'Shipped', ts: order.shipped_at, description: 'Your order is on the way' },
    { label: 'Delivered', ts: order.delivered_at, description: 'Order delivered successfully' },
  ]

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-6 mb-6">
      <h2 className="font-semibold text-gray-900 mb-6">Order Tracking</h2>
      <ol>
        {steps.map((step, idx) => {
          const state = getStepState(idx, order)
          const isLastNormal = idx === steps.length - 1 && !isTerminal

          return (
            <li key={step.label} className="flex gap-4">
              {/* Circle + connector line */}
              <div className="flex flex-col items-center">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 transition-colors ${
                    state === 'done'
                      ? 'bg-indigo-600'
                      : state === 'active'
                      ? 'bg-indigo-600 ring-4 ring-indigo-100'
                      : 'bg-gray-100'
                  }`}
                >
                  {state === 'done' && <Check size={14} className="text-white" />}
                  {state === 'active' && <div className="w-2.5 h-2.5 rounded-full bg-white" />}
                  {state === 'pending' && <div className="w-2.5 h-2.5 rounded-full bg-gray-300" />}
                </div>
                {!isLastNormal && (
                  <div
                    className={`w-0.5 my-1 ${state === 'done' ? 'bg-indigo-600' : 'bg-gray-200'}`}
                    style={{ minHeight: 28 }}
                  />
                )}
              </div>

              {/* Label + timestamp */}
              <div className={`pb-6 flex-1 ${isLastNormal ? '' : ''}`}>
                <p
                  className={`text-sm font-medium leading-tight ${
                    state !== 'pending' ? 'text-gray-900' : 'text-gray-400'
                  }`}
                >
                  {step.label}
                </p>
                {step.ts && state !== 'pending' && (
                  <p className="text-xs text-gray-500 mt-0.5">{fmt(step.ts)}</p>
                )}
                {state === 'active' && !step.ts && step.description && (
                  <p className="text-xs text-indigo-600 mt-0.5">{step.description}</p>
                )}
              </div>
            </li>
          )
        })}

        {/* Terminal step for cancelled / refunded */}
        {isTerminal && (
          <li className="flex gap-4">
            <div className="flex items-center">
              <div className="w-8 h-8 rounded-full flex items-center justify-center bg-red-100 shrink-0">
                <X size={14} className="text-red-500" />
              </div>
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-red-600 capitalize">{order.status}</p>
              {order.status === 'refunded' && (
                <p className="text-xs text-gray-500 mt-0.5">Refund initiated to original payment method</p>
              )}
            </div>
          </li>
        )}
      </ol>
    </div>
  )
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
        <span
          className={`px-3 py-1 rounded-full text-sm font-medium capitalize ${
            STATUS_COLORS[order.status] ?? 'bg-gray-100 text-gray-800'
          }`}
        >
          {order.status}
        </span>
      </div>

      <StatusTimeline order={order} />

      <div className="bg-white border border-gray-200 rounded-xl p-6 mb-6">
        <h2 className="font-semibold text-gray-900 mb-4">Items</h2>
        <div className="space-y-4">
          {order.items.map((item) => (
            <div key={item.id} className="flex items-center gap-4">
              <div className="w-14 h-14 bg-gray-100 rounded-lg overflow-hidden shrink-0">
                {item.product_image && (
                  <img
                    src={item.product_image}
                    alt={item.product_title}
                    className="w-full h-full object-cover"
                  />
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
            <span>Subtotal</span>
            <PriceDisplay amount={order.subtotal} size="sm" />
          </div>
          <div className="flex justify-between text-gray-600">
            <span>GST (18%)</span>
            <PriceDisplay amount={order.tax_amount} size="sm" />
          </div>
          <div className="flex justify-between text-gray-600">
            <span>Shipping</span>
            <PriceDisplay amount={order.shipping_amount} size="sm" />
          </div>
          <div className="flex justify-between font-semibold text-gray-900 border-t pt-2 mt-2">
            <span>Total</span>
            <PriceDisplay amount={order.total} />
          </div>
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-6">
        <h2 className="font-semibold text-gray-900 mb-3">Shipping address</h2>
        <address className="not-italic text-sm text-gray-600 space-y-1">
          <p>{order.shipping_address.line1}</p>
          {order.shipping_address.line2 && <p>{order.shipping_address.line2}</p>}
          <p>
            {order.shipping_address.city}, {order.shipping_address.state}{' '}
            {order.shipping_address.pincode}
          </p>
          <p>{order.shipping_address.country}</p>
        </address>
      </div>
    </div>
  )
}
