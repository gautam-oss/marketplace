import { useState } from 'react'
import { Link } from 'react-router-dom'
import { CheckCircle } from 'lucide-react'
import { useCart } from '../hooks/useCart'
import { useCheckout } from '../hooks/useOrders'
import { useAuthStore } from '../store/authStore'
import { useToast } from '../components/Toast'
import PriceDisplay from '../components/PriceDisplay'
import LoadingSpinner from '../components/LoadingSpinner'

const INDIAN_STATES = [
  'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
  'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka',
  'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram',
  'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu',
  'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal',
  'Andaman and Nicobar Islands', 'Chandigarh', 'Delhi', 'Jammu and Kashmir',
  'Ladakh', 'Lakshadweep', 'Puducherry',
]

interface AddressForm {
  full_name: string
  phone: string
  line1: string
  line2: string
  city: string
  state: string
  pincode: string
  country: string
}

const EMPTY_ADDRESS: AddressForm = {
  full_name: '', phone: '', line1: '', line2: '',
  city: '', state: '', pincode: '', country: 'India',
}

declare global {
  interface Window {
    Razorpay: new (options: Record<string, unknown>) => { open: () => void }
  }
}

type Step = 1 | 2 | 3

function StepIndicator({ step }: { step: Step }) {
  const steps = ['Address', 'Review & Pay', 'Confirmation']
  return (
    <div className="flex items-center justify-center gap-0 mb-8">
      {steps.map((label, i) => {
        const num = i + 1
        const active = step === num
        const done = step > num
        return (
          <div key={label} className="flex items-center">
            <div className="flex flex-col items-center">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-colors ${
                  done ? 'bg-green-500 text-white' : active ? 'bg-indigo-600 text-white' : 'bg-gray-200 text-gray-500'
                }`}
              >
                {done ? '✓' : num}
              </div>
              <span className={`text-xs mt-1 font-medium ${active ? 'text-indigo-600' : 'text-gray-500'}`}>
                {label}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div className={`w-16 sm:w-24 h-0.5 mx-2 mb-4 ${done ? 'bg-green-400' : 'bg-gray-200'}`} />
            )}
          </div>
        )
      })}
    </div>
  )
}

export default function CheckoutPage() {
  const [step, setStep] = useState<Step>(1)
  const [address, setAddress] = useState<AddressForm>(EMPTY_ADDRESS)
  const [orderId, setOrderId] = useState<string | null>(null)
  const [paymentPending, setPaymentPending] = useState(false)

  const { data: cart } = useCart()
  const { mutateAsync: checkout } = useCheckout()
  const { user } = useAuthStore()
  const toast = useToast()

  const items = cart?.items ?? []
  const subtotal = cart?.total ?? 0
  const shipping = subtotal > 500 ? 0 : 50
  const gst = Math.round(subtotal * 0.18 * 100) / 100
  const total = subtotal + shipping + gst

  const handleAddressSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!/^\d{10}$/.test(address.phone)) { toast('Enter a valid 10-digit phone number', 'error'); return }
    if (!/^\d{6}$/.test(address.pincode)) { toast('Enter a valid 6-digit pincode', 'error'); return }
    setStep(2)
  }

  const handlePay = async () => {
    if (!items.length) return
    setPaymentPending(true)
    try {
      const result = await checkout({
        items: items.map((i) => ({ product_id: i.product_id, quantity: i.quantity })),
        shipping_address: {
          full_name: address.full_name,
          phone: address.phone,
          line1: address.line1,
          line2: address.line2 || undefined,
          city: address.city,
          state: address.state,
          pincode: address.pincode,
          country: address.country,
        },
      })

      const rzp = new window.Razorpay({
        key: result.razorpay_key_id,
        amount: result.amount,
        currency: result.currency,
        name: 'Marketplace',
        description: `Order #${result.order_id.slice(0, 8).toUpperCase()}`,
        order_id: result.razorpay_order_id,
        prefill: { name: user?.full_name ?? '', email: user?.email ?? '' },
        theme: { color: '#4F46E5' },
        handler: () => {
          setOrderId(result.order_id)
          setStep(3)
          setPaymentPending(false)
        },
        modal: {
          ondismiss: () => {
            setPaymentPending(false)
            toast('Payment cancelled', 'info')
          },
        },
      })
      rzp.open()
    } catch {
      setPaymentPending(false)
      toast('Checkout failed. Please try again.', 'error')
    }
  }

  const setField = (field: keyof AddressForm) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setAddress((a) => ({ ...a, [field]: e.target.value }))

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6 text-center">Checkout</h1>
      <StepIndicator step={step} />

      {/* ── Step 1: Shipping Address ── */}
      {step === 1 && (
        <form onSubmit={handleAddressSubmit} className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
          <h2 className="font-semibold text-gray-900 mb-2">Shipping Address</h2>

          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Full Name <span className="text-red-500">*</span></label>
              <input required type="text" value={address.full_name} onChange={setField('full_name')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Phone (10 digits) <span className="text-red-500">*</span></label>
              <input required type="tel" maxLength={10} value={address.phone} onChange={setField('phone')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Address Line 1 <span className="text-red-500">*</span></label>
            <input required type="text" value={address.line1} onChange={setField('line1')}
              placeholder="House/Flat no., Building, Street"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Address Line 2 (optional)</label>
            <input type="text" value={address.line2} onChange={setField('line2')}
              placeholder="Area, Landmark"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">City <span className="text-red-500">*</span></label>
              <input required type="text" value={address.city} onChange={setField('city')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">State <span className="text-red-500">*</span></label>
              <select required value={address.state} onChange={setField('state')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white">
                <option value="">Select state</option>
                {INDIAN_STATES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Pincode (6 digits) <span className="text-red-500">*</span></label>
              <input required type="text" maxLength={6} value={address.pincode} onChange={setField('pincode')}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Country</label>
              <input type="text" value="India" readOnly
                className="w-full px-3 py-2 border border-gray-200 bg-gray-50 rounded-lg text-sm text-gray-500" />
            </div>
          </div>

          <button type="submit"
            className="w-full bg-indigo-600 text-white py-3 rounded-xl font-semibold hover:bg-indigo-700 transition-colors mt-2">
            Continue to Payment
          </button>
        </form>
      )}

      {/* ── Step 2: Review & Pay ── */}
      {step === 2 && (
        <div className="space-y-4">
          <div className="bg-white border border-gray-200 rounded-xl p-6">
            <h2 className="font-semibold text-gray-900 mb-4">Order Summary</h2>
            <div className="space-y-3 mb-4">
              {items.map((item) => (
                <div key={item.product_id} className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-gray-100 rounded-lg overflow-hidden shrink-0">
                    {item.product?.images?.[0] && (
                      <img src={item.product.images[0]} alt={item.product.title} className="w-full h-full object-cover" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{item.product?.title}</p>
                    <p className="text-xs text-gray-500">Qty: {item.quantity}</p>
                  </div>
                  <PriceDisplay amount={(item.product?.price ?? 0) * item.quantity} size="sm" />
                </div>
              ))}
            </div>
            <div className="border-t pt-4 space-y-2 text-sm">
              <div className="flex justify-between text-gray-600"><span>Subtotal</span><PriceDisplay amount={subtotal} size="sm" /></div>
              <div className="flex justify-between text-gray-600">
                <span>Shipping</span>
                {shipping === 0 ? <span className="text-green-600 font-medium">FREE</span> : <PriceDisplay amount={shipping} size="sm" />}
              </div>
              <div className="flex justify-between text-gray-600"><span>GST (18%)</span><PriceDisplay amount={gst} size="sm" /></div>
              <div className="flex justify-between font-bold text-gray-900 text-base border-t pt-2">
                <span>Total</span><PriceDisplay amount={total} size="lg" />
              </div>
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-xl p-5 text-sm text-gray-600">
            <p className="font-medium text-gray-900 mb-1">Delivering to</p>
            <p>{address.full_name} · {address.phone}</p>
            <p>{address.line1}{address.line2 && `, ${address.line2}`}</p>
            <p>{address.city}, {address.state} {address.pincode}</p>
            <button onClick={() => setStep(1)} className="text-indigo-600 text-xs hover:underline mt-1">
              Change address
            </button>
          </div>

          <div className="flex gap-3">
            <button onClick={() => setStep(1)}
              className="flex-1 py-3 border border-gray-300 rounded-xl text-sm font-medium hover:bg-gray-50 transition-colors">
              Back
            </button>
            <button
              onClick={handlePay}
              disabled={paymentPending}
              className="flex-[2] bg-indigo-600 text-white py-3 rounded-xl font-bold hover:bg-indigo-700 disabled:opacity-60 transition-colors flex items-center justify-center gap-2"
            >
              {paymentPending ? <LoadingSpinner size="sm" /> : null}
              {paymentPending ? 'Opening payment...' : `Pay ₹${Math.round(total).toLocaleString('en-IN')} with Razorpay`}
            </button>
          </div>
        </div>
      )}

      {/* ── Step 3: Confirmation ── */}
      {step === 3 && orderId && (
        <div className="bg-white border border-gray-200 rounded-xl p-10 text-center">
          <div className="flex justify-center mb-4">
            <CheckCircle size={64} className="text-green-500" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Payment Successful!</h2>
          <p className="text-gray-500 mb-1">Order Confirmed</p>
          <p className="font-mono text-indigo-600 font-bold text-lg mb-1">
            #{orderId.slice(0, 8).toUpperCase()}
          </p>
          <p className="text-sm text-gray-500 mb-8">Estimated delivery: 5-7 business days</p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link
              to={`/orders/${orderId}`}
              className="bg-indigo-600 text-white px-6 py-2.5 rounded-xl font-medium hover:bg-indigo-700 transition-colors"
            >
              Track Order
            </Link>
            <Link
              to="/"
              className="border border-gray-300 px-6 py-2.5 rounded-xl font-medium hover:bg-gray-50 transition-colors text-gray-700"
            >
              Continue Shopping
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}
