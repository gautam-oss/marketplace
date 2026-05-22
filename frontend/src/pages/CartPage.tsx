import { Link } from 'react-router-dom'
import { useCart, useRemoveCartItem, useUpdateCartItem } from '../hooks/useCart'
import { Trash2, ShoppingBag } from 'lucide-react'
import PriceDisplay from '../components/PriceDisplay'
import LoadingSpinner from '../components/LoadingSpinner'

export default function CartPage() {
  const { data: cart, isLoading } = useCart()
  const { mutate: removeItem } = useRemoveCartItem()
  const { mutate: updateItem } = useUpdateCartItem()

  if (isLoading) return <LoadingSpinner className="py-20" size="lg" />

  if (!cart || cart.items.length === 0) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-20 text-center">
        <ShoppingBag size={72} className="mx-auto text-gray-200 mb-4" />
        <h2 className="text-xl font-semibold text-gray-700 mb-2">Your cart is empty</h2>
        <p className="text-gray-500 text-sm mb-8">Browse products and add something you love.</p>
        <Link to="/products" className="bg-indigo-600 text-white px-6 py-2.5 rounded-xl font-medium hover:bg-indigo-700 transition-colors">
          Start Shopping
        </Link>
      </div>
    )
  }

  const subtotal = cart.subtotal
  const shipping = subtotal > 500 ? 0 : 50
  const gst = Math.round(subtotal * 0.18 * 100) / 100
  const grandTotal = subtotal + shipping + gst

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">
        Cart <span className="text-gray-400 font-normal text-lg">({cart.item_count} items)</span>
      </h1>

      <div className="flex flex-col lg:flex-row gap-8">
        {/* Cart items — 2/3 width */}
        <div className="flex-1 min-w-0 space-y-3">
          {cart.items.map((item) => (
            <div key={item.product_id} className="flex items-center gap-4 bg-white border border-gray-200 rounded-xl p-4">
              <Link to={`/products/${item.product?.slug ?? ''}`} className="w-20 h-20 bg-gray-100 rounded-lg overflow-hidden shrink-0">
                {item.product?.images?.[0] ? (
                  <img src={item.product.images[0]} alt={item.product.title} className="w-full h-full object-cover" />
                ) : (
                  <span className="flex items-center justify-center w-full h-full text-2xl">🛍️</span>
                )}
              </Link>

              <div className="flex-1 min-w-0">
                <Link to={`/products/${item.product?.slug ?? ''}`} className="font-medium text-gray-900 hover:text-indigo-600 transition-colors truncate block">
                  {item.product?.title ?? 'Product'}
                </Link>
                <p className="text-sm text-gray-500 mt-0.5">
                  <PriceDisplay amount={item.product?.price ?? 0} size="sm" /> each
                </p>

                {/* Qty stepper */}
                <div className="flex items-center gap-2 mt-3">
                  <button
                    onClick={() => {
                      if (item.quantity <= 1) removeItem(item.product_id)
                      else updateItem({ product_id: item.product_id, quantity: item.quantity - 1 })
                    }}
                    className="w-7 h-7 rounded-md border border-gray-300 flex items-center justify-center text-gray-600 hover:bg-gray-50 text-lg leading-none"
                  >
                    −
                  </button>
                  <span className="w-8 text-center text-sm font-medium">{item.quantity}</span>
                  <button
                    onClick={() => updateItem({ product_id: item.product_id, quantity: item.quantity + 1 })}
                    className="w-7 h-7 rounded-md border border-gray-300 flex items-center justify-center text-gray-600 hover:bg-gray-50 text-lg leading-none"
                  >
                    +
                  </button>
                </div>
              </div>

              <div className="text-right shrink-0">
                <PriceDisplay amount={(item.product?.price ?? 0) * item.quantity} size="md" />
                <button
                  onClick={() => removeItem(item.product_id)}
                  className="mt-2 text-red-400 hover:text-red-600 transition-colors block"
                  title="Remove"
                >
                  <Trash2 size={15} />
                </button>
              </div>
            </div>
          ))}

          <Link to="/products" className="inline-block text-sm text-indigo-600 hover:underline mt-2">
            ← Continue Shopping
          </Link>
        </div>

        {/* Order summary — 1/3 width, sticky */}
        <div className="lg:w-80 shrink-0">
          <div className="bg-white border border-gray-200 rounded-xl p-6 lg:sticky lg:top-24">
            <h2 className="font-semibold text-gray-900 mb-4">Order Summary</h2>

            <div className="space-y-3 text-sm">
              <div className="flex justify-between text-gray-600">
                <span>Subtotal ({cart.item_count} items)</span>
                <PriceDisplay amount={subtotal} size="sm" />
              </div>
              <div className="flex justify-between text-gray-600">
                <span>Shipping</span>
                {shipping === 0 ? (
                  <span className="text-green-600 font-medium">FREE</span>
                ) : (
                  <PriceDisplay amount={shipping} size="sm" />
                )}
              </div>
              {subtotal > 0 && subtotal <= 500 && (
                <p className="text-xs text-amber-600">
                  Add ₹{(500 - subtotal).toFixed(0)} more for free shipping!
                </p>
              )}
              <div className="flex justify-between text-gray-600">
                <span>GST (18%)</span>
                <PriceDisplay amount={gst} size="sm" />
              </div>
              <div className="border-t pt-3 flex justify-between font-bold text-gray-900 text-base">
                <span>Total</span>
                <PriceDisplay amount={grandTotal} size="lg" />
              </div>
            </div>

            <Link
              to="/checkout"
              className="block w-full mt-5 bg-indigo-600 text-white py-3 rounded-xl font-semibold hover:bg-indigo-700 transition-colors text-center"
            >
              Proceed to Checkout
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
