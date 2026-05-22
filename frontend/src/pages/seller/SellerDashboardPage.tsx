import { Link } from 'react-router-dom'
import { Plus, ShoppingCart, TrendingUp, Package, ArrowRight } from 'lucide-react'
import { useMyProducts } from '../../hooks/useProducts'
import { useOrders } from '../../hooks/useOrders'
import LoadingSpinner from '../../components/LoadingSpinner'
import PriceDisplay from '../../components/PriceDisplay'
import type { OrderStatus } from '../../types'

const STATUS_COLORS: Record<OrderStatus, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  paid: 'bg-blue-100 text-blue-800',
  processing: 'bg-indigo-100 text-indigo-800',
  shipped: 'bg-purple-100 text-purple-800',
  delivered: 'bg-green-100 text-green-800',
  cancelled: 'bg-red-100 text-red-800',
  refunded: 'bg-gray-100 text-gray-800',
}

const REVENUE_STATUSES: OrderStatus[] = ['paid', 'processing', 'shipped', 'delivered']

export default function SellerDashboardPage() {
  const { data: products, isLoading: loadingProducts } = useMyProducts(1, 100)
  const { data: orders, isLoading: loadingOrders } = useOrders(1)

  if (loadingProducts || loadingOrders) return <LoadingSpinner className="py-20" size="lg" />

  const totalProducts = products?.total ?? 0
  const activeProducts = products?.items.filter((p) => p.status === 'active').length ?? 0

  const now = new Date()
  const thisMonthOrders = (orders?.items ?? []).filter((o) => {
    const d = new Date(o.created_at)
    return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear()
  })
  const revenueThisMonth = thisMonthOrders
    .filter((o) => REVENUE_STATUSES.includes(o.status))
    .reduce((sum, o) => sum + o.total, 0)

  const recentOrders = orders?.items.slice(0, 5) ?? []
  const topProducts = products?.items.slice(0, 5) ?? []

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Seller Dashboard</h1>
        <Link
          to="/seller/products/new"
          className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
        >
          <Plus size={16} />
          Add Product
        </Link>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {[
          { label: 'Total Products', icon: <Package size={20} />, color: 'bg-indigo-50 text-indigo-600', content: <p className="text-2xl font-bold text-gray-900">{totalProducts.toLocaleString('en-IN')}</p> },
          { label: 'Active Listings', icon: <TrendingUp size={20} />, color: 'bg-green-50 text-green-600', content: <p className="text-2xl font-bold text-gray-900">{activeProducts.toLocaleString('en-IN')}</p> },
          { label: 'Orders This Month', icon: <ShoppingCart size={20} />, color: 'bg-purple-50 text-purple-600', content: <p className="text-2xl font-bold text-gray-900">{thisMonthOrders.length.toLocaleString('en-IN')}</p> },
          { label: 'Revenue This Month', icon: <TrendingUp size={20} />, color: 'bg-amber-50 text-amber-600', content: <PriceDisplay amount={revenueThisMonth} size="lg" /> },
        ].map((s) => (
          <div key={s.label} className="bg-white border border-gray-200 rounded-xl p-5">
            <div className={`inline-flex p-2 rounded-lg ${s.color} mb-3`}>{s.icon}</div>
            {s.content}
            <p className="text-sm text-gray-500 mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Recent Orders */}
        <div className="bg-white border border-gray-200 rounded-xl">
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-900">Recent Orders</h2>
            <Link to="/orders" className="text-xs text-indigo-600 hover:underline flex items-center gap-1">
              View all <ArrowRight size={12} />
            </Link>
          </div>
          {recentOrders.length === 0 ? (
            <p className="text-sm text-gray-500 p-6 text-center">No orders yet</p>
          ) : (
            <div className="divide-y divide-gray-100">
              {recentOrders.map((o) => (
                <div key={o.id} className="flex items-center justify-between px-6 py-3 hover:bg-gray-50">
                  <div>
                    <p className="font-mono text-xs text-indigo-600 font-medium">
                      #{o.id.slice(0, 8).toUpperCase()}
                    </p>
                    <p className="text-xs text-gray-500">
                      {(o.items ?? []).length} item{(o.items ?? []).length !== 1 ? 's' : ''} · {new Date(o.created_at).toLocaleDateString('en-IN')}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <PriceDisplay amount={o.total} size="sm" />
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${STATUS_COLORS[o.status]}`}>
                      {o.status}
                    </span>
                    <Link to={`/orders/${o.id}`} className="text-gray-400 hover:text-indigo-600 transition-colors">
                      <ArrowRight size={14} />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Top Products */}
        <div className="bg-white border border-gray-200 rounded-xl">
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-900">Your Products</h2>
            <Link to="/seller/products" className="text-xs text-indigo-600 hover:underline flex items-center gap-1">
              Manage <ArrowRight size={12} />
            </Link>
          </div>
          {topProducts.length === 0 ? (
            <div className="p-6 text-center">
              <p className="text-sm text-gray-500 mb-3">No products yet.</p>
              <Link to="/seller/products/new" className="text-sm text-indigo-600 hover:underline">
                Add your first product
              </Link>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {topProducts.map((p) => (
                <div key={p.id} className="flex items-center gap-3 px-6 py-3 hover:bg-gray-50">
                  <div className="w-10 h-10 bg-gray-100 rounded-lg overflow-hidden shrink-0">
                    {p.images?.[0] && (
                      <img src={p.images[0]} alt={p.title} className="w-full h-full object-cover" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{p.title}</p>
                    <PriceDisplay amount={p.price} size="sm" />
                  </div>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize shrink-0 ${
                    p.status === 'active' ? 'bg-green-100 text-green-700' :
                    p.status === 'archived' ? 'bg-red-100 text-red-700' :
                    'bg-gray-100 text-gray-600'
                  }`}>
                    {p.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Quick actions */}
      <div className="flex gap-3 mt-6">
        <Link
          to="/seller/products/new"
          className="flex items-center gap-2 bg-indigo-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium hover:bg-indigo-700 transition-colors"
        >
          <Plus size={16} />
          Add New Product
        </Link>
        <Link
          to="/orders"
          className="flex items-center gap-2 border border-gray-300 px-5 py-2.5 rounded-xl text-sm font-medium hover:bg-gray-50 transition-colors text-gray-700"
        >
          <ShoppingCart size={16} />
          View All Orders
        </Link>
      </div>
    </div>
  )
}
